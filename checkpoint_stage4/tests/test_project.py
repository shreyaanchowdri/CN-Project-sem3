"""Comprehensive unit tests for the Intelligent Network Fault Diagnosis Framework.

Covers:
- Baseline topology, shortest path, and connectivity
- Fault injection and scenario resets
- Rule-based fault diagnosis and automated recovery
- Manual device management (add, remove, essential protection)
- Manual connection management (connect, disconnect, self-loop/duplicate prevention)
- Device and link configuration editing and renaming
- Topology JSON serialization and accurate restoration
- Custom topology routing and diagnosis
"""
import unittest
import os
import tempfile
import json
from network_model import (
    build_network,
    shortest_path,
    path_is_usable,
    path_cost,
    add_device,
    remove_device,
    connect_devices,
    disconnect_devices,
    configure_device,
    configure_link,
    save_topology_to_file,
    load_topology_from_file,
    is_essential_device,
    DEVICE_TYPES,
    DEFAULT_NODES,
    discover_routes,
    select_best_route,
    calculate_route_metrics,
    resolve_endpoints,
    generate_unique_device_name,
    get_active_route,
    set_active_route
)
from fault_injection import (
    inject_fault,
    reset_faults,
    SCENARIOS,
    UI_SCENARIOS,
    UI_TO_BACKEND_MAP,
    BACKEND_TO_UI_MAP,
    inject_fault_instance,
    clear_fault_instance
)
from fault_registry import (
    FaultStatus,
    FaultRecord,
    FaultRegistry,
    get_fault_registry
)
from scenario_manager import (
    inject_fault_batch,
    validate_fault_spec,
    validate_fault_batch,
    capture_network_snapshot,
    restore_network_snapshot,
    MultiFaultScenario,
    PREDEFINED_SCENARIOS
)
from monitoring import (
    collect_observations,
    format_monitoring_report,
    generate_monitoring_report,
    calculate_path_packet_loss_probabilistic,
    analyze_network_partitions
)
from diagnostics import diagnose, DiagnosticFinding, format_diagnosis_report, generate_diagnosis_report
from recovery import (
    recover,
    format_recovery_report,
    generate_recovery_report,
    format_verification_report,
    generate_verification_report
)
from metrics import make_metrics


