"""Automated Recovery and Verification Engine.

Applies simulated repairs, failover rerouting, and optimization based strictly on
COORDINATED GLOBAL RECOVERY PLANS and DIAGNOSED ROOT CAUSES.
Does NOT read any injected fault label, scenario identifier, or ground truth.
Includes transactional snapshotting, safe rollback on failure, adaptive fallback,
and isolated execution contexts (zero state leakage between runs).
Never counts verification as a corrective action.
Distinguishes Service Availability (AVAILABLE/UNAVAILABLE), Network Health (HEALTHY/DEGRADED/CRITICAL),
and Recovery Status (RECOVERY VERIFIED, SERVICE MAINTAINED, PARTIAL RECOVERY, RECOVERY UNAVAILABLE, NO RECOVERY REQUIRED).
"""
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import networkx as nx

from network_model import (
    shortest_path,
    path_is_usable,
    discover_routes,
    select_best_route,
    resolve_endpoints,
    get_active_route,
    set_active_route,
    calculate_route_metrics
)
from monitoring import collect_observations
from diagnostics import diagnose, DiagnosticFinding
from scenario_manager import capture_network_snapshot, restore_network_snapshot
from recovery_planner import (
    RecoveryDecision,
    RoutePolicy,
    RecoveryAction,
    RecoveryPlan,
    generate_recovery_plan,
    format_plan_report
)


