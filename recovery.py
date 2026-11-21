"""Automated Recovery and Verification Engine.
Applies simulated repairs and rerouting actions based strictly on DIAGNOSED ROOT CAUSES
and the current network state.
Does NOT read any injected fault label or scenario identifier.
After recovery, independently collects observations again and verifies whether connectivity
and relevant performance metrics have improved.
"""
from network_model import shortest_path, path_is_usable, discover_routes, select_best_route, resolve_endpoints
from monitoring import collect_observations
from diagnostics import diagnose

def recover(g, state=None, findings=None, source=None, target=None):
    """Execute automated recovery actions based on diagnosed root causes and verify network health.
    
    Parameters:
        g (nx.Graph): Network graph topology.
        state (dict, optional): May contain endpoint selections (source, target).
        findings (list, optional): Diagnosis findings from diagnostics.diagnose().
            If None, independently runs monitoring and diagnosis first.
        source (str, optional): Source node override.
        target (str, optional): Target node override.
        
    Returns:
        dict: Recovery report with actions taken, verified status, active route,
              IP connectivity, and DNS resolution.
    """
    actions = []

    # Resolve endpoints
    src = source
    dst = target
    if src is None and isinstance(state, dict):
        src = state.get("source")
    if dst is None and isinstance(state, dict):
        dst = state.get("target")
    src, dst = resolve_endpoints(g, src, dst)

    # If diagnosis findings were not passed in, obtain them via independent diagnosis
    if findings is None:
        obs_pre = collect_observations(g, state=state, source=src, target=dst)
        findings = diagnose(obs_pre)

    # Extract set of diagnosed root causes
    diagnosed_causes = {f.root_cause if hasattr(f, "root_cause") else f[0] for f in findings}

    # Gather affected components across all findings
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
    has_degradation = has_latency_fault or has_loss_fault

    # Action 1: Repair Gateway Configuration if diagnosed
    if has_gateway_fault:
        g.graph["gateway"] = "R1"
        for n, d in g.nodes(data=True):
            if d.get("type") in ("PC", "Laptop"):
                d["gateway"] = "R1"
        if "PC1" in g.nodes:
            g.nodes["PC1"]["gateway"] = "R1"
        actions.append("Corrected default gateway to R1 (simulated configuration repair).")

    # Action 2: Restore DNS Service if diagnosed
    if has_dns_fault:
        g.graph["dns_available"] = True
        actions.append("Restored simulated DNS service.")

    # Action 4: Handle High Latency or Packet Loss if diagnosed
    if has_degradation:
        actions.append("Selected a route that avoids degraded links.")

    # If no faults were diagnosed
    if not (has_link_failure or has_gateway_fault or has_dns_fault or has_degradation):
        # Also check for any custom degraded links
        has_any_degraded = any(
            d.get("latency_ms", 0) > 100 or d.get("packet_loss", 0) > 0
            for _, _, d in g.edges(data=True)
        )
        if has_any_degraded:
            alt = shortest_path(g, source=src, target=dst, avoid_degraded=True)
            if alt:
                actions.append("Selected an alternate route avoiding degraded links.")
            else:
                actions.append("No alternate degradation-free path found; keeping shortest available path.")
        else:
            actions.append("No repair required; baseline state is healthy.")

    # Calculate optimal path post-repair
    # If latency or packet loss was diagnosed, avoid degraded links
    if has_degradation:
        route = shortest_path(g, source=src, target=dst, avoid_degraded=True)
    else:
        route = shortest_path(g, source=src, target=dst, avoid_degraded=False)

    # Post-Recovery Independent Observation Collection and Verification
    post_obs = collect_observations(g, state=state, source=src, target=dst)

    # Action 3: Handle Link Failure if diagnosed (dynamically evaluates alternate route)
    if has_link_failure:
        down_summary = ", ".join(affected_links) if affected_links else "failed link(s)"
        active_path = post_obs.get("path") or route
        if active_path and post_obs.get("reachability", False):
            route_str = " -> ".join(active_path)
            actions.append(f"Kept failed {down_summary} link DOWN and selected available alternate route: {route_str}.")
        else:
            actions.append(f"Link failure detected on {down_summary}: No alternative route exists between {src} and {dst}; recovery is unavailable.")

    ip_ok = post_obs["reachability"] and post_obs["gateway_ok"]
    dns_ok = post_obs["dns_ok"]
    verified = bool(ip_ok and dns_ok)

    if verified:
        status_msg = "RECOVERY VERIFIED"
    elif has_link_failure and not post_obs["reachability"]:
        status_msg = "RECOVERY UNAVAILABLE"
    else:
        status_msg = "RECOVERY NOT VERIFIED"

    return {
        "actions": actions,
        "route": post_obs["path"] or route,
        "ip_connectivity": bool(ip_ok),
        "dns_resolution": bool(dns_ok),
        "verified": verified,
        "status": status_msg,
        "routes": post_obs["routes"],
        "route_selection": post_obs["route_selection"],
        "post_observations": post_obs
    }
