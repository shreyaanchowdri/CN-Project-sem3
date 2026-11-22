"""Graph-based virtual network model and topology management."""
import json
import networkx as nx
from fault_registry import FaultRegistry, get_fault_registry

NODES = {
    "PC1": "End device",
    "R1": "Primary router",
    "R2": "Primary-path router",
    "R3": "Backup-path router",
    "Server": "Destination server"
}

DEFAULT_NODES = set(NODES.keys())

DEVICE_TYPES = ["PC", "Router", "Switch", "Server", "Laptop"]
CONNECTION_TYPES = ["Copper Straight-Through", "Copper Cross-Over", "Fiber", "Serial"]

def generate_unique_device_name(g, device_type="PC"):
    """Generate unique sequential device name (e.g. Router1, Switch1, PC1, Laptop1, Server1)."""
    prefix = str(device_type).strip()
    idx = 1
    while f"{prefix}{idx}" in g.nodes:
        idx += 1
    return f"{prefix}{idx}"

DEFAULT_NODE_DETAILS = {
    "PC1": {
        "type": "PC",
        "kind": "End device",
        "ip": "192.168.1.10",
        "subnet_mask": "255.255.255.0",
        "gateway": "R1",
        "is_default": True
    },
    "R1": {
        "type": "Router",
        "kind": "Primary router",
        "ip": "192.168.1.1",
        "subnet_mask": "255.255.255.0",
        "gateway": "N/A",
        "is_default": True
    },
    "R2": {
        "type": "Router",
        "kind": "Primary-path router",
        "ip": "10.0.1.1",
        "subnet_mask": "255.255.255.0",
        "gateway": "N/A",
        "is_default": True
    },
    "R3": {
        "type": "Router",
        "kind": "Backup-path router",
        "ip": "10.0.2.1",
        "subnet_mask": "255.255.255.0",
        "gateway": "N/A",
        "is_default": True
    },
    "Server": {
        "type": "Server",
        "kind": "Destination server",
        "ip": "172.16.0.10",
        "subnet_mask": "255.255.255.0",
        "gateway": "R2",
        "is_default": True
    }
}

DEFAULT_POSITIONS = {
    "PC1": (0.0, 1.0),
    "R1": (1.0, 1.0),
    "R2": (2.0, 1.65),
    "R3": (2.0, 0.35),
    "Server": (3.0, 1.0)
}

def build_network():
    """Build and return the baseline network graph."""
    g = nx.Graph()
    for node, kind in NODES.items():
        details = dict(DEFAULT_NODE_DETAILS.get(node, {}))
        details.setdefault("kind", kind)
        details.setdefault("type", "Router" if node.startswith("R") else ("PC" if "PC" in node else "Server"))
        details.setdefault("ip", "192.168.1.1")
        details.setdefault("subnet_mask", "255.255.255.0")
        details.setdefault("gateway", "R1" if details["type"] in ("PC", "Server") else "N/A")
        details["is_default"] = True
        g.add_node(node, **details)

    links = [
        ("PC1", "R1", 1, 2),
        ("R1", "R2", 1, 3),
        ("R2", "Server", 1, 3),
        ("R1", "R3", 2, 4),
        ("R3", "Server", 2, 4)
    ]
    for a, b, cost, latency in links:
        g.add_edge(a, b, cost=cost, status="UP", latency_ms=latency, packet_loss=0.0)

    g.graph.update(
        gateway="R1",
        dns_available=True,
        scenario="No fault",
        node_positions=dict(DEFAULT_POSITIONS),
        active_path=["PC1", "R1", "R2", "Server"],
        activated_route=["PC1", "R1", "R2", "Server"],
        fault_registry=FaultRegistry()
    )
    return g

def is_essential_device(name):
    """Check if device is one of the protected essential baseline devices."""
    return name in DEFAULT_NODES

