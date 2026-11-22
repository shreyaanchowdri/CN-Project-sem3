"""Network Monitoring and Telemetry Engine.
Collects telemetry observations derived purely from the simulated network graph state.
Does NOT read any injected fault label, hidden scenario metadata, or ground truth.
Does NOT diagnose root causes, recommend recovery, activate routes, or modify network state.
"""
import networkx as nx
from network_model import (
    shortest_path,
    discover_routes,
    select_best_route,
    resolve_endpoints,
    get_active_route,
    path_is_usable
)

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

    for a, b, d in g.edges(data=True):
        label = f"{a}-{b}"
        status = d.get("status", "UP")
        lat = float(d.get("latency_ms", 0.0))
        loss = float(d.get("packet_loss", 0.0))

        link_status[label] = status
        link_latencies[label] = lat
        link_packet_loss[label] = loss

        if status != "UP":
            down_links.append(label)
            down_edges.append({"link": label, "u": a, "v": b, "status": status})
        if lat > latency_threshold:
            high_latency.append((label, lat))
        if loss > loss_threshold:
            packet_loss.append((label, loss))

    # Device Status Audit
    device_status = {}
    for node, data in g.nodes(data=True):
        # A node is operational if it exists in the graph topology
        device_status[node] = "UP"

    # Resolve source and target endpoints
    src = source
    dst = target
    if src is None and isinstance(state, dict):
        src = state.get("source")
    if dst is None and isinstance(state, dict):
        dst = state.get("target")
    src, dst = resolve_endpoints(g, src, dst)

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

    if observed_path and len(observed_path) >= 2:
        path_edges = [g[u][v] for u, v in zip(observed_path, observed_path[1:]) if g.has_edge(u, v)]
        e2e_latency = round(sum(float(e.get("latency_ms", 2.0)) for e in path_edges), 2)
        path_loss = round(max((float(e.get("packet_loss", 0.0)) for e in path_edges), default=0.0), 2)
        reachability = bool(usable_routes)
    else:
        e2e_latency = None
        path_loss = 100.0
        reachability = False

    # Default Gateway Audit
    invalid_gateways = []
    gw = g.nodes["PC1"].get("gateway", g.graph.get("gateway", "R1")) if "PC1" in g.nodes else g.graph.get("gateway", "R1")

    for node, data in g.nodes(data=True):
        if data.get("type") in ("PC", "Laptop"):
            node_gw = data.get("gateway", gw)
            if node_gw not in g.nodes:
                invalid_gateways.append({
                    "host": node,
                    "configured_gateway": node_gw,
                    "reason": f"Gateway node '{node_gw}' does not exist in the network topology"
                })
            else:
                gw_type = g.nodes[node_gw].get("type")
                if gw_type != "Router":
                    invalid_gateways.append({
                        "host": node,
                        "configured_gateway": node_gw,
                        "reason": f"Gateway node '{node_gw}' is of type '{gw_type}', not a Router"
                    })
                elif not nx.has_path(g, node, node_gw):
                    invalid_gateways.append({
                        "host": node,
                        "configured_gateway": node_gw,
                        "reason": f"No physical path between host '{node}' and gateway '{node_gw}'"
                    })
                else:
                    gw_path = shortest_path(g, node, node_gw)
                    if not gw_path:
                        invalid_gateways.append({
                            "host": node,
                            "configured_gateway": node_gw,
                            "reason": f"Path between host '{node}' and gateway '{node_gw}' is DOWN"
                        })

    if "PC1" in g.nodes:
        pc1_gw = g.nodes["PC1"].get("gateway", gw)
        gateway_ok = not any(ig["host"] == "PC1" for ig in invalid_gateways) and (
            pc1_gw in ("R1", "192.168.1.1") or (
                pc1_gw in g.nodes and g.nodes[pc1_gw].get("type") == "Router" and nx.has_path(g, "PC1", pc1_gw)
            )
        )
    else:
        gateway_ok = len(invalid_gateways) == 0

    # DNS Service Probe
    dns_service_up = bool(g.graph.get("dns_available", True))
    dns_ok = dns_service_up
    dns_resolution = dns_service_up

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
        "packet_loss": packet_loss,
        "routes": routes,
        "available_healthy_routes": healthy_routes,
        "healthy_routes_count": healthy_routes_count,
        "route_selection": route_selection,
        "source": src,
        "target": dst,
        "latency_threshold": latency_threshold,
        "loss_threshold": loss_threshold
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
    
    lines = [
        "=== NETWORK MONITORING REPORT ===",
        f"Endpoint: {src} -> {dst}",
        f"Reachability: {reach}",
        f"Failed links: {down_str}",
        f"Default gateway: {gw_str}",
        f"DNS resolution: {dns_str}",
        f"End-to-end latency: {lat_str}",
        f"Packet loss: {loss_str}",
        f"Available healthy routes: {healthy_cnt}"
    ]
    return "\n".join(lines)

# Public alias
generate_monitoring_report = format_monitoring_report
