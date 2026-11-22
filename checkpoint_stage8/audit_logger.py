"""audit_logger.py - Comprehensive Audit Logging, Recovery History and Analytics Engine.

Provides persistent, structured audit trail of all network events, diagnostic findings,
recovery plans, executed actions, pre/post telemetry metrics, and post-recovery verifications.
Includes analytics computation (success rate, MTTR, deltas) and CSV/JSON export/import.
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class AuditRecord:
    """Represents a single immutable audit entry for a fault diagnosis and recovery run."""

    def __init__(
        self,
        audit_id: str,
        execution_id: str,
        timestamp: Optional[float] = None,
        scenario_id: Optional[str] = None,
        scenario_name: Optional[str] = None,
        finding_ids: Optional[List[str]] = None,
        root_causes: Optional[List[str]] = None,
        plan_id: Optional[str] = None,
        plan_decision: Optional[str] = None,
        actions_count: int = 0,
        actions_summary: Optional[List[str]] = None,
        before_metrics: Optional[Dict[str, Any]] = None,
        after_metrics: Optional[Dict[str, Any]] = None,
        latency_delta_ms: Optional[float] = None,
        loss_delta_pct: Optional[float] = None,
        recovery_status: str = "UNKNOWN",
        service_availability: str = "UNKNOWN",
        network_health: str = "UNKNOWN",
        verification_passed: bool = False,
        rollback_occurred: bool = False,
        fallback_used: bool = False,
        duration_ms: float = 0.0
    ):
        self.audit_id = str(audit_id)
        self.execution_id = str(execution_id)
        self.timestamp = float(timestamp if timestamp is not None else time.time())
        self.timestamp_iso = datetime.fromtimestamp(self.timestamp).isoformat()
        self.scenario_id = str(scenario_id) if scenario_id else "ADHOC"
        self.scenario_name = str(scenario_name) if scenario_name else "Custom Run"
        self.finding_ids = list(finding_ids) if finding_ids else []
        self.root_causes = list(root_causes) if root_causes else []
        self.plan_id = str(plan_id) if plan_id else "PLAN-NONE"
        self.plan_decision = str(plan_decision) if plan_decision else "UNKNOWN"
        self.actions_count = int(actions_count)
        self.actions_summary = list(actions_summary) if actions_summary else []
        self.before_metrics = dict(before_metrics) if before_metrics else {}
        self.after_metrics = dict(after_metrics) if after_metrics else {}
        self.latency_delta_ms = float(latency_delta_ms) if latency_delta_ms is not None else 0.0
        self.loss_delta_pct = float(loss_delta_pct) if loss_delta_pct is not None else 0.0
        self.recovery_status = str(recovery_status)
        self.service_availability = str(service_availability)
        self.network_health = str(network_health)
        self.verification_passed = bool(verification_passed)
        self.rollback_occurred = bool(rollback_occurred)
        self.fallback_used = bool(fallback_used)
        self.duration_ms = float(duration_ms)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary for serialization."""
        return {
            "audit_id": self.audit_id,
            "execution_id": self.execution_id,
            "timestamp": self.timestamp,
            "timestamp_iso": self.timestamp_iso,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "finding_ids": self.finding_ids,
            "root_causes": self.root_causes,
            "plan_id": self.plan_id,
            "plan_decision": self.plan_decision,
            "actions_count": self.actions_count,
            "actions_summary": self.actions_summary,
            "before_metrics": self.before_metrics,
            "after_metrics": self.after_metrics,
            "latency_delta_ms": self.latency_delta_ms,
            "loss_delta_pct": self.loss_delta_pct,
            "recovery_status": self.recovery_status,
            "service_availability": self.service_availability,
            "network_health": self.network_health,
            "verification_passed": self.verification_passed,
            "rollback_occurred": self.rollback_occurred,
            "fallback_used": self.fallback_used,
            "duration_ms": self.duration_ms
        }

    def to_csv_row(self) -> Dict[str, Any]:
        """Flatten record for CSV table row export."""
        before_route = " -> ".join(self.before_metrics.get("route", [])) if self.before_metrics.get("route") else "None"
        after_route = " -> ".join(self.after_metrics.get("route", [])) if self.after_metrics.get("route") else "None"
        return {
            "Audit ID": self.audit_id,
            "Execution ID": self.execution_id,
            "Timestamp": self.timestamp_iso,
            "Scenario ID": self.scenario_id,
            "Scenario Name": self.scenario_name,
            "Root Causes": "; ".join(self.root_causes),
            "Plan ID": self.plan_id,
            "Plan Decision": self.plan_decision,
            "Actions Executed": self.actions_count,
            "Before Latency (ms)": self.before_metrics.get("latency_ms", "N/A"),
            "After Latency (ms)": self.after_metrics.get("latency_ms", "N/A"),
            "Latency Delta (ms)": self.latency_delta_ms,
            "Before Loss (%)": self.before_metrics.get("packet_loss_pct", "N/A"),
            "After Loss (%)": self.after_metrics.get("packet_loss_pct", "N/A"),
            "Loss Delta (%)": self.loss_delta_pct,
            "Before Route": before_route,
            "After Route": after_route,
            "Recovery Status": self.recovery_status,
            "Service Availability": self.service_availability,
            "Network Health": self.network_health,
            "Verification": "PASSED" if self.verification_passed else "FAILED",
            "Rollback": "YES" if self.rollback_occurred else "NO",
            "Fallback": "YES" if self.fallback_used else "NO"
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AuditRecord":
        """Deserialize from dictionary."""
        return cls(
            audit_id=d.get("audit_id", "AUD-0000"),
            execution_id=d.get("execution_id", "EXEC-0000"),
            timestamp=d.get("timestamp"),
            scenario_id=d.get("scenario_id"),
            scenario_name=d.get("scenario_name"),
            finding_ids=d.get("finding_ids"),
            root_causes=d.get("root_causes"),
            plan_id=d.get("plan_id"),
            plan_decision=d.get("plan_decision"),
            actions_count=d.get("actions_count", 0),
            actions_summary=d.get("actions_summary"),
            before_metrics=d.get("before_metrics"),
            after_metrics=d.get("after_metrics"),
            latency_delta_ms=d.get("latency_delta_ms"),
            loss_delta_pct=d.get("loss_delta_pct"),
            recovery_status=d.get("recovery_status", "UNKNOWN"),
            service_availability=d.get("service_availability", "UNKNOWN"),
            network_health=d.get("network_health", "UNKNOWN"),
            verification_passed=d.get("verification_passed", False),
            rollback_occurred=d.get("rollback_occurred", False),
            fallback_used=d.get("fallback_used", False),
            duration_ms=d.get("duration_ms", 0.0)
        )


class AuditLogger:
    """Manages audit records and calculates recovery effectiveness analytics."""

    def __init__(self):
        self._records: List[AuditRecord] = []
        self._counter: int = 0

    def next_audit_id(self) -> str:
        self._counter += 1
        return f"AUD-{self._counter:04d}"

    def record_execution(
        self,
        recovery_result: Dict[str, Any],
        plan: Optional[Any] = None,
        findings: Optional[List[Any]] = None,
        before_observations: Optional[Dict[str, Any]] = None,
        scenario_id: Optional[str] = None,
        scenario_name: Optional[str] = None,
        duration_ms: float = 0.0
    ) -> AuditRecord:
        """Create and store an AuditRecord from a completed recovery run.
        
        Computes metric deltas (latency, loss), extracts root causes and plan decisions.
        """
        audit_id = self.next_audit_id()
        exec_id = recovery_result.get("execution_id", "EXEC-0000")

        # Extract findings info
        finding_ids = []
        root_causes = []
        if findings:
            for f in findings:
                fid = getattr(f, "finding_id", None)
                if fid:
                    finding_ids.append(str(fid))
                rc = getattr(f, "root_cause", f[0] if isinstance(f, (list, tuple)) else str(f))
                if rc not in root_causes:
                    root_causes.append(str(rc))

        # Extract plan info
        plan_id = "PLAN-NONE"
        plan_decision = "UNKNOWN"
        p = plan or recovery_result.get("plan")
        if p:
            plan_id = getattr(p, "plan_id", str(p.get("plan_id") if isinstance(p, dict) else "PLAN-0000"))
            plan_decision = getattr(p, "decision", str(p.get("decision") if isinstance(p, dict) else "UNKNOWN"))

        # Extract before metrics
        before_obs = before_observations or {}
        before_lat = before_obs.get("end_to_end_latency_ms")
        before_loss = before_obs.get("path_packet_loss")
        before_route = before_obs.get("active_path") or before_obs.get("path")
        before_reach = before_obs.get("reachability", False)

        before_metrics = {
            "route": before_route,
            "latency_ms": before_lat,
            "packet_loss_pct": before_loss,
            "reachability": before_reach
        }

        # Extract after metrics
        post_obs = recovery_result.get("post_observations", {})
        after_lat = post_obs.get("end_to_end_latency_ms")
        after_loss = post_obs.get("path_packet_loss")
        after_route = recovery_result.get("route") or post_obs.get("active_path")
        after_reach = post_obs.get("reachability", False)

        after_metrics = {
            "route": after_route,
            "latency_ms": after_lat,
            "packet_loss_pct": after_loss,
            "reachability": after_reach
        }

        # Calculate deltas (negative delta = improvement)
        lat_delta = 0.0
        if before_lat is not None and after_lat is not None:
            lat_delta = round(float(after_lat) - float(before_lat), 2)

        loss_delta = 0.0
        if before_loss is not None and after_loss is not None:
            loss_delta = round(float(after_loss) - float(before_loss), 2)

        actions_list = recovery_result.get("actions", [])

        record = AuditRecord(
            audit_id=audit_id,
            execution_id=exec_id,
            timestamp=time.time(),
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            finding_ids=finding_ids,
            root_causes=root_causes,
            plan_id=plan_id,
            plan_decision=plan_decision,
            actions_count=recovery_result.get("corrective_actions_count", len(recovery_result.get("action_details", []))),
            actions_summary=actions_list,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            latency_delta_ms=lat_delta,
            loss_delta_pct=loss_delta,
            recovery_status=recovery_result.get("status", "UNKNOWN"),
            service_availability=recovery_result.get("service_availability", "UNKNOWN"),
            network_health=recovery_result.get("network_health", "UNKNOWN"),
            verification_passed=bool(recovery_result.get("verified", False)),
            rollback_occurred=bool(recovery_result.get("rollback_occurred", False)),
            fallback_used=bool(recovery_result.get("fallback_used", False)),
            duration_ms=duration_ms
        )

        self._records.append(record)
        return record

    def get_record(self, audit_id: str) -> Optional[AuditRecord]:
        for r in self._records:
            if r.audit_id == audit_id:
                return r
        return None

    def get_all_records(self) -> List[AuditRecord]:
        return list(self._records)

    def get_recent_records(self, limit: int = 10) -> List[AuditRecord]:
        return list(reversed(self._records[-limit:]))

    def filter_records(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[str] = None,
        verified: Optional[bool] = None,
        root_cause: Optional[str] = None
    ) -> List[AuditRecord]:
        results = []
        for r in self._records:
            if scenario_id and r.scenario_id != scenario_id:
                continue
            if status and r.recovery_status != status:
                continue
            if verified is not None and r.verification_passed != verified:
                continue
            if root_cause and root_cause not in r.root_causes:
                continue
            results.append(r)
        return results

    def compute_analytics(self) -> Dict[str, Any]:
        """Calculate comprehensive recovery effectiveness analytics over all recorded executions."""
        total = len(self._records)
        if total == 0:
            return {
                "total_runs": 0,
                "verified_count": 0,
                "success_rate_pct": 0.0,
                "service_maintained_count": 0,
                "failed_count": 0,
                "unavailable_count": 0,
                "total_actions_executed": 0,
                "rollbacks_count": 0,
                "fallbacks_count": 0,
                "avg_latency_delta_ms": 0.0,
                "avg_loss_delta_pct": 0.0,
                "root_cause_counts": {},
                "decision_counts": {}
            }

        verified_cnt = sum(1 for r in self._records if r.verification_passed)
        maintained_cnt = sum(1 for r in self._records if r.recovery_status == "SERVICE MAINTAINED")
        failed_cnt = sum(1 for r in self._records if r.recovery_status == "RECOVERY FAILED")
        unavail_cnt = sum(1 for r in self._records if "UNAVAILABLE" in r.recovery_status)

        total_actions = sum(r.actions_count for r in self._records)
        rollbacks = sum(1 for r in self._records if r.rollback_occurred)
        fallbacks = sum(1 for r in self._records if r.fallback_used)

        lat_deltas = [r.latency_delta_ms for r in self._records if r.latency_delta_ms != 0.0]
        avg_lat_delta = round(sum(lat_deltas) / len(lat_deltas), 2) if lat_deltas else 0.0

        loss_deltas = [r.loss_delta_pct for r in self._records if r.loss_delta_pct != 0.0]
        avg_loss_delta = round(sum(loss_deltas) / len(loss_deltas), 2) if loss_deltas else 0.0

        rc_counts: Dict[str, int] = {}
        for r in self._records:
            for rc in r.root_causes:
                rc_counts[rc] = rc_counts.get(rc, 0) + 1

        decision_counts: Dict[str, int] = {}
        for r in self._records:
            d = r.plan_decision
            decision_counts[d] = decision_counts.get(d, 0) + 1

        success_rate = round((verified_cnt / total) * 100.0, 1)

        return {
            "total_runs": total,
            "verified_count": verified_cnt,
            "success_rate_pct": success_rate,
            "service_maintained_count": maintained_cnt,
            "failed_count": failed_cnt,
            "unavailable_count": unavail_cnt,
            "total_actions_executed": total_actions,
            "rollbacks_count": rollbacks,
            "fallbacks_count": fallbacks,
            "avg_latency_delta_ms": avg_lat_delta,
            "avg_loss_delta_pct": avg_loss_delta,
            "root_cause_counts": rc_counts,
            "decision_counts": decision_counts
        }

    def export_to_csv(self, filepath: str) -> bool:
        """Export all audit records to a CSV file."""
        if not self._records:
            # Write empty header file
            fieldnames = [
                "Audit ID", "Execution ID", "Timestamp", "Scenario ID", "Scenario Name",
                "Root Causes", "Plan ID", "Plan Decision", "Actions Executed",
                "Before Latency (ms)", "After Latency (ms)", "Latency Delta (ms)",
                "Before Loss (%)", "After Loss (%)", "Loss Delta (%)",
                "Before Route", "After Route", "Recovery Status", "Service Availability",
                "Network Health", "Verification", "Rollback", "Fallback"
            ]
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
            return True

        rows = [r.to_csv_row() for r in self._records]
        fieldnames = list(rows[0].keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return True

    def export_to_json(self, filepath: str) -> bool:
        """Export all audit records and analytics to a JSON file."""
        data = {
            "version": "2.0",
            "exported_at": datetime.now().isoformat(),
            "record_count": len(self._records),
            "analytics": self.compute_analytics(),
            "records": [r.to_dict() for r in self._records]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True

    def import_from_json(self, filepath: str) -> int:
        """Import audit records from a previously exported JSON file."""
        if not os.path.exists(filepath):
            return 0
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        records_data = data.get("records", [])
        imported = 0
        for item in records_data:
            rec = AuditRecord.from_dict(item)
            self._records.append(rec)
            # Update counter to prevent ID collision
            try:
                num = int(rec.audit_id.replace("AUD-", ""))
                if num > self._counter:
                    self._counter = num
            except ValueError:
                pass
            imported += 1
        return imported

    def clear(self):
        """Reset all audit records."""
        self._records.clear()
        self._counter = 0


# Global default AuditLogger instance
_default_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Retrieve the global singleton AuditLogger instance."""
    return _default_audit_logger


def record_audit(
    recovery_result: Dict[str, Any],
    plan: Optional[Any] = None,
    findings: Optional[List[Any]] = None,
    before_observations: Optional[Dict[str, Any]] = None,
    scenario_id: Optional[str] = None,
    scenario_name: Optional[str] = None,
    duration_ms: float = 0.0
) -> AuditRecord:
    """Convenience helper to log a recovery run to the global audit logger."""
    return get_audit_logger().record_execution(
        recovery_result=recovery_result,
        plan=plan,
        findings=findings,
        before_observations=before_observations,
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        duration_ms=duration_ms
    )
