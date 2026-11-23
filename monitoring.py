"""Network Monitoring and Telemetry Engine.

Collects telemetry observations derived purely from the simulated network graph state.
Does NOT read any injected fault label, hidden scenario metadata, or ground truth.
Does NOT diagnose root causes, recommend recovery, activate routes, or modify network state.
Includes comprehensive Network Partition Analysis, connected-component isolation,
independent probabilistic packet-loss calculations, and multi-link telemetry.
"""
import networkx as nx
from network_model import (
    shortest_path,
    discover_routes,
    select_best_route,
    resolve_endpoints,
    get_active_route,
    path_is_usable,
    resolve_gateway_node
)


def calculate_path_packet_loss_probabilistic(path_edges) -> float:
    """Calculate end-to-end packet loss assuming independent link loss probabilities:
    P(end-to-end loss) = 1 - product(1 - p_i).
    
    Converts individual link percentages into probabilities [0, 1], multiplies
    independent success probabilities, and converts the complement back to percentage.
    """
    if not path_edges:
        return 0.0
    prob_success = 1.0
    for e in path_edges:
        loss_pct = float(e.get("packet_loss", 0.0))
        p_i = max(0.0, min(100.0, loss_pct)) / 100.0
        prob_success *= (1.0 - p_i)
    return round((1.0 - prob_success) * 100.0, 2)


def analyze_network_partitions(g: nx.Graph, source=None, target=None) -> dict:
    """Perform connected-component analysis on the operational subgraph (excluding DOWN links).
    
    Identifies connected components, isolated devices, partition status, and whether
    source and target endpoints remain in the same operational component.
    """
    # Operational subgraph includes all devices but ONLY links with status UP
    g_op = nx.Graph()
    g_op.add_nodes_from(g.nodes(data=True))
    for u, v, d in g.edges(data=True):
        if d.get("status") == "UP":
            g_op.add_edge(u, v, **d)

    components = [sorted(list(c)) for c in nx.connected_components(g_op)]
    num_components = len(components)
    is_partitioned = num_components > 1

    # Isolated devices have degree 0 in operational graph
    isolated_devices = sorted([n for n in g_op.nodes if g_op.degree(n) == 0])

    src_dst_connected = False
    partition_blocks_traffic = False
    if source and target and source in g_op and target in g_op:
        if source == target:
            src_dst_connected = True
            partition_blocks_traffic = False
        else:
            src_dst_connected = nx.has_path(g_op, source, target)
            partition_blocks_traffic = not src_dst_connected

    # Down links contributing to partition
    down_links = [f"{u}-{v}" for u, v, d in g.edges(data=True) if d.get("status") != "UP"]

    return {
        "is_partitioned": is_partitioned,
        "component_count": num_components,
        "components": components,
        "isolated_devices": isolated_devices,
        "source_target_connected": src_dst_connected,
        "partition_blocks_traffic": partition_blocks_traffic,
        "contributing_failed_links": down_links,
        "operational_nodes_count": g_op.number_of_nodes(),
        "operational_edges_count": g_op.number_of_edges()
    }