class FrameworkTests(unittest.TestCase):
    # -------------------------------------------------------------------------
    # Baseline & Existing Tests
    # -------------------------------------------------------------------------
    def test_topology_has_five_links_and_pc_connection(self):
        g = build_network()
        self.assertEqual(g.number_of_nodes(), 5)
        self.assertEqual(g.number_of_edges(), 5)
        self.assertTrue(g.has_edge("PC1", "R1"))
        self.assertEqual(g.nodes["PC1"]["kind"], "End device")

    def test_baseline_path(self):
        self.assertEqual(shortest_path(build_network()), ["PC1", "R1", "R2", "Server"])

    def test_link_failure_uses_backup(self):
        g = build_network()
        s = inject_fault(g, "Link failure (R2-Server)")
        o = collect_observations(g, s)
        self.assertIn("Link failure", [x[0] for x in diagnose(o)])
        r = recover(g, s)
        self.assertEqual(r["route"], ["PC1", "R1", "R3", "Server"])
        self.assertTrue(r["verified"])

    def test_gateway_repair_is_verified(self):
        g = build_network()
        s = inject_fault(g, "Wrong default gateway")
        self.assertFalse(collect_observations(g, s)["gateway_ok"])
        r = recover(g, s)
        self.assertTrue(r["ip_connectivity"])
        self.assertTrue(r["verified"])

    def test_dns_repair_is_verified(self):
        g = build_network()
        s = inject_fault(g, "DNS failure")
        self.assertFalse(collect_observations(g, s)["dns_ok"])
        r = recover(g, s)
        self.assertTrue(r["dns_resolution"])
        self.assertTrue(r["verified"])

    def test_latency_and_loss_detected_and_rerouted(self):
        for scenario in ("High latency (R1-R2)", "Packet loss (R1-R2)"):
            g = build_network()
            s = inject_fault(g, scenario)
            names = [x[0] for x in diagnose(collect_observations(g, s))]
            self.assertTrue(any(n in names for n in ("High latency", "Packet loss")))
            self.assertEqual(recover(g, s)["route"], ["PC1", "R1", "R3", "Server"])

    def test_reset_faults(self):
        g = build_network()
        inject_fault(g, "DNS failure")
        inject_fault(g, "No fault")
        self.assertTrue(g.graph["dns_available"])
        self.assertEqual(g.graph["gateway"], "R1")

    # -------------------------------------------------------------------------
    # Feature 1: Manual Device Management Tests
    # -------------------------------------------------------------------------
    def test_add_device_valid_types(self):
        g = build_network()
        for dev_type in DEVICE_TYPES:
            name = f"Test_{dev_type}"
            added = add_device(g, name, device_type=dev_type, ip="10.10.10.10")
            self.assertEqual(added, name)
            self.assertIn(name, g.nodes)
            self.assertEqual(g.nodes[name]["type"], dev_type)
            self.assertEqual(g.nodes[name]["ip"], "10.10.10.10")
            self.assertFalse(g.nodes[name]["is_default"])

    def test_add_device_duplicate_and_invalid(self):
        g = build_network()
        with self.assertRaises(ValueError):
            add_device(g, "PC1", device_type="PC")  # Duplicate
        with self.assertRaises(ValueError):
            add_device(g, "   ", device_type="PC")  # Blank name
        with self.assertRaises(ValueError):
            add_device(g, "ValidName", device_type="InvalidType")  # Invalid type

    def test_remove_custom_device(self):
        g = build_network()
        add_device(g, "PC2", device_type="PC", ip="192.168.1.20")
        connect_devices(g, "PC2", "R1")
        self.assertIn("PC2", g.nodes)
        self.assertTrue(g.has_edge("PC2", "R1"))

        remove_device(g, "PC2")
        self.assertNotIn("PC2", g.nodes)
        self.assertFalse(g.has_edge("PC2", "R1"))

    def test_prevent_deletion_of_essential_default_devices(self):
        g = build_network()
        for default_node in DEFAULT_NODES:
            self.assertTrue(is_essential_device(default_node))
            with self.assertRaises(ValueError):
                remove_device(g, default_node, force=False)
            self.assertIn(default_node, g.nodes)

    # -------------------------------------------------------------------------
    # Feature 2: Manual Connection Management Tests
    # -------------------------------------------------------------------------
    def test_connect_devices_and_attributes(self):
        g = build_network()
        add_device(g, "Switch1", device_type="Switch")
        connect_devices(g, "PC1", "Switch1", cost=2, latency_ms=5, packet_loss=1.5, status="UP")

        self.assertTrue(g.has_edge("PC1", "Switch1"))
        edge = g["PC1"]["Switch1"]
        self.assertEqual(edge["cost"], 2)
        self.assertEqual(edge["latency_ms"], 5.0)
        self.assertEqual(edge["packet_loss"], 1.5)
        self.assertEqual(edge["status"], "UP")

    def test_prevent_self_connection(self):
        g = build_network()
        with self.assertRaises(ValueError):
            connect_devices(g, "PC1", "PC1")

    def test_prevent_duplicate_connection(self):
        g = build_network()
        self.assertTrue(g.has_edge("PC1", "R1"))
        with self.assertRaises(ValueError):
            connect_devices(g, "PC1", "R1")
        with self.assertRaises(ValueError):
            connect_devices(g, "R1", "PC1")

    def test_disconnect_devices(self):
        g = build_network()
        self.assertTrue(g.has_edge("R1", "R3"))
        disconnect_devices(g, "R1", "R3")
        self.assertFalse(g.has_edge("R1", "R3"))
        with self.assertRaises(ValueError):
            disconnect_devices(g, "R1", "R3")  # Already disconnected

    # -------------------------------------------------------------------------
    # Feature 3: Device & Link Configuration Tests
    # -------------------------------------------------------------------------
    def test_configure_device_parameters(self):
        g = build_network()
        add_device(g, "DevX", device_type="PC")
        configure_device(g, "DevX", device_type="Server", ip="172.16.5.5", subnet_mask="255.255.0.0", gateway="172.16.0.1")
        d = g.nodes["DevX"]
        self.assertEqual(d["type"], "Server")
        self.assertEqual(d["ip"], "172.16.5.5")
        self.assertEqual(d["subnet_mask"], "255.255.0.0")
        self.assertEqual(d["gateway"], "172.16.0.1")

    def test_configure_device_renaming(self):
        g = build_network()
        add_device(g, "OldNode", device_type="Router")
        connect_devices(g, "OldNode", "R1")
        final_name = configure_device(g, "OldNode", new_name="NewNode")
        self.assertEqual(final_name, "NewNode")
        self.assertNotIn("OldNode", g.nodes)
        self.assertIn("NewNode", g.nodes)
        self.assertTrue(g.has_edge("NewNode", "R1"))

    def test_configure_link_parameters(self):
        g = build_network()
        configure_link(g, "R1", "R2", cost=5, latency_ms=120.0, packet_loss=25.0, status="DOWN")
        edge = g["R1"]["R2"]
        self.assertEqual(edge["cost"], 5)
        self.assertEqual(edge["latency_ms"], 120.0)
        self.assertEqual(edge["packet_loss"], 25.0)
        self.assertEqual(edge["status"], "DOWN")

    # -------------------------------------------------------------------------
    # Feature 4: Save & Load Network Topologies Tests
    # -------------------------------------------------------------------------
    def test_save_and_load_topology(self):
        g = build_network()
        add_device(g, "PC_Custom", device_type="PC", ip="192.168.10.5", gateway="R1")
        connect_devices(g, "PC_Custom", "R1", cost=3, latency_ms=10, packet_loss=2.0)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            save_topology_to_file(g, temp_path)
            self.assertTrue(os.path.exists(temp_path))

            loaded_g, positions = load_topology_from_file(temp_path)
            self.assertEqual(loaded_g.number_of_nodes(), g.number_of_nodes())
            self.assertEqual(loaded_g.number_of_edges(), g.number_of_edges())
            self.assertIn("PC_Custom", loaded_g.nodes)
            self.assertEqual(loaded_g.nodes["PC_Custom"]["ip"], "192.168.10.5")
            self.assertTrue(loaded_g.has_edge("PC_Custom", "R1"))
            self.assertEqual(loaded_g["PC_Custom"]["R1"]["cost"], 3)
            self.assertEqual(loaded_g["PC_Custom"]["R1"]["latency_ms"], 10.0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------------------
    # Feature 6: Dynamic Route Participation & Metrics Tests
    # -------------------------------------------------------------------------
    def test_manually_added_device_participates_in_route(self):
        g = build_network()
        # Add high-speed router R4 directly connecting R1 to Server with cost=1, latency=1
        add_device(g, "R4", device_type="Router", ip="10.0.4.1")
        connect_devices(g, "R1", "R4", cost=1, latency_ms=1)
        connect_devices(g, "R4", "Server", cost=1, latency_ms=1)

        # Baseline cost was R1-R2 (1) + R2-Server (1) = 2.
        # Now R1-R4 (1) + R4-Server (1) = 2.
        # Let's break R1-R2 and R1-R3 to force traffic through R4
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["status"] = "DOWN"

        path = shortest_path(g, source="PC1", target="Server")
        self.assertEqual(path, ["PC1", "R1", "R4", "Server"])
        self.assertTrue(path_is_usable(g, path))

    def test_custom_topology_metrics(self):
        g = build_network()
        add_device(g, "PC99", device_type="PC")
        connect_devices(g, "PC99", "Server", cost=10, latency_ms=50, packet_loss=5.0)
        path = ["PC99", "Server"]
        metrics = make_metrics(g, path, diagnosis_time=0.01, recovery_time=0.02)
        self.assertEqual(metrics["Reachability"], "REACHABLE")
        self.assertEqual(metrics["Hop count"], 1)
        self.assertEqual(metrics["Route cost"], 10)
        self.assertEqual(metrics["Average link latency (ms)"], 50.0)
        self.assertEqual(metrics["Maximum packet loss (%)"], 5.0)

    # -------------------------------------------------------------------------
    # Drag-and-Drop Interactive Positioning Tests
    # -------------------------------------------------------------------------
    def test_drag_and_drop_existing_devices(self):
        import tkinter as tk
        from main import App
        from matplotlib.backend_bases import MouseEvent

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            targets = {
                "PC1": (-1.0, 1.5),
                "R1": (0.5, 0.8),
                "R2": (1.8, 2.1),
                "R3": (1.9, -0.2),
                "Server": (3.5, 1.2)
            }

            for node_name, (tx, ty) in targets.items():
                p = app.get_node_position(node_name)
                disp = app.ax.transData.transform(p)
                ep = MouseEvent("button_press_event", app.canvas, disp[0], disp[1], button=1)
                ep.xdata, ep.ydata = p[0], p[1]
                ep.inaxes = app.ax
                app.on_press(ep)
                self.assertEqual(app.drag_node, node_name)
                self.assertTrue(app.is_dragging)

                em = MouseEvent("motion_notify_event", app.canvas, disp[0] + 15, disp[1] + 15, button=1)
                em.xdata, em.ydata = tx, ty
                em.inaxes = app.ax
                app.on_motion(em)
                self.assertEqual(app.node_pos[node_name], (tx, ty))

                er = MouseEvent("button_release_event", app.canvas, disp[0] + 15, disp[1] + 15, button=1)
                er.xdata, er.ydata = tx, ty
                er.inaxes = app.ax
                app.on_release(er)
                self.assertFalse(app.is_dragging)
                self.assertIsNone(app.drag_node)
                self.assertEqual(app.node_pos[node_name], (tx, ty))

            # Verify all connected links remain valid and attached
            for u, v in [("PC1", "R1"), ("R1", "R2"), ("R2", "Server"), ("R1", "R3"), ("R3", "Server")]:
                self.assertTrue(app.g.has_edge(u, v))
                self.assertEqual(app.g[u][v]["status"], "UP")
        finally:
            root.update_idletasks()
            root.destroy()

    def test_drag_and_drop_newly_added_device(self):
        import tkinter as tk
        from main import App
        from matplotlib.backend_bases import MouseEvent

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Add PC6 and connect to R1
            add_device(app.g, "PC6", device_type="PC", ip="192.168.1.66")
            connect_devices(app.g, "PC6", "R1", cost=2, latency_ms=4.0, packet_loss=0.0)
            app.refresh_endpoint_selectors()
            app.draw()
            root.update()

            p = app.get_node_position("PC6")
            disp = app.ax.transData.transform(p)
            ep = MouseEvent("button_press_event", app.canvas, disp[0], disp[1], button=1)
            ep.xdata, ep.ydata = p[0], p[1]
            ep.inaxes = app.ax
            app.on_press(ep)
            self.assertEqual(app.drag_node, "PC6")

            em = MouseEvent("motion_notify_event", app.canvas, disp[0] + 25, disp[1] + 25, button=1)
            em.xdata, em.ydata = -2.2, 0.4
            em.inaxes = app.ax
            app.on_motion(em)

            er = MouseEvent("button_release_event", app.canvas, disp[0] + 25, disp[1] + 25, button=1)
            er.xdata, er.ydata = -2.2, 0.4
            er.inaxes = app.ax
            app.on_release(er)

            self.assertEqual(app.node_pos["PC6"], (-2.2, 0.4))
            self.assertTrue(app.g.has_edge("PC6", "R1"))
            self.assertEqual(app.g["PC6"]["R1"]["cost"], 2)
            self.assertEqual(app.g["PC6"]["R1"]["latency_ms"], 4.0)
        finally:
            root.update_idletasks()
            root.destroy()

    def test_dragged_positions_preserved_across_save_and_load(self):
        import tkinter as tk
        from main import App
        from matplotlib.backend_bases import MouseEvent

        root = tk.Tk()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            app = App(root)
            root.update()

            # Move PC1 and Server to custom coordinates
            p_pc1 = app.get_node_position("PC1")
            disp_pc1 = app.ax.transData.transform(p_pc1)
            ep = MouseEvent("button_press_event", app.canvas, disp_pc1[0], disp_pc1[1], button=1)
            ep.xdata, ep.ydata = p_pc1[0], p_pc1[1]
            ep.inaxes = app.ax
            app.on_press(ep)
            em = MouseEvent("motion_notify_event", app.canvas, disp_pc1[0], disp_pc1[1], button=1)
            em.xdata, em.ydata = -1.5, 2.5
            em.inaxes = app.ax
            app.on_motion(em)
            er = MouseEvent("button_release_event", app.canvas, disp_pc1[0], disp_pc1[1], button=1)
            er.xdata, er.ydata = -1.5, 2.5
            er.inaxes = app.ax
            app.on_release(er)

            save_topology_to_file(app.g, temp_path, app.node_pos)
            loaded_g, loaded_pos = load_topology_from_file(temp_path)

            self.assertEqual(loaded_pos["PC1"], (-1.5, 2.5))
            self.assertEqual(loaded_pos["PC1"], app.node_pos["PC1"])
            self.assertEqual(loaded_pos["Server"], app.node_pos["Server"])
        finally:
            root.update_idletasks()
            root.destroy()
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------------------
    # Phase 1: Multiple-Route Discovery, Comparison & Selection Tests
    # -------------------------------------------------------------------------
    def test_multiple_route_discovery_baseline(self):
        g = build_network()
        routes = discover_routes(g, source="PC1", target="Server")
        self.assertEqual(len(routes), 2)

        r_primary = [r for r in routes if r["path"] == ["PC1", "R1", "R2", "Server"]][0]
        r_backup = [r for r in routes if r["path"] == ["PC1", "R1", "R3", "Server"]][0]

        # Verify Primary Route metrics: 1(PC1-R1) + 1(R1-R2) + 1(R2-Server) = 3 cost; 2+3+3 = 8ms latency
        self.assertEqual(r_primary["cost"], 3)
        self.assertEqual(r_primary["latency_ms"], 8.0)
        self.assertEqual(r_primary["max_loss"], 0.0)
        self.assertEqual(r_primary["availability"], "Healthy")

        # Verify Backup Route metrics: 1(PC1-R1) + 2(R1-R3) + 2(R3-Server) = 5 cost; 2+4+4 = 10ms latency
        self.assertEqual(r_backup["cost"], 5)
        self.assertEqual(r_backup["latency_ms"], 10.0)
        self.assertEqual(r_backup["max_loss"], 0.0)
        self.assertEqual(r_backup["availability"], "Healthy")

        # Verify Best Route Selection: Primary chosen due to lower cost (3 vs 5)
        selection = select_best_route(g, routes=routes)
        self.assertEqual(selection["selected_path"], ["PC1", "R1", "R2", "Server"])
        self.assertIn("optimal healthy route", selection["explanation"])
        self.assertIn("PC1 -> R1 -> R2 -> Server", selection["explanation"])

    def test_route_selection_on_link_failure(self):
        g = build_network()
        s = inject_fault(g, "Link failure (R2-Server)")
        routes = discover_routes(g, source="PC1", target="Server")

        r_primary = [r for r in routes if r["path"] == ["PC1", "R1", "R2", "Server"]][0]
        r_backup = [r for r in routes if r["path"] == ["PC1", "R1", "R3", "Server"]][0]

        self.assertEqual(r_primary["availability"], "Unavailable")
        self.assertFalse(r_primary["is_usable"])
        self.assertTrue(any("DOWN" in b for b in r_primary["bottlenecks"]))

        self.assertEqual(r_backup["availability"], "Healthy")
        self.assertTrue(r_backup["is_usable"])

        selection = select_best_route(g, routes=routes)
        self.assertEqual(selection["selected_path"], ["PC1", "R1", "R3", "Server"])
        self.assertIn("unavailable", selection["explanation"])

    def test_route_selection_on_high_latency(self):
        g = build_network()
        s = inject_fault(g, "High latency (R1-R2)")
        routes = discover_routes(g, source="PC1", target="Server")

        r_primary = [r for r in routes if r["path"] == ["PC1", "R1", "R2", "Server"]][0]
        r_backup = [r for r in routes if r["path"] == ["PC1", "R1", "R3", "Server"]][0]

        self.assertEqual(r_primary["availability"], "Degraded")
        self.assertTrue(r_primary["is_degraded"])
        self.assertEqual(r_primary["latency_ms"], 254.0)

        self.assertEqual(r_backup["availability"], "Healthy")
        self.assertFalse(r_backup["is_degraded"])

        selection = select_best_route(g, routes=routes)
        self.assertEqual(selection["selected_path"], ["PC1", "R1", "R3", "Server"])
        self.assertIn("degraded", selection["explanation"])

    def test_route_selection_on_packet_loss(self):
        g = build_network()
        s = inject_fault(g, "Packet loss (R1-R2)")
        routes = discover_routes(g, source="PC1", target="Server")

        r_primary = [r for r in routes if r["path"] == ["PC1", "R1", "R2", "Server"]][0]
        r_backup = [r for r in routes if r["path"] == ["PC1", "R1", "R3", "Server"]][0]

        self.assertEqual(r_primary["availability"], "Degraded")
        self.assertEqual(r_primary["max_loss"], 40.0)

        self.assertEqual(r_backup["availability"], "Healthy")
        self.assertEqual(r_backup["max_loss"], 0.0)

        selection = select_best_route(g, routes=routes)
        self.assertEqual(selection["selected_path"], ["PC1", "R1", "R3", "Server"])
        self.assertIn("degraded", selection["explanation"])

    def test_route_selection_all_routes_degraded(self):
        g = build_network()
        # Degrade both routes: R1-R2 has 40% loss, R1-R3 has 10% loss
        g["R1"]["R2"]["packet_loss"] = 40.0
        g["R1"]["R3"]["packet_loss"] = 10.0

        routes = discover_routes(g, source="PC1", target="Server")
        for r in routes:
            self.assertEqual(r["availability"], "Degraded")

        selection = select_best_route(g, routes=routes)
        # Should pick R3 path because 10% loss < 40% loss
        self.assertEqual(selection["selected_path"], ["PC1", "R1", "R3", "Server"])
        self.assertIn("Warning: No completely healthy path exists", selection["explanation"])

    def test_route_selection_all_routes_down(self):
        g = build_network()
        # Sever both paths
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["status"] = "DOWN"

        routes = discover_routes(g, source="PC1", target="Server")
        for r in routes:
            self.assertEqual(r["availability"], "Unavailable")

        selection = select_best_route(g, routes=routes)
        self.assertIsNone(selection["selected_path"])
        self.assertIsNone(selection["selected_route"])
        self.assertIn("All candidate routes are UNAVAILABLE", selection["explanation"])

    def test_custom_topology_three_routes_discovery(self):
        g = build_network()
        # Add high-speed direct router R4
        add_device(g, "R4", device_type="Router", ip="10.0.4.1")
        connect_devices(g, "PC1", "R4", cost=1, latency_ms=1.0)
        connect_devices(g, "R4", "Server", cost=1, latency_ms=1.0)

        routes = discover_routes(g, source="PC1", target="Server")
        # Now 3 simple paths: PC1-R4-Server, PC1-R1-R2-Server, PC1-R1-R3-Server
        self.assertEqual(len(routes), 3)

        selection = select_best_route(g, routes=routes)
        # R4 route has cost 2 (1+1) and latency 2ms (1+1), which beats R2 (cost 3) and R3 (cost 5)
        self.assertEqual(selection["selected_path"], ["PC1", "R4", "Server"])
        self.assertEqual(selection["selected_route"]["cost"], 2)
        self.assertEqual(selection["selected_route"]["latency_ms"], 2.0)

    def test_route_ranking_equal_cost_latency_tiebreaker(self):
        g = build_network()
        # Make costs identical: R2 path has cost 1+1+1 = 3
        # Configure R3 path links to also have cost 1 each: 1+1+1 = 3
        g["R1"]["R3"]["cost"] = 1
        g["R3"]["Server"]["cost"] = 1

        # R2 path latency: PC1-R1 (2ms) + R1-R2 (3ms) + R2-Server (3ms) = 8.0ms
        # R3 path latency: PC1-R1 (2ms) + R1-R3 (1ms) + R3-Server (1ms) = 4.0ms
        g["R1"]["R3"]["latency_ms"] = 1.0
        g["R3"]["Server"]["latency_ms"] = 1.0

        routes = discover_routes(g, source="PC1", target="Server")
        r2_path = [r for r in routes if r["path"] == ["PC1", "R1", "R2", "Server"]][0]
        r3_path = [r for r in routes if r["path"] == ["PC1", "R1", "R3", "Server"]][0]

        self.assertEqual(r2_path["cost"], 3)
        self.assertEqual(r3_path["cost"], 3)
        self.assertEqual(r2_path["latency_ms"], 8.0)
        self.assertEqual(r3_path["latency_ms"], 4.0)

        # Tie-breaker must select R3 path because 4.0ms < 8.0ms
        selection = select_best_route(g, routes=routes)
        self.assertEqual(selection["selected_path"], ["PC1", "R1", "R3", "Server"])
        self.assertEqual(selection["selected_route"]["latency_ms"], 4.0)

    def test_failed_links_strictly_excluded_from_selection(self):
        g = build_network()
        # Mark PC1-R1-R2-Server link DOWN
        g["PC1"]["R1"]["status"] = "DOWN"
        # Create an alternative working detour PC1 - R4 - Server
        add_device(g, "R4", device_type="Router")
        connect_devices(g, "PC1", "R4", cost=10, latency_ms=50.0, status="UP")
        connect_devices(g, "R4", "Server", cost=10, latency_ms=50.0, status="UP")

        routes = discover_routes(g, source="PC1", target="Server")
        # All routes containing PC1-R1 must be unavailable
        for r in routes:
            if "R1" in r["path"]:
                self.assertFalse(r["is_usable"])
                self.assertEqual(r["availability"], "Unavailable")
                self.assertIn("PC1-R1 (DOWN)", r["bottlenecks"])

        selection = select_best_route(g, routes=routes)
        # Only the working detour PC1-R4-Server must be selected despite high cost (20)
        self.assertEqual(selection["selected_path"], ["PC1", "R4", "Server"])
        self.assertTrue(selection["selected_route"]["is_usable"])

    # -------------------------------------------------------------------------
    # Feature 7: Independent Observation-Based Root-Cause Diagnosis Tests
    # -------------------------------------------------------------------------
    def test_diagnosis_independent_of_injected_fault_label(self):
        """Proves the diagnosis engine produces identical findings regardless of injected fault label."""
        g = build_network()
        s = inject_fault(g, "Link failure (R2-Server)")
        o1 = collect_observations(g, s)
        f1 = diagnose(o1)

        # Remove scenario label completely from graph
        if "scenario" in g.graph:
            del g.graph["scenario"]
        o2 = collect_observations(g)
        f2 = diagnose(o2)

        self.assertEqual([x[0] for x in f1], [x[0] for x in f2])
        self.assertEqual(f1[0].root_cause, "Link failure")
        self.assertEqual(f2[0].root_cause, "Link failure")
        self.assertEqual(f1[0].affected_components, f2[0].affected_components)

    def test_diagnosis_cannot_access_fault_identifier(self):
        """Proves the diagnosis engine operates strictly on raw observations without fault metadata."""
        # Manually constructed observation dict with zero scenario/fault metadata
        raw_obs = {
            "down_links": ["R2-Server"],
            "gateway_ok": True,
            "dns_ok": True,
            "dns_resolution": True,
            "high_latency": [],
            "packet_loss": [],
            "reachability": False,
            "path": None
        }
        # Ensure no scenario or fault keys exist in raw_obs
        self.assertNotIn("scenario", raw_obs)
        self.assertNotIn("fault", raw_obs)

        findings = diagnose(raw_obs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].root_cause, "Link failure")
        self.assertEqual(findings[0].affected_components, ["R2-Server"])
        self.assertEqual(findings[0].severity, "CRITICAL")
        self.assertEqual(findings[0].confidence, 1.0)

    def test_diagnosis_label_deliberately_changed_or_hidden(self):
        """Proves diagnosis result remains unchanged when fault label is changed to a fake decoy."""
        g = build_network()
        inject_fault(g, "Link failure (R2-Server)")

        # Deliberately falsify the scenario name and fault label
        g.graph["scenario"] = "FAKE_DECOY_DNS_FAULT"
        decoy_state = {"fault": "INCORRECT_GATEWAY_LABEL", "source": "PC1", "target": "Server"}

        obs = collect_observations(g, decoy_state)
        findings = diagnose(obs)

        # Diagnosis must report Link failure based on link evidence, completely ignoring decoy labels
        root_causes = [f.root_cause for f in findings]
        self.assertIn("Link failure", root_causes)
        self.assertNotIn("FAKE_DECOY_DNS_FAULT", root_causes)
        self.assertNotIn("INCORRECT_GATEWAY_LABEL", root_causes)
        self.assertIn("R2-Server", findings[0].affected_components)

    def test_diagnose_down_link_from_link_state(self):
        """Proves a DOWN link is diagnosed strictly from link-state telemetry observations."""
        g = build_network()
        # Direct state manipulation without calling inject_fault
        g["R1"]["R3"]["status"] = "DOWN"

        obs = collect_observations(g)
        findings = diagnose(obs)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].root_cause, "Link failure")
        self.assertEqual(findings[0].affected_components, ["R1-R3"])
        self.assertEqual(findings[0].confidence, 1.0)
        self.assertIn("DOWN", findings[0].evidence)

    def test_diagnose_invalid_gateway_from_configuration(self):
        """Proves an invalid gateway is diagnosed from configuration audit observations."""
        g = build_network()
        # Directly set PC1 gateway to a nonexistent node
        g.nodes["PC1"]["gateway"] = "R99"

        obs = collect_observations(g)
        self.assertFalse(obs["gateway_ok"])
        self.assertTrue(any(ig["host"] == "PC1" for ig in obs["invalid_gateways"]))

        findings = diagnose(obs)
        gw_findings = [f for f in findings if f.root_cause == "Incorrect default gateway"]
        self.assertEqual(len(gw_findings), 1)
        self.assertEqual(gw_findings[0].severity, "HIGH")
        self.assertEqual(gw_findings[0].confidence, 0.98)
        self.assertIn("PC1", gw_findings[0].affected_components)
        self.assertIn("R99", gw_findings[0].affected_components)

    def test_diagnose_dns_failure_from_resolution_evidence(self):
        """Proves DNS failure is diagnosed by distinguishing operational IP connectivity from failed DNS probe."""
        g = build_network()
        # DNS unavailable but all links UP
        g.graph["dns_available"] = False

        obs = collect_observations(g)
        # IP path is UP and reachable
        self.assertTrue(obs["reachability"])
        self.assertIsNotNone(obs["path"])
        # DNS resolution is False
        self.assertFalse(obs["dns_ok"])
        self.assertFalse(obs["dns_resolution"])

        findings = diagnose(obs)
        dns_findings = [f for f in findings if f.root_cause == "DNS service failure"]
        self.assertEqual(len(dns_findings), 1)
        self.assertEqual(dns_findings[0].severity, "HIGH")
        self.assertEqual(dns_findings[0].confidence, 0.95)
        self.assertIn("IP network connectivity is operational", dns_findings[0].evidence)

    def test_diagnose_high_latency_and_packet_loss_from_measurements(self):
        """Proves high latency and packet loss are diagnosed from measured metric values exceeding thresholds."""
        g = build_network()
        g["R1"]["R2"]["latency_ms"] = 350.0
        g["R1"]["R2"]["packet_loss"] = 35.0

        obs = collect_observations(g, latency_threshold=100.0, loss_threshold=0.0)
        findings = diagnose(obs)

        root_causes = {f.root_cause for f in findings}
        self.assertIn("High latency", root_causes)
        self.assertIn("Packet loss", root_causes)

        lat_f = next(f for f in findings if f.root_cause == "High latency")
        loss_f = next(f for f in findings if f.root_cause == "Packet loss")

        self.assertEqual(lat_f.affected_components, ["R1-R2"])
        self.assertEqual(lat_f.confidence, 0.90)
        self.assertEqual(loss_f.affected_components, ["R1-R2"])
        self.assertEqual(loss_f.confidence, 0.92)

    def test_multiple_simultaneous_faults_produce_multiple_findings(self):
        """Proves multiple simultaneous faults produce multiple distinct findings."""
        g = build_network()
        # Inject 4 simultaneous distinct faults
        g["R2"]["Server"]["status"] = "DOWN"
        g.nodes["PC1"]["gateway"] = "R99"
        g.graph["dns_available"] = False
        g["R1"]["R2"]["latency_ms"] = 250.0

        obs = collect_observations(g)
        findings = diagnose(obs)

        self.assertEqual(len(findings), 4)
        causes = [f.root_cause for f in findings]
        self.assertIn("Link failure", causes)
        self.assertIn("Incorrect default gateway", causes)
        self.assertIn("DNS service failure", causes)
        self.assertIn("High latency", causes)

        # Check each finding has severity, confidence, affected components, and recommended action
        for f in findings:
            self.assertTrue(len(f.root_cause) > 0)
            self.assertTrue(len(f.evidence) > 0)
            self.assertTrue(len(f.severity) > 0)
            self.assertTrue(0.0 < f.confidence <= 1.0)
            self.assertTrue(len(f.recommended_action) > 0)

    def test_recovery_uses_diagnosis_and_verifies_outcome(self):
        """Proves recovery engine executes repairs based on diagnosis findings and verifies outcome."""
        g = build_network()
        g.nodes["PC1"]["gateway"] = "R99"
        g.graph["dns_available"] = False

        # Independent observation and diagnosis
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertEqual(len(findings), 2)

        # Clear any scenario from graph to prove recovery does not rely on it
        g.graph.pop("scenario", None)

        result = recover(g, findings=findings)
        self.assertTrue(result["verified"])
        self.assertTrue(result["ip_connectivity"])
        self.assertTrue(result["dns_resolution"])
        self.assertEqual(result["status"], "RECOVERY VERIFIED")
        self.assertEqual(g.nodes["PC1"]["gateway"], "R1")
        self.assertTrue(g.graph["dns_available"])

    def test_confidence_levels_calibrated_and_not_arbitrary_100(self):
        """Proves confidence levels reflect justification and do not claim 100% without direct certainty."""
        g = build_network()
        # Test link down (hardware conclusive = 1.0)
        g["R1"]["R2"]["status"] = "DOWN"
        # Test latency (measured/sampled = 0.90)
        g["R1"]["R3"]["latency_ms"] = 250.0
        # Test loss (sampled = 0.92)
        g["PC1"]["R1"]["packet_loss"] = 20.0
        # Test DNS (probe = 0.95)
        g.graph["dns_available"] = False
        # Test gateway (configuration audit = 0.98)
        g.nodes["PC1"]["gateway"] = "R99"

        obs = collect_observations(g)
        findings = diagnose(obs)

        conf_by_cause = {f.root_cause: f.confidence for f in findings}
        self.assertEqual(conf_by_cause["Link failure"], 1.0)  # Conclusive proof
        self.assertEqual(conf_by_cause["Incorrect default gateway"], 0.98)
        self.assertEqual(conf_by_cause["DNS service failure"], 0.95)
        self.assertEqual(conf_by_cause["High latency"], 0.90)  # Sampled RTT
        self.assertEqual(conf_by_cause["Packet loss"], 0.92)   # Sampled loss

        # Assert that non-conclusive measurement faults do NOT report 100%
        self.assertLess(conf_by_cause["High latency"], 1.0)
        self.assertLess(conf_by_cause["Packet loss"], 1.0)
        self.assertLess(conf_by_cause["DNS service failure"], 1.0)

    def test_diagnostic_finding_backward_compatibility(self):
        """Proves DiagnosticFinding supports tuple unpacking and legacy index access."""
        finding = DiagnosticFinding(
            root_cause="Test Fault",
            evidence="Test Evidence",
            affected_components=["R1-R2"],
            severity="HIGH",
            confidence=0.95,
            recommended_action="Test Action"
        )
        # Test tuple indexing
        self.assertEqual(finding[0], "Test Fault")
        self.assertEqual(finding[1], "Test Evidence")
        self.assertEqual(len(finding), 2)

        # Test tuple unpacking
        name, why = finding
        self.assertEqual(name, "Test Fault")
        self.assertEqual(why, "Test Evidence")

        # Test attribute access
        self.assertEqual(finding.root_cause, "Test Fault")
        self.assertEqual(finding.evidence, "Test Evidence")
        self.assertEqual(finding.affected_components, ["R1-R2"])
        self.assertEqual(finding.severity, "HIGH")
        self.assertEqual(finding.confidence, 0.95)
        self.assertEqual(finding.recommended_action, "Test Action")

        # Test dictionary conversion
        d = finding.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["root_cause"], "Test Fault")

    # -------------------------------------------------------------------------
    # Cisco Packet Tracer Simulation Workspace Tests
    # -------------------------------------------------------------------------
    def test_packet_tracer_palette_auto_naming(self):
        """Verifies auto-generation of unique device names for all palette types."""
        g = build_network()
        # Default network has PC1, R1, R2, R3, Server
        self.assertEqual(generate_unique_device_name(g, "Router"), "Router1")
        self.assertEqual(generate_unique_device_name(g, "Switch"), "Switch1")
        self.assertEqual(generate_unique_device_name(g, "PC"), "PC2")
        self.assertEqual(generate_unique_device_name(g, "Laptop"), "Laptop1")
        self.assertEqual(generate_unique_device_name(g, "Server"), "Server1")

        # Add Router1, Switch1, Laptop1 and ensure counters increment
        add_device(g, "Router1", "Router")
        add_device(g, "Switch1", "Switch")
        add_device(g, "Laptop1", "Laptop")
        self.assertEqual(generate_unique_device_name(g, "Router"), "Router2")
        self.assertEqual(generate_unique_device_name(g, "Switch"), "Switch2")
        self.assertEqual(generate_unique_device_name(g, "Laptop"), "Laptop2")

    def test_packet_tracer_laptop_device_support(self):
        """Verifies Laptop end-device support in topology, addressing, and route discovery."""
        g = build_network()
        # Add a Switch and Laptop
        add_device(g, "SW1", "Switch", ip="192.168.1.254")
        add_device(g, "Laptop1", "Laptop", ip="192.168.1.50", subnet_mask="255.255.255.0", gateway="R1", dns_server="8.8.8.8")
        connect_devices(g, "Laptop1", "SW1", cost=1, latency_ms=1.5, connection_type="Copper Straight-Through")
        connect_devices(g, "SW1", "R1", cost=1, latency_ms=1.5, connection_type="Copper Straight-Through")

        # Verify endpoint resolution resolves Laptop
        src, dst = resolve_endpoints(g)
        self.assertEqual(dst, "Server")

        # Discover routes from Laptop1 to Server
        routes = discover_routes(g, source="Laptop1", target="Server")
        self.assertGreaterEqual(len(routes), 2)
        paths = [r["path"] for r in routes]
        self.assertIn(["Laptop1", "SW1", "R1", "R2", "Server"], paths)
        self.assertIn(["Laptop1", "SW1", "R1", "R3", "Server"], paths)

        # Best route selection
        sel = select_best_route(g, routes=routes)
        self.assertEqual(sel["selected_path"], ["Laptop1", "SW1", "R1", "R2", "Server"])

    def test_packet_tracer_connect_tool_and_connection_types(self):
        """Verifies connection management with cable types, duplicate prevention, and self-connection prevention."""
        g = build_network()
        add_device(g, "Router1", "Router")
        add_device(g, "Router2", "Router")

        # Test Fiber cable connection
        connect_devices(g, "Router1", "Router2", cost=5, latency_ms=1.0, connection_type="Fiber")
        self.assertTrue(g.has_edge("Router1", "Router2"))
        self.assertEqual(g["Router1"]["Router2"]["connection_type"], "Fiber")
        self.assertEqual(g["Router1"]["Router2"]["cost"], 5)

        # Test duplicate link prevention
        with self.assertRaises(ValueError):
            connect_devices(g, "Router1", "Router2")

        # Test self-connection prevention
        with self.assertRaises(ValueError):
            connect_devices(g, "Router1", "Router1")

    def test_packet_tracer_dynamic_fault_injection_and_diagnosis(self):
        """Verifies dynamic fault injection targeting arbitrary links and observation-based diagnosis."""
        g = build_network()
        add_device(g, "SW1", "Switch")
        add_device(g, "Laptop1", "Laptop", gateway="R1")
        connect_devices(g, "Laptop1", "SW1", cost=1, latency_ms=2.0)
        connect_devices(g, "SW1", "R1", cost=1, latency_ms=2.0)

        # Dynamic fault injection on custom link
        inject_fault(g, "Link failure", target_link=("Laptop1", "SW1"))
        self.assertEqual(g["Laptop1"]["SW1"]["status"], "DOWN")

        # Collect observations and verify observation-based diagnosis
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertTrue(any("Laptop1" in f.evidence and "SW1" in f.evidence for f in findings))
        self.assertTrue(any(f.root_cause == "Link failure" for f in findings))

    def test_packet_tracer_recovery_and_verification_dynamic(self):
        """Verifies automated recovery restores health and reroutes on dynamic topologies."""
        g = build_network()
        add_device(g, "SW1", "Switch")
        add_device(g, "Laptop1", "Laptop", gateway="R99")
        connect_devices(g, "Laptop1", "SW1", cost=1, latency_ms=2.0)
        connect_devices(g, "SW1", "R1", cost=1, latency_ms=2.0)

        # Fail link R1-R2
        g["R1"]["R2"]["status"] = "DOWN"
        obs = collect_observations(g, source="Laptop1", target="Server")
        findings = diagnose(obs)
        self.assertTrue(any(f.root_cause == "Link failure" for f in findings))
        self.assertTrue(any(f.root_cause == "Incorrect default gateway" for f in findings))

        rec = recover(g, findings=findings, source="Laptop1", target="Server")
        self.assertTrue(rec["verified"])
        self.assertEqual(g.nodes["Laptop1"]["gateway"], "R1")
        self.assertEqual(rec["route"], ["Laptop1", "SW1", "R1", "R3", "Server"])

    def test_packet_tracer_workspace_tools_and_zoom(self):
        """Verifies GUI mode switching, tool state, and zoom/pan functionality."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Tool mode switching
            app.set_tool("connect")
            self.assertEqual(app.current_tool, "connect")
            app.set_tool("delete")
            self.assertEqual(app.current_tool, "delete")
            app.set_tool("move")
            self.assertEqual(app.current_tool, "move")
            app.set_tool("select")
            self.assertEqual(app.current_tool, "select")

            # Zoom controls
            init_xlim = app.ax.get_xlim()
            app.zoom_in()
            zoomed_in_xlim = app.ax.get_xlim()
            self.assertLess(zoomed_in_xlim[1] - zoomed_in_xlim[0], init_xlim[1] - init_xlim[0])

            app.zoom_out()
            zoomed_out_xlim = app.ax.get_xlim()
            self.assertGreater(zoomed_out_xlim[1] - zoomed_out_xlim[0], zoomed_in_xlim[1] - zoomed_in_xlim[0])

            app.fit_to_screen()
            fit_xlim = app.ax.get_xlim()
            self.assertIsNotNone(fit_xlim)
        finally:
            root.update_idletasks()
            root.destroy()

    def test_packet_tracer_device_palette_addition_and_inspection(self):
        """Verifies adding devices via palette and modifying parameters via Inspector."""
        import tkinter as tk
        from unittest.mock import patch
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Add Laptop from palette
            app.add_device_from_palette("Laptop")
            self.assertIn("Laptop1", app.g.nodes)
            self.assertEqual(app.selected_node, "Laptop1")
            self.assertEqual(app.insp_dev_name.get(), "Laptop1")

            # Inspect and modify properties
            app.insp_dev_ip.set("192.168.10.55")
            app.insp_dev_gw.set("R1")
            with patch("tkinter.messagebox.showinfo"):
                app.apply_device_inspection_changes()

            self.assertEqual(app.g.nodes["Laptop1"]["ip"], "192.168.10.55")
            self.assertEqual(app.g.nodes["Laptop1"]["gateway"], "R1")
        finally:
            root.update_idletasks()
            root.destroy()

    def test_packet_tracer_link_inspection_and_editing(self):
        """Verifies selecting and editing link properties through Inspector tab."""
        import tkinter as tk
        from unittest.mock import patch
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Select link R1 <-> R2
            app.select_link_for_inspection("R1", "R2")
            self.assertEqual(app.selected_link, ("R1", "R2"))
            self.assertEqual(app.insp_link_label.get(), "R1 <-> R2")

            # Modify link parameters
            app.insp_link_cost.set("7")
            app.insp_link_lat.set("12.5")
            app.insp_link_loss.set("3.0")
            app.insp_link_type.set("Fiber")
            with patch("tkinter.messagebox.showinfo"):
                app.apply_link_inspection_changes()

            edge = app.g["R1"]["R2"]
            self.assertEqual(edge["cost"], 7)
            self.assertEqual(edge["latency_ms"], 12.5)
            self.assertEqual(edge["packet_loss"], 3.0)
            self.assertEqual(edge["connection_type"], "Fiber")
        finally:
            root.update_idletasks()
            root.destroy()

    def test_packet_tracer_save_and_load_with_laptops_and_connections(self):
        """Verifies topology serialization and loading preserving Laptops and connection types."""
        g = build_network()
        add_device(g, "Laptop1", "Laptop", ip="10.0.0.5", subnet_mask="255.255.0.0", gateway="R1", dns_server="1.1.1.1", pos=(-2.5, 1.5))
        connect_devices(g, "Laptop1", "R1", cost=2, latency_ms=3.5, packet_loss=0.0, status="UP", connection_type="Fiber")

        positions = dict(g.graph.get("node_positions", {}))
        positions["Laptop1"] = (-2.5, 1.5)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            save_topology_to_file(g, temp_path, positions)
            loaded_g, loaded_pos = load_topology_from_file(temp_path)

            self.assertIn("Laptop1", loaded_g.nodes)
            self.assertEqual(loaded_g.nodes["Laptop1"]["type"], "Laptop")
            self.assertEqual(loaded_g.nodes["Laptop1"]["ip"], "10.0.0.5")
            self.assertEqual(loaded_g.nodes["Laptop1"]["dns_server"], "1.1.1.1")
            self.assertEqual(loaded_pos["Laptop1"], (-2.5, 1.5))

            self.assertTrue(loaded_g.has_edge("Laptop1", "R1"))
            self.assertEqual(loaded_g["Laptop1"]["R1"]["connection_type"], "Fiber")
            self.assertEqual(loaded_g["Laptop1"]["R1"]["cost"], 2)
            self.assertEqual(loaded_g["Laptop1"]["R1"]["latency_ms"], 3.5)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # -------------------------------------------------------------------------
    # Cisco Packet Tracer: Copy, Paste, Cut, Duplicate, Undo & Redo Tests
    # -------------------------------------------------------------------------
    def test_copy_and_paste_single_device_preserves_config_no_links(self):
        """Verifies copying a device preserves configuration, generates unique ID, and does not duplicate links."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Select PC1
            app.selected_node = "PC1"
            app.selected_nodes = ["PC1"]
            orig_d = dict(app.g.nodes["PC1"])
            orig_pos = app.node_pos["PC1"]

            # Copy
            copied = app.copy_selected()
            self.assertEqual(len(copied), 1)
            self.assertEqual(copied[0]["orig_name"], "PC1")
            self.assertEqual(copied[0]["type"], "PC")
            self.assertEqual(copied[0]["ip"], orig_d.get("ip", ""))

            # Paste
            pasted = app.paste_clipboard()
            self.assertEqual(len(pasted), 1)
            new_dev = pasted[0]
            self.assertEqual(new_dev, "PC2")
            self.assertIn(new_dev, app.g.nodes)

            # Check configuration preserved
            new_d = app.g.nodes[new_dev]
            self.assertEqual(new_d["type"], "PC")
            self.assertEqual(new_d["ip"], orig_d.get("ip", ""))
            self.assertEqual(new_d["subnet_mask"], orig_d.get("subnet_mask", "255.255.255.0"))
            self.assertEqual(new_d["gateway"], orig_d.get("gateway", "R1"))

            # Check no links duplicated
            self.assertEqual(app.g.degree(new_dev), 0)

            # Check position offset
            new_pos = app.node_pos[new_dev]
            self.assertNotEqual(new_pos, orig_pos)
            self.assertAlmostEqual(new_pos[0], orig_pos[0] + 0.5, places=2)
            self.assertAlmostEqual(new_pos[1], orig_pos[1] - 0.4, places=2)
        finally:
            root.update_idletasks()
            root.destroy()

    def test_repeated_pasting_unique_names_and_cascading_offset(self):
        """Verifies repeated Ctrl+V creates distinct unique devices with cascading positions."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            app.selected_node = "PC1"
            app.selected_nodes = ["PC1"]
            app.copy_selected()

            # Paste 3 times
            p1 = app.paste_clipboard()[0]
            p2 = app.paste_clipboard()[0]
            p3 = app.paste_clipboard()[0]

            self.assertEqual(p1, "PC2")
            self.assertEqual(p2, "PC3")
            self.assertEqual(p3, "PC4")

            # Check all have unique coordinates
            pos1 = app.node_pos[p1]
            pos2 = app.node_pos[p2]
            pos3 = app.node_pos[p3]
            self.assertNotEqual(pos1, pos2)
            self.assertNotEqual(pos2, pos3)
            self.assertGreater(pos2[0], pos1[0])
            self.assertGreater(pos3[0], pos2[0])
        finally:
            root.update_idletasks()
            root.destroy()

    def test_cut_device_and_paste(self):
        """Verifies Cut removes device and its links from topology and allows pasting afterward."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Add custom switch and connect to R1
            add_device(app.g, "Switch1", device_type="Switch", pos=(0.5, 0.5))
            connect_devices(app.g, "Switch1", "R1")
            app.node_pos["Switch1"] = (0.5, 0.5)

            self.assertIn("Switch1", app.g.nodes)
            self.assertTrue(app.g.has_edge("Switch1", "R1"))

            # Cut Switch1
            app.selected_node = "Switch1"
            app.selected_nodes = ["Switch1"]
            cut_nodes = app.cut_selected()
            self.assertEqual(cut_nodes, ["Switch1"])

            # Verify Switch1 and its edge are gone from topology
            self.assertNotIn("Switch1", app.g.nodes)
            self.assertNotIn("Switch1", app.node_pos)

            # Paste the cut switch
            pasted = app.paste_clipboard()
            self.assertEqual(len(pasted), 1)
            new_sw = pasted[0]
            self.assertEqual(new_sw, "Switch1")
            self.assertIn(new_sw, app.g.nodes)
            self.assertEqual(app.g.nodes[new_sw]["type"], "Switch")
            # Existing connections are not copied
            self.assertFalse(app.g.has_edge(new_sw, "R1"))
        finally:
            root.update_idletasks()
            root.destroy()

    def test_duplicate_device_shortcut(self):
        """Verifies quick duplicate operation preserves configuration and assigns unique name."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            app.selected_node = "Server"
            app.selected_nodes = ["Server"]
            app.g.nodes["Server"]["ip"] = "192.168.1.100"

            duplicated = app.duplicate_selected()
            self.assertEqual(len(duplicated), 1)
            new_srv = duplicated[0]
            self.assertEqual(new_srv, "Server1")
            self.assertIn(new_srv, app.g.nodes)
            self.assertEqual(app.g.nodes[new_srv]["type"], "Server")
            self.assertEqual(app.g.nodes[new_srv]["ip"], "192.168.1.100")
            self.assertEqual(app.g.degree(new_srv), 0)
        finally:
            root.update_idletasks()
            root.destroy()

    def test_multiple_selection_and_copy_paste_relative_positions(self):
        """Verifies selecting multiple devices, copying them, and pasting preserves relative layout."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Select R1 and R2
            app.selected_nodes = ["R1", "R2"]
            app.selected_node = "R2"

            p_r1 = app.node_pos["R1"]
            p_r2 = app.node_pos["R2"]
            rel_orig = (round(p_r2[0] - p_r1[0], 2), round(p_r2[1] - p_r1[1], 2))

            copied = app.copy_selected()
            self.assertEqual(len(copied), 2)

            pasted = app.paste_clipboard()
            self.assertEqual(len(pasted), 2)
            d1, d2 = pasted[0], pasted[1]

            # Relative offset between pasted devices must match original
            p_d1 = app.node_pos[d1]
            p_d2 = app.node_pos[d2]
            rel_pasted = (round(p_d2[0] - p_d1[0], 2), round(p_d2[1] - p_d1[1], 2))
            self.assertEqual(rel_orig, rel_pasted)

            # Neither has external links
            self.assertEqual(app.g.degree(d1), 0)
            self.assertEqual(app.g.degree(d2), 0)
        finally:
            root.update_idletasks()
            root.destroy()

    def test_undo_and_redo_device_and_link_operations(self):
        """Verifies undo and redo for device addition, connection, and deletion."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # 1. Add device
            app.add_device_from_palette("Laptop")
            self.assertIn("Laptop1", app.g.nodes)

            # Undo addition
            app.undo()
            self.assertNotIn("Laptop1", app.g.nodes)

            # Redo addition
            app.redo()
            self.assertIn("Laptop1", app.g.nodes)

            # 2. Connect devices
            app.record_undo_state("Connect Laptop1-R1")
            connect_devices(app.g, "Laptop1", "R1", cost=2)
            self.assertTrue(app.g.has_edge("Laptop1", "R1"))

            # Undo connection
            app.undo()
            self.assertFalse(app.g.has_edge("Laptop1", "R1"))

            # Redo connection
            app.redo()
            self.assertTrue(app.g.has_edge("Laptop1", "R1"))
        finally:
            root.update_idletasks()
            root.destroy()

    def test_keyboard_shortcut_safety_when_text_field_focused(self):
        """Verifies keyboard shortcuts are not intercepted when editing text input fields."""
        import tkinter as tk
        from tkinter import ttk
        from unittest.mock import MagicMock
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            entry_mock = ttk.Entry(root)
            canvas_mock = app.canvas.get_tk_widget()

            # Event targeting an Entry widget
            evt_entry = MagicMock()
            evt_entry.widget = entry_mock

            # Handlers must return None so entry handles text copy/paste/cut/undo
            self.assertIsNone(app._on_ctrl_c(evt_entry))
            self.assertIsNone(app._on_ctrl_v(evt_entry))
            self.assertIsNone(app._on_ctrl_x(evt_entry))
            self.assertIsNone(app._on_ctrl_z(evt_entry))
            self.assertIsNone(app._on_ctrl_y(evt_entry))
            self.assertIsNone(app._on_ctrl_a(evt_entry))
            self.assertIsNone(app._on_delete_key(evt_entry))

            # Event targeting canvas
            evt_canvas = MagicMock()
            evt_canvas.widget = canvas_mock

            # Handlers must intercept and return "break"
            app.selected_node = "PC1"
            app.selected_nodes = ["PC1"]
            self.assertEqual(app._on_ctrl_c(evt_canvas), "break")
            self.assertEqual(len(app.clipboard), 1)

            self.assertEqual(app._on_ctrl_v(evt_canvas), "break")
            self.assertIn("PC2", app.g.nodes)

            self.assertEqual(app._on_ctrl_z(evt_canvas), "break")
            self.assertNotIn("PC2", app.g.nodes)
        finally:
            root.update_idletasks()
            root.destroy()

    def test_fault_injection_all_six_scenarios_and_backend_mapping(self):
        """Verifies all six UI scenario options inject properly, map to backend, diagnose, and recover."""
        expected_scenarios = [
            "No Fault \u2013 Healthy Baseline",
            "Link Failure",
            "Wrong Default Gateway",
            "DNS Service Failure",
            "High Network Latency",
            "Packet Loss"
        ]
        self.assertEqual(list(UI_SCENARIOS), expected_scenarios)

        # 1. No Fault \u2013 Healthy Baseline
        g = build_network()
        res = inject_fault(g, "No Fault \u2013 Healthy Baseline")
        self.assertEqual(res["fault"], "No fault")
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertEqual(findings[0].root_cause, "No fault detected")

        # 2. Link Failure
        g = build_network()
        res = inject_fault(g, "Link Failure")
        self.assertEqual(res["fault"], "Link failure (R2-Server)")
        self.assertEqual(g["R2"]["Server"]["status"], "DOWN")
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertTrue(any(f.root_cause == "Link failure" for f in findings))
        rec_res = recover(g, findings=findings)
        self.assertTrue(rec_res["verified"])

        # 3. Wrong Default Gateway
        g = build_network()
        res = inject_fault(g, "Wrong Default Gateway")
        self.assertEqual(res["fault"], "Wrong default gateway")
        self.assertEqual(g.nodes["PC1"]["gateway"], "R9")
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertTrue(any(f.root_cause == "Incorrect default gateway" for f in findings))
        rec_res = recover(g, findings=findings)
        self.assertTrue(rec_res["verified"])
        self.assertEqual(g.nodes["PC1"]["gateway"], "R1")

        # 4. DNS Service Failure
        g = build_network()
        res = inject_fault(g, "DNS Service Failure")
        self.assertEqual(res["fault"], "DNS failure")
        self.assertFalse(g.graph["dns_available"])
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertTrue(any(f.root_cause == "DNS service failure" for f in findings))
        rec_res = recover(g, findings=findings)
        self.assertTrue(rec_res["verified"])
        self.assertTrue(g.graph["dns_available"])

        # 5. High Network Latency
        g = build_network()
        res = inject_fault(g, "High Network Latency")
        self.assertEqual(res["fault"], "High latency (R1-R2)")
        self.assertEqual(g["R1"]["R2"]["latency_ms"], 250.0)
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertTrue(any(f.root_cause == "High latency" for f in findings))

        # 6. Packet Loss
        g = build_network()
        res = inject_fault(g, "Packet Loss")
        self.assertEqual(res["fault"], "Packet loss (R1-R2)")
        self.assertEqual(g["R1"]["R2"]["packet_loss"], 40.0)
        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertTrue(any(f.root_cause == "Packet loss" for f in findings))

    def test_packet_tracer_fault_dropdown_ui_width_height_and_options(self):
        """Verifies the scenario dropdown in Cisco Packet Tracer workspace has sufficient width, height, and options."""
        import tkinter as tk
        from main import App

        root = tk.Tk()
        try:
            app = App(root)
            root.update()

            # Verify dropdown options
            combo = app.scenario_combo
            values = list(combo["values"])
            self.assertEqual(len(values), 6)
            self.assertIn("No Fault \u2013 Healthy Baseline", values)
            self.assertIn("Link Failure", values)
            self.assertIn("Wrong Default Gateway", values)
            self.assertIn("DNS Service Failure", values)
            self.assertIn("High Network Latency", values)
            self.assertIn("Packet Loss", values)

            # Verify width and height
            self.assertGreaterEqual(int(combo["width"]), 28)
            self.assertGreaterEqual(int(combo["height"]), 6)

            # Test selecting and injecting each of the 6 options
            for opt in values:
                app.choice.set(opt)
                app.inject()
                root.update_idletasks()
                if "No Fault" in opt:
                    self.assertEqual(app.badge_lbl["text"], "HEALTHY")
                else:
                    self.assertEqual(app.badge_lbl["text"], "CRITICAL")
                self.assertIn(opt, app.history[-1][1])

            # Test reset restores default option
            app.reset()
            self.assertEqual(app.choice.get(), "No Fault \u2013 Healthy Baseline")
            self.assertEqual(app.badge_lbl["text"], "HEALTHY")
        finally:
            root.update_idletasks()
            root.destroy()

    def test_link_failure_every_connection_and_dynamic_topology(self):
        """Verifies Link Failure fault injection across every single connection in both default and custom topologies."""
        # 1. Test EVERY single connection in the default 5-node topology
        g = build_network()
        all_edges = list(g.edges())
        self.assertEqual(len(all_edges), 5)

        for u, v in all_edges:
            reset_faults(g)
            # Inject Link Failure targeting this specific link using "u ↔ v" formatted string
            target_str = f"{u} \u2194 {v}"
            res = inject_fault(g, "Link Failure", target_link=target_str)
            self.assertEqual(res["fault"], "Link failure (R2-Server)")
            self.assertEqual(res["failed_link_str"], f"{u} \u2194 {v}")
            self.assertEqual(g[u][v]["status"], "DOWN")

            # Verify ONLY the targeted link is DOWN, all other links remain UP
            for eu, ev, ed in g.edges(data=True):
                if (eu == u and ev == v) or (eu == v and ev == u):
                    self.assertEqual(ed["status"], "DOWN")
                else:
                    self.assertEqual(ed["status"], "UP", f"Link {eu}-{ev} should remain UP when {u}-{v} failed")

            # Collect observations independently
            obs = collect_observations(g)
            self.assertEqual(len(obs["down_links"]), 1)
            self.assertIn(obs["down_links"][0], (f"{u}-{v}", f"{v}-{u}"))

            # Diagnosis engine strictly uses observations (no ground-truth cheating)
            findings = diagnose(obs)
            link_findings = [f for f in findings if f.root_cause == "Link failure"]
            self.assertGreaterEqual(len(link_findings), 1)
            self.assertIn(obs["down_links"][0], link_findings[0].affected_components)

            # Recovery engine verification
            rec = recover(g, findings=findings)
            if (u, v) in (("PC1", "R1"), ("R1", "PC1")):
                # Single point of failure: PC1 is disconnected
                self.assertFalse(rec["verified"])
                self.assertEqual(rec["status"], "RECOVERY UNAVAILABLE")
                self.assertFalse(rec["ip_connectivity"])
                self.assertIn("No alternative route exists", rec["actions"][-1])
            elif (u, v) in (("R2", "Server"), ("Server", "R2"), ("R1", "R2"), ("R2", "R1")):
                # Alternate route via R3 exists
                self.assertTrue(rec["verified"])
                self.assertEqual(rec["status"], "RECOVERY VERIFIED")
                self.assertEqual(rec["route"], ["PC1", "R1", "R3", "Server"])
                self.assertIn("selected available alternate route", rec["actions"][-1])
            elif (u, v) in (("R1", "R3"), ("R3", "R1"), ("R3", "Server"), ("Server", "R3")):
                # Primary route via R2 is unaffected: service maintained without redundant failover
                self.assertTrue(rec["verified"])
                self.assertIn(rec["status"], ("SERVICE MAINTAINED", "RECOVERY VERIFIED"))
                self.assertEqual(rec["route"], ["PC1", "R1", "R2", "Server"])

        # 2. Test dynamically across a custom multi-device topology (PC, Laptop, Router, Switch, Server)
        g_custom = build_network()
        # Add new devices
        add_device(g_custom, "Laptop1", "Laptop", ip="192.168.1.15", gateway="R1")
        add_device(g_custom, "SW1", "Switch", ip="192.168.1.2")
        add_device(g_custom, "R4", "Router", ip="10.0.3.1")
        add_device(g_custom, "WebSrv", "Server", ip="10.0.4.10")

        # Connect devices
        connect_devices(g_custom, "Laptop1", "SW1", latency_ms=1.0, packet_loss=0.0, cost=1)
        connect_devices(g_custom, "SW1", "R1", latency_ms=1.5, packet_loss=0.0, cost=1)
        connect_devices(g_custom, "R2", "R4", latency_ms=3.0, packet_loss=0.0, cost=2)
        connect_devices(g_custom, "R3", "R4", latency_ms=4.0, packet_loss=0.0, cost=3)
        connect_devices(g_custom, "R4", "WebSrv", latency_ms=2.0, packet_loss=0.0, cost=1)

        custom_edges = list(g_custom.edges())
        self.assertEqual(len(custom_edges), 10)

        # Loop through ALL 10 connections in the custom topology
        for cu, cv in custom_edges:
            reset_faults(g_custom)
            res = inject_fault(g_custom, "Link Failure", target_link=(cu, cv))
            self.assertEqual(g_custom[cu][cv]["status"], "DOWN")

            # Check that ONLY (cu, cv) is DOWN
            for a, b, d in g_custom.edges(data=True):
                if (a == cu and b == cv) or (a == cv and b == cu):
                    self.assertEqual(d["status"], "DOWN")
                else:
                    self.assertEqual(d["status"], "UP")

            # Verify telemetry observation
            obs = collect_observations(g_custom, source="Laptop1", target="WebSrv")
            self.assertIn(obs["down_links"][0], (f"{cu}-{cv}", f"{cv}-{cu}"))

            # Verify diagnosis
            findings = diagnose(obs)
            self.assertTrue(any(f.root_cause == "Link failure" for f in findings))

    def test_link_failure_gui_dropdown_dialog_and_empty_topology(self):
        """Verifies GUI link selection dropdown, pick dialog, event logging, and empty/all-down edge cases."""
        import tkinter as tk
        from unittest.mock import patch
        from main import App

        root = tk.Tk()
        try:
            with patch("tkinter.messagebox.showwarning"), patch("tkinter.messagebox.showinfo"):
                app = App(root)
                root.update()

                # 1. Test get_topology_link_labels() returns all current connections
                labels = app.get_topology_link_labels()
                self.assertEqual(len(labels), 5)
                self.assertIn("PC1 \u2194 R1", labels)
                self.assertIn("R1 \u2194 R2", labels)
                self.assertIn("R2 \u2194 Server", labels)
                self.assertIn("R1 \u2194 R3", labels)
                self.assertIn("R3 \u2194 Server", labels)

                # 2. Select Link Failure scenario and verify target link controls appear
                app.choice.set("Link Failure")
                app._update_link_failure_controls()
                self.assertEqual(list(app.target_link_combo["values"]), labels)

                # 3. Select PC1 ↔ R1 and inject
                app.target_link_choice.set("PC1 \u2194 R1")
                app.inject()
                root.update_idletasks()
                self.assertEqual(app.g["PC1"]["R1"]["status"], "DOWN")
                self.assertEqual(app.g["R1"]["R2"]["status"], "UP")
                self.assertEqual(app.badge_lbl["text"], "CRITICAL")
                self.assertIn("LINK DOWN: PC1 \u2194 R1", app.status_lbl["text"])

                # Verify event log logged the failed link
                log_entries = [line for line in app.history if "Link Failure on PC1 \u2194 R1" in str(line) or "Link Failure" in str(line)]
                self.assertTrue(len(log_entries) > 0)

                # Recover with PC1 ↔ R1 down -> RECOVERY UNAVAILABLE
                app.recover()
                root.update_idletasks()
                self.assertIn("RECOVERY UNAVAILABLE", app.status_lbl["text"])

                # 4. Reset, select R2 ↔ Server and inject
                app.reset()
                app.choice.set("Link Failure")
                app._update_link_failure_controls()
                app.target_link_choice.set("R2 \u2194 Server")
                app.inject()
                root.update_idletasks()
                self.assertEqual(app.g["R2"]["Server"]["status"], "DOWN")
                self.assertEqual(app.g["R1"]["R3"]["status"], "UP")
                self.assertEqual(app.g["R3"]["Server"]["status"], "UP")

                # Recover with R2 ↔ Server down -> RECOVERY VERIFIED & STABLE
                app.recover()
                root.update_idletasks()
                self.assertIn("RECOVERY VERIFIED & STABLE", app.status_lbl["text"])

                # 5. Empty topology edge case
                app.g.clear()
                app.refresh_target_link_options()
                self.assertEqual(app.get_topology_link_labels(), [])
                # Injecting on empty topology must not raise exception
                app.inject()

                # 6. All links down edge case
                app.reset()
                for _, _, d in app.g.edges(data=True):
                    d["status"] = "DOWN"
                app.choice.set("Link Failure")
                app.inject()  # Gracefully handled without uncaught exception
        finally:
            root.update_idletasks()
            root.destroy()


class RedesignedArchitectureTests(unittest.TestCase):
    """Rigorous validation tests for the redesigned 4-stage diagnosis and recovery architecture.
    
    Verifies:
    1. No-fault baseline
    2. Each of the five individual fault scenarios
    3. Multiple simultaneous faults (evaluating all 5 rules independently)
    4. Diagnosis independence from injected fault labels / metadata
    5. Evidence-based diagnosis with calibrated confidence values
    6. Severity and network impact classification
    7. Route discovery without route activation
    8. Route activation only during recovery
    9. Correct gateway restoration dynamically derived from topology
    10. DNS restoration and independent post-recovery verification
    11. Latency improvement verification (and optimization unavailable reporting)
    12. Packet-loss improvement verification (and recovery unavailable reporting)
    13. Recovery unavailable when no healthy route exists
    14. Failed recovery must not be reported as successful
    15. Failed links must remain DOWN after failover
    16. Repeated diagnosis produces consistent, deterministic results
    17. Recovery does not modify unrelated network state
    18. Fresh monitoring observations collected after recovery and distinct reports
    """

    def test_1_no_fault_baseline(self):
        """1. No-fault baseline: verifies monitoring, diagnosis, recovery, and verification on healthy network."""
        g = build_network()
        obs = collect_observations(g)

        self.assertTrue(obs["reachability"])
        self.assertEqual(obs["down_links"], [])
        self.assertTrue(obs["gateway_ok"])
        self.assertTrue(obs["dns_ok"])
        self.assertGreaterEqual(obs["healthy_routes_count"], 1)

        rep_a = format_monitoring_report(obs)
        self.assertIn("=== NETWORK MONITORING REPORT ===", rep_a)
        self.assertIn("Reachability: REACHABLE", rep_a)
        self.assertIn("Failed links: None (All UP)", rep_a)

        findings = diagnose(obs)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].root_cause, "No fault detected")
        self.assertEqual(findings[0].severity, "INFO")
        self.assertEqual(findings[0].confidence, 1.0)

        rep_b = format_diagnosis_report(findings)
        self.assertIn("=== ROOT-CAUSE DIAGNOSIS REPORT ===", rep_b)
        self.assertIn("No fault detected", rep_b)

        res = recover(g, findings=findings)
        self.assertTrue(res["verified"])
        self.assertIn(res["status"], ("NO RECOVERY REQUIRED", "RECOVERY VERIFIED"))
        self.assertFalse(res["action_executed"])
        self.assertEqual(len(res["action_details"]), 0)
        self.assertEqual(res["service_availability"], "AVAILABLE")
        self.assertEqual(res["network_health"], "HEALTHY")

        rep_c = format_recovery_report(res)
        self.assertIn("=== AUTOMATED RECOVERY REPORT ===", rep_c)

        rep_d = format_verification_report(res)
        self.assertIn("=== POST-RECOVERY VERIFICATION REPORT ===", rep_d)
        self.assertIn("Verification Result     : PASSED", rep_d)

    def test_2_each_of_five_individual_fault_scenarios(self):
        """2. Verifies independent diagnosis and recovery for all five fault scenarios."""
        # Scenario 1: Link failure
        g1 = build_network()
        g1["R2"]["Server"]["status"] = "DOWN"
        obs1 = collect_observations(g1)
        findings1 = diagnose(obs1)
        self.assertTrue(any(f.root_cause == "Link failure" for f in findings1))
        res1 = recover(g1, findings=findings1)
        self.assertTrue(res1["verified"])
        self.assertEqual(res1["route"], ["PC1", "R1", "R3", "Server"])
        self.assertEqual(g1["R2"]["Server"]["status"], "DOWN")

        # Scenario 2: Wrong default gateway
        g2 = build_network()
        g2.nodes["PC1"]["gateway"] = "R99"
        obs2 = collect_observations(g2)
        findings2 = diagnose(obs2)
        self.assertTrue(any(f.root_cause == "Incorrect default gateway" for f in findings2))
        res2 = recover(g2, findings=findings2)
        self.assertTrue(res2["verified"])
        self.assertEqual(g2.nodes["PC1"]["gateway"], "R1")

        # Scenario 3: DNS failure
        g3 = build_network()
        g3.graph["dns_available"] = False
        obs3 = collect_observations(g3)
        self.assertTrue(obs3["reachability"])  # IP intact
        self.assertFalse(obs3["dns_ok"])
        findings3 = diagnose(obs3)
        self.assertTrue(any(f.root_cause == "DNS service failure" for f in findings3))
        res3 = recover(g3, findings=findings3)
        self.assertTrue(res3["verified"])
        self.assertTrue(g3.graph["dns_available"])

        # Scenario 4: High latency
        g4 = build_network()
        g4["R1"]["R2"]["latency_ms"] = 250.0
        obs4 = collect_observations(g4)
        findings4 = diagnose(obs4)
        self.assertTrue(any(f.root_cause == "High latency" for f in findings4))
        res4 = recover(g4, findings=findings4)
        self.assertTrue(res4["verified"])
        self.assertEqual(res4["route"], ["PC1", "R1", "R3", "Server"])
        self.assertEqual(res4["post_observations"]["end_to_end_latency_ms"], 10.0)

        # Scenario 5: Packet loss
        g5 = build_network()
        g5["R1"]["R2"]["packet_loss"] = 40.0
        obs5 = collect_observations(g5)
        findings5 = diagnose(obs5)
        self.assertTrue(any(f.root_cause == "Packet loss" for f in findings5))
        res5 = recover(g5, findings=findings5)
        self.assertTrue(res5["verified"])
        self.assertEqual(res5["route"], ["PC1", "R1", "R3", "Server"])
        self.assertEqual(res5["post_observations"]["path_packet_loss"], 0.0)

    def test_3_multiple_simultaneous_faults(self):
        """3. Multiple simultaneous faults: evaluates all 5 rules independently without early exit."""
        g = build_network()
        # Inject 3 distinct simultaneous faults
        g["R2"]["Server"]["status"] = "DOWN"
        g.nodes["PC1"]["gateway"] = "R99"
        g.graph["dns_available"] = False

        obs = collect_observations(g)
        findings = diagnose(obs)

        # Must report all 3 distinct faults
        causes = [f.root_cause for f in findings]
        self.assertEqual(len(findings), 3)
        self.assertIn("Link failure", causes)
        self.assertIn("Incorrect default gateway", causes)
        self.assertIn("DNS service failure", causes)

        # Recovery must execute all three repairs
        res = recover(g, findings=findings)
        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], "RECOVERY VERIFIED")
        self.assertTrue(res["action_executed"])
        self.assertEqual(len(res["action_details"]), 3)
        self.assertEqual(res["service_availability"], "AVAILABLE")
        self.assertEqual(res["network_health"], "DEGRADED")
        self.assertEqual(g["R2"]["Server"]["status"], "DOWN")  # Kept DOWN
        self.assertEqual(g.nodes["PC1"]["gateway"], "R1")      # Gateway repaired
        self.assertTrue(g.graph["dns_available"])               # DNS restored
        self.assertEqual(res["route"], ["PC1", "R1", "R3", "Server"])  # Failover activated

        # Test another pair: Wrong gateway + Packet loss
        g2 = build_network()
        g2.nodes["PC1"]["gateway"] = "R88"
        g2["R1"]["R2"]["packet_loss"] = 35.0
        obs2 = collect_observations(g2)
        findings2 = diagnose(obs2)
        causes2 = [f.root_cause for f in findings2]
        self.assertIn("Incorrect default gateway", causes2)
        self.assertIn("Packet loss", causes2)

        res2 = recover(g2, findings=findings2)
        self.assertTrue(res2["verified"])
        self.assertEqual(g2.nodes["PC1"]["gateway"], "R1")
        self.assertEqual(res2["route"], ["PC1", "R1", "R3", "Server"])

    def test_4_diagnosis_independence_from_injected_fault_labels(self):
        """4. Diagnosis independence: operates purely on telemetry, ignoring deceptive fault labels."""
        g = build_network()
        g["R1"]["R3"]["status"] = "DOWN"

        # Plant decoy labels intended to mislead an unprincipled diagnostic engine
        g.graph["scenario"] = "FAKE_DNS_OUTAGE"
        decoy_state = {"fault": "FAKE_GATEWAY_MISCONFIGURATION", "source": "PC1", "target": "Server"}

        obs = collect_observations(g, decoy_state)
        findings = diagnose(obs)

        # Must diagnose strictly Link failure on R1-R3
        causes = [f.root_cause for f in findings]
        self.assertEqual(causes, ["Link failure"])
        self.assertEqual(findings[0].affected_components, ["R1-R3"])
        self.assertNotIn("FAKE_DNS_OUTAGE", str(findings))
        self.assertNotIn("FAKE_GATEWAY_MISCONFIGURATION", str(findings))

    def test_5_evidence_based_diagnosis(self):
        """5. Evidence-based diagnosis: confidence values and evidence strings reflect concrete observations."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["latency_ms"] = 220.0
        g["PC1"]["R1"]["packet_loss"] = 25.0
        g.nodes["PC1"]["gateway"] = "R77"
        g.graph["dns_available"] = False

        obs = collect_observations(g)
        findings = diagnose(obs)

        conf_map = {f.root_cause: f.confidence for f in findings}
        self.assertEqual(conf_map["Link failure"], 1.0)
        self.assertEqual(conf_map["Incorrect default gateway"], 0.98)
        self.assertEqual(conf_map["DNS service failure"], 0.95)
        self.assertEqual(conf_map["High latency"], 0.90)
        self.assertEqual(conf_map["Packet loss"], 0.92)

        for f in findings:
            self.assertTrue(len(f.evidence) > 20)
            self.assertIn("IF ", f.evidence)
            self.assertIn("THEN ", f.evidence)

    def test_6_severity_and_impact_classification(self):
        """6. Severity and impact classification: reflects actual network impact and redundancy."""
        g = build_network()
        # Single link down on primary path, but backup route is operational
        g["R2"]["Server"]["status"] = "DOWN"
        obs = collect_observations(g)
        findings = diagnose(obs)

        link_finding = next(f for f in findings if f.root_cause == "Link failure")
        self.assertEqual(link_finding.affected_components, ["R2-Server"])
        self.assertIn("failover", link_finding.network_impact.lower())
        self.assertEqual(link_finding.healthy_alternative_routes, 1)

        # Complete disconnection: all links from PC1 down
        g2 = build_network()
        g2["PC1"]["R1"]["status"] = "DOWN"
        obs2 = collect_observations(g2)
        findings2 = diagnose(obs2)
        link_finding2 = next(f for f in findings2 if f.root_cause == "Link failure")
        self.assertEqual(link_finding2.severity, "CRITICAL")
        self.assertIn("outage", link_finding2.network_impact.lower())
        self.assertEqual(link_finding2.endpoint_reachability, "UNREACHABLE")

    def test_7_route_discovery_without_activation(self):
        """7. Route discovery without activation: monitoring and diagnosis must NOT activate routes."""
        g = build_network()
        initial_active = get_active_route(g)
        self.assertEqual(initial_active, ["PC1", "R1", "R2", "Server"])

        # Collect observations and perform diagnosis
        obs = collect_observations(g)
        self.assertGreaterEqual(len(obs["routes"]), 2)
        findings = diagnose(obs)

        # Forwarding state in network must NOT have been changed
        current_active = get_active_route(g)
        self.assertEqual(current_active, initial_active)
        self.assertEqual(g.graph.get("active_path"), initial_active)

    def test_8_route_activation_only_during_recovery(self):
        """8. Route activation only during recovery: recovery module activates routes when appropriate."""
        g = build_network()
        g["R2"]["Server"]["status"] = "DOWN"

        # Prior to recovery, active forwarding route has not switched
        self.assertEqual(get_active_route(g), ["PC1", "R1", "R2", "Server"])

        # Recovery executes failover and activates the alternative route
        res = recover(g)
        self.assertTrue(res["verified"])
        self.assertEqual(get_active_route(g), ["PC1", "R1", "R3", "Server"])
        self.assertEqual(g.graph.get("active_path"), ["PC1", "R1", "R3", "Server"])

    def test_9_correct_gateway_restoration(self):
        """9. Correct gateway restoration: gateway derived from connected router, not rerouted around."""
        g = build_network()
        g.nodes["PC1"]["gateway"] = "NonExistentRouter"

        res = recover(g)
        self.assertTrue(res["verified"])
        # PC1 is connected to R1; dynamic discovery must assign R1
        self.assertEqual(g.nodes["PC1"]["gateway"], "R1")
        self.assertTrue(res["gateway_valid"])

    def test_10_dns_restoration_and_independent_verification(self):
        """10. DNS restoration and independent verification: DNS resolution verified separately from IP."""
        g = build_network()
        g.graph["dns_available"] = False

        res = recover(g)
        self.assertTrue(res["dns_resolution"])
        self.assertTrue(res["ip_connectivity"])
        self.assertTrue(g.graph["dns_available"])
        self.assertEqual(res["verification_checks"]["dns_resolution"], "PASS")
        self.assertEqual(res["verification_checks"]["endpoint_ip_connectivity"], "PASS")

    def test_11_latency_improvement_verification(self):
        """11. Latency improvement: reroutes to lower latency and verifies improvement; reports when unavailable."""
        g = build_network()
        g["R1"]["R2"]["latency_ms"] = 250.0  # Path PC1-R1-R2-Server = 255 ms
        # Alternate PC1-R1-R3-Server = 10 ms

        res = recover(g)
        self.assertTrue(res["verified"])
        self.assertEqual(res["route"], ["PC1", "R1", "R3", "Server"])
        self.assertLess(res["post_observations"]["end_to_end_latency_ms"], 20.0)

        # When all alternative paths are equally degraded, reports optimization unavailable
        g2 = build_network()
        g2["R1"]["R2"]["latency_ms"] = 300.0
        g2["R1"]["R3"]["latency_ms"] = 300.0
        g2["R3"]["Server"]["latency_ms"] = 300.0
        res2 = recover(g2)
        self.assertIn("OPTIMIZATION UNAVAILABLE", res2["status"])

    def test_12_packet_loss_improvement_verification(self):
        """12. Packet loss improvement: reroutes to lower loss route and verifies improvement."""
        g = build_network()
        g["R1"]["R2"]["packet_loss"] = 45.0

        res = recover(g)
        self.assertTrue(res["verified"])
        self.assertEqual(res["route"], ["PC1", "R1", "R3", "Server"])
        self.assertEqual(res["post_observations"]["path_packet_loss"], 0.0)

        # When all paths have high packet loss, reports recovery unavailable
        g2 = build_network()
        g2["R1"]["R2"]["packet_loss"] = 50.0
        g2["R1"]["R3"]["packet_loss"] = 50.0
        res2 = recover(g2)
        self.assertIn("RECOVERY UNAVAILABLE", res2["status"])

    def test_13_recovery_unavailable_when_no_healthy_route_exists(self):
        """13. Recovery unavailable when no healthy route exists: honest reporting when failover impossible."""
        g = build_network()
        g["R2"]["Server"]["status"] = "DOWN"
        g["R3"]["Server"]["status"] = "DOWN"

        res = recover(g)
        self.assertFalse(res["verified"])
        self.assertEqual(res["status"], "RECOVERY UNAVAILABLE")
        self.assertEqual(g["R2"]["Server"]["status"], "DOWN")
        self.assertEqual(g["R3"]["Server"]["status"], "DOWN")

    def test_14_failed_recovery_must_not_be_reported_as_successful(self):
        """14. Failed recovery must not be reported as successful: verified flag is False on failure."""
        g = build_network()
        g["PC1"]["R1"]["status"] = "DOWN"

        res = recover(g)
        self.assertFalse(res["verified"])
        self.assertNotEqual(res["status"], "RECOVERY VERIFIED")
        self.assertEqual(res["status"], "RECOVERY UNAVAILABLE")

    def test_15_failed_links_must_remain_down_after_failover(self):
        """15. Failed links must remain DOWN after failover: recovery must never falsely mark failed links UP."""
        g = build_network()
        g["R2"]["Server"]["status"] = "DOWN"

        res = recover(g)
        self.assertTrue(res["verified"])
        self.assertEqual(g["R2"]["Server"]["status"], "DOWN")
        self.assertIn("R2-Server", res["post_observations"]["down_links"])

    def test_16_repeated_diagnosis_produces_consistent_results(self):
        """16. Repeated diagnosis consistency: multiple consecutive runs yield identical findings."""
        g = build_network()
        g["R2"]["Server"]["status"] = "DOWN"
        g.nodes["PC1"]["gateway"] = "R99"

        obs = collect_observations(g)
        runs = [diagnose(obs) for _ in range(5)]

        for r in runs[1:]:
            self.assertEqual(len(r), len(runs[0]))
            self.assertEqual([f.root_cause for f in r], [f.root_cause for f in runs[0]])
            self.assertEqual([f.severity for f in r], [f.severity for f in runs[0]])
            self.assertEqual([f.confidence for f in r], [f.confidence for f in runs[0]])
            self.assertEqual([f.evidence for f in r], [f.evidence for f in runs[0]])

    def test_17_recovery_does_not_modify_unrelated_network_state(self):
        """17. Recovery does not modify unrelated network state: unassociated nodes/links remain untouched."""
        g = build_network()
        add_device(g, "Laptop9", device_type="Laptop", ip="192.168.1.99", gateway="R1")
        connect_devices(g, "Laptop9", "R3", cost=1, latency_ms=3, packet_loss=0.0)

        # Inject and recover link failure on R2-Server
        g["R2"]["Server"]["status"] = "DOWN"
        res = recover(g)
        self.assertTrue(res["verified"])

        # Unrelated device Laptop9 must remain completely unaffected
        self.assertIn("Laptop9", g.nodes)
        self.assertEqual(g.nodes["Laptop9"]["ip"], "192.168.1.99")
        self.assertEqual(g.nodes["Laptop9"]["gateway"], "R1")
        self.assertTrue(g.has_edge("Laptop9", "R3"))
        self.assertEqual(g["Laptop9"]["R3"]["status"], "UP")
        self.assertEqual(g["Laptop9"]["R3"]["latency_ms"], 3.0)

    def test_18_fresh_monitoring_observations_collected_after_recovery(self):
        """18. Fresh post-recovery observations and distinct four-report generation."""
        g = build_network()
        g["R2"]["Server"]["status"] = "DOWN"

        obs_pre = collect_observations(g)
        findings = diagnose(obs_pre)
        res = recover(g, findings=findings)

        # Verify post_observations are fresh and reflect post-recovery state
        post_obs = res["post_observations"]
        self.assertIsNotNone(post_obs)
        self.assertTrue(post_obs["reachability"])
        self.assertEqual(post_obs["active_path"], ["PC1", "R1", "R3", "Server"])

        # Verify all four reports produce distinct, dedicated outputs
        rep_a = format_monitoring_report(obs_pre)
        rep_b = format_diagnosis_report(findings)
        rep_c = format_recovery_report(res)
        rep_d = format_verification_report(res)

        self.assertIn("=== NETWORK MONITORING REPORT ===", rep_a)
        self.assertIn("=== ROOT-CAUSE DIAGNOSIS REPORT ===", rep_b)
        self.assertIn("=== AUTOMATED RECOVERY REPORT ===", rep_c)
        self.assertIn("=== POST-RECOVERY VERIFICATION REPORT ===", rep_d)

        # Ensure no report copies header or identity of another report
        self.assertNotIn("=== AUTOMATED RECOVERY REPORT ===", rep_a)
        self.assertNotIn("=== POST-RECOVERY VERIFICATION REPORT ===", rep_b)
        self.assertNotIn("=== ROOT-CAUSE DIAGNOSIS REPORT ===", rep_c)

    def test_19_failed_link_with_alternative_route_already_active(self):
        """19. Failed link with alternative route already active: service maintained without route switch."""
        g = build_network()
        # In baseline network, active route is PC1 -> R1 -> R2 -> Server
        self.assertEqual(get_active_route(g), ["PC1", "R1", "R2", "Server"])

        # Mark R1-R3 DOWN (on the unused alternate path)
        g["R1"]["R3"]["status"] = "DOWN"

        obs = collect_observations(g)
        findings = diagnose(obs)
        self.assertTrue(any(f.root_cause == "Link failure" for f in findings))

        res = recover(g, findings=findings)

        # Must report SERVICE MAINTAINED with 0 corrective actions
        self.assertEqual(res["status"], "SERVICE MAINTAINED")
        self.assertFalse(res["action_executed"])
        self.assertEqual(len(res["action_details"]), 0)
        self.assertIn("A healthy alternative route was already active", res["reason"])

        # Active route must NOT have been changed unnecessarily
        self.assertEqual(res["route"], ["PC1", "R1", "R2", "Server"])
        self.assertEqual(get_active_route(g), ["PC1", "R1", "R2", "Server"])

        # Failed link remains DOWN
        self.assertEqual(g["R1"]["R3"]["status"], "DOWN")
        self.assertEqual(res["verification_checks"]["failed_links_isolated"], "PASS")

        # Service availability is AVAILABLE, but network health is DEGRADED
        self.assertEqual(res["service_availability"], "AVAILABLE")
        self.assertEqual(res["network_health"], "DEGRADED")
        self.assertTrue(res["verified"])

        # Verify Reports C and D
        rep_c = format_recovery_report(res)
        self.assertIn("Recovery Status             : SERVICE MAINTAINED", rep_c)
        self.assertIn("Corrective Actions Executed : 0", rep_c)
        self.assertIn("Action Executed             : NO", rep_c)

        rep_d = format_verification_report(res)
        self.assertIn("Overall Recovery Status : SERVICE MAINTAINED", rep_d)
        self.assertIn("Service Availability    : AVAILABLE", rep_d)
        self.assertIn("Network Health          : DEGRADED", rep_d)
        self.assertIn("Verification Result     : PASSED", rep_d)

    def test_20_failed_link_with_alternative_route_discovered_but_not_active(self):
        """20. Failed link when alternative is not active: activates failover and counts as 1 corrective action."""
        g = build_network()
        # Active route is PC1 -> R1 -> R2 -> Server; fail R2-Server
        g["R2"]["Server"]["status"] = "DOWN"

        res = recover(g)

        # Must activate failover route and report RECOVERY VERIFIED
        self.assertEqual(res["status"], "RECOVERY VERIFIED")
        self.assertTrue(res["action_executed"])
        self.assertEqual(len(res["action_details"]), 1)
        self.assertEqual(res["action_details"][0]["fault"], "Link failure")
        self.assertEqual(res["route"], ["PC1", "R1", "R3", "Server"])
        self.assertEqual(get_active_route(g), ["PC1", "R1", "R3", "Server"])

        # Failed link remains DOWN
        self.assertEqual(g["R2"]["Server"]["status"], "DOWN")
        self.assertEqual(res["verification_checks"]["failed_links_isolated"], "PASS")

        # Service is AVAILABLE, network health is DEGRADED due to failed link
        self.assertEqual(res["service_availability"], "AVAILABLE")
        self.assertEqual(res["network_health"], "DEGRADED")
        self.assertTrue(res["verified"])

    def test_21_failed_link_with_no_alternative_route(self):
        """21. Failed link with no alternative route: reports recovery unavailable, service unavailable."""
        g = build_network()
        # Fail both paths to Server
        g["R2"]["Server"]["status"] = "DOWN"
        g["R3"]["Server"]["status"] = "DOWN"

        res = recover(g)

        self.assertEqual(res["status"], "RECOVERY UNAVAILABLE")
        self.assertFalse(res["verified"])
        self.assertEqual(res["service_availability"], "UNAVAILABLE")
        self.assertEqual(res["network_health"], "CRITICAL")
        self.assertEqual(g["R2"]["Server"]["status"], "DOWN")
        self.assertEqual(g["R3"]["Server"]["status"], "DOWN")

    def test_22_recovery_action_count_equals_actual_corrective_operations(self):
        """22. Corrective action count: strictly equals actual state modifications performed."""
        # 0 actions on baseline healthy
        g0 = build_network()
        res0 = recover(g0)
        self.assertEqual(len(res0["action_details"]), 0)
        self.assertFalse(res0["action_executed"])

        # 0 actions on link failure when alternative is already active
        g_alt = build_network()
        g_alt["R1"]["R3"]["status"] = "DOWN"
        res_alt = recover(g_alt)
        self.assertEqual(len(res_alt["action_details"]), 0)
        self.assertFalse(res_alt["action_executed"])

        # 1 action on single gateway misconfiguration
        g1 = build_network()
        g1.nodes["PC1"]["gateway"] = "R99"
        res1 = recover(g1)
        self.assertEqual(len(res1["action_details"]), 1)
        self.assertTrue(res1["action_executed"])

        # 2 actions on gateway fault + DNS service failure
        g2 = build_network()
        g2.nodes["PC1"]["gateway"] = "R99"
        g2.graph["dns_available"] = False
        res2 = recover(g2)
        self.assertEqual(len(res2["action_details"]), 2)
        self.assertTrue(res2["action_executed"])

    def test_23_verification_does_not_count_as_recovery(self):
        """23. Verification does not count as recovery: passing checks never increment action count."""
        g = build_network()
        res = recover(g)

        self.assertTrue(res["verified"])
        self.assertTrue(res["verification_passed"])
        self.assertEqual(len(res["action_details"]), 0)
        self.assertFalse(res["action_executed"])

        rep_c = format_recovery_report(res)
        self.assertIn("Corrective Actions Executed : 0", rep_c)
        self.assertIn("Action Executed             : NO", rep_c)
        self.assertNotIn("Baseline verification", rep_c)

    def test_24_service_availability_and_network_health_reported_separately(self):
        """24. Service availability and network health: reported separately and accurately."""
        # 1. Baseline: AVAILABLE and HEALTHY
        g1 = build_network()
        res1 = recover(g1)
        self.assertEqual(res1["service_availability"], "AVAILABLE")
        self.assertEqual(res1["network_health"], "HEALTHY")

        # 2. Failed link with working alternative: AVAILABLE but DEGRADED
        g2 = build_network()
        g2["R1"]["R3"]["status"] = "DOWN"
        res2 = recover(g2)
        self.assertEqual(res2["service_availability"], "AVAILABLE")
        self.assertEqual(res2["network_health"], "DEGRADED")
        self.assertNotEqual(res2["network_health"], "HEALTHY")

        # 3. Disconnected network: UNAVAILABLE and CRITICAL
        g3 = build_network()
        g3["PC1"]["R1"]["status"] = "DOWN"
        res3 = recover(g3)
        self.assertEqual(res3["service_availability"], "UNAVAILABLE")
        self.assertEqual(res3["network_health"], "CRITICAL")

        # 4. Verification report text includes both headers distinctly
        rep_d = format_verification_report(res2)
        self.assertIn("Service Availability    : AVAILABLE", rep_d)
        self.assertIn("Network Health          : DEGRADED", rep_d)


