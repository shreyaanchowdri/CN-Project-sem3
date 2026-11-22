"""Fault scenarios alter only the virtual network state."""
SCENARIOS = [
    "No fault",
    "Link failure (R2-Server)",
    "Wrong default gateway",
    "DNS failure",
    "High latency (R1-R2)",
    "Packet loss (R1-R2)"
]

# User-facing UI display labels requested for Cisco Packet Tracer workspace
UI_SCENARIOS = [
    "No Fault \u2013 Healthy Baseline",
    "Link Failure",
    "Wrong Default Gateway",
    "DNS Service Failure",
    "High Network Latency",
    "Packet Loss"
]

# Two-way mapping between UI display labels and canonical backend scenario identifiers
UI_TO_BACKEND_MAP = {
    "No Fault \u2013 Healthy Baseline": "No fault",
    "No Fault - Healthy Baseline": "No fault",
    "No fault": "No fault",
    "Link Failure": "Link failure (R2-Server)",
    "Link failure": "Link failure (R2-Server)",
    "Link failure (R2-Server)": "Link failure (R2-Server)",
    "Wrong Default Gateway": "Wrong default gateway",
    "Wrong default gateway": "Wrong default gateway",
    "DNS Service Failure": "DNS failure",
    "DNS failure": "DNS failure",
    "High Network Latency": "High latency (R1-R2)",
    "High latency": "High latency (R1-R2)",
    "High latency (R1-R2)": "High latency (R1-R2)",
    "Packet Loss": "Packet loss (R1-R2)",
    "Packet loss": "Packet loss (R1-R2)",
    "Packet loss (R1-R2)": "Packet loss (R1-R2)"
}

BACKEND_TO_UI_MAP = {
    "No fault": "No Fault \u2013 Healthy Baseline",
    "Link failure (R2-Server)": "Link Failure",
    "Link failure": "Link Failure",
    "Wrong default gateway": "Wrong Default Gateway",
    "DNS failure": "DNS Service Failure",
    "High latency (R1-R2)": "High Network Latency",
    "High latency": "High Network Latency",
    "Packet loss (R1-R2)": "Packet Loss",
    "Packet loss": "Packet Loss"
}

def map_to_backend_scenario(scenario):
    """Resolve user-facing UI labels, aliases, or prefixes to canonical backend scenario."""
    if not scenario:
        return "No fault"
    if scenario in UI_TO_BACKEND_MAP:
        return UI_TO_BACKEND_MAP[scenario]
    if scenario in SCENARIOS:
        return scenario
    # Normalized hyphen check (en-dash vs hyphen)
    norm = scenario.replace("\u2013", "-").strip()
    if norm in UI_TO_BACKEND_MAP:
        return UI_TO_BACKEND_MAP[norm]
    # Case-insensitive check against UI labels
    s_clean = scenario.strip().lower()
    for k, v in UI_TO_BACKEND_MAP.items():
        if s_clean == k.strip().lower() or s_clean == k.replace("\u2013", "-").strip().lower():
            return v
    # Prefix / substring matching against canonical scenarios
    for sc in SCENARIOS:
        sc_base = sc.split(" (")[0].strip().lower()
        if s_clean == sc.lower() or s_clean.startswith(sc_base) or sc_base.startswith(s_clean):
            return sc
    return scenario

def parse_link_endpoints(target_link):
    """Parse link endpoints from tuple, list, or formatted string like 'PC1 ↔ R1' or 'PC1 <-> R1'."""
    if not target_link:
        return None, None
    if isinstance(target_link, (tuple, list)) and len(target_link) >= 2:
        return str(target_link[0]).strip(), str(target_link[1]).strip()
    if isinstance(target_link, str):
        for sep in ("\u2194", "<->", "<-->", "->", "--", "-"):
            if sep in target_link:
                parts = target_link.split(sep, 1)
                return parts[0].strip(), parts[1].strip()
    return None, None

def reset_faults(g):
    """Reset fault states across all links and graph attributes."""
    for _, _, d in g.edges(data=True):
        d.update(status="UP", latency_ms=2, packet_loss=0.0)
    g.graph.update(gateway="R1", dns_available=True, scenario="No fault")
    if all(n in g for n in ["PC1", "R1", "R2", "Server"]):
        g.graph["active_path"] = ["PC1", "R1", "R2", "Server"]
        g.graph["activated_route"] = ["PC1", "R1", "R2", "Server"]
    for n, d in g.nodes(data=True):
        if d.get("type") in ("PC", "Laptop"):
            d["gateway"] = "R1"
    if "PC1" in g.nodes:
        g.nodes["PC1"]["gateway"] = "R1"