def collect_observations(g, state=None, source=None, target=None, latency_threshold=100.0, loss_threshold=0.0):
    """Scan network topology and collect structured telemetry and health metrics.
    
    All observations are derived strictly from the current simulated network graph state.
    Does NOT read injected fault labels, scenario metadata, or expected diagnosis.
    Does NOT modify network configuration or activate recovery routes.
    
    Parameters:
        g (nx.Graph): Network graph model.
        state (dict, optional): May contain endpoint selections (source, target).
        source (str, optional): Source node override.
        target (str, optional): Target node override.
        latency_threshold (float): Threshold in ms above which a link is flagged high latency.
        loss_threshold (float): Threshold in % above which a link is flagged for packet loss.
        
    Returns:
        dict: Comprehensive structured telemetry observations.
    """
    down_links = []
    down_edges = []
    high_latency = []
    packet_loss = []
    link_status = {}
    link_latencies = {}
    link_packet_loss = {}
    link_classifications = {}
    degraded_links = []
    healthy_links = []

    for a, b, d in g.edges(data=True):
        label = f"{a}-{b}"
        status = d.get("status", "UP")
        lat = float(d.get("latency_ms", 0.0))
        loss = float(d.get("packet_loss", 0.0))

        link_status[label] = status
        link_latencies[label] = lat
        link_packet_loss[label] = loss

        is_degraded = (status == "UP") and (lat > latency_threshold or loss > loss_threshold)
        if status != "UP":
            classification = "DOWN"
            down_links.append(label)
            down_edges.append({"link": label, "u": a, "v": b, "status": status})
        elif is_degraded:
            classification = "DEGRADED"
            degraded_links.append(label)
        else:
            classification = "UP"
            healthy_links.append(label)

        link_classifications[label] = classification

        if lat > latency_threshold:
            high_latency.append((label, lat))
        if loss > loss_threshold:
            packet_loss.append((label, loss))

    # Device Status Audit
    device_status = {}
    for node, data in g.nodes(data=True):
        device_status[node] = "UP"

    # Resolve source and target endpoints
    src = source
    dst = target
    if src is None and isinstance(state, dict):
        src = state.get("source")
    if dst is None and isinstance(state, dict):
        dst = state.get("target")
    src, dst = resolve_endpoints(g, src, dst)

    # Network Partition Analysis
    partition_info = analyze_network_partitions(g, source=src, target=dst)

    # Route Discovery: observe all loopless paths without activating any route
    routes = discover_routes(g, source=src, target=dst)
    usable_routes = [r for r in routes if r.get("is_usable")]
    healthy_routes = [r for r in usable_routes if not r.get("is_degraded")]
    healthy_routes_count = len(healthy_routes)

    # Current forwarding state: observe currently activated route
    active_path = get_active_route(g, source=src, target=dst)
    active_path_usable = path_is_usable(g, active_path) if active_path else False

    # Route Evaluation / Candidate Recommendation for matrix (does NOT activate route)
    route_selection = select_best_route(g, routes=routes, source=src, target=dst)
    best_candidate_path = route_selection["selected_path"]

    # Endpoint Reachability and Telemetry along active route or best usable route
    observed_path = None
    if active_path and active_path_usable:
        observed_path = active_path
    elif best_candidate_path:
        observed_path = best_candidate_path

    if observed_path and len(observed_path) == 1 and observed_path[0] in g:
        e2e_latency = 0.1
        path_loss = 0.0
        max_link_loss = 0.0
        reachability = True
    elif observed_path and len(observed_path) >= 2:
        path_edges = [g[u][v] for u, v in zip(observed_path, observed_path[1:]) if g.has_edge(u, v)]
        e2e_latency = round(sum(float(e.get("latency_ms", 2.0)) for e in path_edges), 2)
        # Probabilistic end-to-end packet loss assuming independent link loss probabilities
        path_loss = calculate_path_packet_loss_probabilistic(path_edges)
        max_link_loss = round(max((float(e.get("packet_loss", 0.0)) for e in path_edges), default=0.0), 2)
        reachability = bool(usable_routes) and partition_info["source_target_connected"]
    else:
        e2e_latency = None
        path_loss = 100.0
        max_link_loss = 100.0
        reachability = False

    # Default Gateway Audit
    invalid_gateways = []
    host_to_audit = src if (src in g.nodes and g.nodes[src].get("type") in ("PC", "Laptop")) else ("PC1" if "PC1" in g.nodes else None)
    gw = g.nodes[host_to_audit].get("gateway", g.graph.get("gateway", "R1")) if host_to_audit else g.graph.get("gateway", "R1")

    for node, data in g.nodes(data=True):
        if data.get("type") in ("PC", "Laptop"):
            node_gw = data.get("gateway", gw)
            gw_router, gw_valid, gw_err = resolve_gateway_node(g, node, node_gw)
            if not gw_valid:
                invalid_gateways.append({
                    "host": node,
                    "configured_gateway": node_gw,
                    "reason": gw_err
                })
            else:
                gw_path = shortest_path(g, node, gw_router)
                if not gw_path:
                    invalid_gateways.append({
                        "host": node,
                        "configured_gateway": node_gw,
                        "reason": f"Path between host '{node}' and gateway '{node_gw}' is DOWN"
                    })

    if host_to_audit:
        h_gw = g.nodes[host_to_audit].get("gateway", gw)
        h_router, h_valid, _ = resolve_gateway_node(g, host_to_audit, h_gw)
        gateway_ok = not any(ig["host"] == host_to_audit for ig in invalid_gateways) and h_valid
    else:
        gateway_ok = len(invalid_gateways) == 0

    # DNS Service Probe
    dns_service_up = bool(g.graph.get("dns_available", True))
    dns_ok = dns_service_up
    dns_resolution = dns_service_up

    # Device reachability mapping from source
    unreachable_devices = []
    if src and src in g:
        for n in g.nodes:
            if n != src and not any(src in comp and n in comp for comp in partition_info["components"]):
                unreachable_devices.append(n)

    return {
        "reachability": reachability,
        "ping_success": reachability,
        "source_dest_reachable": reachability,
        "path": observed_path,
        "active_path": active_path,
        "active_path_usable": active_path_usable,
        "device_status": device_status,
        "link_status": link_status,
        "link_latencies": link_latencies,
        "link_packet_loss": link_packet_loss,
        "link_classifications": link_classifications,
        "degraded_links": degraded_links,
        "healthy_links": healthy_links,
        "down_links": down_links,
        "down_edges": down_edges,
        "invalid_gateways": invalid_gateways,
        "gateway": gw,
        "gateway_ok": gateway_ok,
        "dns_ok": dns_ok,
        "dns_resolution": dns_resolution,
        "end_to_end_latency_ms": e2e_latency,
        "high_latency": high_latency,
        "path_packet_loss": path_loss,
        "max_link_packet_loss": max_link_loss,
        "packet_loss": packet_loss,
        "routes": routes,
        "available_healthy_routes": healthy_routes,
        "healthy_routes_count": healthy_routes_count,
        "route_selection": route_selection,
        "source": src,
        "target": dst,
        "latency_threshold": latency_threshold,
        "loss_threshold": loss_threshold,
        "partition_analysis": partition_info,
        "is_partitioned": partition_info["is_partitioned"],
        "connected_components": partition_info["components"],
        "isolated_devices": partition_info["isolated_devices"],
        "unreachable_devices": unreachable_devices
    }