class Stage1FaultRegistryTests(unittest.TestCase):
    """Stage 1: Dedicated tests for FaultRegistry, FaultRecord, and Multi-Fault Instance Architecture."""

    def test_fault_record_creation_and_attributes(self):
        """Verifies FaultRecord attributes, target property alias, and serialization."""
        rec = FaultRecord(
            fault_id="FLT-0001",
            scenario_id="SCN-0001",
            fault_type="Link failure",
            affected_component="R1-R2",
            parameters={"status": "DOWN", "u": "R1", "v": "R2"},
            status=FaultStatus.ACTIVE,
            recovery_status="UNRESOLVED",
            description="Link R1-R2 is marked DOWN"
        )
        self.assertEqual(rec.fault_id, "FLT-0001")
        self.assertEqual(rec.scenario_id, "SCN-0001")
        self.assertEqual(rec.fault_type, "Link failure")
        self.assertEqual(rec.affected_component, "R1-R2")
        self.assertEqual(rec.target, "R1-R2")
        self.assertEqual(rec.status, "ACTIVE")
        self.assertEqual(rec.recovery_status, "UNRESOLVED")
        self.assertIn("FLT-0001", repr(rec))

        # Serialization round-trip
        d = rec.to_dict()
        self.assertEqual(d["fault_id"], "FLT-0001")
        self.assertEqual(d["parameters"]["status"], "DOWN")
        rec_copy = FaultRecord.from_dict(d)
        self.assertEqual(rec_copy.fault_id, rec.fault_id)
        self.assertEqual(rec_copy.affected_component, rec.affected_component)

    def test_fault_status_lifecycle_and_transitions(self):
        """Verifies valid lifecycle states, transitions, history tracking, and invalid state rejection."""
        rec = FaultRecord("FLT-0002", "SCN-0001", "Packet loss", "R1-R2", {"packet_loss": 35.0})
        self.assertEqual(rec.status, FaultStatus.ACTIVE)
        self.assertEqual(len(rec.history_transitions), 1)

        # Transition to BYPASSED
        rec.update_status(FaultStatus.BYPASSED, recovery_status="BYPASSED", reason="Alternate route selected")
        self.assertEqual(rec.status, FaultStatus.BYPASSED)
        self.assertEqual(rec.recovery_status, "BYPASSED")
        self.assertEqual(len(rec.history_transitions), 2)

        # Transition to RESOLVED
        rec.update_status(FaultStatus.RESOLVED, recovery_status="RESOLVED", reason="Link restored")
        self.assertEqual(rec.status, FaultStatus.RESOLVED)

        # Transition to CLEARED
        rec.update_status(FaultStatus.CLEARED, reason="Simulation reset")
        self.assertEqual(rec.status, FaultStatus.CLEARED)

        # Rejection of invalid status
        with self.assertRaises(ValueError):
            rec.update_status("NOT_A_VALID_STATUS")

    def test_fault_registry_id_generation_and_lookup(self):
        """Verifies unique sequential fault IDs, scenario IDs, and dictionary lookups."""
        reg = FaultRegistry()
        sc1 = reg.create_scenario("Scenario 1")
        sc2 = reg.create_scenario("Scenario 2")
        self.assertEqual(sc1, "SCN-0001")
        self.assertEqual(sc2, "SCN-0002")

        f1 = reg.register_fault("Link failure", "R1-R2", scenario_id=sc1)
        f2 = reg.register_fault("High latency", "R1-R3", scenario_id=sc1)
        f3 = reg.register_fault("DNS failure", "DNS Service", scenario_id=sc2)

        self.assertEqual(f1.fault_id, "FLT-0001")
        self.assertEqual(f2.fault_id, "FLT-0002")
        self.assertEqual(f3.fault_id, "FLT-0003")

        # Lookup
        self.assertIs(reg.get_fault("FLT-0001"), f1)
        self.assertIs(reg.get_fault("FLT-0002"), f2)
        self.assertIs(reg.get_fault("FLT-0003"), f3)
        self.assertIsNone(reg.get_fault("FLT-9999"))

    def test_active_vs_historical_fault_separation(self):
        """Verifies active faults remain strictly separate from historical archived faults."""
        reg = FaultRegistry()
        f1 = reg.register_fault("Link failure", "R1-R2")
        f2 = reg.register_fault("Packet loss", "R2-Server")
        self.assertEqual(len(reg.get_active_faults()), 2)
        self.assertEqual(len(reg.get_historical_faults()), 0)

        # Archive f1
        reg.archive_active_fault(f1.fault_id, status=FaultStatus.RESOLVED, reason="Link repaired")
        self.assertEqual(len(reg.get_active_faults()), 1)
        self.assertEqual(len(reg.get_historical_faults()), 1)
        self.assertEqual(reg.get_active_faults()[0].fault_id, f2.fault_id)
        self.assertEqual(reg.get_historical_faults()[0].fault_id, f1.fault_id)
        self.assertEqual(reg.get_historical_faults()[0].status, FaultStatus.RESOLVED)

        # Lookup still finds both
        self.assertEqual(reg.get_fault(f1.fault_id).status, FaultStatus.RESOLVED)
        self.assertEqual(reg.get_fault(f2.fault_id).status, FaultStatus.ACTIVE)

        # Archive all active
        reg.archive_all_active(status=FaultStatus.CLEARED)
        self.assertEqual(len(reg.get_active_faults()), 0)
        self.assertEqual(len(reg.get_historical_faults()), 2)

    def test_backward_compatibility_single_fault_injection(self):
        """Verifies existing single-fault injection retains legacy return structure and adds registry IDs."""
        g = build_network()
        res = inject_fault(g, "Link Failure")
        self.assertEqual(res["fault"], "Link failure (R2-Server)")
        self.assertIn("details", res)
        self.assertIn("failed_link", res)
        # New Stage 1 fields
        self.assertIn("fault_id", res)
        self.assertIn("scenario_id", res)
        self.assertIn("fault_record", res)
        self.assertTrue(res["fault_id"].startswith("FLT-"))
        self.assertTrue(res["scenario_id"].startswith("SCN-"))

        # Verify registry on graph contains this active fault
        reg = get_fault_registry(g)
        self.assertEqual(reg.count_active(), 1)
        active = reg.get_active_faults()
        self.assertEqual(active[0].fault_id, res["fault_id"])
        self.assertEqual(active[0].fault_type, "Link failure")

        # Resetting faults clears the active registry
        reset_faults(g)
        self.assertEqual(reg.count_active(), 0)
        self.assertEqual(len(reg.get_historical_faults()), 1)
        self.assertEqual(reg.get_historical_faults()[0].status, FaultStatus.CLEARED)

    def test_multiple_simultaneous_link_failures(self):
        """Verifies injecting three simultaneous link failures records all three as active."""
        g = build_network()
        f1 = inject_fault_instance(g, "Link failure", target=("PC1", "R1"))
        f2 = inject_fault_instance(g, "Link failure", target=("R1", "R2"))
        f3 = inject_fault_instance(g, "Link failure", target=("R3", "Server"))

        # Verify all 3 links are DOWN on the graph
        self.assertEqual(g["PC1"]["R1"]["status"], "DOWN")
        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertEqual(g["R3"]["Server"]["status"], "DOWN")
        # Other links remain UP
        self.assertEqual(g["R1"]["R3"]["status"], "UP")
        self.assertEqual(g["R2"]["Server"]["status"], "UP")

        # Verify 3 distinct active faults in registry
        reg = get_fault_registry(g)
        self.assertEqual(reg.count_active(), 3)
        self.assertEqual(reg.count_active(fault_type="Link failure"), 3)
        active_ids = [f.fault_id for f in reg.get_active_faults()]
        self.assertEqual(len(set(active_ids)), 3)

    def test_multiple_simultaneous_lossy_links(self):
        """Verifies injecting multiple lossy links simultaneously with individual loss percentages."""
        g = build_network()
        f1 = inject_fault_instance(g, "Packet loss", target=("R1", "R2"), parameters={"packet_loss": 25.0})
        f2 = inject_fault_instance(g, "Packet loss", target=("R1", "R3"), parameters={"packet_loss": 50.0})

        self.assertEqual(g["R1"]["R2"]["packet_loss"], 25.0)
        self.assertEqual(g["R1"]["R3"]["packet_loss"], 50.0)
        self.assertEqual(g["R2"]["Server"]["packet_loss"], 0.0)

        reg = get_fault_registry(g)
        self.assertEqual(reg.count_active(fault_type="Packet loss"), 2)

    def test_multiple_simultaneous_high_latency_links(self):
        """Verifies injecting multiple high-latency links simultaneously with individual latency values."""
        g = build_network()
        f1 = inject_fault_instance(g, "High latency", target=("R1", "R2"), parameters={"latency_ms": 150.0})
        f2 = inject_fault_instance(g, "High latency", target=("R2", "Server"), parameters={"latency_ms": 320.0})

        self.assertEqual(g["R1"]["R2"]["latency_ms"], 150.0)
        self.assertEqual(g["R2"]["Server"]["latency_ms"], 320.0)
        self.assertEqual(g["R1"]["R3"]["latency_ms"], 4.0)

        reg = get_fault_registry(g)
        self.assertEqual(reg.count_active(fault_type="High latency"), 2)

    def test_mixed_simultaneous_fault_types(self):
        """Verifies injecting mixed fault types simultaneously (Link + Gateway + DNS)."""
        g = build_network()
        f_link = inject_fault_instance(g, "Link failure", target=("R1", "R2"))
        f_gw = inject_fault_instance(g, "Wrong default gateway", target="PC1", parameters={"gateway": "R9"})
        f_dns = inject_fault_instance(g, "DNS failure")

        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertEqual(g.nodes["PC1"]["gateway"], "R9")
        self.assertFalse(g.graph["dns_available"])

        reg = get_fault_registry(g)
        self.assertEqual(reg.count_active(), 3)
        self.assertEqual(reg.count_active("Link failure"), 1)
        self.assertEqual(reg.count_active("Wrong default gateway"), 1)
        self.assertEqual(reg.count_active("DNS failure"), 1)

    def test_clear_fault_instance_preserves_other_active_faults(self):
        """Verifies clearing a specific fault instance restores only that component without affecting other faults."""
        g = build_network()
        f1 = inject_fault_instance(g, "Link failure", target=("R1", "R2"))
        f2 = inject_fault_instance(g, "Link failure", target=("R1", "R3"))
        f3 = inject_fault_instance(g, "DNS failure")

        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertEqual(g["R1"]["R3"]["status"], "DOWN")
        self.assertFalse(g.graph["dns_available"])

        # Clear f1 only
        cleared = clear_fault_instance(g, fault_id=f1.fault_id)
        self.assertTrue(cleared)

        # f1 is restored to UP
        self.assertEqual(g["R1"]["R2"]["status"], "UP")
        # f2 and f3 remain strictly DOWN / unavailable
        self.assertEqual(g["R1"]["R3"]["status"], "DOWN")
        self.assertFalse(g.graph["dns_available"])

        # Registry reflects 2 active faults and 1 historical fault
        reg = get_fault_registry(g)
        self.assertEqual(reg.count_active(), 2)
        self.assertEqual(len(reg.get_historical_faults()), 1)
        self.assertEqual(reg.get_historical_faults()[0].fault_id, f1.fault_id)

    def test_fault_registry_json_persistence(self):
        """Verifies fault registry is preserved across JSON save and load."""
        g = build_network()
        inject_fault_instance(g, "Link failure", target=("R1", "R2"))
        inject_fault_instance(g, "Packet loss", target=("R1", "R3"), parameters={"packet_loss": 30.0})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            save_topology_to_file(g, tmp_path)
            g_loaded, _ = load_topology_from_file(tmp_path)

            reg_loaded = get_fault_registry(g_loaded)
            self.assertEqual(reg_loaded.count_active(), 2)
            active_types = {f.fault_type for f in reg_loaded.get_active_faults()}
            self.assertEqual(active_types, {"Link failure", "Packet loss"})
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_fault_registry_not_used_as_evidence_for_diagnosis(self):
        """Proves monitoring and diagnosis operate strictly on telemetry and do NOT read the fault registry."""
        g = build_network()
        # Inject link failure via graph manipulation without registering it
        g["R1"]["R2"]["status"] = "DOWN"
        # Registry is completely empty
        reg = get_fault_registry(g)
        reg.clear_all(include_history=True)
        self.assertEqual(reg.count_active(), 0)

        # Monitoring and Diagnosis still detect the link failure purely from link status telemetry
        obs = collect_observations(g)
        self.assertIn("R1-R2", obs["down_links"])
        findings = diagnose(obs)
        causes = [getattr(f, "root_cause", f[0]) for f in findings]
        self.assertIn("Link failure", causes)