def inject_fault(g, scenario, target_link=None, target_device=None):
    """Inject a simulated network fault scenario into graph g.
    
    Supports dynamic link selection for Link Failure without hardcoded targets,
    as well as dynamically targeted links and devices across custom topologies.
    """
    canonical_scenario = map_to_backend_scenario(scenario)
    if canonical_scenario not in SCENARIOS:
        raise ValueError(f"Unsupported scenario: {scenario}")
    scenario = canonical_scenario
    reset_faults(g)
    g.graph["scenario"] = scenario

    def resolve_edge(g, preferred_a, preferred_b):
        if target_link:
            ta, tb = parse_link_endpoints(target_link)
            if ta and tb and g.has_edge(ta, tb):
                return ta, tb
            if ta and tb and g.has_edge(tb, ta):
                return tb, ta
        if g.has_edge(preferred_a, preferred_b):
            return preferred_a, preferred_b
        edges = list(g.edges())
        return edges[0] if edges else (None, None)

    if scenario == "No fault":
        return {"fault": scenario, "details": "No fault injected; baseline network state restored."}

    elif scenario in ("Link failure (R2-Server)", "Link Failure", "Link failure"):
        u, v = None, None
        if target_link:
            ta, tb = parse_link_endpoints(target_link)
            if ta and tb and g.has_edge(ta, tb):
                u, v = ta, tb
            elif ta and tb and g.has_edge(tb, ta):
                u, v = tb, ta

        # If no specific target_link was provided, find an available UP link dynamically
        if not u or not v:
            if g.number_of_edges() == 0:
                return {
                    "fault": scenario,
                    "details": "No connections exist in topology to mark DOWN.",
                    "failed_link": None,
                    "target_link": None
                }
            up_edges = [(a, b) for a, b, d in g.edges(data=True) if d.get("status") == "UP"]
            if up_edges:
                # Prefer R2-Server only when scenario was explicitly "Link failure (R2-Server)" for backwards compatibility
                if scenario == "Link failure (R2-Server)" and g.has_edge("R2", "Server") and g["R2"]["Server"].get("status") == "UP":
                    u, v = "R2", "Server"
                else:
                    u, v = up_edges[0]
            else:
                return {
                    "fault": scenario,
                    "details": "All connections in the topology are already DOWN.",
                    "failed_link": None,
                    "target_link": None
                }

        # Change only the selected link's status to DOWN
        g[u][v]["status"] = "DOWN"
        return {
            "fault": scenario,
            "details": f"The {u} \u2194 {v} communication link is marked DOWN.",
            "failed_link": (u, v),
            "failed_link_str": f"{u} \u2194 {v}",
            "target_link": (u, v)
        }

    elif scenario == "Wrong default gateway":
        g.graph["gateway"] = "R9"
        dev = target_device if (target_device and target_device in g.nodes) else ("PC1" if "PC1" in g.nodes else None)
        if not dev:
            for n, d in g.nodes(data=True):
                if d.get("type") in ("PC", "Laptop"):
                    dev = n
                    break
        if dev:
            g.nodes[dev]["gateway"] = "R9"
            return {"fault": scenario, "details": f"{dev} default gateway is changed from R1 to invalid gateway R9."}
        return {"fault": scenario, "details": "Default gateway is changed to invalid gateway R9."}

    elif scenario == "DNS failure":
        g.graph["dns_available"] = False
        return {"fault": scenario, "details": "DNS service is marked unavailable."}

    elif scenario == "High latency (R1-R2)":
        u, v = resolve_edge(g, "R1", "R2")
        if u and v:
            g[u][v]["latency_ms"] = 250.0
            return {"fault": scenario, "details": f"Latency on {u}-{v} is increased to 250 ms."}
        return {"fault": scenario, "details": "Warning: No links exist in topology."}

    elif scenario == "Packet loss (R1-R2)":
        u, v = resolve_edge(g, "R1", "R2")
        if u and v:
            g[u][v]["packet_loss"] = 40.0
            return {"fault": scenario, "details": f"Packet loss on {u}-{v} is increased to 40%."}
        return {"fault": scenario, "details": "Warning: No links exist in topology."}

    return {"fault": scenario, "details": "Simulated fault injected."}
