"""Network Monitoring and Telemetry Engine.
Collects telemetry observations derived purely from the simulated network graph state.
Does NOT read any injected fault label or ground-truth scenario name.
"""
from network_model import shortest_path, discover_routes, select_best_route, resolve_endpoints
import networkx as nx

def collect_observations(g, state=None, source=None, target=None, latency_threshold=100.0, loss_threshold=0.0):
    """Scan the network topology and collect structured telemetry and health metrics.
    
    All observations are derived strictly from the current simulated network graph state.
    Does NOT read injected fault labels or ground-truth scenario names.
    
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

    for a, b, d in g.edges(data=True):
        label = f"{a}-{b}"
        status = d.get("status", "UP")
        lat = float(d.get("latency_ms", 0.0))
        loss = float(d.get("packet_loss", 0.0))

        if status != "UP":
            down_links.append(label)
            down_edges.append({"link": label, "u": a, "v": b, "status": status})
        if lat > latency_threshold:
            high_latency.append((label, lat))
        if loss > loss_threshold:
            packet_loss.append((label, loss))

    # Resolve source and target endpoints
    src = source
    dst = target
    if src is None and isinstance(state, dict):
        src = state.get("source")
    if dst is None and isinstance(state, dict):
        dst = state.get("target")
    src, dst = resolve_endpoints(g, src, dst)

    # Path discovery and route evaluation
    routes = discover_routes(g, source=src, target=dst)
    route_selection = select_best_route(g, routes=routes, source=src, target=dst)
    selected_path = route_selection["selected_path"]

    # Calculate end-to-end telemetry along selected path
    if selected_path and len(selected_path) >= 2:
        path_edges = [g[u][v] for u, v in zip(selected_path, selected_path[1:]) if g.has_edge(u, v)]
        e2e_latency = round(sum(float(e.get("latency_ms", 2.0)) for e in path_edges), 2)
        path_loss = round(max((float(e.get("packet_loss", 0.0)) for e in path_edges), default=0.0), 2)
        reachability = all(e.get("status") == "UP" for e in path_edges)
    else:
        e2e_latency = None
        path_loss = 100.0
        reachability = False

    # Audit default gateway configuration and reachability
    invalid_gateways = []
    gw = g.nodes["PC1"].get("gateway", g.graph.get("gateway", "R1")) if "PC1" in g.nodes else g.graph.get("gateway", "R1")

    # Inspect all hosts (PC and Laptop nodes)
    for node, data in g.nodes(data=True):
        if data.get("type") in ("PC", "Laptop"):
            node_gw = data.get("gateway", gw)
            # Verify if gateway exists in topology
            if node_gw not in g.nodes:
                invalid_gateways.append({
                    "host": node,
                    "configured_gateway": node_gw,
                    "reason": f"Gateway node '{node_gw}' does not exist in the network topology"
                })
            else:
                # Gateway node exists: check if it is a Router and reachable
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
                    # Check if path to gateway is UP
                    gw_path = shortest_path(g, node, node_gw)
                    if not gw_path:
                        invalid_gateways.append({
                            "host": node,
                            "configured_gateway": node_gw,
                            "reason": f"Path between host '{node}' and gateway '{node_gw}' is DOWN"
                        })

    # Overall gateway_ok flag for PC1/primary host
    if "PC1" in g.nodes:
        pc1_gw = g.nodes["PC1"].get("gateway", gw)
        gateway_ok = not any(ig["host"] == "PC1" for ig in invalid_gateways) and (
            pc1_gw in ("R1", "192.168.1.1") or (
                pc1_gw in g.nodes and g.nodes[pc1_gw].get("type") == "Router" and nx.has_path(g, "PC1", pc1_gw)
            )
        )
    else:
        gateway_ok = len(invalid_gateways) == 0

    # DNS service availability and name resolution probe
    dns_service_up = bool(g.graph.get("dns_available", True))
    dns_ok = dns_service_up
    dns_resolution = dns_service_up

    return {
        "reachability": reachability,
        "ping_success": reachability,
        "source_dest_reachable": reachability,
        "path": selected_path,
        "active_path": selected_path,
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
        "route_selection": route_selection,
        "source": src,
        "target": dst,
        "latency_threshold": latency_threshold,
        "loss_threshold": loss_threshold
    }