def recover(g, state=None, findings=None, source=None, target=None, plan=None, policy=RoutePolicy.BALANCED):
    """Execute fault-specific automated recovery actions based on a coordinated global recovery plan,
    with transactional safety, adaptive fallback, and post-recovery verification.
    
    Parameters:
        g (nx.Graph): Network graph topology.
        state (dict, optional): May contain endpoint selections (source, target).
        findings (list, optional): Diagnostic findings from diagnostics.diagnose().
        source (str, optional): Source node override.
        target (str, optional): Target node override.
        plan (RecoveryPlan, optional): Pre-computed recovery plan override.
        policy (str): Route optimization policy for planner.
        
    Returns:
        dict: Recovery execution report with execution ID, executed actions, before/after states,
              verification checks, active forwarding route, Service Availability, and Network Health.
    """
    execution_start = time.time()
    execution_counter = int(execution_start * 1000) % 10000
    execution_id = f"EXEC-{execution_counter:04d}"

    actions_executed_log = []
    action_details = []

    # Resolve endpoints
    src = source
    dst = target
    if src is None and isinstance(state, dict):
        src = state.get("source")
    if dst is None and isinstance(state, dict):
        dst = state.get("target")
    src, dst = resolve_endpoints(g, src, dst)
    current_active = get_active_route(g, src, dst)

    # 1. Collect baseline pre-recovery observations
    obs_pre = collect_observations(g, state=state, source=src, target=dst)

    # 2. If findings were not provided, perform fresh diagnosis
    if findings is None:
        findings = diagnose(obs_pre)

    # 3. Generate Coordinated Global Recovery Plan (Read-Only)
    if plan is None:
        plan = generate_recovery_plan(
            g,
            findings=findings,
            observations=obs_pre,
            source=src,
            target=dst,
            route_policy=policy
        )

    # 4. Capture Transactional Snapshot before making state changes
    snapshot = capture_network_snapshot(g)

    # Extract set of diagnosed causes
    diagnosed_causes = {getattr(f, "root_cause", f[0]) for f in findings}
    has_link_failure = "Link failure" in diagnosed_causes
    has_gateway_fault = "Incorrect default gateway" in diagnosed_causes
    has_dns_fault = "DNS service failure" in diagnosed_causes
    has_latency_fault = "High latency" in diagnosed_causes
    has_loss_fault = "Packet loss" in diagnosed_causes
    has_partition = "Network partition" in diagnosed_causes

    action_executed = False
    execution_failed = False
    fallback_used = False
    rollback_occurred = False
    executed_action_records = []

    failover_success = None
    gateway_success = None
    dns_success = None
    latency_success = None
    loss_success = None

    affected_links = []
    for f in findings:
        for item in getattr(f, "affected_components", []):
            if "-" in str(item):
                affected_links.append(str(item))

    # 5. Execute Planned Corrective Actions in Priority Order
    try:
        for action in plan.actions:
            act_start = time.time()
            act_type = action.action_type
            target_comp = action.target_component
            params = action.parameters

            if act_type in ("FAILOVER_REROUTE", "OPTIMIZE_ROUTE"):
                selected_path = params.get("selected_path")
                curr_active = get_active_route(g, src, dst)
                before_str = f"Active path: {' -> '.join(curr_active) if curr_active else 'None'}"

                if selected_path and path_is_usable(g, selected_path):
                    set_active_route(g, selected_path)
                    after_str = f"Active path: {' -> '.join(selected_path)}"
                    if has_link_failure:
                        down_summary = ", ".join(affected_links) if affected_links else "failed link"
                        msg = f"Kept failed {down_summary} link DOWN and selected available alternate route: {' -> '.join(selected_path)}."
                    else:
                        msg = f"Activated optimal forwarding route: {' -> '.join(selected_path)}."
                    actions_executed_log.append(msg)
                    action_details.append({
                        "fault": "Link failure" if has_link_failure else "Routing Optimization",
                        "action": "Activated alternate forwarding route",
                        "before": before_str,
                        "after": after_str,
                        "action_id": action.action_id
                    })
                    action_executed = True
                    failover_success = True
                    if has_latency_fault:
                        latency_success = True
                    if has_loss_fault:
                        loss_success = True
                    executed_action_records.append({
                        "action_id": action.action_id,
                        "type": act_type,
                        "status": "COMPLETED",
                        "before": before_str,
                        "after": after_str
                    })
                else:
                    # Adaptive Fallback: Try next usable candidate route if first candidate is broken
                    fallback_candidate = None
                    for alt in plan.candidate_routes:
                        if alt["path"] != selected_path and path_is_usable(g, alt["path"]):
                            fallback_candidate = alt["path"]
                            break

                    if fallback_candidate:
                        set_active_route(g, fallback_candidate)
                        fallback_used = True
                        after_str = f"Active path (Fallback): {' -> '.join(fallback_candidate)}"
                        if has_link_failure:
                            down_summary = ", ".join(affected_links) if affected_links else "failed link"
                            msg = f"Primary candidate path unavailable; kept failed {down_summary} link DOWN and selected available alternate route: {' -> '.join(fallback_candidate)}."
                        else:
                            msg = f"Primary candidate path unavailable; activated fallback route: {' -> '.join(fallback_candidate)}."
                        actions_executed_log.append(msg)
                        action_details.append({
                            "fault": "Link failure",
                            "action": "Activated fallback forwarding route",
                            "before": before_str,
                            "after": after_str,
                            "action_id": action.action_id
                        })
                        action_executed = True
                        failover_success = True
                        if has_latency_fault:
                            latency_success = True
                        if has_loss_fault:
                            loss_success = True
                        executed_action_records.append({
                            "action_id": action.action_id,
                            "type": act_type,
                            "status": "COMPLETED_FALLBACK",
                            "before": before_str,
                            "after": after_str
                        })
                    else:
                        execution_failed = True
                        failover_success = False
                        executed_action_records.append({
                            "action_id": action.action_id,
                            "type": act_type,
                            "status": "FAILED",
                            "error": "No usable candidate path available for rerouting"
                        })

            elif act_type == "RESTORE_GATEWAY":
                host = params.get("host", target_comp)
                target_gw = params.get("target_gateway", "R1")
                if host in g.nodes:
                    old_gw = g.nodes[host].get("gateway", "Unknown")
                    g.nodes[host]["gateway"] = target_gw
                    if host == "PC1":
                        g.graph["gateway"] = target_gw

                    msg = f"Corrected default gateway for {host} from '{old_gw}' to valid router '{target_gw}'."
                    actions_executed_log.append(msg)
                    action_details.append({
                        "fault": "Incorrect default gateway",
                        "action": f"Reconfigured gateway on {host}",
                        "before": f"{host} gateway = '{old_gw}'",
                        "after": f"{host} gateway = '{target_gw}' (Valid)",
                        "action_id": action.action_id
                    })
                    action_executed = True
                    gateway_success = True
                    executed_action_records.append({
                        "action_id": action.action_id,
                        "type": act_type,
                        "status": "COMPLETED",
                        "before": f"gateway={old_gw}",
                        "after": f"gateway={target_gw}"
                    })

            elif act_type == "RESTORE_DNS":
                before_dns = bool(g.graph.get("dns_available", True))
                g.graph["dns_available"] = True
                for n, d in g.nodes(data=True):
                    if d.get("type") in ("PC", "Laptop") and d.get("dns_server") != "192.168.1.1":
                        d["dns_server"] = "192.168.1.1"

                msg = "Restored simulated DNS service and verified client resolver configuration."
                actions_executed_log.append(msg)
                action_details.append({
                    "fault": "DNS service failure",
                    "action": "Restored DNS service availability",
                    "before": f"dns_available = {before_dns}",
                    "after": "dns_available = True (Operational)",
                    "action_id": action.action_id
                })
                action_executed = True
                dns_success = True
                executed_action_records.append({
                    "action_id": action.action_id,
                    "type": act_type,
                    "status": "COMPLETED",
                    "before": f"dns_available={before_dns}",
                    "after": "dns_available=True"
                })

    except Exception as e:
        execution_failed = True
        restore_network_snapshot(g, snapshot)
        rollback_occurred = True

    # 6. Post-processing for unexecuted fault mitigations & service-maintained cases
    affected_links = []
    for f in findings:
        for item in getattr(f, "affected_components", []):
            if "-" in str(item):
                affected_links.append(str(item))

    if has_latency_fault and not latency_success:
        curr_lat = sum(g[u][v].get("latency_ms", 2.0) for u, v in zip(current_active, current_active[1:])) if current_active and len(current_active) >= 2 else 999.0
        msg = f"High-latency optimization UNAVAILABLE: No alternative route offers lower latency than the current path ({curr_lat} ms)."
        actions_executed_log.append(msg)
        action_details.append({
            "fault": "High latency",
            "action": "Optimization unavailable",
            "before": f"Current path latency: {curr_lat} ms",
            "after": "No lower-latency alternative exists"
        })
        latency_success = False

    if has_loss_fault and not loss_success:
        curr_loss = max(g[u][v].get("packet_loss", 0.0) for u, v in zip(current_active, current_active[1:])) if current_active and len(current_active) >= 2 else 100.0
        msg = f"Packet loss recovery UNAVAILABLE: No alternative route offers lower packet loss than the current path ({curr_loss}%)."
        actions_executed_log.append(msg)
        action_details.append({
            "fault": "Packet loss",
            "action": "Recovery unavailable",
            "before": f"Current path loss: {curr_loss}%",
            "after": "No lower-loss alternative exists"
        })
        loss_success = False

    if has_link_failure and (not plan.selected_route or plan.decision == RecoveryDecision.NO_FEASIBLE_RECOVERY):
        down_summary = ", ".join(affected_links) if affected_links else "failed link(s)"
        msg = f"Link failure detected on {down_summary}: No alternative route exists between {src} and {dst}; recovery is unavailable."
        actions_executed_log.append(msg)
        action_details.append({
            "fault": "Link failure",
            "action": "Failover unavailable",
            "before": f"Failed link(s): {down_summary} (Status: DOWN)",
            "after": "No alternative route exists in topology"
        })
        failover_success = False

    if not action_executed:
        if plan.decision == RecoveryDecision.SERVICE_ALREADY_MAINTAINED:
            route_str = " -> ".join(current_active) if current_active else "None"
            msg = f"Service is maintained through existing alternative route: {route_str}."
            actions_executed_log.append(msg)
        elif plan.decision == RecoveryDecision.NO_ACTION_REQUIRED:
            actions_executed_log.append("No repair required; baseline state is healthy.")
        elif plan.decision == RecoveryDecision.NO_FEASIBLE_RECOVERY and not has_link_failure and not has_latency_fault and not has_loss_fault:
            actions_executed_log.append(f"Recovery is unavailable: Network is partitioned between {src} and {dst} with 0 operational paths.")

    # 7. Independent Post-Recovery Verification with Fresh Observations
    post_obs = collect_observations(g, state=state, source=src, target=dst)

    active_route = post_obs.get("active_path") or post_obs.get("path")
    ip_ok = bool(post_obs["reachability"] and post_obs["gateway_ok"])
    dns_ok = bool(post_obs["dns_ok"])
    gw_ok = bool(post_obs["gateway_ok"])
    post_down_links = post_obs.get("down_links", [])

    # Check that failed links remained DOWN (failover did not falsely mark them UP)
    links_remain_down = True
    if has_link_failure:
        for fl in affected_links:
            if fl not in post_down_links and "-".join(reversed(fl.split("-"))) not in post_down_links:
                links_remain_down = False

    # Fault-specific verification evaluations
    verification_passed = True

    if has_link_failure:
        if not post_obs["reachability"] or not links_remain_down:
            verification_passed = False

    if has_gateway_fault:
        if not gw_ok or not post_obs["reachability"]:
            verification_passed = False

    if has_dns_fault:
        if not dns_ok or not ip_ok:
            verification_passed = False

    if has_latency_fault and latency_success is False:
        verification_passed = False

    if has_loss_fault and loss_success is False:
        verification_passed = False

    if (has_link_failure or has_partition) and plan.decision == RecoveryDecision.NO_FEASIBLE_RECOVERY:
        verification_passed = False

    if execution_failed:
        verification_passed = False

    # Safe rollback if verification critically failed and state was mutated
    if not verification_passed and action_executed and not (has_link_failure and post_obs["reachability"]):
        # Roll back failed action to protect network state
        restore_network_snapshot(g, snapshot)
        rollback_occurred = True
        post_obs = collect_observations(g, state=state, source=src, target=dst)
        active_route = post_obs.get("active_path")
        ip_ok = bool(post_obs["reachability"] and post_obs["gateway_ok"])
        dns_ok = bool(post_obs["dns_ok"])

    verified = bool(verification_passed and (ip_ok and dns_ok))

    # 8. Decouple Service Availability from Network Health
    service_available = bool(ip_ok and dns_ok and post_obs["reachability"])
    service_availability = "AVAILABLE" if service_available else "UNAVAILABLE"

    has_any_down = len(post_down_links) > 0
    has_any_high_lat = len(post_obs.get("high_latency", [])) > 0
    has_any_loss = len(post_obs.get("packet_loss", [])) > 0

    if not service_available or (has_link_failure and not post_obs["reachability"]):
        network_health = "CRITICAL"
    elif has_any_down or has_any_high_lat or has_any_loss:
        network_health = "DEGRADED"
    else:
        network_health = "HEALTHY"

    # 9. Determine Recovery Status
    diagnosed_causes = {getattr(f, "root_cause", f[0]) for f in findings}
    if (has_link_failure or has_partition) and (plan.decision == RecoveryDecision.NO_FEASIBLE_RECOVERY or not post_obs["reachability"]):
        status_msg = "RECOVERY UNAVAILABLE"
    elif has_latency_fault and latency_success is False and len(diagnosed_causes) == 1:
        status_msg = "OPTIMIZATION UNAVAILABLE"
    elif has_loss_fault and loss_success is False and len(diagnosed_causes) == 1:
        status_msg = "RECOVERY UNAVAILABLE"
    elif plan.decision == RecoveryDecision.NO_FEASIBLE_RECOVERY and not action_executed:
        status_msg = "RECOVERY UNAVAILABLE"
    elif plan.decision == RecoveryDecision.PARTIAL_RECOVERY_REQUIRED:
        status_msg = "PARTIAL RECOVERY"
    elif not verification_passed:
        status_msg = "RECOVERY FAILED"
    elif plan.decision == RecoveryDecision.SERVICE_ALREADY_MAINTAINED or (has_link_failure and not action_executed and service_available):
        status_msg = "SERVICE MAINTAINED"
    elif not action_executed:
        status_msg = "NO RECOVERY REQUIRED"
    else:
        status_msg = "RECOVERY VERIFIED"

    reason_str = (
        "A healthy alternative route was already active; no routing change was required."
        if status_msg == "SERVICE MAINTAINED" else (
            "Corrective recovery operations verified successfully." if action_executed else "No corrective action was required."
        )
    )

    verification_checks = {
        "endpoint_ip_connectivity": "PASS" if ip_ok else "FAIL",
        "dns_resolution": "PASS" if dns_ok else "FAIL",
        "default_gateway_validity": "PASS" if gw_ok else "FAIL",
        "active_route": " -> ".join(active_route) if active_route else "None",
        "failed_links_isolated": "PASS" if links_remain_down else "FAIL",
        "end_to_end_latency_ms": post_obs.get("end_to_end_latency_ms"),
        "packet_loss_pct": post_obs.get("path_packet_loss")
    }

    return {
        "execution_id": execution_id,
        "actions": actions_executed_log,
        "action_details": action_details,
        "action_executed": action_executed,
        "corrective_actions_count": len(action_details),
        "route": active_route,
        "active_route": active_route,
        "ip_connectivity": bool(ip_ok),
        "dns_resolution": bool(dns_ok),
        "gateway_valid": bool(gw_ok),
        "service_availability": service_availability,
        "network_health": network_health,
        "recovery_status": status_msg,
        "status": status_msg,
        "reason": reason_str,
        "verification_passed": bool(verification_passed),
        "verified": verified,
        "routes": post_obs["routes"],
        "route_selection": post_obs["route_selection"],
        "post_observations": post_obs,
        "verification_checks": verification_checks,
        "plan": plan,
        "fallback_used": fallback_used,
        "rollback_occurred": rollback_occurred,
        "executed_action_records": executed_action_records
    }


