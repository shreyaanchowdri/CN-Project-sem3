"""Fault scenarios alter only the virtual network state."""
from fault_registry import (
    FaultStatus,
    FaultRecord,
    FaultRegistry,
    get_fault_registry
)

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

def reset_faults(g, archive_registry=True):
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
    if archive_registry and hasattr(g, "graph") and "fault_registry" in g.graph:
        reg = g.graph["fault_registry"]
        if isinstance(reg, FaultRegistry):
            reg.archive_all_active(status=FaultStatus.CLEARED, reason="Fault reset to baseline")

def inject_fault(g, scenario, target_link=None, target_device=None):
    """Inject a simulated network fault scenario into graph g.
    
    Supports dynamic link selection for Link Failure without hardcoded targets,
    as well as dynamically targeted links and devices across custom topologies.
    Maintains 100% backward compatibility while automatically registering injected
    faults with unique fault and scenario IDs in the FaultRegistry.
    """
    canonical_scenario = map_to_backend_scenario(scenario)
    if canonical_scenario not in SCENARIOS:
        raise ValueError(f"Unsupported scenario: {scenario}")
    scenario = canonical_scenario
    reset_faults(g)
    g.graph["scenario"] = scenario
    reg = get_fault_registry(g)
    sc_id = reg.create_scenario(name=canonical_scenario, description=f"Single fault scenario: {canonical_scenario}")

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
        return {
            "fault": scenario,
            "details": "No fault injected; baseline network state restored.",
            "fault_id": None,
            "scenario_id": sc_id,
            "fault_record": None
        }

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
                    "target_link": None,
                    "fault_id": None,
                    "scenario_id": sc_id
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
                    "target_link": None,
                    "fault_id": None,
                    "scenario_id": sc_id
                }

        # Change only the selected link's status to DOWN
        g[u][v]["status"] = "DOWN"
        rec = reg.register_fault(
            fault_type="Link failure",
            affected_component=f"{u}-{v}",
            parameters={"status": "DOWN", "u": u, "v": v},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description=f"The {u} \u2194 {v} communication link is marked DOWN."
        )
        return {
            "fault": scenario,
            "details": f"The {u} \u2194 {v} communication link is marked DOWN.",
            "failed_link": (u, v),
            "failed_link_str": f"{u} \u2194 {v}",
            "target_link": (u, v),
            "fault_id": rec.fault_id,
            "scenario_id": sc_id,
            "fault_record": rec
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
            details = f"{dev} default gateway is changed from R1 to invalid gateway R9."
            target_host = dev
        else:
            details = "Default gateway is changed to invalid gateway R9."
            target_host = "PC1"

        rec = reg.register_fault(
            fault_type="Wrong default gateway",
            affected_component=target_host,
            parameters={"gateway": "R9", "previous_gateway": "R1"},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description=details
        )
        return {
            "fault": scenario,
            "details": details,
            "fault_id": rec.fault_id,
            "scenario_id": sc_id,
            "fault_record": rec
        }

    elif scenario == "DNS failure":
        g.graph["dns_available"] = False
        rec = reg.register_fault(
            fault_type="DNS failure",
            affected_component="DNS Service",
            parameters={"dns_available": False},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description="DNS service is marked unavailable."
        )
        return {
            "fault": scenario,
            "details": "DNS service is marked unavailable.",
            "fault_id": rec.fault_id,
            "scenario_id": sc_id,
            "fault_record": rec
        }

    elif scenario == "High latency (R1-R2)":
        u, v = resolve_edge(g, "R1", "R2")
        if u and v:
            g[u][v]["latency_ms"] = 250.0
            rec = reg.register_fault(
                fault_type="High latency",
                affected_component=f"{u}-{v}",
                parameters={"latency_ms": 250.0, "u": u, "v": v},
                scenario_id=sc_id,
                status=FaultStatus.ACTIVE,
                description=f"Latency on {u}-{v} is increased to 250 ms."
            )
            return {
                "fault": scenario,
                "details": f"Latency on {u}-{v} is increased to 250 ms.",
                "fault_id": rec.fault_id,
                "scenario_id": sc_id,
                "fault_record": rec
            }
        return {"fault": scenario, "details": "Warning: No links exist in topology."}

    elif scenario == "Packet loss (R1-R2)":
        u, v = resolve_edge(g, "R1", "R2")
        if u and v:
            g[u][v]["packet_loss"] = 40.0
            rec = reg.register_fault(
                fault_type="Packet loss",
                affected_component=f"{u}-{v}",
                parameters={"packet_loss": 40.0, "u": u, "v": v},
                scenario_id=sc_id,
                status=FaultStatus.ACTIVE,
                description=f"Packet loss on {u}-{v} is increased to 40%."
            )
            return {
                "fault": scenario,
                "details": f"Packet loss on {u}-{v} is increased to 40%.",
                "fault_id": rec.fault_id,
                "scenario_id": sc_id,
                "fault_record": rec
            }
        return {"fault": scenario, "details": "Warning: No links exist in topology."}

    return {"fault": scenario, "details": "Simulated fault injected."}

def inject_fault_instance(
    g,
    fault_type,
    target=None,
    parameters=None,
    scenario_id=None,
    description=""
):
    """Inject an individual fault instance into graph g without resetting existing faults.
    
    Supports injecting multiple instances of the same fault type (e.g. 3 link failures,
    multiple lossy links) or arbitrary multi-fault combinations into the simulated network.
    
    Parameters:
        g (nx.Graph): Simulated network topology.
        fault_type (str): Canonical fault type ("Link failure", "Wrong default gateway",
                          "DNS failure", "High latency", or "Packet loss").
        target: Target component (link tuple e.g. ("R1", "R2"), host name e.g. "PC1", etc.).
        parameters (dict, optional): Specific parameter values (e.g. {"latency_ms": 300.0}).
        scenario_id (str, optional): Target scenario ID to group related faults.
        description (str, optional): Custom description string.
        
    Returns:
        FaultRecord: Registered fault record with unique fault_id.
    """
    reg = get_fault_registry(g)
    sc_id = scenario_id or reg.current_scenario_id
    params = dict(parameters) if parameters else {}
    ft = str(fault_type).strip()

    if ft in ("Link failure", "Link Failure"):
        u, v = parse_link_endpoints(target)
        if not (u and v and g.has_edge(u, v)):
            if isinstance(target, (tuple, list)) and len(target) >= 2:
                u, v = str(target[0]), str(target[1])
        if not (u and v and g.has_edge(u, v)):
            raise ValueError(f"Cannot inject link failure: link '{target}' does not exist in graph.")
        g[u][v]["status"] = "DOWN"
        link_str = f"{u}-{v}"
        desc = description or f"Link {u} \u2194 {v} marked DOWN"
        return reg.register_fault(
            fault_type="Link failure",
            affected_component=link_str,
            parameters={"status": "DOWN", "u": u, "v": v, **params},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description=desc
        )

    elif ft in ("Wrong default gateway", "Wrong Default Gateway", "Incorrect default gateway"):
        host = str(target) if target else "PC1"
        if host not in g.nodes:
            raise ValueError(f"Cannot inject gateway fault: host '{host}' does not exist in graph.")
        gw = str(params.get("gateway", "R9"))
        prev_gw = g.nodes[host].get("gateway", "R1")
        g.nodes[host]["gateway"] = gw
        if host == "PC1":
            g.graph["gateway"] = gw
        desc = description or f"Host {host} gateway changed from {prev_gw} to {gw}"
        return reg.register_fault(
            fault_type="Wrong default gateway",
            affected_component=host,
            parameters={"gateway": gw, "previous_gateway": prev_gw, **params},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description=desc
        )

    elif ft in ("DNS failure", "DNS Service Failure"):
        g.graph["dns_available"] = False
        desc = description or "DNS service marked unavailable"
        return reg.register_fault(
            fault_type="DNS failure",
            affected_component="DNS Service",
            parameters={"dns_available": False, **params},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description=desc
        )

    elif ft in ("High latency", "High Network Latency"):
        u, v = parse_link_endpoints(target)
        if not (u and v and g.has_edge(u, v)):
            if isinstance(target, (tuple, list)) and len(target) >= 2:
                u, v = str(target[0]), str(target[1])
        if not (u and v and g.has_edge(u, v)):
            raise ValueError(f"Cannot inject high latency: link '{target}' does not exist in graph.")
        lat = float(params.get("latency_ms", 250.0))
        prev_lat = float(g[u][v].get("latency_ms", 2.0))
        g[u][v]["latency_ms"] = lat
        desc = description or f"Latency on {u}-{v} increased to {lat} ms"
        return reg.register_fault(
            fault_type="High latency",
            affected_component=f"{u}-{v}",
            parameters={"latency_ms": lat, "previous_latency_ms": prev_lat, "u": u, "v": v, **params},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description=desc
        )

    elif ft in ("Packet loss", "Packet Loss"):
        u, v = parse_link_endpoints(target)
        if not (u and v and g.has_edge(u, v)):
            if isinstance(target, (tuple, list)) and len(target) >= 2:
                u, v = str(target[0]), str(target[1])
        if not (u and v and g.has_edge(u, v)):
            raise ValueError(f"Cannot inject packet loss: link '{target}' does not exist in graph.")
        loss = float(params.get("packet_loss", 40.0))
        prev_loss = float(g[u][v].get("packet_loss", 0.0))
        g[u][v]["packet_loss"] = loss
        desc = description or f"Packet loss on {u}-{v} increased to {loss}%"
        return reg.register_fault(
            fault_type="Packet loss",
            affected_component=f"{u}-{v}",
            parameters={"packet_loss": loss, "previous_packet_loss": prev_loss, "u": u, "v": v, **params},
            scenario_id=sc_id,
            status=FaultStatus.ACTIVE,
            description=desc
        )

    else:
        raise ValueError(f"Unsupported fault type '{fault_type}'.")

def clear_fault_instance(g, fault_id=None, fault_record=None):
    """Restore an individual component to baseline and archive its fault record.
    
    Does NOT affect other active faults on the network.
    """
    reg = get_fault_registry(g)
    record = fault_record or (reg.get_fault(fault_id) if fault_id else None)
    if not record:
        return False

    ft = record.fault_type
    target = record.affected_component
    params = record.parameters

    if ft in ("Link failure", "Link Failure"):
        u = params.get("u")
        v = params.get("v")
        if not (u and v):
            u, v = parse_link_endpoints(target)
        if u and v and g.has_edge(u, v):
            g[u][v]["status"] = "UP"

    elif ft in ("Wrong default gateway", "Wrong Default Gateway", "Incorrect default gateway"):
        host = str(target)
        prev_gw = params.get("previous_gateway", "R1")
        if host in g.nodes:
            g.nodes[host]["gateway"] = prev_gw
            if host == "PC1":
                g.graph["gateway"] = prev_gw

    elif ft in ("DNS failure", "DNS Service Failure"):
        g.graph["dns_available"] = True

    elif ft in ("High latency", "High Network Latency"):
        u = params.get("u")
        v = params.get("v")
        if not (u and v):
            u, v = parse_link_endpoints(target)
        prev_lat = float(params.get("previous_latency_ms", 2.0))
        if u and v and g.has_edge(u, v):
            g[u][v]["latency_ms"] = prev_lat

    elif ft in ("Packet loss", "Packet Loss"):
        u = params.get("u")
        v = params.get("v")
        if not (u and v):
            u, v = parse_link_endpoints(target)
        prev_loss = float(params.get("previous_packet_loss", 0.0))
        if u and v and g.has_edge(u, v):
            g[u][v]["packet_loss"] = prev_loss

    reg.archive_active_fault(record.fault_id, status=FaultStatus.CLEARED, reason="Fault instance cleared")
    return True