class Stage2MultiFaultInjectionTests(unittest.TestCase):
    """Stage 2: Acceptance tests for Multi-Fault Injection Engine and Transactional Batch Injection."""

    def test_batch_injection_single_fault(self):
        """Verifies injecting a single fault through the atomic batch engine."""
        g = build_network()
        specs = [{"fault_type": "Link failure", "target": ("R1", "R2")}]
        res = inject_fault_batch(g, specs, scenario_name="Batch Single Link")

        self.assertTrue(res["success"])
        self.assertEqual(res["applied_count"], 1)
        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertEqual(g.graph["scenario"], "Batch Single Link")

    def test_batch_injection_two_different_fault_types(self):
        """Verifies injecting two different fault types simultaneously (Link Failure + DNS)."""
        g = build_network()
        specs = [
            {"fault_type": "Link failure", "target": ("R1", "R2")},
            {"fault_type": "DNS failure"}
        ]
        res = inject_fault_batch(g, specs, scenario_name="Link + DNS Batch")

        self.assertTrue(res["success"])
        self.assertEqual(res["applied_count"], 2)
        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertFalse(g.graph["dns_available"])

    def test_batch_injection_three_simultaneous_link_failures(self):
        """Verifies injecting three or more simultaneous link failures."""
        g = build_network()
        specs = [
            {"fault_type": "Link failure", "target": ("PC1", "R1")},
            {"fault_type": "Link failure", "target": ("R1", "R2")},
            {"fault_type": "Link failure", "target": ("R3", "Server")}
        ]
        res = inject_fault_batch(g, specs, scenario_name="Triple Link Failure")

        self.assertTrue(res["success"])
        self.assertEqual(res["applied_count"], 3)
        self.assertEqual(g["PC1"]["R1"]["status"], "DOWN")
        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertEqual(g["R3"]["Server"]["status"], "DOWN")
        self.assertEqual(g["R1"]["R3"]["status"], "UP")

        reg = get_fault_registry(g)
        self.assertEqual(reg.count_active("Link failure"), 3)

    def test_batch_injection_multiple_packet_loss_instances(self):
        """Verifies injecting multiple lossy links simultaneously with individual loss percentages."""
        g = build_network()
        specs = [
            {"fault_type": "Packet loss", "target": ("R1", "R2"), "parameters": {"packet_loss": 25.0}},
            {"fault_type": "Packet loss", "target": ("R1", "R3"), "parameters": {"packet_loss": 45.0}}
        ]
        res = inject_fault_batch(g, specs, scenario_name="Dual Loss Batch")

        self.assertTrue(res["success"])
        self.assertEqual(g["R1"]["R2"]["packet_loss"], 25.0)
        self.assertEqual(g["R1"]["R3"]["packet_loss"], 45.0)

    def test_batch_injection_multiple_high_latency_instances(self):
        """Verifies injecting multiple high-latency links simultaneously with individual latency values."""
        g = build_network()
        specs = [
            {"fault_type": "High latency", "target": ("R1", "R2"), "parameters": {"latency_ms": 180.0}},
            {"fault_type": "High latency", "target": ("R2", "Server"), "parameters": {"latency_ms": 280.0}}
        ]
        res = inject_fault_batch(g, specs, scenario_name="Dual High Latency Batch")

        self.assertTrue(res["success"])
        self.assertEqual(g["R1"]["R2"]["latency_ms"], 180.0)
        self.assertEqual(g["R2"]["Server"]["latency_ms"], 280.0)

    def test_batch_injection_all_five_fault_categories(self):
        """Verifies injecting all five fault categories simultaneously in one atomic batch."""
        g = build_network()
        specs = [
            {"fault_type": "Link failure", "target": ("R1", "R2")},
            {"fault_type": "Wrong default gateway", "target": "PC1", "parameters": {"gateway": "R9"}},
            {"fault_type": "DNS failure"},
            {"fault_type": "High latency", "target": ("R1", "R3"), "parameters": {"latency_ms": 220.0}},
            {"fault_type": "Packet loss", "target": ("R3", "Server"), "parameters": {"packet_loss": 35.0}}
        ]
        res = inject_fault_batch(g, specs, scenario_name="Quintuply Faulted Network")

        self.assertTrue(res["success"])
        self.assertEqual(res["applied_count"], 5)
        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertEqual(g.nodes["PC1"]["gateway"], "R9")
        self.assertFalse(g.graph["dns_available"])
        self.assertEqual(g["R1"]["R3"]["latency_ms"], 220.0)
        self.assertEqual(g["R3"]["Server"]["packet_loss"], 35.0)

    def test_validation_rejects_invalid_link_target(self):
        """Verifies pre-injection validation rejects nonexistent link targets without mutating graph."""
        g = build_network()
        specs = [{"fault_type": "Link failure", "target": ("PC1", "NonexistentRouter")}]
        res = inject_fault_batch(g, specs)

        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "VALIDATION_FAILED")
        self.assertIn("does not exist", res["details"])
        # Graph must be completely unmodified
        self.assertTrue(all(d.get("status") == "UP" for _, _, d in g.edges(data=True)))

    def test_validation_rejects_duplicate_fault_targets(self):
        """Verifies pre-injection validation rejects duplicate conflicting targets in the same batch."""
        g = build_network()
        specs = [
            {"fault_type": "Link failure", "target": ("R1", "R2")},
            {"fault_type": "Link failure", "target": ("R1", "R2")}
        ]
        res = inject_fault_batch(g, specs)

        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "VALIDATION_FAILED")
        self.assertIn("Duplicate link failure", res["details"])

    def test_validation_rejects_out_of_range_parameters(self):
        """Verifies pre-injection validation rejects out-of-range packet loss and negative latency."""
        g = build_network()
        bad_loss_specs = [{"fault_type": "Packet loss", "target": ("R1", "R2"), "parameters": {"packet_loss": 150.0}}]
        res1 = inject_fault_batch(g, bad_loss_specs)
        self.assertFalse(res1["success"])

        bad_lat_specs = [{"fault_type": "High latency", "target": ("R1", "R2"), "parameters": {"latency_ms": -10.0}}]
        res2 = inject_fault_batch(g, bad_lat_specs)
        self.assertFalse(res2["success"])

    def test_atomic_rollback_on_partial_failure(self):
        """Verifies atomic rollback restores exact graph state if an error occurs mid-application."""
        g = build_network()
        # Initial baseline state
        initial_snap = capture_network_snapshot(g)

        # Batch where the first item is valid, but the second item has an unhandled edge case
        specs = [
            {"fault_type": "Link failure", "target": ("R1", "R2")},
            {"fault_type": "Wrong default gateway", "target": "NonexistentHost"}
        ]
        res = inject_fault_batch(g, specs, rollback_on_failure=True)

        self.assertFalse(res["success"])
        # Link R1-R2 must NOT be left DOWN; it must be completely restored to UP
        self.assertEqual(g["R1"]["R2"]["status"], "UP")

    def test_multifault_scenario_builder_and_preview(self):
        """Verifies MultiFaultScenario builder, preview projection, and apply."""
        g = build_network()
        scenario = MultiFaultScenario(name="Custom Scenario", description="Testing Builder")
        scenario.add_fault("Link failure", target=("R1", "R2"))
        scenario.add_fault("DNS failure")

        self.assertEqual(scenario.count(), 2)

        # Preview projection
        preview = scenario.preview(g)
        self.assertEqual(len(preview), 2)
        self.assertEqual(preview[0]["projected_state"], "status=DOWN")
        self.assertEqual(preview[1]["projected_state"], "dns_available=False")

        # Apply
        res = scenario.apply(g)
        self.assertTrue(res["success"])
        self.assertEqual(res["applied_count"], 2)
        self.assertEqual(g["R1"]["R2"]["status"], "DOWN")
        self.assertFalse(g.graph["dns_available"])

    def test_predefined_scenarios_execution(self):
        """Verifies all predefined benchmark scenarios validate and apply cleanly."""
        for name, specs in PREDEFINED_SCENARIOS.items():
            g = build_network()
            res = inject_fault_batch(g, specs, scenario_name=name)
            self.assertTrue(res["success"], f"Predefined scenario '{name}' failed: {res.get('details')}")
            self.assertEqual(res["applied_count"], len(specs))


