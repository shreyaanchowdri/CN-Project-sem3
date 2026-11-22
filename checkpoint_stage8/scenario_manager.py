"""Multi-Fault Scenario Management and Transactional Batch Injection Engine.

Provides atomic batch fault injection, pre-injection validation, snapshot capture,
safe rollback on failure, and management of multi-fault scenario configurations.
Integrates directly with the FaultRegistry and preserves backward compatibility.
"""
import copy
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import networkx as nx

from fault_registry import (
    FaultStatus,
    FaultRecord,
    FaultRegistry,
    get_fault_registry
)
from fault_injection import (
    inject_fault_instance,
    reset_faults,
    parse_link_endpoints
)

VALID_FAULT_TYPES = [
    "Link failure",
    "Wrong default gateway",
    "DNS failure",
    "High latency",
    "Packet loss"
]


def capture_network_snapshot(g: nx.Graph) -> Dict[str, Any]:
    """Capture a lightweight, exact snapshot of mutable simulated network state."""
    edge_states = {}
    for u, v, d in g.edges(data=True):
        edge_states[(u, v)] = {
            "status": d.get("status", "UP"),
            "latency_ms": d.get("latency_ms", 2.0),
            "packet_loss": d.get("packet_loss", 0.0),
            "cost": d.get("cost", 1),
            "connection_type": d.get("connection_type", "Copper Straight-Through")
        }

    node_states = {}
    for n, d in g.nodes(data=True):
        node_states[n] = {
            "gateway": d.get("gateway", "R1"),
            "dns_server": d.get("dns_server", "192.168.1.1"),
            "ip": d.get("ip"),
            "type": d.get("type")
        }

    graph_meta = {
        "gateway": g.graph.get("gateway", "R1"),
        "dns_available": bool(g.graph.get("dns_available", True)),
        "scenario": g.graph.get("scenario", "No fault"),
        "active_path": list(g.graph.get("active_path", [])) if g.graph.get("active_path") else None,
        "activated_route": list(g.graph.get("activated_route", [])) if g.graph.get("activated_route") else None
    }

    return {
        "timestamp": time.time(),
        "edge_states": edge_states,
        "node_states": node_states,
        "graph_meta": graph_meta
    }


def restore_network_snapshot(g: nx.Graph, snapshot: Dict[str, Any]) -> None:
    """Restore network graph state from a captured snapshot."""
    if not snapshot:
        return

    # Restore edges
    for (u, v), attrs in snapshot.get("edge_states", {}).items():
        if g.has_edge(u, v):
            g[u][v].update(attrs)
        elif g.has_edge(v, u):
            g[v][u].update(attrs)

    # Restore nodes
    for n, attrs in snapshot.get("node_states", {}).items():
        if n in g.nodes:
            g.nodes[n].update(attrs)

    # Restore graph metadata
    meta = snapshot.get("graph_meta", {})
    g.graph.update(
        gateway=meta.get("gateway", "R1"),
        dns_available=bool(meta.get("dns_available", True)),
        scenario=meta.get("scenario", "No fault")
    )
    if meta.get("active_path"):
        g.graph["active_path"] = list(meta["active_path"])
        g.graph["activated_route"] = list(meta["active_path"])
    else:
        g.graph.pop("active_path", None)
        g.graph.pop("activated_route", None)


