"""Automated Recovery and Verification Engine.
Applies simulated repairs and rerouting actions based strictly on DIAGNOSED ROOT CAUSES
and the current network state.
Does NOT read any injected fault label or scenario identifier.
Implements five distinct, fault-specific recovery strategies.
Never counts verification as a corrective action.
Distinguishes Service Availability (AVAILABLE/UNAVAILABLE), Network Health (HEALTHY/DEGRADED/CRITICAL),
and Recovery Status (RECOVERY VERIFIED, SERVICE MAINTAINED, RECOVERY UNAVAILABLE, NO RECOVERY REQUIRED).
After recovery, independently collects fresh observations to verify whether connectivity
and relevant performance metrics have improved.
"""
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
from diagnostics import diagnose

def recover(g, state=None, findings=None, source=None, target=None):
    """Execute fault-specific automated recovery actions based on diagnosed root causes,
    and independently verify post-recovery network health with fresh observations.
    
    Parameters:
        g (nx.Graph): Network graph topology.
        state (dict, optional): May contain endpoint selections (source, target).
        findings (list, optional): Diagnosis findings from diagnostics.diagnose().
            If None, independently runs monitoring and diagnosis first.
        source (str, optional): Source node override.
        target (str, optional): Target node override.
        
    Returns:
        dict: Recovery report with actions taken, before/after states, verification checks,
              active forwarding route, IP connectivity, DNS resolution, Service Availability,
              and Network Health.
    """
    actions = []
    action_details = []

    # Resolve endpoints
    src = source
    dst = target
    if src is None and isinstance(state, dict):
        src = state.get("source")
    if dst is None and isinstance(state, dict):
        dst = state.get("target")
    src, dst = resolve_endpoints(g, src, dst)

    # If diagnosis findings were not provided, perform independent observation & diagnosis
    if findings is None:
        obs_pre = collect_observations(g, state=state, source=src, target=dst)
        findings = diagnose(obs_pre)
    else:
        # Collect baseline pre-recovery observation for before-and-after comparison
        obs_pre = collect_observations(g, state=state, source=src, target=dst)

    # Extract set of diagnosed root causes and affected entities
    diagnosed_causes = {getattr(f, "root_cause", f[0]) for f in findings}
    affected_links = []
    for f in findings:
        aff = getattr(f, "affected_components", [])
        for item in aff:
            if "-" in str(item):
                affected_links.append(str(item))

    has_link_failure = "Link failure" in diagnosed_causes
    has_gateway_fault = "Incorrect default gateway" in diagnosed_causes
    has_dns_fault = "DNS service failure" in diagnosed_causes
    has_latency_fault = "High latency" in diagnosed_causes
    has_loss_fault = "Packet loss" in diagnosed_causes

    # Track specific execution and success flags
    action_executed = False
    failover_success = None
    gateway_success = None
    dns_success = None
    latency_success = None
    loss_success = None
    failover_reason = None
    route_already_active = False

    # -------------------------------------------------------------------------
    # Strategy 2: Correct Wrong Default Gateway
    # Identifies affected host and reconfigures gateway to the valid local router.
    # Does NOT reroute around the gateway misconfiguration.
    # -------------------------------------------------------------------------
    if has_gateway_fault:
        gw_findings = [f for f in findings if getattr(f, "root_cause", f[0]) == "Incorrect default gateway"]
        target_hosts = []
        for gf in gw_findings:
            aff = getattr(gf, "affected_components", [])
            if aff:
                target_hosts.append(aff[0])
        if not target_hosts:
            target_hosts = ["PC1"] if "PC1" in g.nodes else []

        for host in target_hosts:
            if host in g.nodes:
                old_gw = g.nodes[host].get("gateway", "Unknown")
                # Dynamically determine valid gateway router from topology
                router_nbrs = [nbr for nbr in g.neighbors(host) if g.nodes[nbr].get("type") == "Router"]
                if router_nbrs:
                    correct_gw = router_nbrs[0]
                else:
                    all_routers = [n for n, d in g.nodes(data=True) if d.get("type") == "Router" and nx.has_path(g, host, n)]
                    correct_gw = all_routers[0] if all_routers else "R1"

                # Apply actual state modification
                g.nodes[host]["gateway"] = correct_gw
                g.graph["gateway"] = correct_gw

                msg = f"Corrected default gateway for {host} from '{old_gw}' to valid router '{correct_gw}'."
                actions.append(msg)
                action_details.append({
                    "fault": "Incorrect default gateway",
                    "action": f"Reconfigured gateway on {host}",
                    "before": f"{host} gateway = '{old_gw}'",
                    "after": f"{host} gateway = '{correct_gw}' (Valid)"
                })
                action_executed = True
                gateway_success = True

    # -------------------------------------------------------------------------
    # Strategy 3: Restore DNS Service
    # Restores simulated DNS service availability and validates resolver settings.
    # -------------------------------------------------------------------------
    if has_dns_fault:
        before_dns = bool(g.graph.get("dns_available", True))
        g.graph["dns_available"] = True
        for n, d in g.nodes(data=True):
            if d.get("type") in ("PC", "Laptop") and d.get("dns_server") != "192.168.1.1":
                d["dns_server"] = "192.168.1.1"

        msg = "Restored simulated DNS service and verified client resolver configuration."
        actions.append(msg)
        action_details.append({
            "fault": "DNS service failure",
            "action": "Restored DNS service availability",
            "before": f"dns_available = {before_dns}",
            "after": "dns_available = True (Operational)"
        })
        action_executed = True
        dns_success = True

    # -------------------------------------------------------------------------
    # Strategy 4: High Latency Mitigation
    # Reroutes traffic only if an alternative route offers strictly lower latency.
    # -------------------------------------------------------------------------
    if has_latency_fault:
        all_routes = discover_routes(g, source=src, target=dst)
        curr_p = get_active_route(g, src, dst) or (all_routes[0]["path"] if all_routes else None)
        curr_lat = calculate_route_metrics(g, curr_p)["latency_ms"] if curr_p else 999.0

        healthy_routes = [r for r in all_routes if r.get("is_usable") and not r.get("is_degraded")]
        usable_routes = [r for r in all_routes if r.get("is_usable")]

        candidate = None
        if healthy_routes:
            candidate = min(healthy_routes, key=lambda r: (r["latency_ms"], r["cost"]))
        elif usable_routes:
            candidate = min(usable_routes, key=lambda r: (r["latency_ms"], r["cost"]))

        if candidate and candidate["latency_ms"] < curr_lat:
            set_active_route(g, candidate["path"])
            msg = f"Rerouted traffic to lower-latency route: {' -> '.join(candidate['path'])} ({curr_lat} ms -> {candidate['latency_ms']} ms)."
            actions.append(msg)
            action_details.append({
                "fault": "High latency",
                "action": "Activated low-latency route",
                "before": f"Route: {' -> '.join(curr_p) if curr_p else 'None'} ({curr_lat} ms)",
                "after": f"Route: {' -> '.join(candidate['path'])} ({candidate['latency_ms']} ms)"
            })
            action_executed = True
            latency_success = True
        else:
            msg = f"High latency optimization UNAVAILABLE: No alternative route offers lower latency than the current path ({curr_lat} ms)."
            actions.append(msg)
            action_details.append({
                "fault": "High latency",
                "action": "Optimization unavailable",
                "before": f"Route: {' -> '.join(curr_p) if curr_p else 'None'} ({curr_lat} ms)",
                "after": "Current path maintained; no superior alternative exists"
            })
            latency_success = False

    # -------------------------------------------------------------------------
    # Strategy 5: Packet Loss Mitigation
    # Reroutes traffic only if an alternative route offers strictly lower packet loss.
    # -------------------------------------------------------------------------
    if has_loss_fault:
        all_routes = discover_routes(g, source=src, target=dst)
        curr_p = get_active_route(g, src, dst) or (all_routes[0]["path"] if all_routes else None)
        curr_loss = calculate_route_metrics(g, curr_p)["max_loss"] if curr_p else 100.0

        healthy_routes = [r for r in all_routes if r.get("is_usable") and not r.get("is_degraded")]
        usable_routes = [r for r in all_routes if r.get("is_usable")]

        candidate = None
        if healthy_routes:
            candidate = min(healthy_routes, key=lambda r: (r["max_loss"], r["latency_ms"], r["cost"]))
        elif usable_routes:
            candidate = min(usable_routes, key=lambda r: (r["max_loss"], r["latency_ms"], r["cost"]))

        if candidate and candidate["max_loss"] < curr_loss:
            set_active_route(g, candidate["path"])
            msg = f"Rerouted traffic to lower-loss route: {' -> '.join(candidate['path'])} ({curr_loss}% -> {candidate['max_loss']}%)."
            actions.append(msg)
            action_details.append({
                "fault": "Packet loss",
                "action": "Activated low-loss route",
                "before": f"Route: {' -> '.join(curr_p) if curr_p else 'None'} ({curr_loss}% loss)",
                "after": f"Route: {' -> '.join(candidate['path'])} ({candidate['max_loss']}% loss)"
            })
            action_executed = True
            loss_success = True
        else:
            msg = f"Packet loss recovery UNAVAILABLE: No alternative route offers lower packet loss than the current path ({curr_loss}%)."
            actions.append(msg)
            action_details.append({
                "fault": "Packet loss",
                "action": "Recovery unavailable",
                "before": f"Route: {' -> '.join(curr_p) if curr_p else 'None'} ({curr_loss}% loss)",
                "after": "Current path maintained; no lossless alternative exists"
            })
            loss_success = False

    # -------------------------------------------------------------------------
    # Strategy 1: Link Failure Recovery
    # Detects whether a valid alternative route is already active.
    # Only activates failover when the currently active route is broken or not avoiding failed links.
    # Keeps failed link strictly DOWN.
    # -------------------------------------------------------------------------
    if has_link_failure:
        down_summary = ", ".join(affected_links) if affected_links else "failed link(s)"
        all_routes = discover_routes(g, source=src, target=dst)
        usable_routes = [r for r in all_routes if r.get("is_usable")]

        # Inspect currently active route
        current_active = get_active_route(g, src, dst)
        if current_active and len(current_active) >= 2 and path_is_usable(g, current_active):
            # Check if active route hops avoid all failed/DOWN links
            active_hops = {f"{u}-{v}" for u, v in zip(current_active, current_active[1:])} | \
                          {f"{v}-{u}" for u, v in zip(current_active, current_active[1:])}
            failed_set = set(affected_links)
            down_set = {f"{u}-{v}" for u, v, d in g.edges(data=True) if d.get("status") != "UP"} | \
                       {f"{v}-{u}" for u, v, d in g.edges(data=True) if d.get("status") != "UP"}
            if not (active_hops & failed_set) and not (active_hops & down_set):
                route_already_active = True

        if route_already_active:
            # A valid alternative route is ALREADY active!
            # Do not unnecessarily activate another route. Keep failed link DOWN.
            # Record that service is maintained through existing alternative route; no corrective action needed.
            route_str = " -> ".join(current_active)
            msg = f"Service is maintained through existing alternative route: {route_str}."
            actions.append(msg)
            failover_reason = "A healthy alternative route was already active."
            failover_success = True
            # Verification is never counted as a corrective action: action_details is untouched
        elif usable_routes:
            # Healthy alternative route exists but is NOT currently active: activate it!
            selection = select_best_route(g, routes=usable_routes, source=src, target=dst)
            best_alt = selection["selected_path"]
            set_active_route(g, best_alt)
            route_str = " -> ".join(best_alt)
            msg = f"Kept failed {down_summary} link DOWN and selected available alternate route: {route_str}."
            actions.append(msg)
            action_details.append({
                "fault": "Link failure",
                "action": "Activated alternate forwarding route",
                "before": f"Failed link(s): {down_summary} (Status: DOWN)",
                "after": f"Active route: {route_str} (All links UP)"
            })
            action_executed = True
            failover_success = True
        else:
            msg = f"Link failure detected on {down_summary}: No alternative route exists between {src} and {dst}; recovery is unavailable."
            actions.append(msg)
            action_details.append({
                "fault": "Link failure",
                "action": "Failover unavailable",
                "before": f"Failed link(s): {down_summary} (Status: DOWN)",
                "after": "No alternative route exists in topology"
            })
            failover_success = False

    # -------------------------------------------------------------------------
    # Baseline Healthy Network
    # -------------------------------------------------------------------------
    if not (has_link_failure or has_gateway_fault or has_dns_fault or has_latency_fault or has_loss_fault):
        has_any_degraded = any(
            d.get("latency_ms", 0) > 100 or d.get("packet_loss", 0) > 0
            for _, _, d in g.edges(data=True)
        )
        if has_any_degraded:
            alt = shortest_path(g, source=src, target=dst, avoid_degraded=True)
            if alt:
                set_active_route(g, alt)
                actions.append("Selected an alternate route avoiding degraded links.")
                action_details.append({
                    "fault": "Degraded links",
                    "action": "Selected alternate route avoiding degraded links",
                    "before": "Degraded path active",
                    "after": f"Active route: {' -> '.join(alt)}"
                })
                action_executed = True
            else:
                actions.append("No alternate degradation-free path found; keeping shortest available path.")
        else:
            actions.append("No repair required; baseline state is healthy.")
            # Do NOT generate fake "Baseline verification" in action_details

    # -------------------------------------------------------------------------
    # PART 5: INDEPENDENT POST-RECOVERY VERIFICATION
    # Collects fresh observations after recovery actions to independently verify health.
    # -------------------------------------------------------------------------
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
        if not failover_success or not post_obs["reachability"] or not links_remain_down:
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

    verified = bool(verification_passed and (ip_ok and dns_ok))

    # -------------------------------------------------------------------------
    # Distinguish Service Availability from Network Health
    # -------------------------------------------------------------------------
    # Service Availability: AVAILABLE / UNAVAILABLE
    service_available = bool(ip_ok and dns_ok and post_obs["reachability"])
    service_availability = "AVAILABLE" if service_available else "UNAVAILABLE"

    # Network Health: HEALTHY / DEGRADED / CRITICAL
    # A network with a failed link must not be reported as fully HEALTHY merely because an alternate route works.
    has_any_down = len(post_down_links) > 0
    has_any_high_lat = len(post_obs.get("high_latency", [])) > 0
    has_any_loss = len(post_obs.get("packet_loss", [])) > 0

    if not service_available or (has_link_failure and not post_obs["reachability"]):
        network_health = "CRITICAL"
    elif has_any_down or has_any_high_lat or has_any_loss:
        network_health = "DEGRADED"
    else:
        network_health = "HEALTHY"

    # -------------------------------------------------------------------------
    # Determine Recovery Status:
    # RECOVERY VERIFIED / SERVICE MAINTAINED / RECOVERY FAILED / NO RECOVERY REQUIRED
    # -------------------------------------------------------------------------
    if has_link_failure and not post_obs["reachability"]:
        status_msg = "RECOVERY UNAVAILABLE"
    elif has_latency_fault and latency_success is False and len(diagnosed_causes) == 1:
        status_msg = "OPTIMIZATION UNAVAILABLE"
    elif has_loss_fault and loss_success is False and len(diagnosed_causes) == 1:
        status_msg = "RECOVERY UNAVAILABLE"
    elif not verification_passed:
        status_msg = "RECOVERY FAILED"
    elif has_link_failure and route_already_active and not action_executed:
        status_msg = "SERVICE MAINTAINED"
    elif not action_executed:
        status_msg = "NO RECOVERY REQUIRED"
    else:
        status_msg = "RECOVERY VERIFIED"

    reason_str = failover_reason if failover_reason else (
        "Corrective recovery operations verified successfully." if action_executed else "No corrective action was required."
    )

    # Verification checklist
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
        "actions": actions,
        "action_details": action_details,
        "action_executed": action_executed,
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
        "verification_checks": verification_checks
    }

def format_recovery_report(result):
    """Format automated recovery actions into a clean, structured text report (Report C).
    
    Contains exact corrective actions performed and before-and-after state changes.
    Never counts verification as a corrective action.
    """
    actions_count = len(result.get("action_details", []))
    status_str = result.get("status", "UNKNOWN")
    action_exec_str = "YES" if result.get("action_executed") else "NO"

    lines = [
        "=== AUTOMATED RECOVERY REPORT ===",
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
            lines.append(f"• Action {i} [{act.get('fault', 'General')}]:")
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