class Stage3MonitoringAndPartitionTests(unittest.TestCase):
    """Stage 3: Acceptance tests for Advanced Monitoring and Network Partition Detection."""

    def test_link_monitoring_telemetry_and_classification(self):
        """Verifies link monitoring classifies links as UP, DOWN, and DEGRADED."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["latency_ms"] = 250.0  # Degraded
        g["R3"]["Server"]["packet_loss"] = 30.0  # Degraded

        obs = collect_observations(g)
        self.assertEqual(obs["link_classifications"]["R1-R2"], "DOWN")
        self.assertEqual(obs["link_classifications"]["R1-R3"], "DEGRADED")
        self.assertEqual(obs["link_classifications"]["R3-Server"], "DEGRADED")
        self.assertEqual(obs["link_classifications"]["PC1-R1"], "UP")

        self.assertIn("R1-R2", obs["down_links"])
        self.assertIn("R1-R3", obs["degraded_links"])
        self.assertIn("R3-Server", obs["degraded_links"])

    def test_device_monitoring_and_reachability(self):
        """Verifies device monitoring reports device status and identifies unreachable nodes."""
        g = build_network()
        obs = collect_observations(g)
        for dev in ["PC1", "R1", "R2", "R3", "Server"]:
            self.assertEqual(obs["device_status"][dev], "UP")

    def test_network_partition_detection_multiple_components(self):
        """Verifies NetworkX connected components detects partitions when severed links divide network."""
        g = build_network()
        # Cut both paths between R1 and Server (R1-R2 and R1-R3)
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["status"] = "DOWN"

        obs = collect_observations(g, source="PC1", target="Server")
        part = obs["partition_analysis"]

        self.assertTrue(part["is_partitioned"])
        self.assertGreaterEqual(part["component_count"], 2)
        self.assertFalse(part["source_target_connected"])
        self.assertTrue(part["partition_blocks_traffic"])
        self.assertFalse(obs["reachability"])

    def test_network_partition_isolated_device(self):
        """Verifies isolated devices with degree 0 in the operational graph are accurately identified."""
        g = build_network()
        # Disconnect all links incident to PC1
        g["PC1"]["R1"]["status"] = "DOWN"

        obs = collect_observations(g, source="PC1", target="Server")
        part = obs["partition_analysis"]

        self.assertIn("PC1", part["isolated_devices"])
        self.assertIn("PC1", obs["isolated_devices"])

    def test_network_partition_removal(self):
        """Verifies restoring severed links eliminates partition and reports a single connected segment."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["status"] = "DOWN"

        # Initially partitioned
        part1 = analyze_network_partitions(g, source="PC1", target="Server")
        self.assertTrue(part1["is_partitioned"])

        # Restore one link
        g["R1"]["R2"]["status"] = "UP"
        part2 = analyze_network_partitions(g, source="PC1", target="Server")
        self.assertFalse(part2["is_partitioned"])
        self.assertEqual(part2["component_count"], 1)
        self.assertTrue(part2["source_target_connected"])

    def test_end_to_end_probabilistic_packet_loss_calculation(self):
        """Verifies end-to-end packet loss calculates P(e2e loss) = 1 - product(1 - p_i)."""
        # Test formula directly: 2 links with 20% and 30% loss
        # P = 1 - (1 - 0.20)(1 - 0.30) = 1 - (0.80 * 0.70) = 1 - 0.56 = 0.44 = 44.0%
        edges = [{"packet_loss": 20.0}, {"packet_loss": 30.0}]
        e2e_loss = calculate_path_packet_loss_probabilistic(edges)
        self.assertEqual(e2e_loss, 44.0)

        # Test single link: 40% loss
        edges_single = [{"packet_loss": 40.0}]
        self.assertEqual(calculate_path_packet_loss_probabilistic(edges_single), 40.0)

        # Test lossless path: 0% loss
        edges_zero = [{"packet_loss": 0.0}, {"packet_loss": 0.0}, {"packet_loss": 0.0}]
        self.assertEqual(calculate_path_packet_loss_probabilistic(edges_zero), 0.0)

    def test_end_to_end_latency_calculation(self):
        """Verifies cumulative latency across path hops is accurately calculated."""
        g = build_network()
        # Default baseline: PC1-R1 (2ms) -> R1-R2 (3ms) -> R2-Server (3ms) = 8.0ms
        obs = collect_observations(g, source="PC1", target="Server")
        self.assertEqual(obs["end_to_end_latency_ms"], 8.0)

    def test_monitoring_does_not_activate_routes(self):
        """Verifies monitoring evaluates candidates but never modifies graph active_path."""
        g = build_network()
        g.graph["active_path"] = ["PC1", "R1", "R2", "Server"]
        # Make primary route high latency so alternative is preferred
        g["R1"]["R2"]["latency_ms"] = 300.0

        obs = collect_observations(g, source="PC1", target="Server")
        # Candidate recommendation recommends R1-R3 path
        self.assertIn("R3", obs["route_selection"]["selected_path"])
        # Active path in graph forwarding state MUST NOT be changed by monitoring
        self.assertEqual(g.graph["active_path"], ["PC1", "R1", "R2", "Server"])

    def test_format_monitoring_report_contains_partition_and_loss_info(self):
        """Verifies format_monitoring_report includes partition telemetry and probabilistic formula notice."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["status"] = "DOWN"
        obs = collect_observations(g, source="PC1", target="Server")
        rep = format_monitoring_report(obs)

        self.assertIn("Network Topology State: PARTITIONED", rep)
        self.assertIn("P = 1 - ∏(1-p_i)", rep)


class Stage4MultiFaultDiagnosisTests(unittest.TestCase):
    """Stage 4: Acceptance tests for Multi-Fault Root-Cause Diagnosis and Explainable Evaluation."""

    def test_multi_fault_diagnosis_multiple_link_failures(self):
        """Verifies 3 simultaneous link failures produce 3 distinct Link Failure findings."""
        g = build_network()
        g["PC1"]["R1"]["status"] = "DOWN"
        g["R1"]["R2"]["status"] = "DOWN"
        g["R3"]["Server"]["status"] = "DOWN"

        obs = collect_observations(g)
        findings = diagnose(obs)

        link_findings = [f for f in findings if f.root_cause == "Link failure"]
        self.assertEqual(len(link_findings), 3)

        affected = {f.affected_components[0] for f in link_findings}
        self.assertEqual(affected, {"PC1-R1", "R1-R2", "R3-Server"})

        # Each finding must have a unique sequential ID
        finding_ids = [f.finding_id for f in findings]
        self.assertEqual(len(finding_ids), len(set(finding_ids)))

    def test_multi_fault_diagnosis_mixed_scenarios(self):
        """Verifies Link failure + Wrong Gateway + DNS failure diagnosed simultaneously."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        g.nodes["PC1"]["gateway"] = "R9"
        g.graph["dns_available"] = False

        obs = collect_observations(g)
        findings = diagnose(obs)

        causes = {f.root_cause for f in findings}
        self.assertIn("Link failure", causes)
        self.assertIn("Incorrect default gateway", causes)
        self.assertIn("DNS service failure", causes)

    def test_finding_id_uniqueness_and_format(self):
        """Verifies all emitted diagnostic findings follow the sequential DIAG-XXXX format."""
        g = build_network()
        g["R1"]["R2"]["latency_ms"] = 250.0
        g["R1"]["R3"]["packet_loss"] = 40.0

        obs = collect_observations(g)
        findings = diagnose(obs)

        self.assertGreaterEqual(len(findings), 2)
        for f in findings:
            self.assertTrue(f.finding_id.startswith("DIAG-"))

    def test_root_cause_vs_secondary_symptom(self):
        """Verifies network partition is classified as SECONDARY_SYMPTOM and severed links as ROOT_CAUSE."""
        g = build_network()
        # Sever all paths between PC1 and Server
        g["R1"]["R2"]["status"] = "DOWN"
        g["R1"]["R3"]["status"] = "DOWN"

        obs = collect_observations(g, source="PC1", target="Server")
        findings = diagnose(obs)

        root_causes = [f for f in findings if f.finding_type == "ROOT_CAUSE"]
        symptoms = [f for f in findings if f.finding_type == "SECONDARY_SYMPTOM"]

        self.assertGreaterEqual(len(root_causes), 2)  # The two severed links
        self.assertEqual(len(symptoms), 1)  # The resulting network partition
        self.assertEqual(symptoms[0].root_cause, "Network partition")
        self.assertEqual(symptoms[0].severity, "CRITICAL")

    def test_confidence_calibration(self):
        """Verifies calibrated confidence scores: direct 1.0, audit 0.98, DNS probe 0.95."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        g.nodes["PC1"]["gateway"] = "R9"
        g.graph["dns_available"] = False
        g["R1"]["R3"]["latency_ms"] = 250.0

        obs = collect_observations(g)
        findings = diagnose(obs)

        finding_map = {f.root_cause: f for f in findings}
        self.assertEqual(finding_map["Link failure"].confidence, 1.0)
        self.assertEqual(finding_map["Incorrect default gateway"].confidence, 0.98)
        self.assertEqual(finding_map["DNS service failure"].confidence, 0.95)
        self.assertEqual(finding_map["High latency"].confidence, 0.90)

    def test_finding_tuple_backward_compatibility(self):
        """Verifies DiagnosticFinding supports tuple unpacking and indexing."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        obs = collect_observations(g)
        findings = diagnose(obs)
        first = findings[0]

        # Unpack as 2-tuple (root_cause, evidence)
        name, why = first
        self.assertEqual(name, "Link failure")
        self.assertIn("DOWN", why)

        # Indexing
        self.assertEqual(first[0], "Link failure")
        self.assertEqual(first[1], why)

    def test_format_diagnosis_report_contains_structured_fields(self):
        """Verifies format_diagnosis_report includes finding IDs, types, and summary metrics."""
        g = build_network()
        g["R1"]["R2"]["status"] = "DOWN"
        obs = collect_observations(g)
        findings = diagnose(obs)
        rep = format_diagnosis_report(findings)

        self.assertIn("=== ROOT-CAUSE DIAGNOSIS REPORT ===", rep)
        self.assertIn("Total Diagnostic Findings", rep)
        self.assertIn("[DIAG-0001]", rep)
        self.assertIn("Type: ROOT_CAUSE", rep)


if __name__ == "__main__":
    unittest.main()