def validate_fault_spec(g: nx.Graph, spec: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate an individual fault specification against the active graph."""
    if not isinstance(spec, dict):
        return False, "Fault specification must be a dictionary."

    ft = str(spec.get("fault_type", "")).strip()
    if not ft:
        return False, "Missing 'fault_type' in fault specification."

    matched_type = None
    for valid_t in VALID_FAULT_TYPES:
        if ft.lower() == valid_t.lower() or ft.lower().startswith(valid_t.lower()):
            matched_type = valid_t
            break

    if not matched_type:
        return False, f"Unsupported fault type '{ft}'. Must be one of {VALID_FAULT_TYPES}."

    target = spec.get("target")
    params = spec.get("parameters") or {}

    if matched_type == "Link failure":
        u, v = parse_link_endpoints(target)
        if not (u and v and g.has_edge(u, v)):
            if isinstance(target, (tuple, list)) and len(target) >= 2:
                u, v = str(target[0]), str(target[1])
        if not (u and v and g.has_edge(u, v)):
            return False, f"Target link '{target}' does not exist in the active network topology."

    elif matched_type == "Wrong default gateway":
        host = str(target) if target else "PC1"
        if host not in g.nodes:
            return False, f"Target host '{host}' does not exist in the active network topology."
        if g.nodes[host].get("type") not in ("PC", "Laptop", "Server"):
            return False, f"Target node '{host}' is of type '{g.nodes[host].get('type')}', not an end host."

    elif matched_type == "DNS failure":
        # DNS failure operates on simulated resolver/domain service
        pass

    elif matched_type == "High latency":
        u, v = parse_link_endpoints(target)
        if not (u and v and g.has_edge(u, v)):
            if isinstance(target, (tuple, list)) and len(target) >= 2:
                u, v = str(target[0]), str(target[1])
        if not (u and v and g.has_edge(u, v)):
            return False, f"Target link '{target}' does not exist in the active network topology."
        lat = params.get("latency_ms", 250.0)
        try:
            lat_val = float(lat)
            if lat_val < 0.0:
                return False, f"Latency value must be non-negative (received {lat_val})."
        except (ValueError, TypeError):
            return False, f"Latency value '{lat}' must be a valid number."

    elif matched_type == "Packet loss":
        u, v = parse_link_endpoints(target)
        if not (u and v and g.has_edge(u, v)):
            if isinstance(target, (tuple, list)) and len(target) >= 2:
                u, v = str(target[0]), str(target[1])
        if not (u and v and g.has_edge(u, v)):
            return False, f"Target link '{target}' does not exist in the active network topology."
        loss = params.get("packet_loss", 40.0)
        try:
            loss_val = float(loss)
            if loss_val < 0.0 or loss_val > 100.0:
                return False, f"Packet loss percentage must be between 0.0 and 100.0 (received {loss_val}%)."
        except (ValueError, TypeError):
            return False, f"Packet loss value '{loss}' must be a valid number."

    return True, None


def validate_fault_batch(g: nx.Graph, fault_specs: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validate an entire batch of fault specifications, checking for duplicates and conflicts."""
    errors = []
    if not fault_specs:
        return False, ["Fault specification batch cannot be empty."]

    seen_links_down = set()
    seen_host_gateways = set()
    seen_dns = False

    for idx, spec in enumerate(fault_specs, 1):
        is_valid, err = validate_fault_spec(g, spec)
        if not is_valid:
            errors.append(f"Item #{idx}: {err}")
            continue

        ft = spec.get("fault_type", "").lower()
        target = spec.get("target")

        # Duplicate checking
        if "link failure" in ft:
            u, v = parse_link_endpoints(target)
            if not (u and v):
                if isinstance(target, (tuple, list)) and len(target) >= 2:
                    u, v = str(target[0]), str(target[1])
            edge_key = tuple(sorted((u, v)))
            if edge_key in seen_links_down:
                errors.append(f"Item #{idx}: Duplicate link failure specified for link '{u}-{v}'.")
            seen_links_down.add(edge_key)

        elif "gateway" in ft:
            host = str(target) if target else "PC1"
            if host in seen_host_gateways:
                errors.append(f"Item #{idx}: Conflicting gateway fault already specified for host '{host}'.")
            seen_host_gateways.add(host)

        elif "dns" in ft:
            if seen_dns:
                errors.append(f"Item #{idx}: Duplicate DNS failure specified in the same batch.")
            seen_dns = True

    return (len(errors) == 0), errors


def inject_fault_batch(
    g: nx.Graph,
    fault_specs: List[Dict[str, Any]],
    scenario_name: str = "Multi-Fault Scenario",
    description: str = "",
    rollback_on_failure: bool = True,
    reset_first: bool = True
) -> Dict[str, Any]:
    """Atomically inject multiple simultaneous network faults into graph g.
    
    Captures snapshot before applying; if validation or application fails partway
    through, safely rolls back all changes to avoid corrupting network state.
    
    Parameters:
        g (nx.Graph): Simulated network topology.
        fault_specs (list[dict]): List of fault specifications.
        scenario_name (str): Scenario label.
        description (str): Scenario description.
        rollback_on_failure (bool): If True, restores network snapshot on any error.
        reset_first (bool): If True, archives existing active faults and resets to baseline first.
        
    Returns:
        dict: Structured batch injection report with scenario_id, applied_faults, status.
    """
    reg = get_fault_registry(g)

    # 1. Pre-injection validation
    is_valid, validation_errors = validate_fault_batch(g, fault_specs)
    if not is_valid:
        error_msg = "; ".join(validation_errors)
        return {
            "success": False,
            "status": "VALIDATION_FAILED",
            "scenario_name": scenario_name,
            "scenario_id": None,
            "applied_count": 0,
            "applied_faults": [],
            "errors": validation_errors,
            "details": f"Batch injection rejected: {error_msg}"
        }

    # 2. Capture clean snapshot before mutation
    snapshot = capture_network_snapshot(g)

    if reset_first:
        reset_faults(g, archive_registry=True)

    # 3. Create unique Scenario in registry
    scenario_id = reg.create_scenario(name=scenario_name, description=description or f"Batch of {len(fault_specs)} faults")
    g.graph["scenario"] = scenario_name

    applied_records = []
    try:
        for spec in fault_specs:
            rec = inject_fault_instance(
                g=g,
                fault_type=spec["fault_type"],
                target=spec.get("target"),
                parameters=spec.get("parameters"),
                scenario_id=scenario_id,
                description=spec.get("description", "")
            )
            applied_records.append(rec)

        return {
            "success": True,
            "status": "ACTIVE",
            "scenario_name": scenario_name,
            "scenario_id": scenario_id,
            "applied_count": len(applied_records),
            "applied_faults": [r.to_dict() for r in applied_records],
            "fault_records": applied_records,
            "details": f"Successfully applied {len(applied_records)} simultaneous faults under {scenario_id}."
        }

    except Exception as e:
        # Atomic rollback on exception
        if rollback_on_failure:
            restore_network_snapshot(g, snapshot)
            for rec in applied_records:
                reg.archive_active_fault(rec.fault_id, status=FaultStatus.CANCELLED, reason="Batch injection failure rollback")

        return {
            "success": False,
            "status": "ROLLED_BACK" if rollback_on_failure else "PARTIAL_FAILURE",
            "scenario_name": scenario_name,
            "scenario_id": scenario_id,
            "applied_count": 0 if rollback_on_failure else len(applied_records),
            "applied_faults": [] if rollback_on_failure else [r.to_dict() for r in applied_records],
            "errors": [str(e)],
            "details": f"Batch injection failed and was safely rolled back: {str(e)}"
        }


class MultiFaultScenario:
    """Configurable multi-fault scenario builder and previewer."""

    def __init__(self, name: str = "New Multi-Fault Scenario", description: str = ""):
        self.name = name
        self.description = description
        self.fault_items: List[Dict[str, Any]] = []

    def add_fault(
        self,
        fault_type: str,
        target: Any = None,
        parameters: Optional[Dict[str, Any]] = None,
        description: str = ""
    ) -> "MultiFaultScenario":
        """Add a fault specification to the scenario."""
        self.fault_items.append({
            "fault_type": fault_type,
            "target": target,
            "parameters": dict(parameters) if parameters else {},
            "description": description
        })
        return self

    def remove_fault(self, index: int) -> bool:
        """Remove a fault specification by index."""
        if 0 <= index < len(self.fault_items):
            self.fault_items.pop(index)
            return True
        return False

    def clear(self) -> None:
        """Clear all fault items in the builder."""
        self.fault_items.clear()

    def count(self) -> int:
        return len(self.fault_items)

    def validate(self, g: nx.Graph) -> Tuple[bool, List[str]]:
        """Validate scenario specifications against the graph."""
        return validate_fault_batch(g, self.fault_items)

    def preview(self, g: nx.Graph) -> List[Dict[str, Any]]:
        """Generate a preview of intended network state changes without modifying graph."""
        preview_list = []
        for idx, item in enumerate(self.fault_items, 1):
            ft = item["fault_type"]
            target = item.get("target")
            params = item.get("parameters", {})

            if "link" in ft.lower():
                u, v = parse_link_endpoints(target)
                if not (u and v) and isinstance(target, (tuple, list)) and len(target) >= 2:
                    u, v = str(target[0]), str(target[1])
                curr_st = g[u][v].get("status", "UP") if (u and v and g.has_edge(u, v)) else "N/A"
                preview_list.append({
                    "item_index": idx,
                    "fault_type": ft,
                    "target": f"{u} <-> {v}",
                    "current_state": f"status={curr_st}",
                    "projected_state": "status=DOWN",
                    "impact": "Link severed; unavailable for traffic forwarding."
                })
            elif "gateway" in ft.lower():
                host = str(target) if target else "PC1"
                curr_gw = g.nodes[host].get("gateway", "R1") if host in g.nodes else "N/A"
                target_gw = params.get("gateway", "R9")
                preview_list.append({
                    "item_index": idx,
                    "fault_type": ft,
                    "target": host,
                    "current_state": f"gateway={curr_gw}",
                    "projected_state": f"gateway={target_gw} (Invalid)",
                    "impact": f"Host {host} will fail to reach default router."
                })
            elif "dns" in ft.lower():
                curr_dns = bool(g.graph.get("dns_available", True))
                preview_list.append({
                    "item_index": idx,
                    "fault_type": ft,
                    "target": "DNS Service",
                    "current_state": f"dns_available={curr_dns}",
                    "projected_state": "dns_available=False",
                    "impact": "Hostname queries will fail across client endpoints."
                })
            elif "latency" in ft.lower():
                u, v = parse_link_endpoints(target)
                if not (u and v) and isinstance(target, (tuple, list)) and len(target) >= 2:
                    u, v = str(target[0]), str(target[1])
                curr_lat = g[u][v].get("latency_ms", 2.0) if (u and v and g.has_edge(u, v)) else "N/A"
                target_lat = params.get("latency_ms", 250.0)
                preview_list.append({
                    "item_index": idx,
                    "fault_type": ft,
                    "target": f"{u} <-> {v}",
                    "current_state": f"latency={curr_lat} ms",
                    "projected_state": f"latency={target_lat} ms",
                    "impact": "Transmission delay and queuing buffer increase."
                })
            elif "loss" in ft.lower():
                u, v = parse_link_endpoints(target)
                if not (u and v) and isinstance(target, (tuple, list)) and len(target) >= 2:
                    u, v = str(target[0]), str(target[1])
                curr_loss = g[u][v].get("packet_loss", 0.0) if (u and v and g.has_edge(u, v)) else "N/A"
                target_loss = params.get("packet_loss", 40.0)
                preview_list.append({
                    "item_index": idx,
                    "fault_type": ft,
                    "target": f"{u} <-> {v}",
                    "current_state": f"packet_loss={curr_loss}%",
                    "projected_state": f"packet_loss={target_loss}%",
                    "impact": "Frame drop and TCP retransmissions."
                })

        return preview_list

    def apply(self, g: nx.Graph, rollback_on_failure: bool = True, reset_first: bool = True) -> Dict[str, Any]:
        """Apply the scenario atomically to graph g."""
        return inject_fault_batch(
            g=g,
            fault_specs=self.fault_items,
            scenario_name=self.name,
            description=self.description,
            rollback_on_failure=rollback_on_failure,
            reset_first=reset_first
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize scenario template."""
        return {
            "name": self.name,
            "description": self.description,
            "fault_items": copy.deepcopy(self.fault_items)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MultiFaultScenario":
        """Load scenario template."""
        scn = cls(name=data.get("name", "Imported Scenario"), description=data.get("description", ""))
        scn.fault_items = copy.deepcopy(data.get("fault_items", []))
        return scn


# Predefined demonstration and benchmark scenarios
PREDEFINED_SCENARIOS = {
    "Demo: Multiple Link Failures (R1-R2 and R1-R3)": [
        {"fault_type": "Link failure", "target": ("R1", "R2")},
        {"fault_type": "Link failure", "target": ("R1", "R3")}
    ],
    "Demo: Triple Link Failure (Partition)": [
        {"fault_type": "Link failure", "target": ("PC1", "R1")},
        {"fault_type": "Link failure", "target": ("R1", "R2")},
        {"fault_type": "Link failure", "target": ("R3", "Server")}
    ],
    "Demo: Combined Link Failure + DNS Failure": [
        {"fault_type": "Link failure", "target": ("R1", "R2")},
        {"fault_type": "DNS failure"}
    ],
    "Demo: Combined Link Failure + Wrong Gateway": [
        {"fault_type": "Link failure", "target": ("R1", "R2")},
        {"fault_type": "Wrong default gateway", "target": "PC1", "parameters": {"gateway": "R9"}}
    ],
    "Demo: Dual Lossy Links": [
        {"fault_type": "Packet loss", "target": ("R1", "R2"), "parameters": {"packet_loss": 30.0}},
        {"fault_type": "Packet loss", "target": ("R1", "R3"), "parameters": {"packet_loss": 50.0}}
    ],
    "Demo: Dual High Latency Links": [
        {"fault_type": "High latency", "target": ("R1", "R2"), "parameters": {"latency_ms": 200.0}},
        {"fault_type": "High latency", "target": ("R2", "Server"), "parameters": {"latency_ms": 300.0}}
    ],
    "Demo: All Five Fault Categories Simultaneously": [
        {"fault_type": "Link failure", "target": ("R1", "R2")},
        {"fault_type": "Wrong default gateway", "target": "PC1", "parameters": {"gateway": "R9"}},
        {"fault_type": "DNS failure"},
        {"fault_type": "High latency", "target": ("R1", "R3"), "parameters": {"latency_ms": 220.0}},
        {"fault_type": "Packet loss", "target": ("R3", "Server"), "parameters": {"packet_loss": 35.0}}
    ]
}
