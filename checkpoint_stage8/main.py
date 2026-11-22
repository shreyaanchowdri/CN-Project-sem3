"""Cisco Packet Tracer-Style Network Simulation & Fault Diagnosis Workspace.

A professional network engineering application combining Packet Tracer usability
with intelligent, observation-based fault diagnosis and automated recovery.
"""
import os
import sys
import time
import json
import csv
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import networkx as nx

from network_model import (
    build_network,
    add_device,
    remove_device,
    connect_devices,
    disconnect_devices,
    configure_device,
    configure_link,
    save_topology_to_file,
    load_topology_from_file,
    save_topology_to_dict,
    load_topology_from_dict,
    is_essential_device,
    DEFAULT_POSITIONS,
    DEFAULT_NODES,
    DEVICE_TYPES,
    CONNECTION_TYPES,
    generate_unique_device_name,
    discover_routes,
    select_best_route,
    resolve_endpoints
)
from fault_injection import (
    inject_fault,
    reset_faults,
    SCENARIOS,
    UI_SCENARIOS,
    UI_TO_BACKEND_MAP,
    BACKEND_TO_UI_MAP,
    parse_link_endpoints
)
from fault_registry import get_fault_registry, FaultStatus
from scenario_manager import (
    PREDEFINED_SCENARIOS,
    inject_fault_batch,
    validate_fault_batch
)
from recovery_planner import (
    generate_recovery_plan,
    format_plan_report,
    RecoveryDecision,
    RoutePolicy
)
from audit_logger import get_audit_logger, record_audit
from network_terminal import NetworkTerminal
from monitoring import collect_observations, format_monitoring_report, generate_monitoring_report
from diagnostics import diagnose, DiagnosticFinding, format_diagnosis_report, generate_diagnosis_report
from recovery import (
    recover,
    format_recovery_report,
    generate_recovery_report,
    format_verification_report,
    generate_verification_report
)
from network_model import get_active_route, set_active_route
from metrics import make_metrics


