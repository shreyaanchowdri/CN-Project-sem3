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
    generate_unique_device_name
)
from fault_injection import (
    inject_fault,
    reset_faults,
    SCENARIOS,
    UI_SCENARIOS,
    UI_TO_BACKEND_MAP,
    BACKEND_TO_UI_MAP
)
from monitoring import collect_observations
from diagnostics import diagnose, DiagnosticFinding
from recovery import recover
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
                # Primary route via R2 is unaffected
                self.assertTrue(rec["verified"])
                self.assertEqual(rec["status"], "RECOVERY VERIFIED")
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


if __name__ == "__main__":
    unittest.main()
