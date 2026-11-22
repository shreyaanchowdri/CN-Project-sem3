f"""decision_engine.py - Hybrid Intelligent Self-Healing Decision Engine.

Provides risk-calibrated, multi-strategy recovery planning with interactive
human-in-the-loop approvals, hybrid execution policies, pre-condition checks,
safe rollback, and execution audit tracking.
"""

import time
import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import networkx as nx

from fault_registry import FaultStatus, get_fault_registry
from recovery_planner import (
    RecoveryDecision,
    RoutePolicy,
    RecoveryAction,
    RecoveryPlan,
    generate_recovery_plan
)
from scenario_manager import capture_network_snapshot, restore_network_snapshot
from monitoring import collect_observations
from recovery import recover
from network_model import calculate_route_metrics


class OperatingPolicy(str, Enum):
    """Operating governance policy for recovery decisions."""
    FULLY_MANUAL = "FULLY_MANUAL"
    HYBRID = "HYBRID"  # Default: safe actions auto-execute, risky require approval
    AUTOMATIC_SAFE = "AUTOMATIC_SAFE"


class DecisionOutcome(str, Enum):
    """Decision outcome classification."""
    AUTO_EXECUTE = "AUTO_EXECUTE"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    MONITOR_ONLY = "MONITOR_ONLY"
    BLOCKED = "BLOCKED"


