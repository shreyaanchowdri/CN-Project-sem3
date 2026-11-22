"""analytics_engine.py - Network Analytics, Telemetry Trends, and Performance Metrics.

Provides metric tracking across network events, MTTR calculation, 6-graph
Matplotlib rendering, and CSV/PNG export capabilities.
"""

import time
import os
import csv
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import networkx as nx

from audit_logger import get_audit_logger
from fault_registry import get_fault_registry


@dataclass
class TelemetryDataPoint:
    """A timestamped telemetry record captured across network operations."""
    timestamp: float
    event_label: str  # "Baseline", "Fault Injected", "Recovered", etc.
    phase: str        # "BASELINE", "FAULT", "RECOVERY"
    e2e_latency_ms: float
    e2e_packet_loss_pct: float
    link_latencies: Dict[str, float]
    link_packet_losses: Dict[str, float]
    service_available: bool
    network_health: str  # "HEALTHY", "DEGRADED", "CRITICAL"
    active_fault_count: int
    active_route: str
    outage_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_label": self.event_label,
            "phase": self.phase,
            "e2e_latency_ms": self.e2e_latency_ms,
            "e2e_packet_loss_pct": self.e2e_packet_loss_pct,
            "link_latencies": self.link_latencies,
            "link_packet_losses": self.link_packet_losses,
            "service_available": self.service_available,
            "network_health": self.network_health,
            "active_fault_count": self.active_fault_count,
            "active_route": self.active_route,
            "outage_seconds": self.outage_seconds
        }