class App:
    """Cisco Packet Tracer-Style Desktop Network Simulation & Diagnosis Workspace."""

    def __init__(self, root):
        self.root = root
        root.title("Cisco Packet Tracer - Intelligent Network Fault Diagnosis & Recovery Workspace")
        root.geometry("1420x860")
        root.minsize(1220, 720)

        # Network Graph Model & Topology State
        self.g = build_network()
        self.node_pos = dict(self.g.graph.get("node_positions", DEFAULT_POSITIONS))
        self.state = {"fault": "No fault"}
        self.last_report = "Workspace initialized."
        self.history = []
        self.diag_time = 0.0
        self.rec_time = 0.0

        # Workspace Modes & Tool States (Packet Tracer Toolset)
        self.current_tool = "select"  # "select", "move", "connect", "delete"
        self.selected_node = None
        self.selected_nodes = []
        self.selected_link = None
        self.connect_source_node = None
        self.palette_equipped_type = None
        self.show_grid = True
        self.zoom_level = 1.0

        # Clipboard, Multiple Selection & Undo/Redo Stacks
        self.clipboard = []
        self.paste_count = 1
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 30
        self.drag_nodes = []
        self.drag_start_positions = {}

        # Interactive Drag-and-Drop & Viewport State
        self.drag_node = None
        self.is_dragging = False
        self.drag_offset = (0.0, 0.0)
        self.drag_start_pos = (0.0, 0.0)
        self.drag_xlim = None
        self.drag_ylim = None
        self.pan_start = None

        # Dashboard, Terminal & Multi-Fault State
        self.custom_fault_batch = []
        self.terminal = None
        self.last_recovery_status = "NOMINAL"
        self.last_recovery_service_availability = "AVAILABLE"
        self.last_recovery_network_health = "HEALTHY"

        # Apply Cisco Packet Tracer Styling
        self._apply_theme()

        # Build Full Packet Tracer UI Layout
        self._build_top_menu()
        self._build_top_toolbar()
        self._build_main_workspace()
        self._build_bottom_panel()

        # Bind Canvas Mouse Events (Matplotlib Canvas)
        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)

        # Keyboard Shortcuts
        self._bind_shortcuts()

        # Initial Render and Population
        self.refresh_endpoint_selectors()
        self.update_route_comparison()
        self.update_inventory()
        self.fit_to_screen()
        self.update_header_status("HEALTHY", "LOGICAL WORKSPACE READY")
        self.update_kpi_dashboard()
        self.refresh_active_faults_view()
        self.refresh_audit_view()
        self.log_event("Packet Tracer logical workspace initialized. Baseline 5-device topology loaded.")

    # -------------------------------------------------------------------------
    # Visual Theme: Cisco Packet Tracer Slate & Modern Network Engineering
    # -------------------------------------------------------------------------
    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Cisco Packet Tracer Color Palette
        self.c_cisco_dark = "#0f172a"     # Slate 900 (Menu / Topbars)
        self.c_toolbar_bg = "#1e293b"     # Slate 800 (Toolbar background)
        self.c_toolbar_btn = "#334155"    # Slate 700 (Tool buttons)
        self.c_toolbar_act = "#0284c7"    # Cisco Cyan (Active tool)
        self.c_workspace_bg = "#f8fafc"   # Clean Workspace White
        self.c_grid_color = "#e2e8f0"     # Grid dot/line
        self.c_border = "#cbd5e1"         # Border Slate 300
        self.c_panel_bg = "#f1f5f9"       # Side panels background

        # Visual States for Network Topology (Requirement 8)
        self.c_healthy_link = "#16a34a"   # Green links: Healthy
        self.c_failed_link = "#dc2626"    # Red links: Failed (DOWN)
        self.c_degraded_link = "#ea580c"  # Orange links: Degraded
        self.c_end_device = "#2563eb"     # Blue devices: End devices (PC, Laptop)
        self.c_router = "#16a34a"         # Green devices: Routers
        self.c_switch = "#d97706"         # Amber devices: Switches
        self.c_server = "#7c3aed"         # Purple devices: Servers
        self.c_selection = "#f59e0b"      # Gold selection halo
        self.c_cable_active = "#10b981"   # Emerald cable connector

        self.root.configure(bg=self.c_panel_bg)

        style.configure("TFrame", background=self.c_panel_bg)
        style.configure("TLabelframe", background=self.c_panel_bg, bordercolor=self.c_border)
        style.configure("TLabelframe.Label", background=self.c_panel_bg, foreground=self.c_cisco_dark, font=("Segoe UI", 9, "bold"))
        style.configure("TLabel", background=self.c_panel_bg, foreground="#334155", font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=self.c_cisco_dark, foreground="#ffffff", font=("Segoe UI", 11, "bold"))

        # Button Styling
        style.configure("TButton", font=("Segoe UI", 8, "bold"), padding=3)
        style.configure("Primary.TButton", background="#2563eb", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])
        style.configure("Success.TButton", background="#16a34a", foreground="#ffffff")
        style.map("Success.TButton", background=[("active", "#15803d")])
        style.configure("Danger.TButton", background="#dc2626", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#b91c1c")])

        # Notebook Tabs
        style.configure("TNotebook", background=self.c_panel_bg)
        style.configure("TNotebook.Tab", font=("Segoe UI", 8, "bold"), padding=[10, 3])

        # Treeview Styles
        style.configure("Treeview", font=("Segoe UI", 8), rowheight=20, background="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI", 8, "bold"), background="#e2e8f0", foreground=self.c_cisco_dark)

        # Combobox dropdown popup styling
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))
        self.root.option_add("*TCombobox*Listbox.background", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.foreground", "#0f172a")
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#0284c7")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    # -------------------------------------------------------------------------
    # Layout 1: Top Menu Bar (File, Edit, View, Tools, Simulation, Help)
    # -------------------------------------------------------------------------
    def _build_top_menu(self):
        menubar = tk.Menu(self.root)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Logical Workspace", command=self.new_workspace, accelerator="Ctrl+N")
        file_menu.add_command(label="Open Topology (JSON)...", command=self.load_topology, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Topology (JSON)", command=self.save_topology, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export Audit Log (CSV)...", command=self.export)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut Device", command=self.cut_selected, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy Device", command=self.copy_selected, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste Device", command=self.paste_clipboard, accelerator="Ctrl+V")
        edit_menu.add_command(label="Duplicate Device", command=self.duplicate_selected, accelerator="Ctrl+D")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All Devices", command=self.select_all_devices, accelerator="Ctrl+A")
        edit_menu.add_command(label="Clear Selection", command=self.clear_selection, accelerator="Esc")
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete Selected Device / Link", command=self.delete_selected, accelerator="Del")
        edit_menu.add_separator()
        edit_menu.add_command(label="Reset to Default Topology", command=self.reset)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Fit to Screen", command=self.fit_to_screen, accelerator="Ctrl+0")
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Workspace Grid", command=self.toggle_grid)
        menubar.add_cascade(label="View", menu=view_menu)

        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Select / Inspect Tool", command=lambda: self.set_tool("select"), accelerator="S")
        tools_menu.add_command(label="Move / Pan Tool", command=lambda: self.set_tool("move"), accelerator="M")
        tools_menu.add_command(label="Connect Devices (Cable)", command=lambda: self.set_tool("connect"), accelerator="C")
        tools_menu.add_command(label="Delete Tool", command=lambda: self.set_tool("delete"), accelerator="D")
        tools_menu.add_separator()
        tools_menu.add_command(label="Open Simulated Network Terminal (CMD)...", command=self.open_network_terminal, accelerator="Ctrl+T")
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Simulation Menu
        sim_menu = tk.Menu(menubar, tearoff=0)
        sim_menu.add_command(label="Inject Active Fault Scenario", command=self.inject)
        sim_menu.add_command(label="Monitor Network & Telemetry", command=self.diagnose, accelerator="F5")
        sim_menu.add_command(label="Automated Recovery & Verification", command=self.recover, accelerator="F6")
        sim_menu.add_separator()
        sc_menu = tk.Menu(sim_menu, tearoff=0)
        for s in UI_SCENARIOS:
            sc_menu.add_command(label=s, command=lambda sc_val=s: self.set_scenario(sc_val))
        sim_menu.add_cascade(label="Select Scenario", menu=sc_menu)
        sim_menu.add_separator()
        sim_menu.add_command(label="Reset Simulation", command=self.reset, accelerator="F4")
        menubar.add_cascade(label="Simulation", menu=sim_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Cisco Packet Tracer Workspace Guide", command=self.show_help_guide)
        help_menu.add_command(label="About Intelligent Network Fault Framework", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_workspace())
        self.root.bind("<Control-s>", lambda e: self.save_topology())
        self.root.bind("<Control-o>", lambda e: self.load_topology())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.fit_to_screen())
        self.root.bind("<F5>", lambda e: self.diagnose())
        self.root.bind("<F6>", lambda e: self.recover())
        self.root.bind("<F4>", lambda e: self.reset())
        self.root.bind("<Control-t>", lambda e: self.open_network_terminal())
        self.root.bind("<Control-T>", lambda e: self.open_network_terminal())
        self.root.bind("<Escape>", lambda e: self.cancel_active_tool())

        # Protected Delete Key Handler
        self.root.bind("<Delete>", self._on_delete_key)

        # Protected Clipboard & Edit Shortcuts (Safety when editing text input fields)
        for k in ("<Control-c>", "<Control-C>"):
            self.root.bind(k, self._on_ctrl_c)
        for k in ("<Control-v>", "<Control-V>"):
            self.root.bind(k, self._on_ctrl_v)
        for k in ("<Control-x>", "<Control-X>"):
            self.root.bind(k, self._on_ctrl_x)
        for k in ("<Control-d>", "<Control-D>"):
            self.root.bind(k, self._on_ctrl_d)
        for k in ("<Control-z>", "<Control-Z>"):
            self.root.bind(k, self._on_ctrl_z)
        for k in ("<Control-y>", "<Control-Y>"):
            self.root.bind(k, self._on_ctrl_y)
        for k in ("<Control-a>", "<Control-A>"):
            self.root.bind(k, self._on_ctrl_a)

    # -------------------------------------------------------------------------
    # Layout 2: Top Toolbar (Tools & Simulation Controls)
    # -------------------------------------------------------------------------
    def _build_top_toolbar(self):
        bar_container = tk.Frame(self.root, bg=self.c_toolbar_bg)
        bar_container.pack(fill="x", side="top")

        # Row 1: Packet Tracer Tools, Edit Shortcuts, View Zoom, Status Pill
        bar_tools = tk.Frame(bar_container, bg=self.c_toolbar_bg, height=36)
        bar_tools.pack(fill="x", side="top", padx=4, pady=(2, 1))

        t_left = tk.Frame(bar_tools, bg=self.c_toolbar_bg)
        t_left.pack(side="left", padx=4)

        tk.Label(t_left, text="TOOLS:", bg=self.c_toolbar_bg, fg="#94a3b8", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(2, 6))

        self.tool_btns = {}
        tool_defs = [
            ("select", "↖ Select", "Select / Inspect device or link"),
            ("move", "✥ Move", "Move / Pan logical workspace"),
            ("connect", "⚡ Connect", "Cable connection tool: click Device 1 then Device 2"),
            ("delete", "✖ Delete", "Delete clicked device or connection")
        ]
        for tid, label, tooltip in tool_defs:
            btn = tk.Button(
                t_left, text=label, font=("Segoe UI", 8, "bold"),
                bg=self.c_toolbar_act if tid == self.current_tool else self.c_toolbar_btn,
                fg="#ffffff", relief="flat", padx=8, pady=2, cursor="hand2",
                command=lambda t=tid: self.set_tool(t)
            )
            btn.pack(side="left", padx=2)
            self.tool_btns[tid] = btn

        tk.Frame(t_left, bg="#475569", width=1, height=20).pack(side="left", padx=4)

        # Quick Edit Buttons (Undo, Redo, Copy, Paste, Duplicate)
        tk.Button(t_left, text="↩ Undo", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=5, pady=2, cursor="hand2", command=self.undo).pack(side="left", padx=1)
        tk.Button(t_left, text="↪ Redo", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=5, pady=2, cursor="hand2", command=self.redo).pack(side="left", padx=1)
        tk.Button(t_left, text="📋 Copy", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=5, pady=2, cursor="hand2", command=self.copy_selected).pack(side="left", padx=1)
        tk.Button(t_left, text="📥 Paste", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=5, pady=2, cursor="hand2", command=self.paste_clipboard).pack(side="left", padx=1)
        tk.Button(t_left, text="⎘ Dup", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=5, pady=2, cursor="hand2", command=self.duplicate_selected).pack(side="left", padx=1)

        tk.Frame(t_left, bg="#475569", width=1, height=20).pack(side="left", padx=4)

        # Zoom & Fit Controls
        tk.Button(t_left, text="🔍+ Zoom In", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=6, pady=2, cursor="hand2", command=self.zoom_in).pack(side="left", padx=2)
        tk.Button(t_left, text="🔍- Zoom Out", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=6, pady=2, cursor="hand2", command=self.zoom_out).pack(side="left", padx=2)
        tk.Button(t_left, text="⛶ Fit Screen", font=("Segoe UI", 8), bg=self.c_toolbar_btn, fg="#ffffff",
                  relief="flat", padx=6, pady=2, cursor="hand2", command=self.fit_to_screen).pack(side="left", padx=2)

        # Right Section: Status Text & Health Pill Badge
        t_right = tk.Frame(bar_tools, bg=self.c_toolbar_bg)
        t_right.pack(side="right", padx=6)

        self.badge_lbl = tk.Label(t_right, text="HEALTHY", font=("Segoe UI", 8, "bold"), bg="#15803d", fg="#ffffff", padx=8, pady=2)
        self.badge_lbl.pack(side="right", padx=6)

        self.status_lbl = tk.Label(t_right, text="LOGICAL WORKSPACE READY", font=("Segoe UI", 8), bg=self.c_toolbar_bg, fg="#94a3b8")
        self.status_lbl.pack(side="right", padx=4)

        # Divider line between Tool Bar and Simulation Strip
        tk.Frame(bar_container, bg="#334155", height=1).pack(fill="x", side="top")

        # Row 2: Simulation & Fault Injection Control Strip
        bar_sim = tk.Frame(bar_container, bg="#0f172a", height=38)
        bar_sim.pack(fill="x", side="top", padx=0, pady=0)

        sim_left = tk.Frame(bar_sim, bg="#0f172a")
        sim_left.pack(side="left", padx=8, pady=4)

        tk.Label(sim_left, text="⚡ SIMULATION:", bg="#0f172a", fg="#38bdf8", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(2, 6))

        tk.Frame(sim_left, bg="#334155", width=1, height=18).pack(side="left", padx=4)

        tk.Label(sim_left, text="Scenario:", bg="#0f172a", fg="#cbd5e1", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(4, 2))

        # Scenario Combobox: Sized with width=30 so complete scenario names are displayed without truncation
        # Height=6 so all 6 options are visible in the dropdown list without scrolling
        self.choice = tk.StringVar(value=UI_SCENARIOS[0])
        self.scenario_combo = ttk.Combobox(
            sim_left,
            textvariable=self.choice,
            values=UI_SCENARIOS,
            state="readonly",
            width=30,
            height=6
        )
        self.scenario_combo.pack(side="left", padx=(2, 8))
        self.scenario_combo.bind("<<ComboboxSelected>>", self._on_scenario_selected)

        # Dynamic Link-Selection Controls for Link Failure Scenario (Requirements 2, 3, 4, 5)
        self.link_select_frame = tk.Frame(sim_left, bg="#0f172a")

        tk.Label(
            self.link_select_frame, text="Target Link:",
            bg="#0f172a", fg="#f59e0b", font=("Segoe UI", 8, "bold")
        ).pack(side="left", padx=(4, 2))

        self.target_link_choice = tk.StringVar()
        self.target_link_combo = ttk.Combobox(
            self.link_select_frame,
            textvariable=self.target_link_choice,
            state="readonly",
            width=18,
            height=8
        )
        self.target_link_combo.pack(side="left", padx=(2, 4))
        self.target_link_combo.bind("<<ComboboxSelected>>", self._on_target_link_selected)

        tk.Button(
            self.link_select_frame, text="🎯 Pick Link...",
            font=("Segoe UI", 7, "bold"), bg="#334155", fg="#cbd5e1",
            relief="flat", padx=6, pady=2, cursor="hand2",
            command=self.show_link_selection_dialog
        ).pack(side="left", padx=2)

        # Simulation Action Buttons
        tk.Button(sim_left, text="⚡ Inject Fault", font=("Segoe UI", 8, "bold"), bg="#dc2626", fg="#ffffff",
                  relief="flat", padx=10, pady=2, cursor="hand2", command=self.inject).pack(side="left", padx=3)
        tk.Button(sim_left, text="🔍 Monitor & Diagnose", font=("Segoe UI", 8, "bold"), bg="#0284c7", fg="#ffffff",
                  relief="flat", padx=10, pady=2, cursor="hand2", command=self.diagnose).pack(side="left", padx=3)
        tk.Button(sim_left, text="🛡 Recover & Verify", font=("Segoe UI", 8, "bold"), bg="#16a34a", fg="#ffffff",
                  relief="flat", padx=10, pady=2, cursor="hand2", command=self.recover).pack(side="left", padx=3)
        tk.Button(sim_left, text="🔄 Reset", font=("Segoe UI", 8, "bold"), bg="#475569", fg="#ffffff",
                  relief="flat", padx=10, pady=2, cursor="hand2", command=self.reset).pack(side="left", padx=3)
        tk.Button(sim_left, text="💻 Terminal", font=("Segoe UI", 8, "bold"), bg="#0f172a", fg="#38bdf8",
                  highlightbackground="#0284c7", highlightcolor="#0284c7", highlightthickness=1,
                  relief="flat", padx=10, pady=2, cursor="hand2", command=self.open_network_terminal).pack(side="left", padx=3)

        # Simulation Right Section: Engine indicator
        sim_right = tk.Frame(bar_sim, bg="#0f172a")
        sim_right.pack(side="right", padx=10, pady=4)

        self.sim_status_note = tk.Label(
            sim_right,
            text="Observation-Based Root-Cause Diagnosis Active",
            font=("Segoe UI", 8, "italic"),
            bg="#0f172a",
            fg="#64748b"
        )
        self.sim_status_note.pack(side="right")

    def get_topology_link_labels(self):
        """Return list of formatted connection strings 'u ↔ v' from active NetworkX graph."""
        if not hasattr(self, "g") or self.g.number_of_edges() == 0:
            return []
        labels = []
        for u, v in self.g.edges():
            labels.append(f"{u} \u2194 {v}")
        return labels

    def refresh_target_link_options(self):
        """Populate the link failure dropdown dynamically from current NetworkX edges."""
        if not hasattr(self, "target_link_combo"):
            return
        labels = self.get_topology_link_labels()
        if not labels:
            self.target_link_combo["values"] = ["(No connections)"]
            self.target_link_choice.set("(No connections)")
            return

        self.target_link_combo["values"] = labels
        cur = self.target_link_choice.get()
        if cur not in labels:
            # If a link is currently selected on canvas, prefer it
            selected_match = None
            if self.selected_link:
                u, v = self.selected_link
                for l in labels:
                    if (u in l and v in l):
                        selected_match = l
                        break
            if selected_match:
                self.target_link_choice.set(selected_match)
            else:
                self.target_link_choice.set(labels[0])

    def _update_link_failure_controls(self):
        """Show or hide the Target Link dropdown based on whether Link Failure is active."""
        if not hasattr(self, "link_select_frame"):
            return
        sc = self.choice.get()
        is_link_failure = (sc in ("Link Failure", "Link failure", "Link failure (R2-Server)"))
        if is_link_failure:
            self.refresh_target_link_options()
            self.link_select_frame.pack(side="left", padx=(2, 6), after=self.scenario_combo)
        else:
            self.link_select_frame.pack_forget()

    def _on_target_link_selected(self, event=None):
        """Handler when user selects a link in the Target Link dropdown."""
        raw = self.target_link_choice.get()
        u, v = parse_link_endpoints(raw)
        if u and v and self.g.has_edge(u, v):
            self.selected_link = (u, v)
            self.selected_node = None
            self.selected_nodes = []
            self.select_link_for_inspection(u, v)
            self.draw()
            self.log_event(f"Selected link failure target: {u} \u2194 {v}")

    def show_link_selection_dialog(self):
        """Display an interactive dialog listing all currently existing connections in active topology."""
        labels = self.get_topology_link_labels()
        if not labels:
            messagebox.showinfo("No Connections", "There are currently no connections in the active topology.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Select Connection to Fail")
        dlg.geometry("540x380")
        dlg.transient(self.root)
        dlg.resizable(False, False)
        dlg.configure(bg=self.c_panel_bg)

        # Header
        hdr = tk.Frame(dlg, bg=self.c_cisco_dark, height=45)
        hdr.pack(fill="x", side="top")
        tk.Label(
            hdr, text="⚡ SELECT CONNECTION TO FAIL (LINK FAILURE)",
            font=("Segoe UI", 10, "bold"), bg=self.c_cisco_dark, fg="#ffffff", padx=12, pady=10
        ).pack(side="left")

        # Instruction
        content = tk.Frame(dlg, bg=self.c_panel_bg, padx=14, pady=10)
        content.pack(fill="both", expand=True)

        tk.Label(
            content,
            text="Choose any connection from the active topology to inject a simulated Link Failure:",
            font=("Segoe UI", 9), bg=self.c_panel_bg, fg="#334155"
        ).pack(anchor="w", pady=(0, 6))

        # Treeview listing all links
        cols = ("Connection", "Type", "Status", "Cost", "Latency", "Loss")
        tree_frame = tk.Frame(content)
        tree_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8, selectmode="browse")
        tree.heading("Connection", text="Connection")
        tree.heading("Type", text="Cable Type")
        tree.heading("Status", text="Status")
        tree.heading("Cost", text="Cost")
        tree.heading("Latency", text="Latency")
        tree.heading("Loss", text="Loss")

        tree.column("Connection", width=120, anchor="center")
        tree.column("Type", width=140, anchor="w")
        tree.column("Status", width=60, anchor="center")
        tree.column("Cost", width=40, anchor="center")
        tree.column("Latency", width=60, anchor="center")
        tree.column("Loss", width=50, anchor="center")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Populate rows from NetworkX graph
        item_to_link = {}
        initial_sel = None
        current_choice = self.target_link_choice.get()

        for u, v, d in self.g.edges(data=True):
            conn_str = f"{u} \u2194 {v}"
            ctype = d.get("connection_type", "Copper Straight-Through")
            st = d.get("status", "UP")
            cost = d.get("cost", 1)
            lat = f"{d.get('latency_ms', 2.0)} ms"
            loss = f"{d.get('packet_loss', 0.0)}%"

            iid = tree.insert("", "end", values=(conn_str, ctype, st, cost, lat, loss))
            item_to_link[iid] = conn_str

            if conn_str == current_choice or f"{v} \u2194 {u}" == current_choice:
                initial_sel = iid

        if not initial_sel and tree.get_children():
            initial_sel = tree.get_children()[0]
        if initial_sel:
            tree.selection_set(initial_sel)
            tree.focus(initial_sel)

        # Bottom Buttons
        btn_bar = tk.Frame(dlg, bg=self.c_panel_bg, padx=12, pady=10)
        btn_bar.pack(fill="x", side="bottom")

        def apply_selection():
            sel = tree.selection()
            if not sel:
                return
            chosen = item_to_link.get(sel[0])
            if chosen:
                self.target_link_choice.set(chosen)
                u, v = parse_link_endpoints(chosen)
                if u and v:
                    self.selected_link = (u, v)
                    self.select_link_for_inspection(u, v)
                    self.draw()
            dlg.destroy()

        def inject_now():
            apply_selection()
            self.choice.set("Link Failure")
            self._update_link_failure_controls()
            self.inject()

        tk.Button(
            btn_bar, text="Cancel", font=("Segoe UI", 9),
            bg="#94a3b8", fg="#ffffff", relief="flat", padx=10, pady=3,
            command=dlg.destroy
        ).pack(side="right", padx=4)

        tk.Button(
            btn_bar, text="Select Link", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", relief="flat", padx=12, pady=3,
            command=apply_selection
        ).pack(side="right", padx=4)

        tk.Button(
            btn_bar, text="⚡ Inject Fault Now", font=("Segoe UI", 9, "bold"),
            bg="#dc2626", fg="#ffffff", relief="flat", padx=12, pady=3,
            command=inject_now
        ).pack(side="left", padx=4)

    def set_scenario(self, scenario_name):
        """Set the active fault scenario from menu or programmatically."""
        self.choice.set(scenario_name)
        self.log_event(f"Selected fault scenario: {scenario_name}")
        self._update_link_failure_controls()

    def _on_scenario_selected(self, event=None):
        """Handler when user selects a scenario in the dropdown."""
        sc = self.choice.get()
        self.log_event(f"Selected fault scenario: {sc}")
        self._update_link_failure_controls()

    def set_tool(self, tool_name):
        self.current_tool = tool_name
        self.connect_source_node = None
        for tid, btn in self.tool_btns.items():
            btn.config(bg=self.c_toolbar_act if tid == tool_name else self.c_toolbar_btn)
        
        cursors = {"select": "", "move": "fleur", "connect": "crosshair", "delete": "pirate" if os.name != "nt" else "X_cursor"}
        cur = cursors.get(tool_name, "")
        try:
            self.canvas.get_tk_widget().config(cursor=cur)
        except Exception:
            self.canvas.get_tk_widget().config(cursor="")
        self.status_lbl.config(text=f"TOOL ACTIVE: {tool_name.upper()} | Click workspace to operate")
        self.draw()

    def cancel_active_tool(self):
        if self.connect_source_node:
            self.log_event("Cable connection tool cancelled.")
            self.connect_source_node = None
        self.clear_selection()
        self.set_tool("select")

    # -------------------------------------------------------------------------
    # Undo / Redo & Snapshot Management (Requirement 6)
    # -------------------------------------------------------------------------
    def get_topology_snapshot(self):
        """Create a deep snapshot of graph nodes, edges, attributes, and positions."""
        nodes_copy = {n: dict(d) for n, d in self.g.nodes(data=True)}
        edges_copy = [(u, v, dict(d)) for u, v, d in self.g.edges(data=True)]
        graph_copy = dict(self.g.graph)
        pos_copy = {n: tuple(pos) for n, pos in self.node_pos.items()}
        return {
            "nodes": nodes_copy,
            "edges": edges_copy,
            "graph": graph_copy,
            "pos": pos_copy,
            "selected_nodes": list(self.selected_nodes),
            "selected_node": self.selected_node,
            "selected_link": self.selected_link
        }

    def restore_topology_snapshot(self, snapshot):
        """Restore topology graph, attributes, and coordinates from a snapshot."""
        self.g.clear()
        self.g.graph.update(snapshot.get("graph", {}))
        for n, d in snapshot.get("nodes", {}).items():
            self.g.add_node(n, **d)
        for u, v, d in snapshot.get("edges", []):
            self.g.add_edge(u, v, **d)
        self.node_pos = {n: tuple(pos) for n, pos in snapshot.get("pos", {}).items()}
        self.g.graph["node_positions"] = dict(self.node_pos)

        # Restore selection
        saved_sel = [n for n in snapshot.get("selected_nodes", []) if n in self.g]
        self.selected_nodes = saved_sel
        if snapshot.get("selected_node") in self.g:
            self.selected_node = snapshot.get("selected_node")
        else:
            self.selected_node = saved_sel[0] if saved_sel else None

        saved_link = snapshot.get("selected_link")
        if saved_link and self.g.has_edge(saved_link[0], saved_link[1]):
            self.selected_link = saved_link
        else:
            self.selected_link = None

        self.refresh_endpoint_selectors()
        self.update_inventory()
        self.update_route_comparison()
        if self.selected_node:
            self.select_device_for_inspection(self.selected_node)
        elif self.selected_link:
            self.select_link_for_inspection(self.selected_link[0], self.selected_link[1])
        self.draw()

    def record_undo_state(self, action_name=""):
        """Record the current topology state onto the undo stack."""
        snapshot = self.get_topology_snapshot()
        self.undo_stack.append((action_name, snapshot))
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        """Undo the last topology operation (Ctrl+Z)."""
        if not self.undo_stack:
            self.status_lbl.config(text="Nothing to undo.")
            return False
        current_state = self.get_topology_snapshot()
        action_name, prev_state = self.undo_stack.pop()
        self.redo_stack.append((action_name, current_state))
        self.restore_topology_snapshot(prev_state)
        self.log_event(f"Undo: Reverted '{action_name}'.")
        self.status_lbl.config(text=f"UNDO: {action_name}")
        return True

    def redo(self):
        """Redo the last undone operation (Ctrl+Y)."""
        if not self.redo_stack:
            self.status_lbl.config(text="Nothing to redo.")
            return False
        current_state = self.get_topology_snapshot()
        action_name, next_state = self.redo_stack.pop()
        self.undo_stack.append((action_name, current_state))
        self.restore_topology_snapshot(next_state)
        self.log_event(f"Redo: Re-applied '{action_name}'.")
        self.status_lbl.config(text=f"REDO: {action_name}")
        return True

    # -------------------------------------------------------------------------
    # Clipboard Operations: Copy, Paste, Cut, Duplicate (Requirements 1, 2, 3, 4, 5)
    # -------------------------------------------------------------------------
    def copy_selected(self):
        """Copy selected device(s) configuration into internal clipboard (Ctrl+C)."""
        nodes_to_copy = [n for n in self.selected_nodes if n in self.g]
        if not nodes_to_copy and self.selected_node and self.selected_node in self.g:
            nodes_to_copy = [self.selected_node]

        if not nodes_to_copy:
            self.status_lbl.config(text="No device selected to copy.")
            return []

        self.clipboard = []
        ref_pos = self.node_pos.get(nodes_to_copy[0], (0, 0))

        for n in nodes_to_copy:
            d = dict(self.g.nodes[n])
            pos = self.node_pos.get(n, (0, 0))
            rel_pos = (round(pos[0] - ref_pos[0], 2), round(pos[1] - ref_pos[1], 2))
            item = {
                "orig_name": n,
                "type": d.get("type", "PC"),
                "ip": d.get("ip", ""),
                "subnet_mask": d.get("subnet_mask", "255.255.255.0"),
                "gateway": d.get("gateway", "R1"),
                "dns_server": d.get("dns_server", "192.168.1.1"),
                "kind": d.get("kind", "End device"),
                "orig_pos": pos,
                "rel_pos": rel_pos
            }
            self.clipboard.append(item)

        self.paste_count = 1
        self.log_event(f"Copied {len(self.clipboard)} device(s) to clipboard: {', '.join(nodes_to_copy)}.")
        self.status_lbl.config(text=f"COPIED: {len(self.clipboard)} device(s)")
        return list(self.clipboard)

    def paste_clipboard(self):
        """Paste device(s) from clipboard with unique names and offset (Ctrl+V)."""
        if not self.clipboard:
            self.status_lbl.config(text="Clipboard is empty.")
            return []

        self.record_undo_state(f"Paste {len(self.clipboard)} device(s)")

        offset_x = 0.5 * self.paste_count
        offset_y = -0.4 * self.paste_count
        self.paste_count += 1

        newly_created = []

        for item in self.clipboard:
            dtype = item.get("type", "PC")
            new_name = generate_unique_device_name(self.g, dtype)

            orig_p = item.get("orig_pos", (0, 0))
            rel_p = item.get("rel_pos", (0, 0))
            if len(self.clipboard) == 1:
                px = round(orig_p[0] + offset_x, 2)
                py = round(orig_p[1] + offset_y, 2)
            else:
                base_p = self.clipboard[0].get("orig_pos", (0, 0))
                px = round(base_p[0] + offset_x + rel_p[0], 2)
                py = round(base_p[1] + offset_y + rel_p[1], 2)

            ip = item.get("ip", "")
            subnet_mask = item.get("subnet_mask", "255.255.255.0")
            gateway = item.get("gateway", "R1")
            dns_server = item.get("dns_server", "192.168.1.1")

            add_device(
                self.g,
                new_name,
                device_type=dtype,
                ip=ip,
                subnet_mask=subnet_mask,
                gateway=gateway,
                dns_server=dns_server,
                pos=(px, py)
            )
            self.node_pos[new_name] = (px, py)
            newly_created.append(new_name)

        self.selected_nodes = list(newly_created)
        self.selected_node = newly_created[-1]
        self.selected_link = None

        self.refresh_endpoint_selectors()
        self.update_inventory()
        self.update_route_comparison()
        self.select_device_for_inspection(self.selected_node)
        self.log_event(f"Pasted {len(newly_created)} device(s): {', '.join(newly_created)}.")
        self.status_lbl.config(text=f"PASTED: {', '.join(newly_created)}")
        self.draw()
        return newly_created

    def cut_selected(self):
        """Cut selected device(s) and remove from topology (Ctrl+X)."""
        nodes_to_cut = [n for n in self.selected_nodes if n in self.g]
        if not nodes_to_cut and self.selected_node and self.selected_node in self.g:
            nodes_to_cut = [self.selected_node]

        if not nodes_to_cut:
            self.status_lbl.config(text="No device selected to cut.")
            return []

        self.copy_selected()
        self.record_undo_state(f"Cut {len(nodes_to_cut)} device(s)")

        for n in nodes_to_cut:
            remove_device(self.g, n, force=True)
            if n in self.node_pos:
                del self.node_pos[n]

        self.selected_nodes = []
        self.selected_node = None
        self.selected_link = None

        self.refresh_endpoint_selectors()
        self.update_inventory()
        self.update_route_comparison()
        self.log_event(f"Cut {len(nodes_to_cut)} device(s): {', '.join(nodes_to_cut)}.")
        self.status_lbl.config(text=f"CUT: {len(nodes_to_cut)} device(s)")
        self.draw()
        return nodes_to_cut

    def duplicate_selected(self):
        """Quick duplicate operation for selected device(s) (Ctrl+D)."""
        nodes_to_dup = [n for n in self.selected_nodes if n in self.g]
        if not nodes_to_dup and self.selected_node and self.selected_node in self.g:
            nodes_to_dup = [self.selected_node]

        if not nodes_to_dup:
            self.status_lbl.config(text="No device selected to duplicate.")
            return []

        self.copy_selected()
        return self.paste_clipboard()

    def select_all_devices(self):
        """Select all devices in the logical workspace (Ctrl+A)."""
        self.selected_nodes = list(self.g.nodes())
        if self.selected_nodes:
            self.selected_node = self.selected_nodes[-1]
            self.select_device_for_inspection(self.selected_node)
        self.selected_link = None
        self.status_lbl.config(text=f"Selected all {len(self.selected_nodes)} devices.")
        self.draw()

    def clear_selection(self):
        """Clear all active selections (Escape)."""
        self.selected_nodes = []
        self.selected_node = None
        self.selected_link = None
        self.draw()

    # -------------------------------------------------------------------------
    # Keyboard Event Filtering: Protect Text Input Fields (Requirement 7)
    # -------------------------------------------------------------------------
    def _is_text_editing_widget(self, widget):
        """Return True if widget is an active text input (Entry, Text, Combobox)."""
        if widget is None:
            return False
        try:
            cls_name = widget.winfo_class()
            if cls_name in ("Entry", "TEntry", "Text", "TCombobox", "Combobox", "Spinbox"):
                return True
        except Exception:
            pass
        return isinstance(widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox))

    def _on_ctrl_c(self, event):
        if self._is_text_editing_widget(event.widget):
            return  # Allow default text entry copy
        self.copy_selected()
        return "break"

    def _on_ctrl_v(self, event):
        if self._is_text_editing_widget(event.widget):
            return  # Allow default text entry paste
        self.paste_clipboard()
        return "break"

    def _on_ctrl_x(self, event):
        if self._is_text_editing_widget(event.widget):
            return  # Allow default text entry cut
        self.cut_selected()
        return "break"

    def _on_ctrl_d(self, event):
        if self._is_text_editing_widget(event.widget):
            return
        self.duplicate_selected()
        return "break"

    def _on_ctrl_z(self, event):
        if self._is_text_editing_widget(event.widget):
            return  # Allow default text entry undo
        self.undo()
        return "break"

    def _on_ctrl_y(self, event):
        if self._is_text_editing_widget(event.widget):
            return  # Allow default text entry redo
        self.redo()
        return "break"

    def _on_ctrl_a(self, event):
        if self._is_text_editing_widget(event.widget):
            return  # Allow default text entry select all
        self.select_all_devices()
        return "break"

    def _on_delete_key(self, event):
        if self._is_text_editing_widget(event.widget):
            return  # Allow text deletion
        self.delete_selected()
        return "break"

    # -------------------------------------------------------------------------
    # Layout 3: Main Workspace Split (Palette | Logical Canvas | Inspector)
    # -------------------------------------------------------------------------
    def _build_main_workspace(self):
        pane = ttk.Panedwindow(self.root, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=4)

        # 1. Left Sidebar: Device Palette
        left = ttk.Frame(pane, width=220)
        pane.add(left, weight=1)

        # 2. Centre: Cisco Packet Tracer Logical Workspace
        center = ttk.Frame(pane, width=760)
        pane.add(center, weight=4)

        # 3. Right: Device & Link Inspector
        right = ttk.Frame(pane, width=380)
        pane.add(right, weight=2)

        self._build_device_palette(left)
        self._build_center_workspace(center)
        self._build_right_inspector(right)

    # -------------------------------------------------------------------------
    # Component: Left Sidebar (Network Device Palette)
    # -------------------------------------------------------------------------
    def _build_device_palette(self, parent):
        box = ttk.LabelFrame(parent, text="Network Device Palette", padding=6)
        box.pack(fill="both", expand=True, padx=2, pady=2)

        ttk.Label(box, text="Click to place or equip device:", font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(0, 4))

        # Device Palette Definitions (Requirement 2 & 8)
        # Category definitions: Routers (Green), Switches (Amber), PCs & Laptops (Blue), Servers (Purple)
        palette_items = [
            ("Router", "Routers", "⟲ Router", "Cisco 2911 ISR", self.c_router, "#dcfce7"),
            ("Switch", "Switches", "⇄ Switch", "Cisco Catalyst 2960", self.c_switch, "#fef3c7"),
            ("PC", "End Devices", "🖥 PC", "Desktop Workstation", self.c_end_device, "#dbeafe"),
            ("Laptop", "End Devices", "💻 Laptop", "Mobile Workstation", self.c_end_device, "#e0f2fe"),
            ("Server", "End Devices", "🖳 Server", "Enterprise Server", self.c_server, "#f3e8ff")
        ]

        for dtype, cat, icon_label, desc, color, bg_tint in palette_items:
            card = tk.Frame(box, bg=bg_tint, bd=1, relief="solid", highlightbackground=color, highlightthickness=1)
            card.pack(fill="x", pady=3)

            top_row = tk.Frame(card, bg=bg_tint)
            top_row.pack(fill="x", padx=4, pady=2)
            tk.Label(top_row, text=icon_label, font=("Segoe UI", 9, "bold"), bg=bg_tint, fg=color).pack(side="left")
            tk.Label(top_row, text=f"[{cat}]", font=("Segoe UI", 7), bg=bg_tint, fg="#64748b").pack(side="right")

            tk.Label(card, text=desc, font=("Segoe UI", 8), bg=bg_tint, fg="#334155").pack(anchor="w", padx=4)

            btn = tk.Button(
                card, text=f"+ Add {dtype}", font=("Segoe UI", 8, "bold"),
                bg=color, fg="#ffffff", relief="flat", cursor="hand2", padx=4, pady=2,
                command=lambda dt=dtype: self.add_device_from_palette(dt)
            )
            btn.pack(fill="x", padx=4, pady=3)

        # Quick Palette Tools
        t_box = ttk.LabelFrame(box, text="Palette Tools", padding=4)
        t_box.pack(fill="x", pady=(8, 2))
        ttk.Button(t_box, text="+ Custom Device Dialog", command=self.open_add_device_dialog).pack(fill="x", pady=1)
        ttk.Button(t_box, text="+ Cable Connect Dialog", command=self.open_connect_dialog).pack(fill="x", pady=1)

        # Topology Statistics Box
        self.stats_lbl = ttk.Label(box, text="Devices: 5 | Links: 5", font=("Segoe UI", 8, "bold"))
        self.stats_lbl.pack(side="bottom", anchor="w", pady=4)

    def add_device_from_palette(self, device_type):
        """Add device with auto-generated unique name (Requirement 2)."""
        self.record_undo_state(f"Add {device_type}")
        name = generate_unique_device_name(self.g, device_type)
        # Position intelligently in workspace viewport
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        cx = (xlim[0] + xlim[1]) / 2.0
        cy = (ylim[0] + ylim[1]) / 2.0
        # Jitter slightly based on existing count
        count = self.g.number_of_nodes()
        angle = count * 0.75
        radius = 0.5 + (count % 3) * 0.25
        px = round(cx + radius * math.cos(angle), 2)
        py = round(cy + radius * math.sin(angle), 2)

        add_device(self.g, name, device_type=device_type, pos=(px, py))
        self.node_pos[name] = (px, py)
        self.selected_node = name
        self.selected_nodes = [name]
        self.selected_link = None
        self.log_event(f"Added new device '{name}' ({device_type}) at position ({px}, {py}).")
        self.refresh_endpoint_selectors()
        self.update_inventory()
        self.select_device_for_inspection(name)
        self.draw()

    # -------------------------------------------------------------------------
    # Component: Centre (Interactive Logical Workspace & KPI Dashboard)
    # -------------------------------------------------------------------------
    def _build_center_workspace(self, parent):
        self._build_kpi_dashboard(parent)
        top_box = ttk.LabelFrame(parent, text="Logical Workspace (Cisco Packet Tracer Environment)", padding=2)
        top_box.pack(fill="both", expand=True, padx=2, pady=2)

        self.fig = Figure(figsize=(7.5, 4.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=top_box)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_kpi_dashboard(self, parent):
        """Build real-time 8-card Network Management KPI dashboard bar."""
        self.kpi_bar = tk.Frame(parent, bg="#0f172a", height=52)
        self.kpi_bar.pack(fill="x", padx=2, pady=(1, 3))

        self.kpi_labels = {}
        cards_def = [
            ("dev", "DEVICES", "5", "Nodes"),
            ("links", "LINKS", "5", "Connections"),
            ("faults", "FAULTS", "0", "Active"),
            ("crit", "CRITICAL", "0", "Outages"),
            ("avail", "AVAILABILITY", "AVAILABLE", "Transport"),
            ("health", "HEALTH", "HEALTHY", "Telemetry"),
            ("route", "ACTIVE ROUTE", "PC1 -> R1 -> R2 -> Server", "Forwarding"),
            ("status", "RECOVERY", "NOMINAL", "Last Status")
        ]

        for cid, title, default_val, sub in cards_def:
            card = tk.Frame(self.kpi_bar, bg="#1e293b", bd=1, relief="solid")
            card.pack(side="left", fill="both", expand=True, padx=2, pady=2)

            t_lbl = tk.Label(card, text=title, bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 7, "bold"))
            t_lbl.pack(anchor="w", padx=4, pady=(2, 0))

            v_lbl = tk.Label(card, text=default_val, bg="#1e293b", fg="#ffffff", font=("Segoe UI", 9, "bold"), anchor="w")
            v_lbl.pack(anchor="w", padx=4, pady=0)

            s_lbl = tk.Label(card, text=sub, bg="#1e293b", fg="#64748b", font=("Segoe UI", 7), anchor="w")
            s_lbl.pack(anchor="w", padx=4, pady=(0, 2))

            self.kpi_labels[cid] = (v_lbl, s_lbl)

    # -------------------------------------------------------------------------
    # Component: Right Sidebar (Inspector: Device, Link, Network Overview)
    # -------------------------------------------------------------------------
    def _build_right_inspector(self, parent):
        self.insp_tabs = ttk.Notebook(parent)
        self.insp_tabs.pack(fill="both", expand=True, padx=2, pady=2)

        # Tab 1: Device Configuration Inspector (Requirement 5)
        tab_dev = ttk.Frame(self.insp_tabs, padding=4)
        self.insp_tabs.add(tab_dev, text="Device Config")

        self.insp_dev_name = tk.StringVar()
        self.insp_dev_type = tk.StringVar()
        self.insp_dev_ip = tk.StringVar()
        self.insp_dev_mask = tk.StringVar()
        self.insp_dev_gw = tk.StringVar()
        self.insp_dev_dns = tk.StringVar()

        form_d = ttk.Frame(tab_dev)
        form_d.pack(fill="x", pady=2)

        ttk.Label(form_d, text="Device Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.dev_select_combo = ttk.Combobox(form_d, textvariable=self.insp_dev_name, state="readonly", width=18)
        self.dev_select_combo.grid(row=0, column=1, padx=4, pady=2)
        self.dev_select_combo.bind("<<ComboboxSelected>>", lambda e: self.select_device_for_inspection(self.insp_dev_name.get()))

        ttk.Label(form_d, text="Device Type:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Combobox(form_d, textvariable=self.insp_dev_type, values=DEVICE_TYPES, state="readonly", width=18).grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(form_d, text="IP Address:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(form_d, textvariable=self.insp_dev_ip, width=20).grid(row=2, column=1, padx=4, pady=2)

        ttk.Label(form_d, text="Subnet Mask:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(form_d, textvariable=self.insp_dev_mask, width=20).grid(row=3, column=1, padx=4, pady=2)

        ttk.Label(form_d, text="Default Gateway:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(form_d, textvariable=self.insp_dev_gw, width=20).grid(row=4, column=1, padx=4, pady=2)

        ttk.Label(form_d, text="DNS Server:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(form_d, textvariable=self.insp_dev_dns, width=20).grid(row=5, column=1, padx=4, pady=2)

        d_btns = ttk.Frame(tab_dev)
        d_btns.pack(fill="x", pady=6)
        ttk.Button(d_btns, text="💾 Apply Device Changes", style="Primary.TButton", command=self.apply_device_inspection_changes).pack(fill="x", pady=2)
        ttk.Button(d_btns, text="✖ Delete Selected Device", style="Danger.TButton", command=self.delete_selected_device).pack(fill="x", pady=2)

        # Tab 2: Link Configuration Inspector (Requirement 4)
        tab_link = ttk.Frame(self.insp_tabs, padding=4)
        self.insp_tabs.add(tab_link, text="Link Config")

        self.insp_link_label = tk.StringVar()
        self.insp_link_cost = tk.StringVar()
        self.insp_link_lat = tk.StringVar()
        self.insp_link_loss = tk.StringVar()
        self.insp_link_st = tk.StringVar()
        self.insp_link_type = tk.StringVar()

        form_l = ttk.Frame(tab_link)
        form_l.pack(fill="x", pady=2)

        ttk.Label(form_l, text="Selected Link:").grid(row=0, column=0, sticky="w", pady=2)
        self.link_select_combo = ttk.Combobox(form_l, textvariable=self.insp_link_label, state="readonly", width=18)
        self.link_select_combo.grid(row=0, column=1, padx=4, pady=2)
        self.link_select_combo.bind("<<ComboboxSelected>>", lambda e: self.on_link_combo_selected())

        ttk.Label(form_l, text="Link Cost:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(form_l, textvariable=self.insp_link_cost, width=20).grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(form_l, text="Latency (ms):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(form_l, textvariable=self.insp_link_lat, width=20).grid(row=2, column=1, padx=4, pady=2)

        ttk.Label(form_l, text="Packet Loss (%):").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(form_l, textvariable=self.insp_link_loss, width=20).grid(row=3, column=1, padx=4, pady=2)

        ttk.Label(form_l, text="Status:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Combobox(form_l, textvariable=self.insp_link_st, values=["UP", "DOWN"], state="readonly", width=18).grid(row=4, column=1, padx=4, pady=2)

        ttk.Label(form_l, text="Cable Type:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Combobox(form_l, textvariable=self.insp_link_type, values=CONNECTION_TYPES, state="readonly", width=18).grid(row=5, column=1, padx=4, pady=2)

        l_btns = ttk.Frame(tab_link)
        l_btns.pack(fill="x", pady=6)
        ttk.Button(l_btns, text="💾 Apply Link Changes", style="Primary.TButton", command=self.apply_link_inspection_changes).pack(fill="x", pady=2)
        ttk.Button(l_btns, text="✖ Disconnect Link", style="Danger.TButton", command=self.disconnect_selected_link).pack(fill="x", pady=2)

        # Tab 3: Network Topology Overview & Tables
        tab_ov = ttk.Frame(self.insp_tabs, padding=4)
        self.insp_tabs.add(tab_ov, text="Overview")

        # Path Endpoints Box
        ep_box = ttk.LabelFrame(tab_ov, text="Route Endpoints Selection", padding=4)
        ep_box.pack(fill="x", pady=2)
        ep_f = ttk.Frame(ep_box)
        ep_f.pack(fill="x")
        ttk.Label(ep_f, text="Source:").grid(row=0, column=0, sticky="w")
        self.source_choice = tk.StringVar(value="PC1")
        self.source_combo = ttk.Combobox(ep_f, textvariable=self.source_choice, state="readonly", width=8)
        self.source_combo.grid(row=0, column=1, padx=2)
        self.source_combo.bind("<<ComboboxSelected>>", lambda e: self.on_endpoint_changed())

        ttk.Label(ep_f, text="Target:").grid(row=0, column=2, sticky="w")
        self.target_choice = tk.StringVar(value="Server")
        self.target_combo = ttk.Combobox(ep_f, textvariable=self.target_choice, state="readonly", width=8)
        self.target_combo.grid(row=0, column=3, padx=2)
        self.target_combo.bind("<<ComboboxSelected>>", lambda e: self.on_endpoint_changed())

        # Device Inventory
        ttk.Label(tab_ov, text="Device Table:", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 1))
        self.dev_tree = ttk.Treeview(tab_ov, columns=("Name", "Type", "IP"), show="headings", height=4)
        for col, w in [("Name", 60), ("Type", 60), ("IP", 90)]:
            self.dev_tree.heading(col, text=col)
            self.dev_tree.column(col, width=w, anchor="center")
        self.dev_tree.pack(fill="x", pady=1)

        # Link Inventory
        ttk.Label(tab_ov, text="Link Table:", font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(4, 1))
        self.link_tree = ttk.Treeview(tab_ov, columns=("Link", "Status", "Lat", "Loss"), show="headings", height=4)
        for col, w in [("Link", 80), ("Status", 45), ("Lat", 50), ("Loss", 45)]:
            self.link_tree.heading(col, text=col)
            self.link_tree.column(col, width=w, anchor="center")
        self.link_tree.pack(fill="both", expand=True, pady=1)

        # Tab 4: Multi-Fault Scenario Builder
        self._build_multi_fault_tab()

        # Tab 5: Active Fault Registry
        self._build_active_faults_tab()

    # -------------------------------------------------------------------------
    # Layout 4: Bottom Panel (Dockable Simulation Output & Event Log)
    # -------------------------------------------------------------------------
    def _build_bottom_panel(self):
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill="x", side="bottom", padx=6, pady=(0, 4))

        self.bottom_tabs = ttk.Notebook(bottom_frame)
        self.bottom_tabs.pack(fill="x", expand=True)

        # Tab 1: Simulation & Independent Diagnosis (Requirement 6)
        tab_diag = ttk.Frame(self.bottom_tabs, padding=4)
        self.bottom_tabs.add(tab_diag, text="🩺 Diagnosis & Telemetry")

        d_frame = ttk.Frame(tab_diag)
        d_frame.pack(fill="both", expand=True)
        self.output_diag = tk.Text(d_frame, height=5, wrap="word", font=("Consolas", 8), bg="#ffffff")
        d_scroll = ttk.Scrollbar(d_frame, orient="vertical", command=self.output_diag.yview)
        self.output_diag.configure(yscrollcommand=d_scroll.set)
        d_scroll.pack(side="right", fill="y")
        self.output_diag.pack(side="left", fill="both", expand=True)

        # Tab 2: Recovery & Verification (Requirement 6)
        tab_rec = ttk.Frame(self.bottom_tabs, padding=4)
        self.bottom_tabs.add(tab_rec, text="🛡 Recovery & Verification")

        r_frame = ttk.Frame(tab_rec)
        r_frame.pack(fill="both", expand=True)
        self.output_rec = tk.Text(r_frame, height=5, wrap="word", font=("Consolas", 8), bg="#ffffff")
        r_scroll = ttk.Scrollbar(r_frame, orient="vertical", command=self.output_rec.yview)
        self.output_rec.configure(yscrollcommand=r_scroll.set)
        r_scroll.pack(side="right", fill="y")
        self.output_rec.pack(side="left", fill="both", expand=True)

        # Tab 3: Multiple-Route Discovery Matrix (Requirement 6)
        tab_routes = ttk.Frame(self.bottom_tabs, padding=4)
        self.bottom_tabs.add(tab_routes, text="🔀 Multi-Route Matrix")

        columns = ("Path", "Cost", "Latency", "Loss", "Availability", "Selected")
        self.route_tree = ttk.Treeview(tab_routes, columns=columns, show="headings", height=3)
        col_widths = [("Path", 260), ("Cost", 45), ("Latency", 70), ("Loss", 65), ("Availability", 85), ("Selected", 80)]
        for col, w in col_widths:
            self.route_tree.heading(col, text=col)
            self.route_tree.column(col, width=w, anchor="center")
        self.route_tree.column("Path", anchor="w")
        self.route_tree.pack(fill="x", pady=1)

        exp_frame = tk.Frame(tab_routes, bg="#e2e8f0", bd=1, relief="solid")
        exp_frame.pack(fill="x", pady=(1, 0))
        tk.Label(exp_frame, text="SELECTION DECISION:", bg="#e2e8f0", fg=self.c_cisco_dark, font=("Segoe UI", 8, "bold")).pack(side="left", padx=4, pady=1)
        self.explanation_label = tk.Label(exp_frame, text="Evaluating routes...", bg="#e2e8f0", fg="#1e293b", font=("Segoe UI", 8), anchor="w", wraplength=700, justify="left")
        self.explanation_label.pack(side="left", fill="x", expand=True, padx=4, pady=1)
        exp_frame.bind("<Configure>", lambda e: self.explanation_label.config(wraplength=max(200, e.width - 160)))

        # Tab 4: Performance Metrics Table
        tab_perf = ttk.Frame(self.bottom_tabs, padding=4)
        self.bottom_tabs.add(tab_perf, text="📊 Performance")

        p_frame = ttk.Frame(tab_perf)
        p_frame.pack(fill="both", expand=True)
        self.metrics_text = tk.Text(p_frame, height=5, wrap="word", font=("Consolas", 8), bg="#ffffff")
        p_scroll = ttk.Scrollbar(p_frame, orient="vertical", command=self.metrics_text.yview)
        self.metrics_text.configure(yscrollcommand=p_scroll.set)
        p_scroll.pack(side="right", fill="y")
        self.metrics_text.pack(side="left", fill="both", expand=True)

        # Tab 5: Event Audit Log
        tab_log = ttk.Frame(self.bottom_tabs, padding=4)
        self.bottom_tabs.add(tab_log, text="📋 Event Log")

        log_frame = ttk.Frame(tab_log)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=5, font=("Consolas", 8), bg="#ffffff")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        # Tab 6: Global Recovery Planner
        self._build_recovery_planner_tab()

        # Tab 7: Audit History & Analytics
        self._build_audit_tab()

    def _build_multi_fault_tab(self):
        tab_mf = ttk.Frame(self.insp_tabs, padding=4)
        self.insp_tabs.add(tab_mf, text="Multi-Fault")

        # Section 1: Predefined Scenarios
        p_box = ttk.LabelFrame(tab_mf, text="Predefined Multi-Fault Scenarios", padding=4)
        p_box.pack(fill="x", pady=2)

        self.predef_var = tk.StringVar(value=list(PREDEFINED_SCENARIOS.keys())[0])
        predef_combo = ttk.Combobox(
            p_box, textvariable=self.predef_var,
            values=list(PREDEFINED_SCENARIOS.keys()),
            state="readonly", width=22
        )
        predef_combo.pack(fill="x", pady=2)
        predef_combo.bind("<<ComboboxSelected>>", self._on_predef_scenario_selected)

        first_items = PREDEFINED_SCENARIOS[self.predef_var.get()]
        first_desc = f"{len(first_items)} faults: " + ", ".join(f.get("fault_type", "fault") for f in first_items)
        self.predef_desc_lbl = tk.Label(
            p_box, text=first_desc,
            bg=self.c_panel_bg, fg="#475569", font=("Segoe UI", 7),
            wraplength=200, justify="left", anchor="w"
        )
        self.predef_desc_lbl.pack(fill="x", pady=2)

        ttk.Button(
            p_box, text="⚡ Inject Predefined Batch", style="Danger.TButton",
            command=self.inject_predefined_scenario
        ).pack(fill="x", pady=2)

        # Section 2: Custom Multi-Fault Batch Builder
        b_box = ttk.LabelFrame(tab_mf, text="Custom Scenario Builder", padding=4)
        b_box.pack(fill="both", expand=True, pady=2)

        f_type_frame = ttk.Frame(b_box)
        f_type_frame.pack(fill="x", pady=1)
        ttk.Label(f_type_frame, text="Type:").pack(side="left")
        self.custom_type_var = tk.StringVar(value="Link failure")
        type_combo = ttk.Combobox(
            f_type_frame, textvariable=self.custom_type_var,
            values=["Link failure", "Incorrect default gateway", "DNS service failure", "High latency", "Packet loss"],
            state="readonly", width=16
        )
        type_combo.pack(side="right", fill="x", expand=True, padx=(4, 0))
        type_combo.bind("<<ComboboxSelected>>", self._on_custom_type_selected)

        f_target_frame = ttk.Frame(b_box)
        f_target_frame.pack(fill="x", pady=1)
        ttk.Label(f_target_frame, text="Target:").pack(side="left")
        self.custom_target_var = tk.StringVar()
        self.custom_target_combo = ttk.Combobox(
            f_target_frame, textvariable=self.custom_target_var,
            state="readonly", width=16
        )
        self.custom_target_combo.pack(side="right", fill="x", expand=True, padx=(4, 0))

        f_param_frame = ttk.Frame(b_box)
        f_param_frame.pack(fill="x", pady=1)
        ttk.Label(f_param_frame, text="Param:").pack(side="left")
        self.custom_param_var = tk.StringVar()
        ttk.Entry(f_param_frame, textvariable=self.custom_param_var, width=16).pack(side="right", fill="x", expand=True, padx=(4, 0))

        btn_row = ttk.Frame(b_box)
        btn_row.pack(fill="x", pady=2)
        ttk.Button(btn_row, text="➕ Add", command=self.add_custom_fault_to_batch).pack(side="left", fill="x", expand=True, padx=1)
        ttk.Button(btn_row, text="➖ Remove", command=self.remove_custom_batch_item).pack(side="right", fill="x", expand=True, padx=1)

        self.custom_batch_listbox = tk.Listbox(b_box, height=3, font=("Segoe UI", 7), bg="#ffffff")
        self.custom_batch_listbox.pack(fill="both", expand=True, pady=2)

        ttk.Button(b_box, text="⚡ Inject Custom Batch", style="Danger.TButton", command=self.inject_custom_batch).pack(fill="x", pady=1)
        ttk.Button(b_box, text="🔄 Clear All Faults", style="Primary.TButton", command=self.clear_all_registered_faults).pack(fill="x", pady=1)

        self._refresh_custom_target_options()

    def _build_active_faults_tab(self):
        tab_af = ttk.Frame(self.insp_tabs, padding=4)
        self.insp_tabs.add(tab_af, text="Active Faults")

        self.active_faults_tree = ttk.Treeview(
            tab_af, columns=("ID", "Type", "Target", "Status", "Severity"), show="headings", height=8
        )
        for col, w in [("ID", 65), ("Type", 85), ("Target", 65), ("Status", 55), ("Severity", 55)]:
            self.active_faults_tree.heading(col, text=col)
            self.active_faults_tree.column(col, width=w, anchor="center")
        self.active_faults_tree.pack(fill="both", expand=True, pady=2)

        btn_f = ttk.Frame(tab_af)
        btn_f.pack(fill="x", pady=4)
        ttk.Button(btn_f, text="Resolve Selected", style="Primary.TButton", command=self.resolve_selected_fault).pack(fill="x", pady=1)
        ttk.Button(btn_f, text="Clear All Registered", style="Danger.TButton", command=self.clear_all_registered_faults).pack(fill="x", pady=1)
        ttk.Button(btn_f, text="Refresh View", command=self.refresh_active_faults_view).pack(fill="x", pady=1)

    def _build_recovery_planner_tab(self):
        tab_plan = ttk.Frame(self.bottom_tabs, padding=4)
        self.bottom_tabs.add(tab_plan, text="📐 Recovery Planner")

        top_f = ttk.Frame(tab_plan)
        top_f.pack(fill="x", pady=(0, 2))
        self.plan_decision_lbl = tk.Label(
            top_f, text="Pre-Execution Recovery Plan: No plan generated yet.",
            bg="#e2e8f0", fg=self.c_cisco_dark, font=("Segoe UI", 8, "bold"), anchor="w", padx=6, pady=2
        )
        self.plan_decision_lbl.pack(side="left", fill="x", expand=True)

        ttk.Button(top_f, text="⚡ Execute Coordinated Recovery", style="Success.TButton", command=self.recover).pack(side="right", padx=4)

        split = ttk.PanedWindow(tab_plan, orient="horizontal")
        split.pack(fill="both", expand=True)

        left_f = ttk.Frame(split)
        right_f = ttk.Frame(split)
        split.add(left_f, weight=3)
        split.add(right_f, weight=2)

        ttk.Label(left_f, text="Multi-Objective Candidate Route Ranking:", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        cols_r = ("Rank", "Path", "Cost", "Latency", "Loss", "Score", "Status")
        self.plan_routes_tree = ttk.Treeview(left_f, columns=cols_r, show="headings", height=4)
        for col, w in [("Rank", 40), ("Path", 170), ("Cost", 40), ("Latency", 55), ("Loss", 50), ("Score", 50), ("Status", 65)]:
            self.plan_routes_tree.heading(col, text=col)
            self.plan_routes_tree.column(col, width=w, anchor="center")
        self.plan_routes_tree.column("Path", anchor="w")
        self.plan_routes_tree.pack(fill="both", expand=True)

        ttk.Label(right_f, text="Planned Corrective Action Sequence:", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        cols_a = ("ID", "Priority", "Action Type", "Target", "Expected Result")
        self.plan_actions_tree = ttk.Treeview(right_f, columns=cols_a, show="headings", height=4)
        for col, w in [("ID", 60), ("Priority", 50), ("Action Type", 100), ("Target", 65), ("Expected Result", 160)]:
            self.plan_actions_tree.heading(col, text=col)
            self.plan_actions_tree.column(col, width=w, anchor="center")
        self.plan_actions_tree.pack(fill="both", expand=True)

    def _build_audit_tab(self):
        tab_audit = ttk.Frame(self.bottom_tabs, padding=4)
        self.bottom_tabs.add(tab_audit, text="📜 Audit & Analytics")

        self.audit_summary_frame = tk.Frame(tab_audit, bg="#1e293b", bd=1, relief="solid")
        self.audit_summary_frame.pack(fill="x", pady=(0, 3))
        self.audit_summary_lbl = tk.Label(
            self.audit_summary_frame,
            text="Analytics: Total Runs: 0 | Verified: 0 (0.0%) | Service Maintained: 0 | Actions Executed: 0 | Rollbacks: 0 | Fallbacks: 0",
            bg="#1e293b", fg="#e2e8f0", font=("Segoe UI", 8, "bold"), padx=6, pady=3, anchor="w"
        )
        self.audit_summary_lbl.pack(fill="x")

        cols_aud = ("Audit ID", "Execution ID", "Timestamp", "Scenario", "Status", "Availability", "Health", "Verified", "Actions", "Lat Δ", "Loss Δ")
        self.audit_tree = ttk.Treeview(tab_audit, columns=cols_aud, show="headings", height=4)
        for col, w in [
            ("Audit ID", 65), ("Execution ID", 75), ("Timestamp", 120), ("Scenario", 110),
            ("Status", 110), ("Availability", 75), ("Health", 65), ("Verified", 55),
            ("Actions", 50), ("Lat Δ", 50), ("Loss Δ", 50)
        ]:
            self.audit_tree.heading(col, text=col)
            self.audit_tree.column(col, width=w, anchor="center")
        self.audit_tree.pack(fill="both", expand=True)

        b_bar = ttk.Frame(tab_audit)
        b_bar.pack(fill="x", pady=(2, 0))
        ttk.Button(b_bar, text="📥 Export Audit Log (CSV)...", command=self.export_audit_csv).pack(side="left", padx=2)
        ttk.Button(b_bar, text="💾 Export Audit Log (JSON)...", command=self.export_audit_json).pack(side="left", padx=2)
        ttk.Button(b_bar, text="🗑 Clear Audit History", command=self.clear_audit_history).pack(side="left", padx=2)
        ttk.Button(b_bar, text="Refresh Audit View", command=self.refresh_audit_view).pack(side="right", padx=2)

    def _on_predef_scenario_selected(self, event=None):
        name = self.predef_var.get()
        sc_items = PREDEFINED_SCENARIOS.get(name, [])
        desc = f"{len(sc_items)} faults: " + ", ".join(f.get("fault_type", "Fault") for f in sc_items)
        self.predef_desc_lbl.config(text=desc)

    def _on_custom_type_selected(self, event=None):
        self._refresh_custom_target_options()

    def _refresh_custom_target_options(self):
        ft = self.custom_type_var.get()
        if ft in ("Link failure", "High latency", "Packet loss"):
            labels = self.get_topology_link_labels()
            self.custom_target_combo["values"] = labels
            if labels and self.custom_target_var.get() not in labels:
                self.custom_target_var.set(labels[0])
        elif ft == "Incorrect default gateway":
            pcs = [n for n, d in self.g.nodes(data=True) if d.get("type") in ("PC", "Laptop")]
            self.custom_target_combo["values"] = pcs
            if pcs and self.custom_target_var.get() not in pcs:
                self.custom_target_var.set(pcs[0])
        elif ft == "DNS service failure":
            self.custom_target_combo["values"] = ["DNS Service"]
            self.custom_target_var.set("DNS Service")

    def add_custom_fault_to_batch(self):
        ft = self.custom_type_var.get()
        tgt = self.custom_target_var.get()
        param = self.custom_param_var.get()

        spec = {"fault_type": ft}
        if ft in ("Link failure", "High latency", "Packet loss"):
            u, v = parse_link_endpoints(tgt)
            if not (u and v):
                messagebox.showerror("Invalid Target", f"Invalid target link: '{tgt}'.")
                return
            spec["target"] = (u, v)
            if ft == "High latency":
                try:
                    spec["parameters"] = {"latency_ms": float(param) if param else 250.0}
                except ValueError:
                    spec["parameters"] = {"latency_ms": 250.0}
            elif ft == "Packet loss":
                try:
                    spec["parameters"] = {"packet_loss": float(param) if param else 30.0}
                except ValueError:
                    spec["parameters"] = {"packet_loss": 30.0}
        elif ft == "Incorrect default gateway":
            spec["target"] = tgt or "PC1"
            spec["parameters"] = {"gateway": param if param else "192.168.1.99"}
        elif ft == "DNS service failure":
            spec["target"] = "DNS Service"
            spec["parameters"] = {"dns_available": False}

        self.custom_fault_batch.append(spec)
        disp_str = f"[{ft}] Target: {spec['target']} Params: {spec.get('parameters', {})}"
        self.custom_batch_listbox.insert(tk.END, disp_str)
        self.log_event(f"Added fault to custom batch: {disp_str}")

    def remove_custom_batch_item(self):
        sel = self.custom_batch_listbox.curselection()
        if sel:
            idx = sel[0]
            self.custom_batch_listbox.delete(idx)
            del self.custom_fault_batch[idx]

    def inject_predefined_scenario(self):
        name = self.predef_var.get()
        batch = PREDEFINED_SCENARIOS.get(name)
        if not batch:
            return
        res = inject_fault_batch(self.g, batch, scenario_name=name)
        if not res.get("success"):
            messagebox.showerror("Batch Injection Error", f"Batch injection failed: {res.get('details')}")
            return
        records = res.get("applied_faults", [])

        self.draw()
        self.update_route_comparison()
        self.update_inventory()
        self.update_kpi_dashboard()
        self.refresh_active_faults_view()
        self.log_event(f"Injected predefined multi-fault scenario: '{name}' ({len(records)} faults registered).")
        messagebox.showinfo("Multi-Fault Injection", f"Successfully injected predefined scenario:\n'{name}'\n({len(records)} faults active).")

    def inject_custom_batch(self):
        if not self.custom_fault_batch:
            messagebox.showwarning("Empty Batch", "No faults added to custom batch.")
            return

        res = inject_fault_batch(self.g, self.custom_fault_batch, scenario_name="Custom Batch")
        if not res.get("success"):
            messagebox.showerror("Batch Injection Error", f"Batch injection failed: {res.get('details')}")
            return
        records = res.get("applied_faults", [])

        self.draw()
        self.update_route_comparison()
        self.update_inventory()
        self.update_kpi_dashboard()
        self.refresh_active_faults_view()
        self.log_event(f"Injected custom multi-fault batch ({len(records)} faults registered).")
        messagebox.showinfo("Custom Batch Injection", f"Successfully injected {len(records)} faults into network.")

    def clear_all_registered_faults(self):
        reg = get_fault_registry(self.g)
        reg.clear_all(self.g)
        self.custom_fault_batch.clear()
        self.custom_batch_listbox.delete(0, tk.END)
        self.last_recovery_status = "NOMINAL"
        self.last_recovery_service_availability = "AVAILABLE"
        self.last_recovery_network_health = "HEALTHY"
        self.draw()
        self.update_route_comparison()
        self.update_inventory()
        self.update_kpi_dashboard()
        self.refresh_active_faults_view()
        self.log_event("Cleared all registered faults; restored healthy baseline.")
        messagebox.showinfo("Faults Cleared", "All active faults cleared from registry and topology.")

    def resolve_selected_fault(self):
        sel = self.active_faults_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a fault from the table to resolve.")
            return
        item = self.active_faults_tree.item(sel[0])
        fid = item["values"][0]
        reg = get_fault_registry(self.g)
        rec = reg.get_fault(fid)
        if rec:
            from fault_injection import clear_fault_instance
            clear_fault_instance(self.g, rec)
            self.draw()
            self.update_route_comparison()
            self.update_inventory()
            self.update_kpi_dashboard()
            self.refresh_active_faults_view()
            self.log_event(f"Resolved fault instance {fid} ({rec.fault_type}).")

    def refresh_active_faults_view(self):
        if not hasattr(self, "active_faults_tree"):
            return
        for item in self.active_faults_tree.get_children():
            self.active_faults_tree.delete(item)

        reg = get_fault_registry(self.g)
        for f in reg.get_active_faults():
            tgt = getattr(f, "affected_component", getattr(f, "target", "N/A"))
            tgt_str = f"{tgt[0]}-{tgt[1]}" if isinstance(tgt, (list, tuple)) else str(tgt)
            ft = getattr(f, "fault_type", "Fault")
            st = f.status.value if hasattr(f.status, "value") else str(f.status)
            sev = getattr(f, "severity", "HIGH")
            self.active_faults_tree.insert("", tk.END, values=(
                f.fault_id, ft, tgt_str, st, sev
            ))

    def update_recovery_planner_view(self, plan=None):
        if not hasattr(self, "plan_routes_tree"):
            return

        if plan is None:
            src = self.source_choice.get() if hasattr(self, "source_choice") else "PC1"
            dst = self.target_choice.get() if hasattr(self, "target_choice") else "Server"
            findings = getattr(self, "findings", [])
            plan = generate_recovery_plan(self.g, findings, source=src, target=dst)

        self.plan_decision_lbl.config(
            text=f"Plan [{plan.plan_id}] Decision: {plan.decision} | Policy: {plan.policy_used} | Expected: {plan.expected_outcome}"
        )

        for item in self.plan_routes_tree.get_children():
            self.plan_routes_tree.delete(item)

        for rank, r in enumerate(plan.candidate_routes, 1):
            p_str = " -> ".join(r["path"])
            is_sel = "SELECTED" if plan.selected_route and r["path"] == plan.selected_route["path"] else ("USABLE" if r.get("is_usable") else "DOWN")
            score = r.get("score", "N/A")
            self.plan_routes_tree.insert("", tk.END, values=(
                rank, p_str, r.get("cost", 1), f"{r.get('latency_ms', 0):.1f}ms", f"{r.get('probabilistic_loss', r.get('max_loss', 0)):.1f}%", score, is_sel
            ))

        for item in self.plan_actions_tree.get_children():
            self.plan_actions_tree.delete(item)

        for act in plan.actions:
            tgt_str = str(act.target_component)
            self.plan_actions_tree.insert("", tk.END, values=(
                act.action_id, act.priority, act.action_type, tgt_str, act.expected_result
            ))

    def refresh_audit_view(self):
        if not hasattr(self, "audit_tree"):
            return

        for item in self.audit_tree.get_children():
            self.audit_tree.delete(item)

        logger = get_audit_logger()
        analytics = logger.compute_analytics()

        self.audit_summary_lbl.config(
            text=f"Analytics: Total Runs: {analytics['total_runs']} | Verified: {analytics['verified_count']} ({analytics['success_rate_pct']}%) | Maintained: {analytics['service_maintained_count']} | Actions: {analytics['total_actions_executed']} | Rollbacks: {analytics['rollbacks_count']} | Fallbacks: {analytics['fallbacks_count']} | Avg Lat Δ: {analytics['avg_latency_delta_ms']}ms | Avg Loss Δ: {analytics['avg_loss_delta_pct']}%"
        )

        for r in logger.get_all_records():
            self.audit_tree.insert("", tk.END, values=(
                r.audit_id, r.execution_id, r.timestamp_iso, r.scenario_id,
                r.recovery_status, r.service_availability, r.network_health,
                "PASS" if r.verification_passed else "FAIL",
                r.actions_count, f"{r.latency_delta_ms:+.1f}", f"{r.loss_delta_pct:+.1f}%"
            ))

    def export_audit_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Recovery Audit Log to CSV"
        )
        if filepath:
            get_audit_logger().export_to_csv(filepath)
            messagebox.showinfo("Export Successful", f"Audit log exported to:\n{filepath}")

    def export_audit_json(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Recovery Audit Log to JSON"
        )
        if filepath:
            get_audit_logger().export_to_json(filepath)
            messagebox.showinfo("Export Successful", f"Audit log exported to:\n{filepath}")

    def clear_audit_history(self):
        if messagebox.askyesno("Confirm Clear", "Clear all recovery audit history records?"):
            get_audit_logger().clear()
            self.refresh_audit_view()

    def update_kpi_dashboard(self):
        """Update KPI values and colors based on current network state and registry."""
        if not hasattr(self, "kpi_labels") or not self.kpi_labels:
            return

        reg = get_fault_registry(self.g)
        active_f_cnt = reg.get_active_fault_count()
        crit_f_cnt = len([f for f in reg.get_active_faults() if getattr(f, "severity", "HIGH") == "CRITICAL"])

        self.kpi_labels["dev"][0].config(text=str(self.g.number_of_nodes()))
        self.kpi_labels["links"][0].config(text=str(self.g.number_of_edges()))

        self.kpi_labels["faults"][0].config(
            text=str(active_f_cnt),
            fg="#ef4444" if active_f_cnt > 0 else "#4ade80"
        )
        self.kpi_labels["crit"][0].config(
            text=str(crit_f_cnt),
            fg="#ef4444" if crit_f_cnt > 0 else "#94a3b8"
        )

        avail_str = getattr(self, "last_recovery_service_availability", "AVAILABLE")
        health_str = getattr(self, "last_recovery_network_health", "HEALTHY")
        if active_f_cnt > 0 and not hasattr(self, "last_recovery_network_health"):
            health_str = "DEGRADED"

        self.kpi_labels["avail"][0].config(
            text=avail_str,
            fg="#4ade80" if avail_str == "AVAILABLE" else "#ef4444"
        )
        health_fg = "#4ade80" if health_str == "HEALTHY" else ("#f59e0b" if health_str == "DEGRADED" else "#ef4444")
        self.kpi_labels["health"][0].config(text=health_str, fg=health_fg)

        src = self.source_choice.get() if hasattr(self, "source_choice") else "PC1"
        dst = self.target_choice.get() if hasattr(self, "target_choice") else "Server"
        curr_p = get_active_route(self.g, src, dst)
        route_str = " -> ".join(curr_p) if curr_p else "None"
        if len(route_str) > 28:
            route_str = route_str[:25] + "..."
        self.kpi_labels["route"][0].config(text=route_str)

        status_str = getattr(self, "last_recovery_status", "NOMINAL")
        self.kpi_labels["status"][0].config(text=status_str)

    def open_network_terminal(self):
        from network_terminal import NetworkTerminal
        curr_host = self.selected_node or "PC1"
        self.terminal = NetworkTerminal(self.root, self.g, default_host=curr_host, on_state_change=self.on_terminal_state_change)
        self.log_event("Simulated Network Terminal launched.")

    def on_terminal_state_change(self):
        self.draw()
        self.update_kpi_dashboard()
        self.update_route_comparison()
        self.refresh_active_faults_view()
        self.refresh_audit_view()

    # -------------------------------------------------------------------------
    # Visual Topology Rendering (Packet Tracer Logical Workspace)
    # -------------------------------------------------------------------------
    def draw(self, is_dragging=False, xlim=None, ylim=None):
        self.ax.clear()
        pos = {n: self.get_node_position(n) for n in self.g.nodes}

        # Background and Workspace Grid
        self.ax.set_facecolor(self.c_workspace_bg)
        if self.show_grid:
            self.ax.grid(True, linestyle=":", color=self.c_grid_color, alpha=0.75)
        else:
            self.ax.grid(False)

        # 1. Render Connections (Requirement 8)
        # Green links: Healthy | Red links: Failed (DOWN) | Orange links: Degraded
        if self.g.number_of_edges() > 0:
            for u, v, d in self.g.edges(data=True):
                p1 = pos[u]
                p2 = pos[v]
                status = d.get("status", "UP")
                lat = float(d.get("latency_ms", 2.0))
                loss = float(d.get("packet_loss", 0.0))

                if status != "UP":
                    edge_color = self.c_failed_link
                    line_style = "-"
                    width = 3.0
                elif lat > 100 or loss > 0:
                    edge_color = self.c_degraded_link
                    line_style = "-"
                    width = 2.5
                else:
                    edge_color = self.c_healthy_link
                    line_style = "-"
                    width = 2.5

                # Highlight link if selected
                is_selected_link = (self.selected_link in ((u, v), (v, u)))
                if is_selected_link:
                    # Draw selection glow under line
                    self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=self.c_selection, linewidth=5.5, alpha=0.7, zorder=1)

                # Draw main cable connection line
                self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=edge_color, linestyle=line_style, linewidth=width, zorder=2)

                # Draw interface port dots at endpoints
                self.ax.scatter([p1[0], p2[0]], [p1[1], p2[1]], s=28, color=edge_color, zorder=3, edgecolors="#0f172a", linewidths=0.8)

                # Draw Link Telemetry Label at midpoint (Requirement 8)
                mx = (p1[0] + p2[0]) / 2.0
                my = (p1[1] + p2[1]) / 2.0
                label_text = f"{lat}ms | {loss}%" if status == "UP" else "✖ LINK DOWN"
                badge_bg = "#fee2e2" if status != "UP" else ("#ffedd5" if (lat > 100 or loss > 0) else "#f0fdf4")
                badge_fg = edge_color
                self.ax.text(
                    mx, my, label_text, fontsize=6.8, fontweight="bold", color=badge_fg,
                    ha="center", va="center", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=badge_bg, edgecolor=edge_color, alpha=0.92, linewidth=0.8)
                )

        # 2. Render Cable Tool Connection Source (Active Preview)
        if self.connect_source_node and self.connect_source_node in pos:
            sp = pos[self.connect_source_node]
            # Draw pulsing halo around connection source
            circ = patches.Circle(sp, radius=0.26, fill=False, edgecolor=self.c_cable_active, linewidth=2.5, linestyle="--", zorder=5)
            self.ax.add_patch(circ)

        # 3. Render Devices (Requirement 8)
        # Blue: End devices (PC, Laptop) | Green: Routers | Amber: Switches | Purple: Servers
        if self.g.number_of_nodes() > 0:
            for n, d in self.g.nodes(data=True):
                p = pos[n]
                dtype = d.get("type", "PC")
                if dtype in ("PC", "Laptop"):
                    color = self.c_end_device
                    symbol = "PC" if dtype == "PC" else "LAP"
                elif dtype == "Router":
                    color = self.c_router
                    symbol = "R"
                elif dtype == "Switch":
                    color = self.c_switch
                    symbol = "SW"
                elif dtype == "Server":
                    color = self.c_server
                    symbol = "SRV"
                else:
                    color = "#64748b"
                    symbol = dtype[:3]

                # Selected Device Highlight Ring
                if n == self.selected_node or n in getattr(self, "selected_nodes", []):
                    halo = patches.Circle(p, radius=0.28, fill=False, edgecolor=self.c_selection, linewidth=3.0, zorder=6)
                    self.ax.add_patch(halo)

                # Device Node Body Circle
                node_circle = patches.Circle(p, radius=0.18, facecolor=color, edgecolor="#0f172a", linewidth=1.5, zorder=7)
                self.ax.add_patch(node_circle)

                # Device Glyph / Symbol inside Node
                self.ax.text(p[0], p[1], symbol, fontsize=7.5, fontweight="bold", color="#ffffff", ha="center", va="center", zorder=8)

                # Device Name & IP Beneath Node
                self.ax.text(p[0], p[1] - 0.28, n, fontsize=8.2, fontweight="bold", color="#0f172a", ha="center", va="top", zorder=9)
                ip_str = d.get("ip", "")
                if ip_str:
                    self.ax.text(p[0], p[1] - 0.44, ip_str, fontsize=6.8, color="#475569", ha="center", va="top", zorder=9)

        # Logical Workspace Title Banner
        title_str = (
            f"Cisco Packet Tracer Logical Topology ({self.g.number_of_nodes()} Devices, {self.g.number_of_edges()} Connections)\n"
            f"Green: Healthy Links | Red: Failed Links | Orange: Degraded • Blue: PC/Laptop | Green: Router | Amber: Switch | Purple: Server"
        )
        self.ax.set_title(title_str, fontsize=8.2, color=self.c_cisco_dark, pad=6)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        # Viewport boundaries
        if xlim is not None and ylim is not None:
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
        else:
            comp_xlim, comp_ylim = self.compute_view_limits(pos)
            self.ax.set_xlim(comp_xlim)
            self.ax.set_ylim(comp_ylim)

        if is_dragging:
            self.canvas.draw_idle()
        else:
            self.fig.tight_layout()
            self.canvas.draw()

    # -------------------------------------------------------------------------
    # Mouse Interaction: Select, Move, Connect, Delete, Drag-and-Drop
    # -------------------------------------------------------------------------
    def on_press(self, event):
        if event.inaxes != self.ax or event.button != 1:
            return
        if event.xdata is None or event.ydata is None:
            return

        # Give canvas keyboard focus so Ctrl shortcuts trigger
        try:
            self.canvas.get_tk_widget().focus_set()
        except Exception:
            pass

        # Detect Ctrl key modifier for multiple selection
        is_ctrl = (getattr(event, "key", None) == "control") or (
            hasattr(event, "guiEvent") and bool(event.guiEvent and (event.guiEvent.state & 0x0004))
        )

        # Find closest node within pixel tolerance
        closest_node, node_dist = self._find_closest_node(event.x, event.y)

        # 1. CONNECT TOOL (Cable Connection) - Requirement 4
        if self.current_tool == "connect":
            if closest_node and node_dist <= 38:
                if self.connect_source_node is None:
                    # Select first device
                    self.connect_source_node = closest_node
                    self.status_lbl.config(text=f"Connecting from '{closest_node}'... Click second device to connect.")
                    self.log_event(f"Cable Tool: First device '{closest_node}' selected. Click target device.")
                    self.draw()
                else:
                    # Select second device
                    src = self.connect_source_node
                    dst = closest_node
                    self.connect_source_node = None
                    if src == dst:
                        messagebox.showwarning("Invalid Connection", "Cannot connect a device to itself (self-connections not allowed).")
                    elif self.g.has_edge(src, dst):
                        messagebox.showinfo("Existing Link", f"A connection between '{src}' and '{dst}' already exists.")
                    else:
                        self.record_undo_state(f"Connect {src} <-> {dst}")
                        connect_devices(self.g, src, dst)
                        self.log_event(f"Created connection between '{src}' and '{dst}'.")
                        self.refresh_endpoint_selectors()
                        self.update_inventory()
                        self.update_route_comparison()
                        self.selected_link = (src, dst)
                        self.select_link_for_inspection(src, dst)
                        self.draw()
                        # Open link configuration dialog (Requirement 4)
                        self.open_configure_link_dialog_for(src, dst)
            return

        # 2. DELETE TOOL - Requirement 3
        if self.current_tool == "delete":
            if closest_node and node_dist <= 38:
                self.delete_device_by_name(closest_node)
            else:
                closest_edge = self._find_closest_edge(event.x, event.y)
                if closest_edge:
                    self.delete_link_by_endpoints(closest_edge[0], closest_edge[1])
            return

        # 3. SELECT / MOVE MODE (Default) - Requirement 3, 5 & Multiple Selection
        if closest_node and node_dist <= 38:
            if is_ctrl:
                # Toggle node in multiple selection
                if closest_node in self.selected_nodes:
                    self.selected_nodes.remove(closest_node)
                    if self.selected_node == closest_node:
                        self.selected_node = self.selected_nodes[-1] if self.selected_nodes else None
                else:
                    self.selected_nodes.append(closest_node)
                    self.selected_node = closest_node
                self.selected_link = None
                if self.selected_node:
                    self.select_device_for_inspection(self.selected_node)
                self.draw()
                return

            # Normal click without Ctrl:
            if closest_node not in self.selected_nodes:
                self.selected_nodes = [closest_node]
            self.selected_node = closest_node
            self.selected_link = None
            self.select_device_for_inspection(closest_node)

            # Initiate Drag-and-drop for selected nodes (group drag)
            self.drag_node = closest_node
            self.drag_nodes = list(self.selected_nodes)
            self.drag_start_positions = {n: self.node_pos[n] for n in self.drag_nodes if n in self.node_pos}
            self.is_dragging = True
            curr_pos = self.node_pos[closest_node]
            self.drag_start_pos = curr_pos
            self.drag_offset = (curr_pos[0] - event.xdata, curr_pos[1] - event.ydata)
            self.drag_xlim = self.ax.get_xlim()
            self.drag_ylim = self.ax.get_ylim()
            self.canvas.get_tk_widget().config(cursor="fleur")
            self.draw()
        else:
            # Check if user clicked an edge / link
            closest_edge = self._find_closest_edge(event.x, event.y)
            if closest_edge:
                self.selected_link = closest_edge
                self.selected_node = None
                self.selected_nodes = []
                self.select_link_for_inspection(closest_edge[0], closest_edge[1])
                self.draw()
            else:
                # Clicked empty space
                if not is_ctrl:
                    self.selected_node = None
                    self.selected_nodes = []
                    self.selected_link = None
                if self.current_tool == "move":
                    self.pan_start = (event.xdata, event.ydata)
                    self.canvas.get_tk_widget().config(cursor="fleur")
                self.draw()

    def on_motion(self, event):
        # Handle Node Dragging (supports group or single)
        if self.is_dragging and self.drag_node is not None:
            if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
                return

            target_x = round(event.xdata + self.drag_offset[0], 3)
            target_y = round(event.ydata + self.drag_offset[1], 3)
            dx = target_x - self.drag_start_pos[0]
            dy = target_y - self.drag_start_pos[1]

            if not self.drag_nodes:
                self.drag_nodes = [self.drag_node]
                self.drag_start_positions = {self.drag_node: self.drag_start_pos}

            # Auto-expand viewport margins dynamically
            if self.drag_xlim and self.drag_ylim:
                xmin, xmax = self.drag_xlim
                ymin, ymax = self.drag_ylim
            else:
                xmin, xmax = self.ax.get_xlim()
                ymin, ymax = self.ax.get_ylim()
            margin_x, margin_y = 0.4, 0.3

            for n in self.drag_nodes:
                if n in self.drag_start_positions:
                    orig = self.drag_start_positions[n]
                    nx = round(orig[0] + dx, 3)
                    ny = round(orig[1] + dy, 3)
                    self.node_pos[n] = (nx, ny)
                    self.g.graph.setdefault("node_positions", {})[n] = (nx, ny)
                    if nx < xmin + margin_x:
                        xmin = nx - 0.5
                    if nx > xmax - margin_x:
                        xmax = nx + 0.5
                    if ny < ymin + margin_y:
                        ymin = ny - 0.5
                    if ny > ymax - margin_y:
                        ymax = ny + 0.5

            self.drag_xlim = (xmin, xmax)
            self.drag_ylim = (ymin, ymax)
            self.draw(is_dragging=True, xlim=self.drag_xlim, ylim=self.drag_ylim)
            return

        # Handle Pan Workspace
        if self.current_tool == "move" and self.pan_start is not None:
            if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
                return
            dx = event.xdata - self.pan_start[0]
            dy = event.ydata - self.pan_start[1]
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            self.ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
            self.ax.set_ylim(ylim[0] - dy, ylim[1] - dy)
            self.canvas.draw_idle()
            return

        # Hover Cursor Updates
        if event.inaxes == self.ax and event.x is not None and event.y is not None:
            cnode, dist = self._find_closest_node(event.x, event.y)
            if cnode and dist <= 38:
                if self.current_tool == "connect":
                    self.canvas.get_tk_widget().config(cursor="crosshair")
                elif self.current_tool == "delete":
                    self.canvas.get_tk_widget().config(cursor="pirate" if os.name != "nt" else "X_cursor")
                else:
                    self.canvas.get_tk_widget().config(cursor="hand2")
            else:
                cedge = self._find_closest_edge(event.x, event.y)
                if cedge and self.current_tool in ("select", "delete"):
                    self.canvas.get_tk_widget().config(cursor="hand2" if self.current_tool == "select" else "pirate")
                else:
                    self.canvas.get_tk_widget().config(cursor="fleur" if self.current_tool == "move" else "")

    def on_release(self, event):
        self.pan_start = None
        if not self.is_dragging:
            return

        moved_node = self.drag_node
        drag_nodes = list(self.drag_nodes) if self.drag_nodes else ([moved_node] if moved_node else [])
        start_positions = dict(self.drag_start_positions)

        self.is_dragging = False
        self.drag_node = None
        self.drag_nodes = []
        self.drag_start_positions = {}
        self.drag_xlim = None
        self.drag_ylim = None
        self.canvas.get_tk_widget().config(cursor="")

        # Check if any node moved from start position to record undo
        has_moved = False
        for n in drag_nodes:
            if n in start_positions and self.node_pos.get(n) != start_positions[n]:
                has_moved = True
                break

        if has_moved:
            self.record_undo_state(f"Reposition {len(drag_nodes)} device(s)")
            if len(drag_nodes) == 1 and moved_node:
                final_pos = self.node_pos[moved_node]
                self.log_event(f"Device '{moved_node}' repositioned to ({final_pos[0]:.2f}, {final_pos[1]:.2f}).")
            else:
                self.log_event(f"Repositioned {len(drag_nodes)} device(s) as group.")

        self.update_route_comparison()
        self.draw()

    def on_scroll(self, event):
        """Mouse wheel zoom in / out."""
        if event.inaxes != self.ax:
            return
        if event.button == "up":
            self.zoom_in()
        elif event.button == "down":
            self.zoom_out()

    def _find_closest_node(self, px, py):
        closest_node = None
        min_dist = float("inf")
        for node in self.g.nodes:
            pos = self.get_node_position(node)
            disp = self.ax.transData.transform(pos)
            dist = ((disp[0] - px) ** 2 + (disp[1] - py) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest_node = node
        return closest_node, min_dist

    def _find_closest_edge(self, px, py):
        if not self.g.number_of_edges():
            return None
        min_dist = float("inf")
        closest_edge = None
        for u, v in self.g.edges():
            p1 = self.get_node_position(u)
            p2 = self.get_node_position(v)
            disp1 = self.ax.transData.transform(p1)
            disp2 = self.ax.transData.transform(p2)
            x1, y1 = disp1[0], disp1[1]
            x2, y2 = disp2[0], disp2[1]
            dx, dy = x2 - x1, y2 - y1
            lsq = dx * dx + dy * dy
            if lsq == 0:
                dist = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / lsq))
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                dist = ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5
            if dist < min_dist and dist <= 16:
                min_dist = dist
                closest_edge = (u, v)
        return closest_edge

    # -------------------------------------------------------------------------
    # Zoom, Pan & Viewport Handlers (Requirement 3)
    # -------------------------------------------------------------------------
    def zoom_in(self):
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        cx, cy = (xlim[0] + xlim[1]) / 2.0, (ylim[0] + ylim[1]) / 2.0
        w, h = (xlim[1] - xlim[0]) * 0.8 / 2.0, (ylim[1] - ylim[0]) * 0.8 / 2.0
        self.ax.set_xlim(cx - w, cx + w)
        self.ax.set_ylim(cy - h, cy + h)
        self.canvas.draw_idle()

    def zoom_out(self):
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        cx, cy = (xlim[0] + xlim[1]) / 2.0, (ylim[0] + ylim[1]) / 2.0
        w, h = (xlim[1] - xlim[0]) * 1.25 / 2.0, (ylim[1] - ylim[0]) * 1.25 / 2.0
        self.ax.set_xlim(cx - w, cx + w)
        self.ax.set_ylim(cy - h, cy + h)
        self.canvas.draw_idle()

    def fit_to_screen(self):
        pos = {n: self.get_node_position(n) for n in self.g.nodes}
        xlim, ylim = self.compute_view_limits(pos)
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.canvas.draw_idle()

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.draw()

    # -------------------------------------------------------------------------
    # Inspector Handlers: Device Configuration & Link Configuration
    # -------------------------------------------------------------------------
    def select_device_for_inspection(self, node_name):
        if node_name not in self.g:
            return
        d = self.g.nodes[node_name]
        self.selected_node = node_name
        self.insp_dev_name.set(node_name)
        self.insp_dev_type.set(d.get("type", "PC"))
        self.insp_dev_ip.set(d.get("ip", ""))
        self.insp_dev_mask.set(d.get("subnet_mask", "255.255.255.0"))
        self.insp_dev_gw.set(d.get("gateway", "R1"))
        self.insp_dev_dns.set(d.get("dns_server", "192.168.1.1"))
        self.insp_tabs.select(0)

    def apply_device_inspection_changes(self):
        node = self.selected_node
        if not node or node not in self.g:
            return
        new_name = self.insp_dev_name.get().strip()
        dtype = self.insp_dev_type.get().strip()
        ip = self.insp_dev_ip.get().strip()
        mask = self.insp_dev_mask.get().strip()
        gw = self.insp_dev_gw.get().strip()
        dns = self.insp_dev_dns.get().strip()
        try:
            self.record_undo_state(f"Configure device '{node}'")
            target = configure_device(self.g, node, new_name=new_name, device_type=dtype, ip=ip, subnet_mask=mask, gateway=gw, dns_server=dns)
            if target != node and node in self.node_pos:
                self.node_pos[target] = self.node_pos.pop(node)
            self.selected_node = target
            if node in self.selected_nodes:
                self.selected_nodes[self.selected_nodes.index(node)] = target
            self.log_event(f"Updated configuration for device '{target}'.")
            self.refresh_endpoint_selectors()
            self.update_inventory()
            self.update_route_comparison()
            self.draw()
            messagebox.showinfo("Configuration Updated", f"Device '{target}' configured successfully.")
        except Exception as e:
            messagebox.showerror("Configuration Error", str(e))

    def delete_selected_device(self):
        self.delete_selected()

    def delete_device_by_name(self, node_name):
        if not node_name or node_name not in self.g:
            return
        if is_essential_device(node_name):
            if not messagebox.askyesno("Protected Baseline Device", f"'{node_name}' is an essential baseline device.\nAre you sure you want to delete it?"):
                return
            self.record_undo_state(f"Delete '{node_name}'")
            remove_device(self.g, node_name, force=True)
        else:
            self.record_undo_state(f"Delete '{node_name}'")
            remove_device(self.g, node_name, force=False)
        if node_name in self.node_pos:
            del self.node_pos[node_name]
        if node_name in self.selected_nodes:
            self.selected_nodes.remove(node_name)
        if self.selected_node == node_name:
            self.selected_node = self.selected_nodes[0] if self.selected_nodes else None
        self.log_event(f"Device '{node_name}' removed from topology.")
        self.refresh_endpoint_selectors()
        self.update_inventory()
        self.update_route_comparison()
        self.draw()

    def select_link_for_inspection(self, u, v):
        if not self.g.has_edge(u, v):
            return
        self.selected_link = (u, v)
        edge = self.g[u][v]
        label = f"{u} <-> {v}"
        self.insp_link_label.set(label)
        self.insp_link_cost.set(str(edge.get("cost", 1)))
        self.insp_link_lat.set(str(edge.get("latency_ms", 2.0)))
        self.insp_link_loss.set(str(edge.get("packet_loss", 0.0)))
        self.insp_link_st.set(edge.get("status", "UP"))
        self.insp_link_type.set(edge.get("connection_type", "Copper Straight-Through"))
        self.insp_tabs.select(1)
        if hasattr(self, "target_link_choice") and hasattr(self, "target_link_combo"):
            target_str = f"{u} \u2194 {v}"
            rev_str = f"{v} \u2194 {u}"
            vals = self.target_link_combo.cget("values")
            if target_str in vals:
                self.target_link_choice.set(target_str)
            elif rev_str in vals:
                self.target_link_choice.set(rev_str)

    def on_link_combo_selected(self):
        raw = self.insp_link_label.get()
        if " <-> " in raw:
            parts = raw.split(" <-> ")
            if len(parts) == 2 and self.g.has_edge(parts[0], parts[1]):
                self.select_link_for_inspection(parts[0], parts[1])
                self.draw()

    def apply_link_inspection_changes(self):
        if not self.selected_link:
            return
        u, v = self.selected_link
        try:
            cost = int(self.insp_link_cost.get())
            lat = float(self.insp_link_lat.get())
            loss = float(self.insp_link_loss.get())
            st = self.insp_link_st.get().strip().upper()
            ctype = self.insp_link_type.get().strip()
            self.record_undo_state(f"Configure link {u} <-> {v}")
            configure_link(self.g, u, v, cost=cost, latency_ms=lat, packet_loss=loss, status=st, connection_type=ctype)
            self.log_event(f"Updated link parameters for {u} <-> {v} (Cost: {cost}, Lat: {lat}ms, Loss: {loss}%, Status: {st}).")
            self.update_inventory()
            self.update_route_comparison()
            self.draw()
            messagebox.showinfo("Link Updated", f"Link '{u} <-> {v}' updated successfully.")
        except Exception as e:
            messagebox.showerror("Link Edit Error", str(e))

    def disconnect_selected_link(self):
        if self.selected_link:
            self.delete_link_by_endpoints(self.selected_link[0], self.selected_link[1])

    def delete_link_by_endpoints(self, u, v):
        if not self.g.has_edge(u, v):
            return
        if messagebox.askyesno("Disconnect Link", f"Disconnect link between '{u}' and '{v}'?"):
            self.record_undo_state(f"Disconnect link {u} <-> {v}")
            disconnect_devices(self.g, u, v)
            self.selected_link = None
            self.log_event(f"Disconnected link {u} <-> {v}.")
            self.update_inventory()
            self.update_route_comparison()
            self.draw()

    def delete_selected(self):
        nodes_to_del = [n for n in self.selected_nodes if n in self.g]
        if not nodes_to_del and self.selected_node and self.selected_node in self.g:
            nodes_to_del = [self.selected_node]

        if nodes_to_del:
            self.record_undo_state(f"Delete {len(nodes_to_del)} device(s)")
            for n in list(nodes_to_del):
                if is_essential_device(n):
                    if not messagebox.askyesno("Protected Baseline Device", f"'{n}' is an essential baseline device.\nAre you sure you want to delete it?"):
                        continue
                    remove_device(self.g, n, force=True)
                else:
                    remove_device(self.g, n, force=False)
                if n in self.node_pos:
                    del self.node_pos[n]
            self.selected_node = None
            self.selected_nodes = []
            self.log_event(f"Removed selected device(s) from topology.")
            self.refresh_endpoint_selectors()
            self.update_inventory()
            self.update_route_comparison()
            self.draw()
        elif self.selected_link:
            self.disconnect_selected_link()

    # -------------------------------------------------------------------------
    # Simulation: Inject, Monitor, Diagnose, Recover, Verify, Reset
    # -------------------------------------------------------------------------
    def inject(self):
        try:
            scenario_name = self.choice.get()
            is_link_failure = (scenario_name in ("Link Failure", "Link failure", "Link failure (R2-Server)"))

            if is_link_failure:
                if self.g.number_of_edges() == 0:
                    messagebox.showwarning("No Connections", "No connections exist in the active topology to inject a link failure.")
                    self.log_event("Link failure injection cancelled: No connections exist in topology.")
                    return
                all_down = all(d.get("status") == "DOWN" for _, _, d in self.g.edges(data=True))
                if all_down:
                    messagebox.showwarning("All Links Down", "All connections in the active topology are already DOWN.")
                    self.log_event("Link failure injection cancelled: All links are already DOWN.")
                    return

                # Read target link from dropdown
                chosen_link_str = self.target_link_choice.get() if hasattr(self, "target_link_choice") else ""
                u, v = parse_link_endpoints(chosen_link_str)
                if not (u and v and self.g.has_edge(u, v)):
                    # Fallback to selected_link if valid
                    if self.selected_link and self.g.has_edge(self.selected_link[0], self.selected_link[1]):
                        u, v = self.selected_link
                    else:
                        up_edges = [(a, b) for a, b, d in self.g.edges(data=True) if d.get("status") == "UP"]
                        if up_edges:
                            u, v = up_edges[0]
                        else:
                            u, v = list(self.g.edges())[0]

                target_link = (u, v)
                self.selected_link = target_link
            else:
                target_link = self.selected_link

            target_device = self.selected_node

            self.state = inject_fault(self.g, scenario_name, target_link=target_link, target_device=target_device)
            self.state["source"] = self.source_choice.get()
            self.state["target"] = self.target_choice.get()

            self.draw()
            self.update_route_comparison()
            self.update_inventory()
            self.update_kpi_dashboard()
            self.refresh_active_faults_view()

            is_no_fault = self.state.get("fault") == "No fault" or scenario_name in ("No fault", "No Fault \u2013 Healthy Baseline", "No Fault - Healthy Baseline")
            if is_no_fault:
                self.update_header_status("HEALTHY", "BASELINE STATE RESTORED")
            elif is_link_failure and target_link:
                self.update_header_status("CRITICAL", f"LINK DOWN: {target_link[0]} \u2194 {target_link[1]}")
            else:
                self.update_header_status("CRITICAL", f"FAULT ACTIVE: {scenario_name}")

            report = (
                f"=== SIMULATION FAULT INJECTION ===\n"
                f"Scenario: {scenario_name}\n"
                f"State   : {self.state.get('fault', scenario_name)}\n"
                f"Details : {self.state['details']}\n\n"
                f"Next: Click 'Monitor & Diagnose' to execute observation-based root-cause diagnosis."
            )
            self.show_diag(report)
            self.bottom_tabs.select(0)

            if is_link_failure and target_link:
                self.log_event(f"Fault injected: Link Failure on {target_link[0]} \u2194 {target_link[1]}")
                self.log_event(f"Link '{target_link[0]} \u2194 {target_link[1]}' status changed to DOWN.")
            else:
                self.log_event(f"Fault injected: {scenario_name}")
            self.history.append(("fault", scenario_name))
        except Exception as e:
            messagebox.showerror("Injection Error", str(e))

    def diagnose(self):
        start = time.perf_counter()
        if not hasattr(self, "state") or not self.state:
            self.state = {"fault": "No fault"}
        self.state["source"] = self.source_choice.get()
        self.state["target"] = self.target_choice.get()

        # Stage 1: Network Monitoring Module (telemetry observations only)
        self.obs = collect_observations(self.g, self.state)
        # Stage 2: Independent Root-Cause Diagnosis Module
        self.findings = diagnose(self.obs)
        self.diag_time = time.perf_counter() - start

        # Generate Separate Report A and Report B
        rep_a = format_monitoring_report(self.obs)
        rep_b = format_diagnosis_report(self.findings)

        combined_report = f"{rep_a}\n\n{rep_b}\n\nDiagnosis execution time: {self.diag_time:.6f} s"
        self.show_diag(combined_report)
        self.bottom_tabs.select(0)

        # Update health badge
        has_down = bool(self.obs["down_links"])
        has_degraded = bool(self.obs["high_latency"] or self.obs["packet_loss"])
        if has_down or not self.obs["gateway_ok"] or not self.obs["dns_ok"]:
            self.update_header_status("CRITICAL", "DIAGNOSIS: FAULT IDENTIFIED")
        elif has_degraded:
            self.update_header_status("DEGRADED", "DIAGNOSIS: DEGRADED PERFORMANCE")
        else:
            self.update_header_status("HEALTHY", "DIAGNOSIS: OPTIMAL HEALTH")

        self.update_route_comparison()
        self.update_kpi_dashboard()
        self.update_recovery_planner_view()
        self.log_event("Diagnosis completed: " + "; ".join(getattr(f, "root_cause", f[0]) for f in self.findings))
        self.history.append(("diagnosis", "; ".join(getattr(f, "root_cause", f[0]) for f in self.findings)))

    def recover(self):
        if not hasattr(self, "findings"):
            self.diagnose()
        start = time.perf_counter()
        self.state["source"] = self.source_choice.get()
        self.state["target"] = self.target_choice.get()

        # Stage 3: Fault-Specific Automated Recovery & Stage 4: Post-Recovery Verification
        result = recover(self.g, self.state, findings=self.findings)
        self.rec_time = time.perf_counter() - start
        metrics = make_metrics(self.g, result["route"], self.diag_time, self.rec_time)

        # Generate Separate Report C and Report D
        rep_c = format_recovery_report(result)
        rep_d = format_verification_report(result)

        combined_rec = f"{rep_c}\n\n{rep_d}\n\nRecovery execution time: {self.rec_time:.6f} s"
        self.show_rec(combined_rec)
        self.bottom_tabs.select(1)

        # Performance Tab Output
        perf_lines = ["=== NETWORK PERFORMANCE METRICS ==="]
        for k, v in metrics.items():
            perf_lines.append(f"{k:28}: {v}")
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("end", "\n".join(perf_lines))

        self.draw()
        self.update_route_comparison()
        self.update_inventory()
        self.last_recovery_status = result.get("status", "UNKNOWN")
        self.last_recovery_service_availability = result.get("service_availability", "AVAILABLE")
        self.last_recovery_network_health = result.get("network_health", "HEALTHY")
        self.update_kpi_dashboard()
        self.refresh_active_faults_view()
        self.refresh_audit_view()
        self.update_recovery_planner_view(result.get("plan"))

        if result["verified"]:
            if result.get("status") == "SERVICE MAINTAINED":
                self.update_header_status("DEGRADED", "SERVICE MAINTAINED (ALTERNATE ROUTE ACTIVE)")
            elif result.get("status") == "NO RECOVERY REQUIRED":
                self.update_header_status("HEALTHY", "BASELINE HEALTHY: NO RECOVERY REQUIRED")
            else:
                self.update_header_status("HEALTHY", "RECOVERY VERIFIED & STABLE")
        elif result.get("status") in ("RECOVERY UNAVAILABLE", "RECOVERY FAILED"):
            self.update_header_status("CRITICAL", "RECOVERY UNAVAILABLE: NO ALTERNATE ROUTE")
        else:
            self.update_header_status("CRITICAL", "RECOVERY NOT VERIFIED")

        self.log_event(f"Recovery executed: {result['status']} | Active route: {metrics['Selected route']}")
        self.history.append(("recovery", result["status"]))

    def reset(self):
        self.record_undo_state("Reset to Baseline")
        self.g = build_network()
        self.node_pos = dict(self.g.graph.get("node_positions", DEFAULT_POSITIONS))
        self.selected_node = None
        self.selected_nodes = []
        self.selected_link = None
        self.clipboard = []
        self.paste_count = 1
        self.connect_source_node = None
        for name in ("obs", "findings"):
            if hasattr(self, name):
                delattr(self, name)
        self.diag_time = 0.0
        self.rec_time = 0.0
        self.choice.set(UI_SCENARIOS[0])

        self.refresh_endpoint_selectors()
        self.fit_to_screen()
        self.draw()
        self.update_route_comparison()
        self.update_inventory()
        get_fault_registry().clear_all()
        self.last_recovery_status = "NOMINAL"
        self.last_recovery_service_availability = "AVAILABLE"
        self.last_recovery_network_health = "HEALTHY"
        self.update_kpi_dashboard()
        self.refresh_active_faults_view()
        self.update_header_status("HEALTHY", "LOGICAL WORKSPACE RESTORED")

        self.show_diag("Baseline network restored. All links UP and 0% loss.\nReady for simulation.")
        self.show_rec("Recovery engine standby.")
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("end", "Run 'Recover & Verify' to generate complete performance metrics.")
        self.log_event("Simulation reset; baseline topology restored.")

    def new_workspace(self):
        if messagebox.askyesno("New Logical Workspace", "Clear current topology and start a blank workspace?"):
            self.record_undo_state("New Workspace")
            self.g = nx.Graph()
            self.g.graph.update(gateway="N/A", dns_available=True, scenario="No fault", node_positions={})
            self.node_pos = {}
            self.selected_node = None
            self.selected_nodes = []
            self.selected_link = None
            self.clipboard = []
            self.paste_count = 1
            self.connect_source_node = None
            self.refresh_endpoint_selectors()
            self.update_inventory()
            self.update_route_comparison()
            self.draw()
            self.log_event("Created new blank Cisco Packet Tracer logical workspace.")

    def export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="network_experiment_log.csv"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Event", "Details"])
            w.writerows(self.history)
        self.log_event(f"Audit log exported: {path}")
        messagebox.showinfo("Export Successful", f"Audit experiment log saved to:\n{path}")

    # -------------------------------------------------------------------------
    # Route Comparison Matrix & Explanation Engine
    # -------------------------------------------------------------------------
    def update_route_comparison(self):
        src = self.source_choice.get()
        dst = self.target_choice.get()
        src, dst = resolve_endpoints(self.g, src, dst)

        routes = discover_routes(self.g, source=src, target=dst)
        selection = select_best_route(self.g, routes=routes, source=src, target=dst)
        best_path = selection["selected_path"]

        # Clear existing rows
        for item in self.route_tree.get_children():
            self.route_tree.delete(item)

        if not routes:
            self.route_tree.insert("", "end", values=("No physical paths discovered", "N/A", "N/A", "N/A", "Unavailable", "None"))
            self.explanation_label.config(text=f"No route available between {src} and {dst}.")
            return

        active_route = get_active_route(self.g, source=src, target=dst)
        for r in routes:
            is_best = (r["path"] == best_path)
            is_active = (r["path"] == active_route)
            if is_active and is_best:
                sel_text = "★ ACTIVE & REC"
            elif is_active:
                sel_text = "● ACTIVE"
            elif is_best:
                sel_text = "✦ RECOMMENDED"
            else:
                sel_text = "CANDIDATE"

            self.route_tree.insert("", "end", values=(
                r["path_str"],
                r["cost"],
                f"{r['latency_ms']} ms",
                f"{r['max_loss']}%",
                r["availability"],
                sel_text
            ))

        active_str = " -> ".join(active_route) if active_route else "None"
        self.explanation_label.config(text=f"[Active Forwarding Route: {active_str}] Policy Decision: {selection['explanation']}")

    def on_endpoint_changed(self):
        self.update_route_comparison()
        self.draw()
        self.log_event(f"Changed path endpoints: {self.source_choice.get()} -> {self.target_choice.get()}")

    # -------------------------------------------------------------------------
    # UI Helper Methods
    # -------------------------------------------------------------------------
    def show_diag(self, text):
        self.output_diag.delete("1.0", "end")
        self.output_diag.insert("end", text)

    def show_rec(self, text):
        self.output_rec.delete("1.0", "end")
        self.output_rec.insert("end", text)

    def log_event(self, text):
        self.log.insert("end", f"{time.strftime('%H:%M:%S')} | {text}\n")
        self.log.see("end")

    def update_header_status(self, badge, text):
        colors = {"HEALTHY": "#15803d", "DEGRADED": "#c2410c", "CRITICAL": "#b91c1c"}
        self.badge_lbl.config(text=badge, bg=colors.get(badge, "#475569"))
        self.status_lbl.config(text=text)

    def refresh_endpoint_selectors(self):
        nodes = list(self.g.nodes())
        self.source_combo["values"] = nodes
        self.target_combo["values"] = nodes
        if self.source_choice.get() not in nodes:
            self.source_choice.set("PC1" if "PC1" in nodes else (nodes[0] if nodes else ""))
        if self.target_choice.get() not in nodes:
            self.target_choice.set("Server" if "Server" in nodes else (nodes[-1] if nodes else ""))
        self.dev_select_combo["values"] = nodes
        edge_labels = [f"{a} <-> {b}" for a, b in self.g.edges()]
        self.link_select_combo["values"] = edge_labels
        self.refresh_target_link_options()

    def get_node_position(self, node):
        if node in self.node_pos:
            return self.node_pos[node]
        dev_type = self.g.nodes[node].get("type", "Router")
        type_x = {"PC": 0.0, "Laptop": 0.0, "Switch": 1.0, "Router": 2.0, "Server": 3.0}
        x = type_x.get(dev_type, 1.5)
        same_nodes = [n for n in self.g.nodes if self.g.nodes[n].get("type") == dev_type]
        idx = same_nodes.index(node) if node in same_nodes else len(same_nodes)
        total = max(1, len(same_nodes))
        y = 1.0 if total == 1 else (0.3 + (1.4 * idx / (total - 1)))
        pos = (x, y)
        self.node_pos[node] = pos
        return pos

    def compute_view_limits(self, pos):
        if not pos:
            return (-1.0, 4.0), (-0.5, 2.5)
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)
        pad_x = max(0.6, span_x * 0.20)
        pad_y = max(0.5, span_y * 0.25)
        return (min_x - pad_x, max_x + pad_x), (min_y - pad_y, max_y + pad_y)

    def update_inventory(self):
        # Update device tree
        for item in self.dev_tree.get_children():
            self.dev_tree.delete(item)
        for n, d in self.g.nodes(data=True):
            self.dev_tree.insert("", "end", values=(
                n,
                d.get("type", "Unknown"),
                d.get("ip", "N/A")
            ))

        # Update link tree
        for item in self.link_tree.get_children():
            self.link_tree.delete(item)
        for a, b, d in self.g.edges(data=True):
            self.link_tree.insert("", "end", values=(
                f"{a} <-> {b}",
                d.get("status", "UP"),
                f"{d.get('latency_ms', 0)} ms",
                f"{d.get('packet_loss', 0)}%"
            ))

        # Update palette stats
        self.stats_lbl.config(text=f"Devices: {self.g.number_of_nodes()} | Links: {self.g.number_of_edges()}")

    # -------------------------------------------------------------------------
    # Dialogs & Persistence (Save / Load / Configure Dialogs)
    # -------------------------------------------------------------------------
    def open_add_device_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Add Device to Workspace")
        dlg.geometry("380x300")
        dlg.transient(self.root)
        dlg.grab_set()

        form = ttk.Frame(dlg, padding=12)
        form.pack(fill="both", expand=True)

        name_var = tk.StringVar(value=generate_unique_device_name(self.g, "PC"))
        type_var = tk.StringVar(value="PC")
        ip_var = tk.StringVar()
        mask_var = tk.StringVar(value="255.255.255.0")
        gw_var = tk.StringVar(value="R1")

        ttk.Label(form, text="Device Name:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=name_var, width=20).grid(row=0, column=1, pady=4)

        ttk.Label(form, text="Device Type:").grid(row=1, column=0, sticky="w", pady=4)
        type_combo = ttk.Combobox(form, textvariable=type_var, values=DEVICE_TYPES, state="readonly", width=18)
        type_combo.grid(row=1, column=1, pady=4)

        ttk.Label(form, text="IP Address:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=ip_var, width=20).grid(row=2, column=1, pady=4)

        ttk.Label(form, text="Subnet Mask:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=mask_var, width=20).grid(row=3, column=1, pady=4)

        ttk.Label(form, text="Default Gateway:").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=gw_var, width=20).grid(row=4, column=1, pady=4)

        def on_add():
            try:
                name = name_var.get().strip()
                dtype = type_var.get().strip()
                ip = ip_var.get().strip() or None
                mask = mask_var.get().strip()
                gw = gw_var.get().strip()
                self.record_undo_state(f"Add {dtype}")
                add_device(self.g, name, device_type=dtype, ip=ip, subnet_mask=mask, gateway=gw)
                self.selected_node = name
                self.selected_nodes = [name]
                self.log_event(f"Added device '{name}' ({dtype}).")
                self.refresh_endpoint_selectors()
                self.update_inventory()
                self.update_route_comparison()
                self.draw()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Validation Error", str(e), parent=dlg)

        ttk.Button(form, text="Add Device", style="Primary.TButton", command=on_add).grid(row=5, column=0, columnspan=2, pady=12)

    def open_connect_dialog(self):
        nodes = list(self.g.nodes())
        if len(nodes) < 2:
            messagebox.showinfo("Need More Devices", "At least two devices are required to create a connection.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Connect Devices (Cable Setup)")
        dlg.geometry("400x320")
        dlg.transient(self.root)
        dlg.grab_set()

        form = ttk.Frame(dlg, padding=12)
        form.pack(fill="both", expand=True)

        a_var = tk.StringVar(value=nodes[0])
        b_var = tk.StringVar(value=nodes[1] if len(nodes) > 1 else nodes[0])
        cost_var = tk.StringVar(value="1")
        lat_var = tk.StringVar(value="2.0")
        loss_var = tk.StringVar(value="0.0")
        st_var = tk.StringVar(value="UP")
        type_var = tk.StringVar(value="Copper Straight-Through")

        ttk.Label(form, text="Device 1:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=a_var, values=nodes, state="readonly", width=18).grid(row=0, column=1, pady=3)

        ttk.Label(form, text="Device 2:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=b_var, values=nodes, state="readonly", width=18).grid(row=1, column=1, pady=3)

        ttk.Label(form, text="Cable Type:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=type_var, values=CONNECTION_TYPES, state="readonly", width=18).grid(row=2, column=1, pady=3)

        ttk.Label(form, text="Cost (metric):").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=cost_var, width=20).grid(row=3, column=1, pady=3)

        ttk.Label(form, text="Latency (ms):").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=lat_var, width=20).grid(row=4, column=1, pady=3)

        ttk.Label(form, text="Packet Loss (%):").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=loss_var, width=20).grid(row=5, column=1, pady=3)

        ttk.Label(form, text="Status:").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=st_var, values=["UP", "DOWN"], state="readonly", width=18).grid(row=6, column=1, pady=3)

        def on_connect():
            try:
                a = a_var.get()
                b = b_var.get()
                cost = int(cost_var.get())
                lat = float(lat_var.get())
                loss = float(loss_var.get())
                st = st_var.get()
                ctype = type_var.get()
                self.record_undo_state(f"Connect {a} <-> {b}")
                connect_devices(self.g, a, b, cost=cost, latency_ms=lat, packet_loss=loss, status=st, connection_type=ctype)
                self.log_event(f"Connected '{a}' to '{b}' (Cost: {cost}, Lat: {lat}ms).")
                self.refresh_endpoint_selectors()
                self.update_inventory()
                self.update_route_comparison()
                self.draw()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Connection Error", str(e), parent=dlg)

        ttk.Button(form, text="Create Connection", style="Primary.TButton", command=on_connect).grid(row=7, column=0, columnspan=2, pady=10)

    def open_configure_link_dialog_for(self, u, v):
        """Open link configuration dialog immediately after cable connection (Requirement 4)."""
        if not self.g.has_edge(u, v):
            return
        edge = self.g[u][v]
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Link Configuration: {u} <-> {v}")
        dlg.geometry("380x280")
        dlg.transient(self.root)
        dlg.grab_set()

        form = ttk.Frame(dlg, padding=12)
        form.pack(fill="both", expand=True)

        cost_var = tk.StringVar(value=str(edge.get("cost", 1)))
        lat_var = tk.StringVar(value=str(edge.get("latency_ms", 2.0)))
        loss_var = tk.StringVar(value=str(edge.get("packet_loss", 0.0)))
        st_var = tk.StringVar(value=edge.get("status", "UP"))
        type_var = tk.StringVar(value=edge.get("connection_type", "Copper Straight-Through"))

        ttk.Label(form, text=f"Endpoints: {u} <-> {v}", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 6))

        ttk.Label(form, text="Cable Type:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=type_var, values=CONNECTION_TYPES, state="readonly", width=18).grid(row=1, column=1, pady=3)

        ttk.Label(form, text="Link Cost:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=cost_var, width=20).grid(row=2, column=1, pady=3)

        ttk.Label(form, text="Latency (ms):").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=lat_var, width=20).grid(row=3, column=1, pady=3)

        ttk.Label(form, text="Packet Loss (%):").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=loss_var, width=20).grid(row=4, column=1, pady=3)

        ttk.Label(form, text="Status:").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=st_var, values=["UP", "DOWN"], state="readonly", width=18).grid(row=5, column=1, pady=3)

        def on_save():
            try:
                configure_link(self.g, u, v, cost=int(cost_var.get()), latency_ms=float(lat_var.get()),
                               packet_loss=float(loss_var.get()), status=st_var.get(), connection_type=type_var.get())
                self.log_event(f"Configured link {u} <-> {v}.")
                self.update_inventory()
                self.update_route_comparison()
                self.draw()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        ttk.Button(form, text="Save Link Settings", style="Primary.TButton", command=on_save).grid(row=6, column=0, columnspan=2, pady=10)

    def open_configure_device_dialog(self):
        devices = list(self.g.nodes())
        if not devices:
            messagebox.showinfo("No Devices", "No devices exist to configure.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Configure Device Properties")
        dlg.geometry("400x320")
        dlg.transient(self.root)
        dlg.grab_set()

        form = ttk.Frame(dlg, padding=12)
        form.pack(fill="both", expand=True)

        target_var = tk.StringVar(value=devices[0])
        name_var = tk.StringVar(value=devices[0])
        type_var = tk.StringVar()
        ip_var = tk.StringVar()
        mask_var = tk.StringVar()
        gw_var = tk.StringVar()

        def load_fields(name):
            d = self.g.nodes[name]
            name_var.set(name)
            type_var.set(d.get("type", "PC"))
            ip_var.set(d.get("ip", ""))
            mask_var.set(d.get("subnet_mask", "255.255.255.0"))
            gw_var.set(d.get("gateway", "R1"))

        load_fields(devices[0])

        ttk.Label(form, text="Select Device:").grid(row=0, column=0, sticky="w", pady=3)
        target_combo = ttk.Combobox(form, textvariable=target_var, values=devices, state="readonly", width=18)
        target_combo.grid(row=0, column=1, pady=3)
        target_combo.bind("<<ComboboxSelected>>", lambda e: load_fields(target_var.get()))

        ttk.Label(form, text="Rename Device:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=name_var, width=20).grid(row=1, column=1, pady=3)

        ttk.Label(form, text="Device Type:").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=type_var, values=DEVICE_TYPES, state="readonly", width=18).grid(row=2, column=1, pady=3)

        ttk.Label(form, text="IP Address:").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=ip_var, width=20).grid(row=3, column=1, pady=3)

        ttk.Label(form, text="Subnet Mask:").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=mask_var, width=20).grid(row=4, column=1, pady=3)

        ttk.Label(form, text="Default Gateway:").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=gw_var, width=20).grid(row=5, column=1, pady=3)

        def on_save():
            try:
                target = target_var.get()
                new_n = name_var.get().strip()
                dtype = type_var.get().strip()
                ip = ip_var.get().strip()
                mask = mask_var.get().strip()
                gw = gw_var.get().strip()
                res_name = configure_device(self.g, target, new_name=new_n, device_type=dtype, ip=ip, subnet_mask=mask, gateway=gw)
                self.log_event(f"Configured device '{res_name}'.")
                self.refresh_endpoint_selectors()
                self.update_inventory()
                self.update_route_comparison()
                self.draw()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        ttk.Button(form, text="Save Changes", style="Primary.TButton", command=on_save).grid(row=6, column=0, columnspan=2, pady=10)

    def open_remove_device_dialog(self):
        devices = list(self.g.nodes())
        if not devices:
            messagebox.showinfo("No Devices", "No devices exist to remove.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Remove Device")
        dlg.geometry("340x160")
        dlg.transient(self.root)
        dlg.grab_set()

        form = ttk.Frame(dlg, padding=12)
        form.pack(fill="both", expand=True)

        dev_var = tk.StringVar(value=devices[0])
        ttk.Label(form, text="Select Device to Remove:").pack(anchor="w", pady=3)
        ttk.Combobox(form, textvariable=dev_var, values=devices, state="readonly", width=20).pack(fill="x", pady=4)

        def on_delete():
            self.delete_device_by_name(dev_var.get())
            dlg.destroy()

        ttk.Button(form, text="Remove Device", style="Danger.TButton", command=on_delete).pack(fill="x", pady=10)

    def open_configure_link_dialog(self):
        edges = list(self.g.edges())
        if not edges:
            messagebox.showinfo("No Links", "No links exist to configure.")
            return
        edge_labels = [f"{a} <-> {b}" for a, b in edges]

        dlg = tk.Toplevel(self.root)
        dlg.title("Edit Link Properties")
        dlg.geometry("380x280")
        dlg.transient(self.root)
        dlg.grab_set()

        form = ttk.Frame(dlg, padding=12)
        form.pack(fill="both", expand=True)

        link_var = tk.StringVar(value=edge_labels[0])
        cost_var = tk.StringVar()
        lat_var = tk.StringVar()
        loss_var = tk.StringVar()
        st_var = tk.StringVar()

        def load_edge_data(raw):
            a, b = raw.split(" <-> ")
            d = self.g[a][b]
            cost_var.set(str(d.get("cost", 1)))
            lat_var.set(str(d.get("latency_ms", 2.0)))
            loss_var.set(str(d.get("packet_loss", 0.0)))
            st_var.set(d.get("status", "UP"))

        load_edge_data(edge_labels[0])

        ttk.Label(form, text="Select Link:").grid(row=0, column=0, sticky="w", pady=3)
        link_combo = ttk.Combobox(form, textvariable=link_var, values=edge_labels, state="readonly", width=18)
        link_combo.grid(row=0, column=1, pady=3)
        link_combo.bind("<<ComboboxSelected>>", lambda e: load_edge_data(link_var.get()))

        ttk.Label(form, text="Cost (metric):").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=cost_var, width=20).grid(row=1, column=1, pady=3)

        ttk.Label(form, text="Latency (ms):").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=lat_var, width=20).grid(row=2, column=1, pady=3)

        ttk.Label(form, text="Packet Loss (%):").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=loss_var, width=20).grid(row=3, column=1, pady=3)

        ttk.Label(form, text="Status:").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=st_var, values=["UP", "DOWN"], state="readonly", width=18).grid(row=4, column=1, pady=3)

        def on_save():
            try:
                a, b = link_var.get().split(" <-> ")
                configure_link(self.g, a, b, cost=int(cost_var.get()), latency_ms=float(lat_var.get()),
                               packet_loss=float(loss_var.get()), status=st_var.get())
                self.log_event(f"Configured link {a} <-> {b}.")
                self.update_inventory()
                self.update_route_comparison()
                self.draw()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        ttk.Button(form, text="Save Link Settings", style="Primary.TButton", command=on_save).grid(row=5, column=0, columnspan=2, pady=10)

    def open_disconnect_dialog(self):
        edges = list(self.g.edges())
        if not edges:
            messagebox.showinfo("No Links", "No links exist to disconnect.")
            return
        edge_labels = [f"{a} <-> {b}" for a, b in edges]

        dlg = tk.Toplevel(self.root)
        dlg.title("Disconnect Link")
        dlg.geometry("340x160")
        dlg.transient(self.root)
        dlg.grab_set()

        form = ttk.Frame(dlg, padding=12)
        form.pack(fill="both", expand=True)

        link_var = tk.StringVar(value=edge_labels[0])
        ttk.Label(form, text="Select Link to Disconnect:").pack(anchor="w", pady=3)
        ttk.Combobox(form, textvariable=link_var, values=edge_labels, state="readonly", width=20).pack(fill="x", pady=4)

        def on_disconnect():
            a, b = link_var.get().split(" <-> ")
            self.delete_link_by_endpoints(a, b)
            dlg.destroy()

        ttk.Button(form, text="Disconnect Link", style="Danger.TButton", command=on_disconnect).pack(fill="x", pady=10)

    # -------------------------------------------------------------------------
    # Topology Persistence (Save & Load JSON) - Requirement 9
    # -------------------------------------------------------------------------
    def save_topology(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="network_topology.json"
        )
        if not path:
            return
        try:
            save_topology_to_file(self.g, path, self.node_pos)
            self.log_event(f"Topology saved successfully to: {path}")
            messagebox.showinfo("Saved", f"Topology saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def load_topology(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if not path:
            return
        try:
            self.record_undo_state("Load Topology")
            g, positions = load_topology_from_file(path)
            self.g = g
            self.node_pos = positions
            self.selected_node = None
            self.selected_nodes = []
            self.selected_link = None
            self.clipboard = []
            self.paste_count = 1
            self.connect_source_node = None
            self.refresh_endpoint_selectors()
            self.fit_to_screen()
            self.draw()
            self.update_route_comparison()
            self.update_inventory()
            self.update_kpi_dashboard()
            self.refresh_active_faults_view()
            self.update_header_status("HEALTHY", "CUSTOM TOPOLOGY LOADED")
            self.log_event(f"Topology loaded from: {path} ({g.number_of_nodes()} devices, {g.number_of_edges()} links)")
            messagebox.showinfo("Loaded", f"Topology loaded successfully from:\n{path}")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def show_help_guide(self):
        guide = (
            "CISCO PACKET TRACER LOGICAL WORKSPACE GUIDE\n\n"
            "1. WORKSPACE TOOLS:\n"
            "   • Select (S): Click any device or link to inspect its properties in the right inspector.\n"
            "   • Move (M): Pan freely across the logical workspace canvas.\n"
            "   • Connect (C): Cable tool! Click Device 1, then click Device 2 to connect them.\n"
            "   • Delete (D): Click any device or connection to delete it.\n\n"
            "2. DEVICE PALETTE:\n"
            "   • Click any palette button (+ Add Router, + Add Switch, etc.) to place a new device.\n"
            "   • Device names (Router1, Switch1, PC1, etc.) are generated automatically.\n\n"
            "3. SIMULATION & DIAGNOSIS:\n"
            "   • Inject Fault: Simulates a fault scenario on selected or baseline components.\n"
            "   • Monitor & Diagnose: Gathers pure telemetry and executes IF-THEN root-cause diagnosis.\n"
            "   • Recover & Verify: Applies targeted repairs and verifies network health improvement.\n"
            "   • Multi-Route Matrix: Discovers and compares all loopless routes with explainable decisions."
        )
        messagebox.showinfo("Packet Tracer Guide", guide)

    def show_about(self):
        about = (
            "Intelligent Network Fault Diagnosis & Automated Recovery Framework\n"
            "Cisco Packet Tracer-Inspired Simulation Workspace Edition\n\n"
            "Features:\n"
            "• Cisco Packet Tracer logical workspace interface\n"
            "• Interactive drag-and-drop, zoom, pan, and cable connection tool\n"
            "• Independent observation-based root-cause diagnosis (IF-THEN rules)\n"
            "• Multi-path route discovery and explainable selection decisions\n"
            "• Automated recovery and post-repair health verification\n"
            "• Full JSON topology persistence and CSV audit logging"
        )
        messagebox.showinfo("About Application", about)


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