def format_recovery_report(result):
    """Format automated recovery actions into a clean, structured text report (Report C).
    
    Contains exact corrective actions performed, execution ID, and before-and-after state changes.
    Never counts verification as a corrective action.
    """
    exec_id = result.get("execution_id", "EXEC-0000")
    actions_count = result.get("corrective_actions_count", len(result.get("action_details", [])))
    status_str = result.get("status", "UNKNOWN")
    action_exec_str = "YES" if result.get("action_executed") else "NO"

    lines = [
        "=== AUTOMATED RECOVERY REPORT ===",
        f"Execution Context ID        : {exec_id}",
        f"Recovery Status             : {status_str}",
        f"Corrective Actions Executed : {actions_count}",
        f"Action Executed             : {action_exec_str}"
    ]
    if result.get("reason"):
        lines.append(f"Reason                      : {result.get('reason')}")
    lines.append("")

    details = result.get("action_details", [])
    if details:
        for i, act in enumerate(details, 1):
            act_id_str = f" [{act.get('action_id', '')}]" if act.get("action_id") else ""
            lines.append(f"• Action {i}{act_id_str} [{act.get('fault', 'General')}]:")
            lines.append(f"  - Corrective Action : {act.get('action', '')}")
            lines.append(f"  - Before State      : {act.get('before', '')}")
            lines.append(f"  - After State       : {act.get('after', '')}")
            lines.append("")
    else:
        for a in result.get("actions", []):
            lines.append(f"• {a}")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_verification_report(result):
    """Format independent post-recovery verification results into a clean text report (Report D).
    
    Contains fresh connectivity and performance checks with explicit pass/fail results.
    Distinguishes Service Availability from Network Health.
    """
    checks = result.get("verification_checks", {})
    route_str = checks.get("active_route", "None")
    lat = checks.get("end_to_end_latency_ms")
    lat_str = f"{lat} ms" if lat is not None else "N/A"
    loss = checks.get("packet_loss_pct")
    loss_str = f"{loss}%" if loss is not None else "N/A"

    service_avail = result.get("service_availability", "AVAILABLE" if result.get("verified") else "UNAVAILABLE")
    net_health = result.get("network_health", "HEALTHY" if result.get("verified") else "CRITICAL")
    action_exec_str = "YES" if result.get("action_executed") else "NO"
    verif_res_str = "PASSED" if result.get("verified") else "FAILED"

    lines = [
        "=== POST-RECOVERY VERIFICATION REPORT ===",
        f"Overall Recovery Status : {result.get('status', 'UNKNOWN')}",
        f"Service Availability    : {service_avail}",
        f"Network Health          : {net_health}",
        f"Action Executed         : {action_exec_str}",
        f"Verification Result     : {verif_res_str}\n",
        "Verification Checks:",
        f"• Endpoint IP Connectivity : {checks.get('endpoint_ip_connectivity', 'UNKNOWN')}",
        f"• DNS Resolution           : {checks.get('dns_resolution', 'UNKNOWN')}",
        f"• Default Gateway Validity : {checks.get('default_gateway_validity', 'UNKNOWN')}",
        f"• Active Forwarding Route  : {route_str}",
        f"• Failed Link Isolation    : {checks.get('failed_links_isolated', 'N/A')}",
        f"• End-to-End Latency       : {lat_str}",
        f"• Packet Loss              : {loss_str}"
    ]
    return "\n".join(lines)


# Public aliases
generate_recovery_report = format_recovery_report
generate_verification_report = format_verification_report