class AnalyticsEngine:
    """Manages telemetry historical time-series and generates 6 network analysis graphs."""

    def __init__(self):
        self.history: List[TelemetryDataPoint] = []
        self._outage_start: Optional[float] = None

    def record_telemetry(
        self,
        g: nx.Graph,
        event_label: str = "Telemetry Observation",
        phase: str = "BASELINE",
        observations: Optional[Dict[str, Any]] = None
    ) -> TelemetryDataPoint:
        """Capture current telemetry state into history."""
        now = time.time()
        link_lat = {}
        link_loss = {}

        for u, v, d in g.edges(data=True):
            lbl = f"{u}-{v}"
            link_lat[lbl] = float(d.get("latency_ms", 2.0))
            link_loss[lbl] = float(d.get("packet_loss", 0.0))

        if observations:
            lat_val = observations.get("end_to_end_latency_ms")
            e2e_lat = float(lat_val) if lat_val is not None else 0.0
            loss_val = observations.get("path_packet_loss")
            e2e_loss = float(loss_val) if loss_val is not None else (100.0 if not observations.get("reachability", True) else 0.0)
            avail = bool(observations.get("reachability", True))
            p = observations.get("path") or observations.get("active_path") or []
            route_str = " -> ".join(p) if p else "None"
        else:
            avail = True
            e2e_lat = 10.0
            e2e_loss = 0.0
            route_str = "PC1 -> R1 -> R2 -> Server"

        # Outage tracking
        outage_sec = 0.0
        if not avail:
            if self._outage_start is None:
                self._outage_start = now
            outage_sec = now - self._outage_start
        else:
            if self._outage_start is not None:
                outage_sec = now - self._outage_start
                self._outage_start = None

        reg = get_fault_registry(g)
        f_count = reg.get_active_fault_count()

        if f_count == 0 and avail:
            health = "HEALTHY"
        elif not avail:
            health = "CRITICAL"
        else:
            health = "DEGRADED"

        dp = TelemetryDataPoint(
            timestamp=now,
            event_label=event_label,
            phase=phase,
            e2e_latency_ms=e2e_lat,
            e2e_packet_loss_pct=e2e_loss,
            link_latencies=link_lat,
            link_packet_losses=link_loss,
            service_available=avail,
            network_health=health,
            active_fault_count=f_count,
            active_route=route_str,
            outage_seconds=round(outage_sec, 2)
        )
        self.history.append(dp)
        return dp

    def calculate_mttr(self) -> Dict[str, Any]:
        """Calculate Mean Time to Recovery (MTTR) and recovery statistics."""
        audit_records = get_audit_logger().get_all_records()
        durations = [getattr(r, "duration_ms", 0.0) / 1000.0 for r in audit_records if getattr(r, "duration_ms", 0.0) > 0]
        verified_count = sum(1 for r in audit_records if getattr(r, "verification_passed", False))
        total_runs = len(audit_records)

        mttr = sum(durations) / len(durations) if durations else 0.0
        success_rate = (verified_count / total_runs * 100.0) if total_runs > 0 else 100.0

        return {
            "total_recovery_runs": total_runs,
            "verified_recoveries": verified_count,
            "success_rate_pct": round(success_rate, 1),
            "mttr_seconds": round(mttr, 3),
            "min_recovery_seconds": round(min(durations), 3) if durations else 0.0,
            "max_recovery_seconds": round(max(durations), 3) if durations else 0.0
        }

    def render_six_graphs(
        self,
        fig: Optional[Figure] = None,
        candidate_routes: Optional[List[Dict[str, Any]]] = None,
        g: Optional[nx.Graph] = None
    ) -> Figure:
        """Render all 6 analytical graphs onto a 2x3 Matplotlib figure."""
        if fig is None:
            fig = plt.Figure(figsize=(14, 8), dpi=100)
        fig.clear()
        fig.subplots_adjust(hspace=0.72, wspace=0.28, left=0.07, right=0.96, top=0.90, bottom=0.14)

        # Style colors
        bg_color = "#f8fafc"
        grid_color = "#e2e8f0"
        fig.patch.set_facecolor(bg_color)

        # ---------------------------------------------------------------------
        # Graph 1: Network Latency Trends (Before, During, After)
        # ---------------------------------------------------------------------
        ax1 = fig.add_subplot(2, 3, 1)
        ax1.set_facecolor("#ffffff")
        ax1.set_title("1. Network Latency Trends (ms)", fontsize=9, fontweight="bold", color="#1e293b")
        ax1.set_ylabel("Latency (ms)", fontsize=8)
        ax1.grid(True, linestyle="--", alpha=0.5, color=grid_color)

        if self.history:
            pts = self.history[-8:]
            x_pts = list(range(1, len(pts) + 1))
            e2e_lats = [dp.e2e_latency_ms for dp in pts]
            labels = [dp.event_label[:10] for dp in pts]

            ax1.plot(x_pts, e2e_lats, marker="o", color="#0284c7", linewidth=2, label="E2E Latency")
            ax1.set_xticks(x_pts)
            ax1.set_xticklabels(labels, rotation=18, ha="right", fontsize=7.5)
            ax1.legend(loc="upper left", fontsize=7)
        elif g is not None:
            from monitoring import collect_observations
            obs = collect_observations(g)
            cur_lat = obs.get("end_to_end_latency_ms")
            lat_val = float(cur_lat) if cur_lat is not None else 10.0
            ax1.plot([1], [lat_val], marker="o", color="#0284c7", linewidth=2, label="Current E2E")
            ax1.set_xticks([1])
            ax1.set_xticklabels(["Current"], rotation=18, ha="right", fontsize=7.5)
            ax1.legend(loc="upper left", fontsize=7)
        else:
            ax1.set_xticks([])
            ax1.text(0.5, 0.5, "Awaiting Telemetry Events", ha="center", va="center", transform=ax1.transAxes, color="#64748b", fontsize=8)

        # ---------------------------------------------------------------------
        # Graph 2: Packet Loss Analysis (Individual Links vs End-to-End)
        # ---------------------------------------------------------------------
        ax2 = fig.add_subplot(2, 3, 2)
        ax2.set_facecolor("#ffffff")
        ax2.set_title("2. Packet Loss Analysis (%)", fontsize=9, fontweight="bold", color="#1e293b")
        ax2.set_ylabel("Packet Loss (%)", fontsize=8)
        ax2.grid(True, linestyle="--", alpha=0.5, color=grid_color)

        if self.history:
            latest = self.history[-1]
            links = list(latest.link_packet_losses.keys())
            losses = [latest.link_packet_losses[k] for k in links]
            links.append("E2E Loss")
            losses.append(latest.e2e_packet_loss_pct)

            clean_links = [k.replace("-", "↔")[:10] for k in links]
            colors = ["#ef4444" if l > 0 else "#22c55e" for l in losses]
            bars = ax2.bar(range(len(clean_links)), losses, color=colors, width=0.45)
            ax2.set_ylim(0, max(100, max(losses) + 10) if losses else 100)
            ax2.set_xticks(range(len(clean_links)))
            ax2.set_xticklabels(clean_links, rotation=18, ha="right", fontsize=7.5)
            for bar, l in zip(bars, losses):
                if l > 0:
                    ax2.text(bar.get_x() + bar.get_width()/2, l + 2, f"{l:.0f}%", ha="center", fontsize=7)
        elif g is not None:
            clean_links = [f"{u}↔{v}"[:10] for u, v in g.edges()] + ["E2E Loss"]
            losses = [float(g[u][v].get("packet_loss", 0.0)) for u, v in g.edges()] + [0.0]
            colors = ["#ef4444" if l > 0 else "#22c55e" for l in losses]
            ax2.bar(range(len(clean_links)), losses, color=colors, width=0.45)
            ax2.set_ylim(0, 100)
            ax2.set_xticks(range(len(clean_links)))
            ax2.set_xticklabels(clean_links, rotation=18, ha="right", fontsize=7.5)
        else:
            ax2.set_xticks([])
            ax2.text(0.5, 0.5, "Awaiting Loss Telemetry", ha="center", va="center", transform=ax2.transAxes, color="#64748b", fontsize=8)

        # ---------------------------------------------------------------------
        # Graph 3: Network Availability & Outage Timeline
        # ---------------------------------------------------------------------
        ax3 = fig.add_subplot(2, 3, 3)
        ax3.set_facecolor("#ffffff")
        ax3.set_title("3. Service Availability Timeline", fontsize=9, fontweight="bold", color="#1e293b")
        ax3.set_ylabel("Availability State", fontsize=8)
        ax3.set_yticks([0, 1])
        ax3.set_yticklabels(["DOWN (0)", "UP (1)"], fontsize=8)
        ax3.grid(True, linestyle="--", alpha=0.5, color=grid_color)

        if self.history:
            pts = self.history[-8:]
            x_pts = list(range(1, len(pts) + 1))
            avails = [1 if dp.service_available else 0 for dp in pts]
            labels = [dp.event_label[:10] for dp in pts]
            ax3.step(x_pts, avails, where="mid", color="#16a34a", linewidth=2.5)
            ax3.fill_between(x_pts, avails, step="mid", alpha=0.15, color="#16a34a")
            ax3.set_xticks(x_pts)
            ax3.set_xticklabels(labels, rotation=18, ha="right", fontsize=7.5)
        elif g is not None:
            is_up = nx.has_path(g, "PC1", "Server") if ("PC1" in g and "Server" in g) else True
            st_val = 1 if is_up else 0
            ax3.step([1], [st_val], where="mid", color="#16a34a" if is_up else "#dc2626", linewidth=2.5)
            ax3.set_xticks([1])
            ax3.set_xticklabels(["Current"], rotation=18, ha="right", fontsize=7.5)
        else:
            ax3.set_xticks([])
            ax3.text(0.5, 0.5, "Awaiting Availability Events", ha="center", va="center", transform=ax3.transAxes, color="#64748b", fontsize=8)

        # ---------------------------------------------------------------------
        # Graph 4: Fault Distribution (Type & Severity)
        # ---------------------------------------------------------------------
        ax4 = fig.add_subplot(2, 3, 4)
        ax4.set_facecolor("#ffffff")
        ax4.set_title("4. Fault Distribution by Category", fontsize=9, fontweight="bold", color="#1e293b")
        ax4.grid(True, linestyle="--", alpha=0.5, color=grid_color)

        categories = ["Link Cut", "Gateway", "DNS", "High Lat", "Loss"]
        reg = get_fault_registry(g)
        active_faults = reg.get_active_faults()
        counts = [0, 0, 0, 0, 0]
        for f in active_faults:
            ft = f.fault_type.lower()
            if "link" in ft: counts[0] += 1
            elif "gateway" in ft: counts[1] += 1
            elif "dns" in ft: counts[2] += 1
            elif "latency" in ft: counts[3] += 1
            elif "loss" in ft: counts[4] += 1

        bar_c = ["#dc2626", "#ea580c", "#d97706", "#2563eb", "#7c3aed"]
        ax4.bar(range(len(categories)), counts, color=bar_c, width=0.45)
        ax4.set_ylabel("Active Fault Count", fontsize=8)
        ax4.set_ylim(0, max(4, max(counts) + 1))
        ax4.set_xticks(range(len(categories)))
        ax4.set_xticklabels(categories, rotation=20, ha="right", fontsize=8)
        for i, cnt in enumerate(counts):
            if cnt > 0:
                ax4.text(i, cnt + 0.1, str(cnt), ha="center", fontsize=8, fontweight="bold")

        # ---------------------------------------------------------------------
        # Graph 5: Recovery Performance & MTTR
        # ---------------------------------------------------------------------
        ax5 = fig.add_subplot(2, 3, 5)
        ax5.set_facecolor("#ffffff")
        ax5.set_title("5. Recovery Performance & MTTR", fontsize=9, fontweight="bold", color="#1e293b")
        ax5.grid(True, linestyle="--", alpha=0.5, color=grid_color)

        stats = self.calculate_mttr()
        labels_perf = ["Runs", "Verified", "MTTR (s)"]
        vals_perf = [stats["total_recovery_runs"], stats["verified_recoveries"], stats["mttr_seconds"]]

        bars_p = ax5.bar(range(len(labels_perf)), vals_perf, color=["#3b82f6", "#10b981", "#8b5cf6"], width=0.42)
        ax5.set_ylabel("Metric Value", fontsize=8)
        ax5.set_xticks(range(len(labels_perf)))
        ax5.set_xticklabels(labels_perf, rotation=20, ha="right", fontsize=8)
        for b, v in zip(bars_p, vals_perf):
            if v > 0:
                txt = f"{v:.2f}" if isinstance(v, float) else str(v)
                ax5.text(b.get_x() + b.get_width()/2, v + (0.1 if v < 5 else v*0.05), txt, ha="center", fontsize=7)

        # ---------------------------------------------------------------------
        # Graph 6: Multi-Objective Route Comparison
        # ---------------------------------------------------------------------
        ax6 = fig.add_subplot(2, 3, 6)
        ax6.set_facecolor("#ffffff")
        ax6.set_title("6. Candidate Route Latency & Cost", fontsize=9, fontweight="bold", color="#1e293b")
        ax6.grid(True, linestyle="--", alpha=0.5, color=grid_color)

        r_names = []
        r_lats = []
        r_costs = []

        if candidate_routes:
            for i, r in enumerate(candidate_routes[:4], 1):
                p_str = " -> ".join([n for n in r["path"] if n != "PC1" and n != "Server"]) or "Direct"
                r_names.append(f"R{i}: {p_str}")
                r_lats.append(float(r.get("latency_ms", 10.0)))
                r_costs.append(float(r.get("cost", 2)) * 10.0)  # scaled for display
        elif g is not None and "PC1" in g and "Server" in g and nx.has_path(g, "PC1", "Server"):
            from recovery_planner import select_optimal_recovery_route
            _, cand, _ = select_optimal_recovery_route(g, "PC1", "Server")
            for i, r in enumerate(cand[:4], 1):
                p_str = " -> ".join([n for n in r["path"] if n != "PC1" and n != "Server"]) or "Direct"
                r_names.append(f"R{i}: {p_str}")
                r_lats.append(float(r.get("latency_ms", 10.0)))
                r_costs.append(float(r.get("cost", 2)) * 10.0)

        if r_names:
            import numpy as np
            x_idx = np.arange(len(r_names))
            w = 0.35

            ax6.bar(x_idx - w/2, r_lats, width=w, label="Latency (ms)", color="#0ea5e9")
            ax6.bar(x_idx + w/2, r_costs, width=w, label="Cost (x10)", color="#f59e0b")
            ax6.set_xticks(x_idx)
            ax6.set_xticklabels(r_names, rotation=20, ha="right", fontsize=8)
            ax6.legend(loc="upper right", fontsize=7)
        else:
            ax6.set_xticks([])
            ax6.text(0.5, 0.5, "No Candidate Routes", ha="center", va="center", transform=ax6.transAxes, color="#64748b", fontsize=8)

        return fig

        return fig

    def export_csv(self, filepath: str) -> bool:
        """Export all recorded telemetry points to CSV."""
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Event", "Phase", "E2E_Latency_ms", "E2E_Loss_pct",
                    "Service_Available", "Network_Health", "Active_Faults", "Active_Route", "Outage_Sec"
                ])
                for dp in self.history:
                    writer.writerow([
                        dp.timestamp, dp.event_label, dp.phase, dp.e2e_latency_ms,
                        dp.e2e_packet_loss_pct, dp.service_available, dp.network_health,
                        dp.active_fault_count, dp.active_route, dp.outage_seconds
                    ])
            return True
        except Exception:
            return False

    def export_png(self, filepath: str) -> bool:
        """Render and save the 6 analytical graphs to a high-resolution PNG file."""
        try:
            fig = self.render_six_graphs()
            fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Reset analytics telemetry history."""
        self.history.clear()
        self._outage_start = None


# Global singleton instance
_global_analytics_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Return the global AnalyticsEngine singleton."""
    global _global_analytics_engine
    if _global_analytics_engine is None:
        _global_analytics_engine = AnalyticsEngine()
    return _global_analytics_engine