def format_monitoring_report(obs):
    """Format observed network telemetry into a clean, structured text report (Report A).
    
    Contains only observed network conditions without diagnosing root causes or modifying state.
    """
    src = obs.get("source", "PC1")
    dst = obs.get("target", "Server")
    reach = "REACHABLE" if obs.get("reachability") else "UNREACHABLE"
    
    down_links = obs.get("down_links", [])
    down_str = ", ".join(down_links) if down_links else "None (All UP)"

    degraded_links = obs.get("degraded_links", [])
    degraded_str = ", ".join(degraded_links) if degraded_links else "None"
    
    gw = obs.get("gateway", "R1")
    gw_ok = obs.get("gateway_ok", True)
    gw_str = f"{gw} (Valid)" if gw_ok else f"{gw} (Invalid)"
    
    dns_ok = obs.get("dns_ok", True)
    dns_str = "OPERATIONAL" if dns_ok else "FAILED"
    
    lat = obs.get("end_to_end_latency_ms")
    lat_str = f"{lat} ms" if lat is not None else "N/A (Path broken)"
    
    loss = obs.get("path_packet_loss")
    loss_str = f"{loss}%" if loss is not None else "100% (Unreachable)"
    
    healthy_cnt = obs.get("healthy_routes_count", 0)

    # Partition telemetry
    part_info = obs.get("partition_analysis", {})
    is_part = part_info.get("is_partitioned", False)
    comp_cnt = part_info.get("component_count", 1)
    isolated = part_info.get("isolated_devices", [])
    isolated_str = ", ".join(isolated) if isolated else "None"
    part_str = f"PARTITIONED ({comp_cnt} isolated segments)" if is_part else "CONNECTED (Single segment)"

    lines = [
        "=== NETWORK MONITORING REPORT ===",
        f"Endpoint: {src} -> {dst}",
        f"Reachability: {reach}",
        f"Network Topology State: {part_str}",
        f"Isolated Devices: {isolated_str}",
        f"Failed links: {down_str}",
        f"Degraded links: {degraded_str}",
        f"Default gateway: {gw_str}",
        f"DNS resolution: {dns_str}",
        f"End-to-end latency: {lat_str}",
        f"Packet loss: {loss_str} (P = 1 - ∏(1-p_i))",
        f"Available healthy routes: {healthy_cnt}"
    ]
    return "\n".join(lines)


# Public aliases
generate_monitoring_report = format_monitoring_report