def add_device(g, name, device_type="PC", ip=None, subnet_mask="255.255.255.0", gateway=None, pos=None, dns_server="192.168.1.1"):
    """Add a new device to the network."""
    name = str(name).strip()
    if not name:
        raise ValueError("Device name cannot be empty.")
    if name in g:
        raise ValueError(f"Device '{name}' already exists in the network.")
    if device_type not in DEVICE_TYPES:
        raise ValueError(f"Invalid device type '{device_type}'. Must be one of {DEVICE_TYPES}.")

    if not ip:
        type_prefix = {
            "PC": "192.168.1.",
            "Laptop": "192.168.1.",
            "Router": "10.0.3.",
            "Switch": "192.168.1.",
            "Server": "172.16.0."
        }
        existing_ips = {d.get("ip") for _, d in g.nodes(data=True) if d.get("ip")}
        idx = 20
        while f"{type_prefix.get(device_type, '192.168.1.')}{idx}" in existing_ips:
            idx += 1
        ip = f"{type_prefix.get(device_type, '192.168.1.')}{idx}"

    if gateway is None:
        gateway = "R1" if device_type in ("PC", "Laptop", "Server") else "N/A"

    g.add_node(
        name,
        type=device_type,
        kind=f"Custom {device_type}",
        ip=str(ip).strip(),
        subnet_mask=str(subnet_mask).strip(),
        gateway=str(gateway).strip(),
        dns_server=str(dns_server).strip(),
        is_default=False
    )

    if pos is not None:
        positions = g.graph.setdefault("node_positions", {})
        positions[name] = tuple(pos)

    return name

def remove_device(g, name, force=False):
    """Remove a device from the network. Protects essential default devices unless forced."""
    if name not in g:
        raise ValueError(f"Device '{name}' does not exist.")
    if not force and is_essential_device(name):
        raise ValueError(f"Cannot delete essential default device '{name}'. Default devices are required for standard baseline scenarios.")

    g.remove_node(name)
    if "node_positions" in g.graph and name in g.graph["node_positions"]:
        del g.graph["node_positions"][name]
    return True

def connect_devices(g, a, b, cost=1, latency_ms=2, packet_loss=0.0, status="UP", connection_type="Copper Straight-Through"):
    """Connect two devices with link attributes."""
    if a not in g:
        raise ValueError(f"Device '{a}' does not exist in the network.")
    if b not in g:
        raise ValueError(f"Device '{b}' does not exist in the network.")
    if a == b:
        raise ValueError("Cannot connect a device to itself (self-connections not allowed).")
    if g.has_edge(a, b):
        raise ValueError(f"A link between '{a}' and '{b}' already exists.")

    cost_val = max(1, int(cost))
    latency_val = max(0.0, float(latency_ms))
    loss_val = max(0.0, min(100.0, float(packet_loss)))
    status_val = str(status).upper()
    if status_val not in ("UP", "DOWN"):
        status_val = "UP"
    conn_type = str(connection_type) if connection_type else "Copper Straight-Through"

    g.add_edge(a, b, cost=cost_val, status=status_val, latency_ms=latency_val, packet_loss=loss_val, connection_type=conn_type)
    return True

def disconnect_devices(g, a, b):
    """Disconnect an existing link between two devices."""
    if not g.has_edge(a, b):
        raise ValueError(f"No link exists between '{a}' and '{b}'.")
    g.remove_edge(a, b)
    return True

