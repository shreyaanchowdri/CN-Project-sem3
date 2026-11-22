"""Performance measurements for the simulated network."""
from network_model import path_cost

def make_metrics(g, path, diagnosis_time=0.0, recovery_time=0.0):
    valid = bool(path)
    edges = [g[a][b] for a, b in zip(path, path[1:])] if valid and all(g.has_edge(a, b) for a, b in zip(path, path[1:])) else []
    total_lat = round(sum(e['latency_ms'] for e in edges), 2) if edges else 0
    avg_lat = round(total_lat / len(edges), 2) if edges else 0
    return {
        "Reachability": "REACHABLE" if valid else "UNREACHABLE",
        "Selected route": " -> ".join(path) if path else "None",
        "Hop count": len(path) - 1 if path else 0,
        "Route cost": path_cost(g, path) if edges else (0 if not path else "N/A"),
        "Average link latency (ms)": avg_lat,
        "Total route latency (ms)": total_lat,
        "Maximum packet loss (%)": max((e['packet_loss'] for e in edges), default=0),
        "Diagnosis time (seconds)": round(diagnosis_time, 6),
        "Recovery time (seconds)": round(recovery_time, 6)
    }
