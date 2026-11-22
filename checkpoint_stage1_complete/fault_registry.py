"""Structured Fault Registry and Lifecycle State Management.

Provides unique fault IDs, scenario IDs, lifecycle transitions, and
separation between active and historical faults.
Used strictly for simulation state tracking, scenario management, and auditing.
Monitoring and Diagnosis modules must NOT use this registry as evidence.
"""
import time
from typing import Any, Dict, List, Optional, Tuple, Union


class FaultStatus:
    """Standard lifecycle states for simulated network faults."""
    ACTIVE = "ACTIVE"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    RESOLVED = "RESOLVED"
    BYPASSED = "BYPASSED"
    UNRESOLVED = "UNRESOLVED"
    CLEARED = "CLEARED"

    ALL_STATUSES = {ACTIVE, PARTIALLY_RESOLVED, RESOLVED, BYPASSED, UNRESOLVED, CLEARED}

    @classmethod
    def is_valid(cls, status: str) -> bool:
        return str(status).upper() in cls.ALL_STATUSES


class FaultRecord:
    """Structured record of an injected fault instance."""

    def __init__(
        self,
        fault_id: str,
        scenario_id: str,
        fault_type: str,
        affected_component: Union[str, Tuple[str, str], List[str]],
        parameters: Optional[Dict[str, Any]] = None,
        status: str = FaultStatus.ACTIVE,
        recovery_status: str = "UNRESOLVED",
        timestamp: Optional[float] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.fault_id = str(fault_id)
        self.scenario_id = str(scenario_id)
        self.fault_type = str(fault_type)
        self.affected_component = affected_component
        self.parameters = dict(parameters) if parameters else {}
        self.status = str(status).upper() if FaultStatus.is_valid(status) else FaultStatus.ACTIVE
        self.recovery_status = str(recovery_status)
        self.timestamp = float(timestamp) if timestamp is not None else time.time()
        self.description = str(description)
        self.metadata = dict(metadata) if metadata else {}
        self.history_transitions: List[Dict[str, Any]] = [
            {
                "status": self.status,
                "recovery_status": self.recovery_status,
                "timestamp": self.timestamp,
                "reason": "Initial injection"
            }
        ]

    @property
    def target(self) -> Union[str, Tuple[str, str], List[str]]:
        """Alias for affected_component."""
        return self.affected_component

    def update_status(self, new_status: str, recovery_status: Optional[str] = None, reason: str = "") -> bool:
        """Transition fault to a new lifecycle state."""
        st = str(new_status).upper()
        if not FaultStatus.is_valid(st):
            raise ValueError(f"Invalid fault status '{new_status}'. Must be one of {FaultStatus.ALL_STATUSES}.")
        self.status = st
        if recovery_status is not None:
            self.recovery_status = str(recovery_status)
        self.history_transitions.append({
            "status": self.status,
            "recovery_status": self.recovery_status,
            "timestamp": time.time(),
            "reason": reason
        })
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize fault record to dictionary."""
        return {
            "fault_id": self.fault_id,
            "scenario_id": self.scenario_id,
            "fault_type": self.fault_type,
            "affected_component": self.affected_component,
            "parameters": self.parameters,
            "status": self.status,
            "recovery_status": self.recovery_status,
            "timestamp": self.timestamp,
            "description": self.description,
            "metadata": self.metadata,
            "history_transitions": list(self.history_transitions)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FaultRecord":
        """Reconstruct a fault record from dictionary."""
        rec = cls(
            fault_id=data.get("fault_id", "FLT-UNKNOWN"),
            scenario_id=data.get("scenario_id", "SCN-UNKNOWN"),
            fault_type=data.get("fault_type", "Generic fault"),
            affected_component=data.get("affected_component", "Unknown"),
            parameters=data.get("parameters", {}),
            status=data.get("status", FaultStatus.ACTIVE),
            recovery_status=data.get("recovery_status", "UNRESOLVED"),
            timestamp=data.get("timestamp"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )
        if "history_transitions" in data and isinstance(data["history_transitions"], list):
            rec.history_transitions = list(data["history_transitions"])
        return rec

    def __repr__(self) -> str:
        return (
            f"FaultRecord(id='{self.fault_id}', scenario='{self.scenario_id}', "
            f"type='{self.fault_type}', target={self.affected_component}, status='{self.status}')"
        )


class FaultRegistry:
    """Manages active and historical faults, unique identifiers, and lifecycle state changes."""

    def __init__(self):
        self._active_faults: Dict[str, FaultRecord] = {}
        self._historical_faults: List[FaultRecord] = []
        self._fault_counter: int = 0
        self._scenario_counter: int = 0
        self._current_scenario_id: Optional[str] = None

    @property
    def current_scenario_id(self) -> str:
        if not self._current_scenario_id:
            self.create_scenario("Default Scenario")
        return self._current_scenario_id  # type: ignore

    def create_scenario(self, name: str = "", description: str = "") -> str:
        """Create a new unique scenario ID and set it as current."""
        self._scenario_counter += 1
        scenario_id = f"SCN-{self._scenario_counter:04d}"
        self._current_scenario_id = scenario_id
        return scenario_id

    def set_current_scenario_id(self, scenario_id: str) -> None:
        """Set the active scenario ID."""
        self._current_scenario_id = str(scenario_id)

    def _next_fault_id(self) -> str:
        self._fault_counter += 1
        return f"FLT-{self._fault_counter:04d}"

    def register_fault(
        self,
        fault_type: str,
        affected_component: Union[str, Tuple[str, str], List[str]],
        parameters: Optional[Dict[str, Any]] = None,
        scenario_id: Optional[str] = None,
        status: str = FaultStatus.ACTIVE,
        recovery_status: str = "UNRESOLVED",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> FaultRecord:
        """Register a new fault instance with a unique ID."""
        fault_id = self._next_fault_id()
        sc_id = scenario_id or self.current_scenario_id
        record = FaultRecord(
            fault_id=fault_id,
            scenario_id=sc_id,
            fault_type=fault_type,
            affected_component=affected_component,
            parameters=parameters,
            status=status,
            recovery_status=recovery_status,
            description=description,
            metadata=metadata
        )
        self._active_faults[fault_id] = record
        return record

    def get_fault(self, fault_id: str) -> Optional[FaultRecord]:
        """Look up a fault by its unique ID across active and historical records."""
        if fault_id in self._active_faults:
            return self._active_faults[fault_id]
        for f in self._historical_faults:
            if f.fault_id == fault_id:
                return f
        return None

    def get_active_faults(
        self,
        scenario_id: Optional[str] = None,
        fault_type: Optional[str] = None
    ) -> List[FaultRecord]:
        """Return a copy of currently active faults, optionally filtered."""
        results = list(self._active_faults.values())
        if scenario_id:
            results = [f for f in results if f.scenario_id == scenario_id]
        if fault_type:
            results = [f for f in results if f.fault_type == fault_type]
        return results

    def get_historical_faults(self, scenario_id: Optional[str] = None) -> List[FaultRecord]:
        """Return a copy of archived historical faults, optionally filtered."""
        if scenario_id:
            return [f for f in self._historical_faults if f.scenario_id == scenario_id]
        return list(self._historical_faults)

    def get_all_faults(self) -> List[FaultRecord]:
        """Return combined list of active and historical faults."""
        return list(self._active_faults.values()) + list(self._historical_faults)

    def count_active(self, fault_type: Optional[str] = None) -> int:
        """Count active faults, optionally filtered by fault type."""
        return len(self.get_active_faults(fault_type=fault_type))

    def update_fault_status(
        self,
        fault_id: str,
        new_status: str,
        recovery_status: Optional[str] = None,
        reason: str = ""
    ) -> bool:
        """Update the lifecycle status of an active or historical fault."""
        fault = self.get_fault(fault_id)
        if not fault:
            return False
        fault.update_status(new_status, recovery_status, reason)
        return True

    def archive_active_fault(self, fault_id: str, status: str = FaultStatus.CLEARED, reason: str = "Archived") -> bool:
        """Move a specific active fault to the historical archive."""
        if fault_id not in self._active_faults:
            return False
        rec = self._active_faults.pop(fault_id)
        rec.update_status(status, reason=reason)
        self._historical_faults.append(rec)
        return True

    def archive_all_active(self, status: str = FaultStatus.CLEARED, reason: str = "Archived all active faults") -> int:
        """Archive all active faults into history."""
        active_ids = list(self._active_faults.keys())
        count = len(active_ids)
        for fid in active_ids:
            self.archive_active_fault(fid, status=status, reason=reason)
        return count

    def clear_all(self, include_history: bool = False) -> None:
        """Clear active faults (and optionally historical records)."""
        if not include_history:
            self.archive_all_active(status=FaultStatus.CLEARED, reason="Reset/clear")
        else:
            self._active_faults.clear()
            self._historical_faults.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full registry state."""
        return {
            "fault_counter": self._fault_counter,
            "scenario_counter": self._scenario_counter,
            "current_scenario_id": self._current_scenario_id,
            "active_faults": [f.to_dict() for f in self._active_faults.values()],
            "historical_faults": [f.to_dict() for f in self._historical_faults]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FaultRegistry":
        """Reconstruct registry from serialized dictionary."""
        reg = cls()
        reg._fault_counter = int(data.get("fault_counter", 0))
        reg._scenario_counter = int(data.get("scenario_counter", 0))
        reg._current_scenario_id = data.get("current_scenario_id")
        for f_data in data.get("active_faults", []):
            rec = FaultRecord.from_dict(f_data)
            reg._active_faults[rec.fault_id] = rec
        for f_data in data.get("historical_faults", []):
            rec = FaultRecord.from_dict(f_data)
            reg._historical_faults.append(rec)
        return reg


def get_fault_registry(g) -> FaultRegistry:
    """Retrieve or initialize the FaultRegistry on graph g."""
    if not hasattr(g, "graph") or g.graph is None:
        return FaultRegistry()
    if "fault_registry" not in g.graph or not isinstance(g.graph["fault_registry"], FaultRegistry):
        g.graph["fault_registry"] = FaultRegistry()
    return g.graph["fault_registry"]


def set_fault_registry(g, registry: FaultRegistry) -> None:
    """Attach a FaultRegistry to graph g."""
    if hasattr(g, "graph") and g.graph is not None:
        g.graph["fault_registry"] = registry