def configure_device(g, old_name, new_name=None, device_type=None, ip=None, subnet_mask=None, gateway=None, dns_server=None):
    """Edit configuration for a device, with support for renaming."""
    if old_name not in g:
        raise ValueError(f"Device '{old_name}' not found.")

    target_name = old_name
    if new_name and new_name.strip() and new_name.strip() != old_name:
        clean_new = new_name.strip()
        if clean_new in g:
            raise ValueError(f"Device name '{clean_new}' already in use.")
        nx.relabel_nodes(g, {old_name: clean_new}, copy=False)
        target_name = clean_new
        if "node_positions" in g.graph and old_name in g.graph["node_positions"]:
            g.graph["node_positions"][clean_new] = g.graph["node_positions"].pop(old_name)
        if g.graph.get("gateway") == old_name:
            g.graph["gateway"] = clean_new

    node_data = g.nodes[target_name]
    if device_type:
        if device_type not in DEVICE_TYPES:
            raise ValueError(f"Invalid device type '{device_type}'.")
        node_data["type"] = device_type
        if not node_data.get("is_default"):
            node_data["kind"] = f"Custom {device_type}"
    if ip is not None:
        node_data["ip"] = str(ip).strip()
    if subnet_mask is not None:
        node_data["subnet_mask"] = str(subnet_mask).strip()
    if gateway is not None:
        node_data["gateway"] = str(gateway).strip()
    if dns_server is not None:
        node_data["dns_server"] = str(dns_server).strip()

    return target_name

def configure_link(g, a, b, cost=None, latency_ms=None, packet_loss=None, status=None, connection_type=None):
    """Edit link attributes between devices a and b."""
    if not g.has_edge(a, b):
        raise ValueError(f"Link between '{a}' and '{b}' does not exist.")

    edge = g[a][b]
    if cost is not None:
        edge["cost"] = max(1, int(cost))
    if latency_ms is not None:
        edge["latency_ms"] = max(0.0, float(latency_ms))
    if packet_loss is not None:
        edge["packet_loss"] = max(0.0, min(100.0, float(packet_loss)))
    if status is not None:
        st = str(status).upper()
        if st not in ("UP", "DOWN"):
            raise ValueError("Status must be 'UP' or 'DOWN'.")
        edge["status"] = st
    if connection_type is not None:
        edge["connection_type"] = str(connection_type).strip()

    return edge

def save_topology_to_dict(g, positions=None):
    """Serialize graph topology to a clean JSON-friendly dictionary."""
    pos = positions if positions is not None else g.graph.get("node_positions", {})
    devices = []
    for n, d in g.nodes(data=True):
        dev = dict(d)
        dev["name"] = n
        if n in pos:
            dev["pos"] = [round(float(pos[n][0]), 3), round(float(pos[n][1]), 3)]
        devices.append(dev)

    links = []
    for a, b, d in g.edges(data=True):
        link = dict(d)
        link["source"] = a
        link["target"] = b
        links.append(link)

    return {
        "version": "1.0",
        "framework": "Intelligent Network Fault Diagnosis",
        "metadata": {
            "gateway": g.graph.get("gateway", "R1"),
            "dns_available": bool(g.graph.get("dns_available", True)),
            "scenario": g.graph.get("scenario", "No fault"),
            "active_path": g.graph.get("active_path"),
            "activated_route": g.graph.get("activated_route"),
            "fault_registry": get_fault_registry(g).to_dict()
        },
        "devices": devices,
        "links": links
    }

def save_topology_to_file(g, filepath, positions=None):
    """Save graph topology as JSON file."""
    data = save_topology_to_dict(g, positions)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return filepath

def load_topology_from_dict(data):
    """Reconstruct graph topology and positions from dictionary."""
    if not isinstance(data, dict) or "devices" not in data or "links" not in data:
        raise ValueError("Invalid topology data structure.")

    g = nx.Graph()
    meta = data.get("metadata", {})
    reg_data = meta.get("fault_registry")
    reg = FaultRegistry.from_dict(reg_data) if (reg_data and isinstance(reg_data, dict)) else FaultRegistry()
    g.graph.update(
        gateway=meta.get("gateway", "R1"),
        dns_available=bool(meta.get("dns_available", True)),
        scenario=meta.get("scenario", "No fault"),
        active_path=meta.get("active_path"),
        activated_route=meta.get("activated_route"),
        fault_registry=reg
    )

    positions = {}
    for dev in data.get("devices", []):
        dev_copy = dict(dev)
        name = dev_copy.pop("name")
        pos = dev_copy.pop("pos", None)
        if pos and len(pos) >= 2:
            positions[name] = (float(pos[0]), float(pos[1]))
        g.add_node(name, **dev_copy)

    for link in data.get("links", []):
        link_copy = dict(link)
        src = link_copy.pop("source")
        dst = link_copy.pop("target")
        g.add_edge(src, dst, **link_copy)

    g.graph["node_positions"] = positions
    return g, positions