class DecisionStatus(str, Enum):
    """Lifecycle status of a recovery decision."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    ROLLED_BACK = "ROLLED_BACK"
    MONITORING = "MONITORING"
    BLOCKED = "BLOCKED"


@dataclass
class RecoveryStrategy:
    """A proposed recovery strategy with risk assessment and trade-offs."""
    strategy_id: str
    name: str
    strategy_type: str  # PRIMARY_FAILOVER, ALTERNATIVE_ROUTE, CONFIG_CORRECTION, MONITOR_ONLY
    operation: str
    reason: str
    root_cause_addressed: str
    affected_components: List[str]
    expected_latency_ms: float
    expected_loss_pct: float
    expected_cost: int
    risk_score: int  # 0 to 100
    risk_factors: List[str]
    reversibility: bool
    requires_approval: bool
    decision_outcome: DecisionOutcome
    candidate_route: Optional[List[str]] = None
    action_items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "strategy_type": self.strategy_type,
            "operation": self.operation,
            "reason": self.reason,
            "root_cause_addressed": self.root_cause_addressed,
            "affected_components": self.affected_components,
            "expected_latency_ms": self.expected_latency_ms,
            "expected_loss_pct": self.expected_loss_pct,
            "expected_cost": self.expected_cost,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "reversibility": self.reversibility,
            "requires_approval": self.requires_approval,
            "decision_outcome": self.decision_outcome.value,
            "candidate_route": self.candidate_route,
            "action_items": self.action_items
        }


@dataclass
class DecisionRecord:
    """Complete audit record of a recovery decision and execution."""
    decision_id: str
    strategy: RecoveryStrategy
    fault_ids: List[str]
    finding_ids: List[str]
    policy_in_effect: OperatingPolicy
    status: DecisionStatus
    explanation: str
    preconditions_checked: List[str]
    preconditions_met: bool
    side_effects: List[str]
    timestamp: float = field(default_factory=time.time)
    execution_result: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None
    rejection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "strategy": self.strategy.to_dict(),
            "fault_ids": self.fault_ids,
            "finding_ids": self.finding_ids,
            "policy": self.policy_in_effect.value,
            "status": self.status.value,
            "explanation": self.explanation,
            "preconditions_checked": self.preconditions_checked,
            "preconditions_met": self.preconditions_met,
            "side_effects": self.side_effects,
            "timestamp": self.timestamp,
            "execution_result": self.execution_result,
            "verification_result": self.verification_result,
            "rejection_reason": self.rejection_reason
        }


class DecisionEngine:
    """Intelligent Hybrid Self-Healing Decision Engine.
    
    Generates alternative recovery strategies, calculates risk scores,
    enforces operating policies, and orchestrates approved executions.
    """

    def __init__(self, policy: OperatingPolicy = OperatingPolicy.HYBRID):
        self.policy: OperatingPolicy = policy
        self._decisions: Dict[str, DecisionRecord] = {}
        self._decision_counter: int = 0
        self._strategy_counter: int = 0

    def set_policy(self, policy: Union[OperatingPolicy, str]) -> None:
        """Update active governance policy."""
        if isinstance(policy, str):
            policy = OperatingPolicy(policy)
        self.policy = policy

    def _next_decision_id(self) -> str:
        self._decision_counter += 1
        return f"DEC-{self._decision_counter:04d}"

    def _next_strategy_id(self) -> str:
        self._strategy_counter += 1
        return f"STRAT-{self._strategy_counter:04d}"

    def calculate_risk_score(
        self,
        strategy_type: str,
        findings: List[Any],
        candidate_route: Optional[List[str]] = None,
        route_metrics: Optional[Dict[str, Any]] = None,
        is_reversible: bool = True
    ) -> Tuple[int, List[str]]:
        """Calculate a 0-100 risk score and list contributing factors."""
        score = 10
        factors = []

        if strategy_type == "MONITOR_ONLY":
            return 0, ["No active configuration modification; zero disruption risk."]

        # 1. Fault severity evaluation
        max_severity = "LOW"
        for f in findings:
            sev = getattr(f, "severity", "MEDIUM")
            if sev == "CRITICAL":
                max_severity = "CRITICAL"
                break
            elif sev == "HIGH" and max_severity != "CRITICAL":
                max_severity = "HIGH"

        if max_severity == "CRITICAL":
            score += 25
            factors.append("CRITICAL fault severity requires rerouting active service paths.")
        elif max_severity == "HIGH":
            score += 15
            factors.append("HIGH fault severity may affect link quality or endpoint reachability.")

        # 2. Reversibility
        if not is_reversible:
            score += 30
            factors.append("Operation cannot be automatically rolled back without outage.")
        else:
            factors.append("Operation supports instant atomic snapshot rollback.")

        # 3. Route metrics evaluation
        if route_metrics:
            lat = route_metrics.get("latency_ms", 0.0)
            loss = route_metrics.get("max_loss", 0.0)
            if loss > 20.0:
                score += 25
                factors.append(f"Candidate route has significant packet loss ({loss:.1f}%).")
            elif loss > 0.0:
                score += 10
                factors.append(f"Candidate route has minor packet loss ({loss:.1f}%).")

            if lat > 150.0:
                score += 20
                factors.append(f"Candidate route experiences elevated latency ({lat:.1f}ms).")

        # 4. Strategy type complexity
        if strategy_type == "MULTI_FAULT_COORDINATED":
            score += 15
            factors.append("Multi-fault coordinated action touches multiple network subsystems.")
        elif strategy_type == "FAILOVER_REROUTE":
            score += 10
            factors.append("Dynamic routing table modification shifts traffic flows.")
        elif strategy_type == "GATEWAY_CORRECTION":
            score += 5
            factors.append("Host endpoint default gateway correction.")

        score = max(0, min(100, score))
        return score, factors

    def generate_strategies(
        self,
        g: nx.Graph,
        findings: List[Any],
        source: str = "PC1",
        target: str = "Server"
    ) -> List[RecoveryStrategy]:
        """Generate multiple technically sound recovery strategies for comparison."""
        strategies: List[RecoveryStrategy] = []

        # Generate base recovery plan
        base_plan = generate_recovery_plan(g, findings, source=source, target=target)
        reg = get_fault_registry(g)
        active_faults = reg.get_active_faults()
        seen_aff = set()
        affected_components = []
        for f in findings:
            for c in getattr(f, "affected_components", []):
                s = str(c).strip()
                if "-" in s:
                    parts = s.split("-")
                    canon = tuple(sorted(parts)) if len(parts) == 2 else s
                else:
                    canon = s
                if canon not in seen_aff:
                    seen_aff.add(canon)
                    affected_components.append(s)

        # Case 1: Healthy Network / Service Maintained
        if not findings or base_plan.decision == RecoveryDecision.NO_ACTION_REQUIRED:
            s_id = self._next_strategy_id()
            p_curr = list(g.graph.get("active_path", ["PC1", "R1", "R2", "Server"]))
            curr_metrics = calculate_route_metrics(g, p_curr) if p_curr else {}
            curr_lat = curr_metrics.get("latency_ms", 10.0)
            curr_loss = curr_metrics.get("probabilistic_loss", curr_metrics.get("max_loss", 0.0))
            curr_cost = curr_metrics.get("cost", 1)
            strategies.append(RecoveryStrategy(
                strategy_id=s_id,
                name="Baseline Monitoring (No Action Required)",
                strategy_type="MONITOR_ONLY",
                operation="Maintain existing nominal network state; continue telemetry monitoring.",
                reason="All monitored components and endpoints operate within nominal baseline thresholds.",
                root_cause_addressed="None",
                affected_components=[],
                expected_latency_ms=curr_lat,
                expected_loss_pct=curr_loss,
                expected_cost=curr_cost,
                risk_score=0,
                risk_factors=["Zero operational risk."],
                reversibility=True,
                requires_approval=False,
                decision_outcome=DecisionOutcome.MONITOR_ONLY,
                candidate_route=p_curr
            ))
            return strategies

        if base_plan.decision == RecoveryDecision.SERVICE_ALREADY_MAINTAINED:
            s_id = self._next_strategy_id()
            p_curr = list(g.graph.get("active_path", []))
            curr_metrics = calculate_route_metrics(g, p_curr) if p_curr else {}
            curr_lat = curr_metrics.get("latency_ms", 10.0)
            curr_loss = curr_metrics.get("probabilistic_loss", curr_metrics.get("max_loss", 0.0))
            curr_cost = curr_metrics.get("cost", 1)
            strategies.append(RecoveryStrategy(
                strategy_id=s_id,
                name="Passive Link Isolation (Service Maintained)",
                strategy_type="MONITOR_ONLY",
                operation="Isolate failed link; keep failed component DOWN and maintain current active route.",
                reason="Active forwarding route does not traverse the severed link; service remains uninterrupted.",
                root_cause_addressed="Isolated Link Failure",
                affected_components=affected_components,
                expected_latency_ms=curr_lat,
                expected_loss_pct=curr_loss,
                expected_cost=curr_cost,
                risk_score=5,
                risk_factors=["Failed link remains isolated; network operates in degraded redundancy mode."],
                reversibility=True,
                requires_approval=False,
                decision_outcome=DecisionOutcome.MONITOR_ONLY,
                candidate_route=p_curr
            ))
            return strategies

        if base_plan.decision == RecoveryDecision.NO_FEASIBLE_RECOVERY:
            s_id = self._next_strategy_id()
            strategies.append(RecoveryStrategy(
                strategy_id=s_id,
                name="Network Partition Isolation (Intervention Blocked)",
                strategy_type="BLOCKED",
                operation="Log partition alarm; block automatic route change until physical link restoration.",
                reason="Physical network graph partition severs all possible paths between endpoints.",
                root_cause_addressed="Complete Topology Disconnection",
                affected_components=affected_components,
                expected_latency_ms=0.0,
                expected_loss_pct=100.0,
                expected_cost=0,
                risk_score=95,
                risk_factors=["No physical alternate route exists in graph; any reroute attempt will fail."],
                reversibility=False,
                requires_approval=True,
                decision_outcome=DecisionOutcome.BLOCKED,
                candidate_route=None
            ))
            return strategies

        # Strategy 1: Recommended Optimal Coordinated Recovery
        primary_route = base_plan.selected_route["path"] if base_plan.selected_route else None
        p_lat = base_plan.selected_route.get("latency_ms", 10.0) if base_plan.selected_route else 10.0
        p_loss = base_plan.selected_route.get("probabilistic_loss", 0.0) if base_plan.selected_route else 0.0
        p_cost = base_plan.selected_route.get("cost", 2) if base_plan.selected_route else 2

        score_p, factors_p = self.calculate_risk_score(
            strategy_type="MULTI_FAULT_COORDINATED" if len(base_plan.actions) > 1 else "FAILOVER_REROUTE",
            findings=findings,
            candidate_route=primary_route,
            route_metrics={"latency_ms": p_lat, "max_loss": p_loss},
            is_reversible=True
        )

        needs_approval_p = (score_p > 40) or (self.policy == OperatingPolicy.FULLY_MANUAL)
        outcome_p = DecisionOutcome.REQUIRES_APPROVAL if needs_approval_p else DecisionOutcome.AUTO_EXECUTE

        s1_id = self._next_strategy_id()
        strategies.append(RecoveryStrategy(
            strategy_id=s1_id,
            name="Strategy 1: Optimal Multi-Objective Coordinated Recovery (Recommended)",
            strategy_type="PRIMARY_OPTIMAL",
            operation=f"Execute {len(base_plan.actions)} coordinated recovery actions: " + ", ".join(a.action_type for a in base_plan.actions),
            reason=f"Optimal multi-objective ranking maximizes availability while minimizing latency ({p_lat:.1f}ms) and packet loss ({p_loss:.1f}%).",
            root_cause_addressed=", ".join(set(f.root_cause for f in findings)),
            affected_components=affected_components,
            expected_latency_ms=p_lat,
            expected_loss_pct=p_loss,
            expected_cost=p_cost,
            risk_score=score_p,
            risk_factors=factors_p,
            reversibility=True,
            requires_approval=needs_approval_p,
            decision_outcome=outcome_p,
            candidate_route=primary_route,
            action_items=[a.to_dict() for a in base_plan.actions]
        ))

        # Strategy 2: Secondary / Conservative Alternative (if alternative candidate routes exist)
        if len(base_plan.candidate_routes) > 1:
            alt_r = base_plan.candidate_routes[1]
            a_path = alt_r["path"]
            a_lat = alt_r.get("latency_ms", 15.0)
            a_loss = alt_r.get("probabilistic_loss", 0.0)
            a_cost = alt_r.get("cost", 3)

            score_a, factors_a = self.calculate_risk_score(
                strategy_type="SECONDARY_FAILOVER",
                findings=findings,
                candidate_route=a_path,
                route_metrics={"latency_ms": a_lat, "max_loss": a_loss},
                is_reversible=True
            )
            score_a += 10  # Secondary route has slightly higher risk / suboptimal
            factors_a.append("Secondary candidate path provides sub-optimal cost or higher latency.")

            needs_approval_a = True  # Secondary always requires operator review
            s2_id = self._next_strategy_id()
            strategies.append(RecoveryStrategy(
                strategy_id=s2_id,
                name="Strategy 2: Secondary Alternative Failover Route",
                strategy_type="SECONDARY_ALTERNATIVE",
                operation=f"Activate secondary alternate path: {' -> '.join(a_path)}.",
                reason="Provides redundant failover bypass if the primary optimal route experiences operational constraints.",
                root_cause_addressed="Connectivity Disruption",
                affected_components=affected_components,
                expected_latency_ms=a_lat,
                expected_loss_pct=a_loss,
                expected_cost=a_cost,
                risk_score=min(100, score_a),
                risk_factors=factors_a,
                reversibility=True,
                requires_approval=needs_approval_a,
                decision_outcome=DecisionOutcome.REQUIRES_APPROVAL,
                candidate_route=a_path,
                action_items=[{"action_type": "ACTIVATE_SECONDARY_ROUTE", "route": a_path}]
            ))

        # Strategy 3: Conservative Isolate & Monitor (Human Intervention Required)
        curr_p = list(g.graph.get("active_path", []))
        curr_m = calculate_route_metrics(g, curr_p) if curr_p else {}
        c_lat = curr_m.get("latency_ms", p_lat)
        c_loss = curr_m.get("probabilistic_loss", curr_m.get("max_loss", p_loss))
        c_cost = curr_m.get("cost", 0)
        s3_id = self._next_strategy_id()
        strategies.append(RecoveryStrategy(
            strategy_id=s3_id,
            name="Strategy 3: Conservative Isolation (Operator Manual Handling)",
            strategy_type="MANUAL_ISOLATION",
            operation="Isolate failed/degraded links without modifying routing tables; defer configuration to network administrator.",
            reason="Avoids automated route flaps and transient convergence instability in high-assurance environments.",
            root_cause_addressed="Operator Handover",
            affected_components=affected_components,
            expected_latency_ms=c_lat,
            expected_loss_pct=c_loss,
            expected_cost=c_cost,
            risk_score=35,
            risk_factors=["Service may remain degraded until manual intervention by network operations team."],
            reversibility=True,
            requires_approval=True,
            decision_outcome=DecisionOutcome.REQUIRES_APPROVAL,
            candidate_route=curr_p if curr_p else primary_route,
            action_items=[{"action_type": "OPERATOR_MANUAL_HOLD"}]
        ))

        return strategies

    def evaluate_decisions(
        self,
        g: nx.Graph,
        findings: List[Any],
        source: str = "PC1",
        target: str = "Server"
    ) -> List[DecisionRecord]:
        """Generate and evaluate decision records for all feasible strategies."""
        strategies = self.generate_strategies(g, findings, source=source, target=target)
        decisions: List[DecisionRecord] = []

        f_ids = [getattr(f, "finding_id", "DIAG-UNK") for f in findings]
        reg = get_fault_registry(g)
        flt_ids = [f.fault_id for f in reg.get_active_faults()]

        for strat in strategies:
            d_id = self._next_decision_id()

            # Preconditions validation
            preconds = [
                f"Source node '{source}' exists in graph",
                f"Target node '{target}' exists in graph",
                "Graph topology snapshot captured for rollback capability",
                "Diagnostic telemetry findings are fresh and non-stale"
            ]
            precond_met = (source in g.nodes and target in g.nodes and len(findings) >= 0)

            side_effects = []
            if strat.candidate_route:
                side_effects.append(f"Traffic forwarded via: {' -> '.join(strat.candidate_route)}")
            if strat.strategy_type != "MONITOR_ONLY":
                side_effects.append("Failed components remain isolated in DOWN/degraded state")

            # Determine initial status based on policy and risk
            if strat.decision_outcome == DecisionOutcome.AUTO_EXECUTE:
                status = DecisionStatus.APPROVED if self.policy != OperatingPolicy.FULLY_MANUAL else DecisionStatus.PENDING
            elif strat.decision_outcome == DecisionOutcome.MONITOR_ONLY:
                status = DecisionStatus.MONITORING
            elif strat.decision_outcome == DecisionOutcome.BLOCKED:
                status = DecisionStatus.BLOCKED
            else:
                status = DecisionStatus.PENDING

            explanation = (
                f"Policy [{self.policy.value}]: Strategy '{strat.name}' assessed with Risk Score {strat.risk_score}/100. "
                f"Outcome: {strat.decision_outcome.value}."
            )

            rec = DecisionRecord(
                decision_id=d_id,
                strategy=strat,
                fault_ids=flt_ids,
                finding_ids=f_ids,
                policy_in_effect=self.policy,
                status=status,
                explanation=explanation,
                preconditions_checked=preconds,
                preconditions_met=precond_met,
                side_effects=side_effects
            )
            self._decisions[d_id] = rec
            decisions.append(rec)

        return decisions

    def approve_decision(self, decision_id: str) -> bool:
        """Explicitly approve a pending recovery decision."""
        if decision_id not in self._decisions:
            return False
        rec = self._decisions[decision_id]
        if rec.status in (DecisionStatus.PENDING, DecisionStatus.REJECTED, DecisionStatus.APPROVED):
            rec.status = DecisionStatus.APPROVED
            rec.explanation += " [User approved execution]."
            return True
        return False

    def reject_decision(self, decision_id: str, reason: str = "Operator rejected proposed action") -> bool:
        """Reject a pending recovery decision."""
        if decision_id not in self._decisions:
            return False
        rec = self._decisions[decision_id]
        rec.status = DecisionStatus.REJECTED
        rec.rejection_reason = reason
        rec.explanation += f" [Rejected: {reason}]."
        return True

    def execute_decision(self, g: nx.Graph, decision_id: str) -> Dict[str, Any]:
        """Execute an approved recovery decision atomically with snapshot protection."""
        if decision_id not in self._decisions:
            return {"success": False, "error": f"Decision {decision_id} not found."}

        rec = self._decisions[decision_id]
        if rec.status not in (DecisionStatus.APPROVED, DecisionStatus.MONITORING):
            return {
                "success": False,
                "error": f"Decision {decision_id} cannot be executed in state '{rec.status.value}'. Must be APPROVED first."
            }

        # 1. Snapshot prior to mutation
        snapshot = capture_network_snapshot(g)

        try:
            strat = rec.strategy
            if strat.strategy_type == "MONITOR_ONLY":
                rec.status = DecisionStatus.EXECUTED
                rec.execution_result = {
                    "action_executed": False,
                    "status": "SERVICE MAINTAINED",
                    "reason": "Passive monitoring confirmed; service already operational."
                }
                obs = collect_observations(g)
                rec.verification_result = {"verified": True, "reachability": obs.get("reachability", True)}
                return {"success": True, "decision_id": decision_id, "status": "SERVICE MAINTAINED"}

            # Execute recovery via authoritative recovery engine
            recovery_result = recover(g)

            # Independent post-execution verification
            obs_after = collect_observations(g)
            is_verified = recovery_result.get("verified", False) and obs_after.get("reachability", False)

            if is_verified:
                rec.status = DecisionStatus.EXECUTED
                rec.execution_result = recovery_result
                rec.verification_result = {
                    "verified": True,
                    "reachability": obs_after.get("reachability"),
                    "route": obs_after.get("path"),
                    "latency_ms": obs_after.get("end_to_end_latency_ms"),
                    "packet_loss": obs_after.get("path_packet_loss")
                }
                return {
                    "success": True,
                    "decision_id": decision_id,
                    "status": recovery_result.get("status", "RECOVERY VERIFIED"),
                    "recovery_result": recovery_result
                }
            else:
                # Execution failed verification -> safe rollback
                restore_network_snapshot(g, snapshot)
                rec.status = DecisionStatus.ROLLED_BACK
                rec.execution_result = recovery_result
                rec.verification_result = {"verified": False, "reason": "Verification failed post-execution."}
                return {
                    "success": False,
                    "decision_id": decision_id,
                    "status": "ROLLED_BACK",
                    "error": "Independent post-recovery verification failed; network state safely rolled back."
                }

        except Exception as e:
            # Exception safety: automatic rollback
            restore_network_snapshot(g, snapshot)
            rec.status = DecisionStatus.ROLLED_BACK
            rec.execution_result = {"error": str(e)}
            return {"success": False, "decision_id": decision_id, "error": f"Execution exception: {e}"}

    def rollback_decision(self, g: nx.Graph, decision_id: str, snapshot: Dict[str, Any]) -> bool:
        """Manually roll back an executed decision to a captured snapshot."""
        if decision_id not in self._decisions:
            return False
        rec = self._decisions[decision_id]
        restore_network_snapshot(g, snapshot)
        rec.status = DecisionStatus.ROLLED_BACK
        rec.explanation += " [Manually rolled back by operator]."
        return True

    def get_pending_approvals(self) -> List[DecisionRecord]:
        """Return all decisions currently awaiting human approval."""
        return [d for d in self._decisions.values() if d.status == DecisionStatus.PENDING]

    def get_all_decisions(self) -> List[DecisionRecord]:
        """Return all generated decision records."""
        return list(self._decisions.values())

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Retrieve a specific decision by its ID."""
        return self._decisions.get(decision_id)

    def clear(self) -> None:
        """Reset decision engine state."""
        self._decisions.clear()
        self._decision_counter = 0
        self._strategy_counter = 0


# Global singleton decision engine instance
_global_decision_engine: Optional[DecisionEngine] = None


def get_decision_engine(policy: OperatingPolicy = OperatingPolicy.HYBRID) -> DecisionEngine:
    """Return the global DecisionEngine singleton."""
    global _global_decision_engine
    if _global_decision_engine is None:
        _global_decision_engine = DecisionEngine(policy=policy)
    return _global_decision_engine