def load_topology_from_file(filepath):
    """Load graph topology and positions from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return load_topology_from_dict(data)

def resolve_endpoints(g, source=None, target=None):
    """Resolve default source and target endpoints in the graph."""
    if not g or g.number_of_nodes() == 0:
        return None, None

    if source is None or source not in g:
        if "PC1" in g:
            source = "PC1"
        else:
            pcs = [n for n, d in g.nodes(data=True) if d.get("type") in ("PC", "Laptop")]
            source = pcs[0] if pcs else list(g.nodes())[0]

    if target is None or target not in g:
        if "Server" in g:
            target = "Server"
        else:
            servers = [n for n, d in g.nodes(data=True) if d.get("type") == "Server"]
            target = servers[0] if servers else list(g.nodes())[-1]

    return source, target

def calculate_route_metrics(g, path):
    """Calculate comprehensive link and path metrics for a route."""
    if not path:
        return {
            "path": [],
            "path_str": "None",
            "hop_count": 0,
            "cost": 0,
            "latency_ms": 0.0,
            "max_loss": 0.0,
            "avg_loss": 0.0,
            "is_usable": False,
            "is_degraded": False,
            "availability": "Unavailable",
            "bottlenecks": ["Empty path"]
        }
    if len(path) == 1:
        node = path[0]
        in_g = node in g
        return {
            "path": path,
            "path_str": f"{node} (Local Loopback)",
            "hop_count": 0,
            "cost": 0,
            "latency_ms": 0.1,
            "max_loss": 0.0,
            "avg_loss": 0.0,
            "is_usable": in_g,
            "is_degraded": False,
            "availability": "Healthy" if in_g else "Unavailable",
            "bottlenecks": [] if in_g else ["Node not in topology"]
        }

    missing_edges = []
    down_links = []
    high_latency_links = []
    loss_links = []

    total_cost = 0
    total_latency = 0.0
    packet_losses = []

    for a, b in zip(path, path[1:]):
        if not g.has_edge(a, b):
            missing_edges.append(f"{a}-{b}")
            continue
        d = g[a][b]
        total_cost += d.get("cost", 1)
        lat = float(d.get("latency_ms", 0.0))
        total_latency += lat
        loss = float(d.get("packet_loss", 0.0))
        packet_losses.append(loss)

        if d.get("status") != "UP":
            down_links.append(f"{a}-{b} (DOWN)")
        if lat > 100:
            high_latency_links.append(f"{a}-{b} ({lat}ms)")
        if loss > 0:
            loss_links.append(f"{a}-{b} ({loss}%)")

    is_usable = (len(missing_edges) == 0 and len(down_links) == 0)
    is_degraded = is_usable and (len(high_latency_links) > 0 or len(loss_links) > 0)

    if not is_usable:
        availability = "Unavailable"
    elif is_degraded:
        availability = "Degraded"
    else:
        availability = "Healthy"

    bottlenecks = down_links + high_latency_links + loss_links

    # Independent probabilistic packet loss: P(e2e) = 1 - product(1 - p_i / 100)
    prob_success = 1.0
    for loss_val in packet_losses:
        p_i = max(0.0, min(100.0, float(loss_val))) / 100.0
        prob_success *= (1.0 - p_i)
    prob_loss_pct = round((1.0 - prob_success) * 100.0, 2)

    return {
        "path": list(path),
        "path_str": " -> ".join(path),
        "hop_count": len(path) - 1,
        "cost": total_cost,
        "latency_ms": round(total_latency, 2),
        "max_loss": round(max(packet_losses, default=0.0), 2),
        "avg_loss": round(sum(packet_losses) / len(packet_losses), 2) if packet_losses else 0.0,
        "probabilistic_loss": prob_loss_pct,
        "end_to_end_loss": prob_loss_pct,
        "is_usable": is_usable,
        "is_degraded": is_degraded,
        "availability": availability,
        "bottlenecks": bottlenecks
    }

def discover_routes(g, source=None, target=None):
    """Discover all simple loopless routes between source and target, evaluated with metrics."""
    src, dst = resolve_endpoints(g, source, target)
    if not src or not dst or src not in g or dst not in g:
        return []
    if src == dst:
        return [calculate_route_metrics(g, [src])]

    try:
        paths = list(nx.all_simple_paths(g, src, dst))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

    discovered = []
    for p in paths:
        metrics = calculate_route_metrics(g, p)
        discovered.append(metrics)

    # Sort routes: 1) Availability (Healthy > Degraded > Unavailable),
    # 2) Cost, 3) Latency, 4) Max Loss, 5) Hop Count
    availability_order = {"Healthy": 0, "Degraded": 1, "Unavailable": 2}
    discovered.sort(key=lambda r: (
        availability_order.get(r["availability"], 3),
        r["cost"],
        r["latency_ms"],
        r["max_loss"],
        r["hop_count"]
    ))

    return discovered

def select_best_route(g, routes=None, source=None, target=None):
    """Compare all discovered routes and select the optimal route with an explainable decision."""
    if isinstance(routes, str):
        # Caller passed positional arguments: select_best_route(g, source, target)
        source, target, routes = routes, source, None
    if routes is None:
        routes = discover_routes(g, source, target)

    src, dst = resolve_endpoints(g, source, target)
    if not routes:
        return {
            "selected_route": None,
            "selected_path": None,
            "route": None,
            "path": None,
            "explanation": f"No physical path exists between {src} and {dst}.",
            "routes": []
        }

    usable_routes = [r for r in routes if r["is_usable"]]

    if not usable_routes:
        broken_summary = "; ".join(
            f"{r['path_str']} ({', '.join(r['bottlenecks']) or 'DOWN'})"
            for r in routes
        )
        return {
            "selected_route": None,
            "selected_path": None,
            "route": None,
            "path": None,
            "explanation": f"All candidate routes are UNAVAILABLE due to link failures: {broken_summary}",
            "routes": routes
        }

    healthy_routes = [r for r in usable_routes if not r["is_degraded"]]

    if healthy_routes:
        best = min(healthy_routes, key=lambda r: (r["cost"], r["latency_ms"], r["max_loss"], r["hop_count"]))
        if len(routes) == 1:
            explanation = (
                f"Selected only available healthy route {best['path_str']} "
                f"(Cost: {best['cost']}, Latency: {best['latency_ms']}ms, Loss: {best['max_loss']}%)."
            )
        else:
            comp_reasons = []
            for alt in routes:
                if alt["path"] == best["path"]:
                    continue
                if not alt["is_usable"]:
                    comp_reasons.append(f"{alt['path_str']} unavailable ({', '.join(alt['bottlenecks'])})")
                elif alt["is_degraded"]:
                    comp_reasons.append(f"{alt['path_str']} degraded ({', '.join(alt['bottlenecks'])})")
                elif alt["cost"] > best["cost"]:
                    comp_reasons.append(f"{alt['path_str']} higher cost ({alt['cost']} vs {best['cost']})")
                elif alt["latency_ms"] > best["latency_ms"]:
                    comp_reasons.append(f"{alt['path_str']} higher latency ({alt['latency_ms']}ms vs {best['latency_ms']}ms)")

            reason_text = "; ".join(comp_reasons) if comp_reasons else "lowest path cost and latency"
            explanation = (
                f"Selected optimal healthy route {best['path_str']} "
                f"(Cost: {best['cost']}, Latency: {best['latency_ms']}ms, Loss: {best['max_loss']}%). "
                f"Alternatives bypassed: {reason_text}."
            )

        return {
            "selected_route": best,
            "selected_path": best["path"],
            "route": best,
            "path": best["path"],
            "explanation": explanation,
            "routes": routes
        }

    # If all usable routes are degraded, pick the least degraded (min loss, min latency, min cost)
    best_degraded = min(usable_routes, key=lambda r: (r["max_loss"], r["latency_ms"], r["cost"]))
    explanation = (
        f"Selected best available degraded route {best_degraded['path_str']} "
        f"(Cost: {best_degraded['cost']}, Latency: {best_degraded['latency_ms']}ms, Loss: {best_degraded['max_loss']}%). "
        f"Warning: No completely healthy path exists in the network."
    )
    return {
        "selected_route": best_degraded,
        "selected_path": best_degraded["path"],
        "route": best_degraded,
        "path": best_degraded["path"],
        "explanation": explanation,
        "routes": routes
    }

def shortest_path(g, source=None, target=None, avoid_degraded=False):
    """Compute the shortest usable path between source and target."""
    if not g or g.number_of_nodes() == 0:
        return None

    src, dst = resolve_endpoints(g, source, target)
    if not src or not dst or src not in g or dst not in g:
        return None
    if src == dst:
        return [src]

    if avoid_degraded:
        selection = select_best_route(g, source=src, target=dst)
        return selection["selected_path"]

    def weight(a, b, d):
        if d.get("status") != "UP":
            return None
        return d.get("cost", 1)

    usable = nx.Graph()
    usable.add_nodes_from(g.nodes(data=True))
    for a, b, d in g.edges(data=True):
        w = weight(a, b, d)
        if w is not None:
            usable.add_edge(a, b, **d)

    try:
        return nx.shortest_path(usable, src, dst, weight="cost")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None

def path_cost(g, path):
    """Calculate total path cost."""
    if not path or len(path) < 2:
        return 0
    return sum(g[a][b].get("cost", 1) for a, b in zip(path, path[1:]))

def path_is_usable(g, path):
    """Check if all links on path exist and have status 'UP'."""
    if not path:
        return False
    if len(path) == 1:
        return path[0] in g
    return all(
        g.has_edge(a, b) and g[a][b].get("status") == "UP" for a, b in zip(path, path[1:])
    )

def get_active_route(g, source=None, target=None):
    """Retrieve the currently activated forwarding route in the network model.
    
    Distinguishes discovered routes, recommended routes, and activated routes.
    If no route has been explicitly activated in forwarding state, returns None
    or falls back to the default baseline primary path if matching endpoints.
    """
    if not g or g.number_of_nodes() == 0:
        return None
    src, dst = resolve_endpoints(g, source, target)
    if src and dst and src == dst and src in g:
        return [src]
    active = g.graph.get("active_path")
    if active and isinstance(active, (list, tuple)) and len(active) >= 2:
        if active[0] == src and active[-1] == dst:
            return list(active)
    # Default baseline primary path PC1 -> R1 -> R2 -> Server if configured
    if src == "PC1" and dst == "Server" and all(n in g for n in ["PC1", "R1", "R2", "Server"]):
        return ["PC1", "R1", "R2", "Server"]
    # For other endpoints, if operational shortest path exists, return default route
    if src and dst and src in g and dst in g:
        sp = shortest_path(g, src, dst)
        if sp:
            return sp
    return list(active) if active else None

def set_active_route(g, path):
    """Explicitly activate a route in the simulated forwarding state.
    
    Only the Automated Recovery module (or initial baseline setup) activates routes.
    Monitoring and Diagnosis modules must NOT activate routes.
    """
    if path:
        p_list = list(path)
        g.graph["active_path"] = p_list
        g.graph["activated_route"] = p_list
        return p_list
    else:
        g.graph.pop("active_path", None)
        g.graph.pop("activated_route", None)
        return None

def clear_active_route(g):
    """Clear the active forwarding route from network state."""
    g.graph.pop("active_path", None)
    g.graph.pop("activated_route", None)

