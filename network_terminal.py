"""network_terminal.py - Windows CMD-Style Simulated Network Terminal.

Provides an authentic Windows Command Prompt terminal window operating directly on
the live simulated network topology. Supports ICMP ping, traceroute, nslookup, ipconfig,
device switching, routing inspection, live diagnosis, recovery, and command history.
"""

import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional
import networkx as nx

from network_model import discover_routes, calculate_route_metrics, get_active_route, resolve_gateway_node
from monitoring import collect_observations
from diagnostics import diagnose, format_diagnosis_report
from recovery import recover, format_recovery_report
from recovery_planner import generate_recovery_plan, format_plan_report
from decision_engine import get_decision_engine, DecisionStatus
from fault_registry import get_fault_registry


class NetworkTerminal:
    """Windows CMD-style interactive network terminal for network simulation."""

    def __init__(self, parent_window, g: nx.Graph, default_host: str = "PC1", on_state_change=None):
        self.g = g
        self.current_host = default_host if default_host in self.g.nodes else ("PC1" if "PC1" in self.g.nodes else list(self.g.nodes)[0])
        self.on_state_change = on_state_change
        self.history: List[str] = []
        self.history_idx: int = 0

        # Build Toplevel window
        self.win = tk.Toplevel(parent_window)
        self.win.title("Command Prompt - Simulated Network Terminal")
        self.win.geometry("820x520")
        self.win.minsize(600, 380)
        self.win.configure(bg="#0c0c0c")

        # Top banner with host selector and terminal controls
        top_bar = tk.Frame(self.win, bg="#1a1a1a", height=30)
        top_bar.pack(fill="x", side="top", padx=0, pady=0)

        tk.Label(
            top_bar, text="Host Context:", bg="#1a1a1a", fg="#aaaaaa", font=("Segoe UI", 9)
        ).pack(side="left", padx=(10, 4), pady=4)

        self.host_var = tk.StringVar(value=self.current_host)
        self.host_combo = ttk.Combobox(
            top_bar, textvariable=self.host_var, values=list(self.g.nodes), state="readonly", width=12
        )
        self.host_combo.pack(side="left", padx=4, pady=4)
        self.host_combo.bind("<<ComboboxSelected>>", self._on_combo_host_selected)

        tk.Label(
            top_bar, text="Type 'help' for commands | 'cls' to clear | 'exit' to close",
            bg="#1a1a1a", fg="#666666", font=("Segoe UI", 8, "italic")
        ).pack(side="right", padx=10)

        # Main terminal text area
        text_frame = tk.Frame(self.win, bg="#0c0c0c")
        text_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self.text = tk.Text(
            text_frame,
            bg="#0c0c0c",
            fg="#cccccc",
            insertbackground="#ffffff",
            font=("Consolas", 10),
            wrap="char",
            relief="flat",
            highlightthickness=0,
            padx=8,
            pady=8
        )
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        # Configure color tags
        self.text.tag_configure("prompt", foreground="#ffffff", font=("Consolas", 10, "bold"))
        self.text.tag_configure("cmd", foreground="#ffffff")
        self.text.tag_configure("success", foreground="#4ade80")
        self.text.tag_configure("error", foreground="#f87171")
        self.text.tag_configure("warning", foreground="#fbbf24")
        self.text.tag_configure("info", foreground="#60a5fa")
        self.text.tag_configure("dim", foreground="#888888")

        # Bottom command input line
        input_frame = tk.Frame(self.win, bg="#0c0c0c")
        input_frame.pack(fill="x", side="bottom", padx=6, pady=(0, 6))

        self.prompt_label = tk.Label(
            input_frame, text=self._get_prompt_string(), bg="#0c0c0c", fg="#ffffff", font=("Consolas", 10, "bold")
        )
        self.prompt_label.pack(side="left", padx=(8, 2))

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.entry_var,
            bg="#0c0c0c",
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Consolas", 10),
            relief="flat",
            highlightthickness=0
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=2)
        self.entry.focus_set()

        # Keyboard bindings
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<Up>", self._on_history_up)
        self.entry.bind("<Down>", self._on_history_down)
        self.win.bind("<Control-l>", lambda e: self.cmd_cls())
        self.win.bind("<Control-L>", lambda e: self.cmd_cls())

        # Print startup banner
        self._print_banner()

    def _get_prompt_string(self) -> str:
        return f"C:\\NETWORK\\{self.current_host}>"

    def _update_prompt(self):
        self.prompt_label.configure(text=self._get_prompt_string())
        self.host_var.set(self.current_host)

    def _on_combo_host_selected(self, event=None):
        new_host = self.host_var.get()
        if new_host in self.g.nodes:
            self.current_host = new_host
            self._update_prompt()
            self._write(f"Switched terminal host context to [{new_host}].\n\n", "info")

    def _print_banner(self):
        self._write("Microsoft Windows [Version 10.0.22631.4317]\n", "dim")
        self._write("(c) Microsoft Corporation. Simulated Network Management Terminal.\n\n", "dim")
        self._write(f"Connected to node: {self.current_host} ({self.g.nodes[self.current_host].get('ip', 'No IP')})\n", "info")
        self._write("Type 'help' to view available network commands.\n\n", "dim")

    def _write(self, text: str, tag: Optional[str] = None):
        if tag:
            self.text.insert(tk.END, text, tag)
        else:
            self.text.insert(tk.END, text)
        self.text.see(tk.END)

    def _on_enter(self, event=None):
        raw_cmd = self.entry_var.get().strip()
        self.entry_var.set("")
        if not raw_cmd:
            self._write(self._get_prompt_string() + "\n", "prompt")
            return

        # Add to history
        self.history.append(raw_cmd)
        self.history_idx = len(self.history)

        # Print command line
        self._write(self._get_prompt_string() + " " + raw_cmd + "\n", "prompt")

        # Execute
        self._dispatch_command(raw_cmd)

    def _on_history_up(self, event=None):
        if not self.history:
            return "break"
        if self.history_idx > 0:
            self.history_idx -= 1
            self.entry_var.set(self.history[self.history_idx])
            self.entry.icursor(tk.END)
        return "break"

    def _on_history_down(self, event=None):
        if not self.history:
            return "break"
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self.entry_var.set(self.history[self.history_idx])
            self.entry.icursor(tk.END)
        else:
            self.history_idx = len(self.history)
            self.entry_var.set("")
        return "break"

    def _dispatch_command(self, raw_cmd: str):
        parts = raw_cmd.split()
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd in ("help", "?"):
                self.cmd_help()
            elif cmd in ("cls", "clear"):
                self.cmd_cls()
            elif cmd == "hostname":
                self.cmd_hostname()
            elif cmd in ("connect", "switch"):
                self.cmd_connect(args)
            elif cmd in ("ipconfig", "ifconfig"):
                self.cmd_ipconfig(args)
            elif cmd == "ping":
                self.cmd_ping(args)
            elif cmd in ("tracert", "traceroute"):
                self.cmd_tracert(args)
            elif cmd == "nslookup":
                self.cmd_nslookup(args)
            elif cmd in ("show", "list"):
                self.cmd_show(args)
            elif cmd in ("diagnose", "diag"):
                self.cmd_diagnose()
            elif cmd in ("recover", "rec"):
                self.cmd_recover()
            elif cmd == "approve":
                self.cmd_approve(args)
            elif cmd == "reject":
                self.cmd_reject(args)
            elif cmd == "execute":
                self.cmd_execute_decision(args)
            elif cmd == "monitor":
                self.cmd_monitor(args)
            elif cmd == "exit":
                self.win.destroy()
            else:
                self._write(f"'{cmd}' is not recognized as an internal or external command,\noperable program or batch file. Type 'help' for commands.\n\n", "error")
        except Exception as e:
            self._write(f"Command execution error: {e}\n\n", "error")

    # -------------------------------------------------------------------------
    # Command Implementations
    # -------------------------------------------------------------------------
    def cmd_help(self):
        help_text = """
Simulated Network Diagnostic Terminal Commands:

  help, ?              Show this help menu
  cls, clear           Clear the terminal screen (or Ctrl+L)
  hostname             Display current device name
  connect <device>     Switch active terminal device (e.g., connect PC1, connect Server)
  ipconfig [/all]      Display IP, Subnet Mask, Gateway, and DNS server for current host
  ping <target>        Send ICMP Echo requests to destination host or IP
  tracert <target>     Trace active routing hops to destination host or IP
  nslookup <hostname>  Query DNS resolver for hostname resolution
  show devices         Display list of all network devices in topology
  show links           Display list of all physical links, latency, and loss
  show routes          Display discovered routes from current host
  show decisions       Display all recovery decisions generated by Decision Engine
  show pending         Display decisions awaiting human approval
  show plan            Display current multi-objective recovery plan
  diagnose             Run observation-based root-cause diagnosis
  recover              Execute coordinated automated self-healing recovery
  approve <id>         Approve pending recovery decision (e.g., approve DEC-0001)
  reject <id>          Reject recovery decision (e.g., reject DEC-0001)
  execute <id>         Execute approved recovery decision (e.g., execute DEC-0001)
  monitor <fault_id>   Inspect real-time telemetry and state of specific fault
  exit                 Close the terminal window

"""
        self._write(help_text, "info")

    def cmd_cls(self):
        self.text.delete("1.0", tk.END)

    def cmd_hostname(self):
        self._write(f"{self.current_host}\n\n")

    def cmd_connect(self, args: List[str]):
        if not args:
            self._write("Usage: connect <device_name> (e.g., connect Server)\n\n", "warning")
            return
        target = args[0]
        # Match case-insensitively
        matched = None
        for n in self.g.nodes:
            if n.lower() == target.lower():
                matched = n
                break

        if matched:
            self.current_host = matched
            self._update_prompt()
            self._write(f"Connected to {matched} [{self.g.nodes[matched].get('ip', 'N/A')}].\n\n", "success")
        else:
            self._write(f"Device '{target}' not found in topology. Available: {', '.join(self.g.nodes)}\n\n", "error")

    def cmd_ipconfig(self, args: List[str]):
        d = self.g.nodes.get(self.current_host, {})
        ip = d.get("ip", "192.168.1.10")
        mask = d.get("mask", "255.255.255.0")
        gw = d.get("gateway", "192.168.1.1")
        if gw in self.g.nodes and self.g.nodes[gw].get("type") == "Router":
            gw_ip = self.g.nodes[gw].get("ip")
            if gw_ip:
                gw = gw_ip
        elif gw == "R1":
            gw = "192.168.1.1"
        dns = d.get("dns_server", "192.168.1.1")
        dev_type = d.get("type", "Device")

        out = f"""
Windows IP Configuration

Ethernet adapter Local Area Connection:

   Connection-specific DNS Suffix  . : localdomain
   Device Type . . . . . . . . . . . : {dev_type}
   IPv4 Address. . . . . . . . . . . : {ip}
   Subnet Mask . . . . . . . . . . . : {mask}
   Default Gateway . . . . . . . . . : {gw}
   DNS Server. . . . . . . . . . . . : {dns}

"""
        self._write(out)

    def cmd_show(self, args: List[str]):
        if not args:
            self._write("Usage: show <devices | links | routes>\n\n", "warning")
            return
        sub = args[0].lower()
        if sub in ("devices", "dev"):
            self._write(f"\n{'Name':<12} {'Type':<10} {'IP Address':<18} {'Gateway':<12} {'Status'}\n")
            self._write("-" * 62 + "\n", "dim")
            for n, d in sorted(self.g.nodes(data=True)):
                status = d.get("status", "UP")
                tag = "success" if status == "UP" else "error"
                self._write(f"{n:<12} {d.get('type', 'N/A'):<10} {d.get('ip', 'N/A'):<18} {str(d.get('gateway', 'N/A')):<12} ")
                self._write(f"{status}\n", tag)
            self._write("\n")

        elif sub in ("links", "link"):
            self._write(f"\n{'Link':<16} {'Status':<10} {'Latency':<12} {'Packet Loss':<14} {'Cost'}\n")
            self._write("-" * 62 + "\n", "dim")
            for u, v, d in sorted(self.g.edges(data=True)):
                st = d.get("status", "UP")
                tag = "success" if st == "UP" else "error"
                lat = f"{d.get('latency_ms', 2.0)} ms"
                loss = f"{d.get('packet_loss', 0.0)}%"
                cost = str(d.get("cost", 1))
                self._write(f"{u} <-> {v:<9} ")
                self._write(f"{st:<10} ", tag)
                self._write(f"{lat:<12} {loss:<14} {cost}\n")
            self._write("\n")

        elif sub in ("routes", "route"):
            dest = "Server" if "Server" in self.g.nodes and self.current_host != "Server" else (
                "PC1" if "PC1" in self.g.nodes and self.current_host != "PC1" else list(self.g.nodes)[-1]
            )
            routes = discover_routes(self.g, source=self.current_host, target=dest)
            curr_active = get_active_route(self.g, self.current_host, dest)

            self._write(f"\nDiscovered Routes from {self.current_host} to {dest}:\n")
            self._write(f"{'Path':<36} {'Cost':<6} {'Latency':<10} {'Loss':<8} {'Status':<12} {'Active'}\n")
            self._write("-" * 80 + "\n", "dim")

            for r in routes:
                p_str = " -> ".join(r["path"])
                is_active = "*" if r["path"] == curr_active else ""
                st = "USABLE" if r.get("is_usable") else "DOWN"
                tag = "success" if r.get("is_usable") else "error"
                self._write(f"{p_str:<36} {r.get('cost', 1):<6} {r.get('latency_ms', 0):<10.1f} {r.get('max_loss', 0):<8.1f} ")
                self._write(f"{st:<12} ", tag)
                self._write(f"{is_active}\n", "warning" if is_active else None)
            self._write("\n")
        elif sub in ("decisions", "decision"):
            engine = get_decision_engine()
            decs = engine.get_all_decisions()
            if not decs:
                obs = collect_observations(self.g)
                findings = diagnose(obs)
                decs = engine.evaluate_decisions(self.g, findings)

            self._write(f"\n{'Decision ID':<12} {'Strategy':<32} {'Risk':<6} {'Outcome':<18} {'Status'}\n")
            self._write("-" * 80 + "\n", "dim")
            for d in decs:
                st_color = "success" if d.status == DecisionStatus.APPROVED else ("warning" if d.status == DecisionStatus.PENDING else "error")
                self._write(f"{d.decision_id:<12} {d.strategy.name[:30]:<32} {d.strategy.risk_score:<6} {d.strategy.decision_outcome.value:<18} ")
                self._write(f"{d.status.value}\n", st_color)
            self._write("\n")

        elif sub in ("pending", "pending_approvals"):
            engine = get_decision_engine()
            pending = engine.get_pending_approvals()
            self._write(f"\n{'Decision ID':<12} {'Strategy Name':<34} {'Risk':<6} {'Requires Approval'}\n")
            self._write("-" * 72 + "\n", "dim")
            if not pending:
                self._write("No decisions currently pending human approval.\n\n", "success")
            else:
                for d in pending:
                    self._write(f"{d.decision_id:<12} {d.strategy.name[:32]:<34} {d.strategy.risk_score:<6} YES\n", "warning")
                self._write(f"\nUse 'approve <id>' or 'reject <id> [reason]' to act on pending decisions.\n\n", "info")

        elif sub in ("plan", "recovery_plan"):
            obs = collect_observations(self.g)
            findings = diagnose(obs)
            plan = generate_recovery_plan(self.g, findings)
            self._write("\n" + format_plan_report(plan) + "\n\n", "info")

        else:
            self._write(f"Unknown show command: show {sub}. Try: show devices, show links, show routes, show decisions, show pending, show plan.\n\n", "error")

    def cmd_approve(self, args: List[str]):
        if not args:
            self._write("Usage: approve <decision_id> (e.g., approve DEC-0001)\n\n", "warning")
            return
        did = args[0].upper()
        engine = get_decision_engine()
        ok = engine.approve_decision(did)
        if ok:
            self._write(f"Decision [{did}] APPROVED successfully. You may now 'execute {did}'.\n\n", "success")
            if self.on_state_change:
                self.on_state_change()
        else:
            self._write(f"Failed to approve [{did}]. Verify ID exists with 'show decisions'.\n\n", "error")

    def cmd_reject(self, args: List[str]):
        if not args:
            self._write("Usage: reject <decision_id> [reason] (e.g., reject DEC-0001 High risk)\n\n", "warning")
            return
        did = args[0].upper()
        reason = " ".join(args[1:]) if len(args) > 1 else "Rejected via command prompt"
        engine = get_decision_engine()
        ok = engine.reject_decision(did, reason=reason)
        if ok:
            self._write(f"Decision [{did}] REJECTED: {reason}.\n\n", "warning")
            if self.on_state_change:
                self.on_state_change()
        else:
            self._write(f"Failed to reject [{did}]. Verify ID exists.\n\n", "error")

    def cmd_execute_decision(self, args: List[str]):
        if not args:
            self._write("Usage: execute <decision_id> (e.g., execute DEC-0001)\n\n", "warning")
            return
        did = args[0].upper()
        engine = get_decision_engine()
        res = engine.execute_decision(self.g, did)
        if res.get("success"):
            self._write(f"Decision [{did}] EXECUTED successfully.\nStatus: {res.get('status')}\n\n", "success")
            if self.on_state_change:
                self.on_state_change()
        else:
            self._write(f"Execution failed for [{did}]: {res.get('error')}\n\n", "error")

    def cmd_monitor(self, args: List[str]):
        if not args:
            self._write("Usage: monitor <fault_id> (e.g., monitor FLT-0001)\n\n", "warning")
            return
        fid = args[0].upper()
        reg = get_fault_registry(self.g)
        rec = reg.get_fault(fid)
        if rec:
            self._write(f"\nFault Monitor Telemetry [{fid}]:\n")
            self._write(f"  Type:      {rec.fault_type}\n")
            self._write(f"  Target:    {rec.affected_component}\n")
            st_val = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
            self._write(f"  Status:    {st_val}\n")
            self._write(f"  Params:    {rec.parameters}\n")
            self._write(f"  Timestamp: {time.ctime(rec.timestamp)}\n\n", "info")
        else:
            self._write(f"Fault [{fid}] not found in registry.\n\n", "error")

    def _resolve_target(self, target_arg: str) -> Optional[str]:
        # Match node name directly
        for n in self.g.nodes:
            if n.lower() == target_arg.lower():
                return n
        # Match IP address
        for n, d in self.g.nodes(data=True):
            if d.get("ip") == target_arg:
                return n
        return None

    def cmd_ping(self, args: List[str]):
        if not args:
            self._write("Usage: ping <destination_host_or_ip> (e.g., ping Server, ping 192.168.1.100)\n\n", "warning")
            return

        dest_name = self._resolve_target(args[0])
        if not dest_name:
            self._write(f"Ping request could not find host {args[0]}. Please check the name and try again.\n\n", "error")
            return

        target_ip = self.g.nodes[dest_name].get("ip", "192.168.1.100")
        self._write(f"\nPinging {dest_name} [{target_ip}] with 32 bytes of data:\n\n")

        # Check reachability between current_host and dest_name
        obs = collect_observations(self.g, source=self.current_host, target=dest_name)
        reachable = obs.get("reachability", False)
        active_p = obs.get("active_path") or obs.get("path")
        e2e_lat = obs.get("end_to_end_latency_ms", 10.0)
        e2e_loss = obs.get("path_packet_loss", 0.0)

        # Gateway check on current host
        host_d = self.g.nodes[self.current_host]
        host_gw = host_d.get("gateway", "192.168.1.1")
        gw_router, gw_ok, _ = resolve_gateway_node(self.g, self.current_host, host_gw)

        packets_sent = 4
        packets_received = 0
        latencies = []

        for seq in range(packets_sent):
            # Calculate per-packet simulated loss probability
            loss_prob = (e2e_loss / 100.0) if reachable else 1.0
            import random
            is_lost = (loss_prob >= 0.99) or (random.random() < loss_prob) or not reachable or not gw_ok

            if not is_lost:
                packets_received += 1
                # Small jitter +/- 2ms
                pkt_lat = max(1.0, round(float(e2e_lat) + random.uniform(-1.5, 1.5), 1))
                latencies.append(pkt_lat)
                self._write(f"Reply from {target_ip}: bytes=32 time={pkt_lat}ms TTL=64\n", "success")
            else:
                if not gw_ok:
                    self._write(f"Reply from {host_d.get('ip', '127.0.0.1')}: Destination host unreachable (Invalid Gateway).\n", "error")
                elif not reachable:
                    self._write("Request timed out.\n", "error")
                else:
                    self._write("Request timed out.\n", "error")

        packets_lost = packets_sent - packets_received
        loss_pct = round((packets_lost / packets_sent) * 100.0)

        self._write(f"\nPing statistics for {target_ip}:\n")
        self._write(f"    Packets: Sent = {packets_sent}, Received = {packets_received}, Lost = {packets_lost} ({loss_pct}% loss),\n")
        if latencies:
            min_l = min(latencies)
            max_l = max(latencies)
            avg_l = round(sum(latencies) / len(latencies), 1)
            self._write("Approximate round trip times in milli-seconds:\n")
            self._write(f"    Minimum = {min_l}ms, Maximum = {max_l}ms, Average = {avg_l}ms\n\n")
        else:
            self._write("\n")

    def cmd_tracert(self, args: List[str]):
        if not args:
            self._write("Usage: tracert <destination_host_or_ip> (e.g., tracert Server)\n\n", "warning")
            return

        dest_name = self._resolve_target(args[0])
        if not dest_name:
            self._write(f"Unable to resolve target system name {args[0]}.\n\n", "error")
            return

        target_ip = self.g.nodes[dest_name].get("ip", "192.168.1.100")
        self._write(f"\nTracing route to {dest_name} [{target_ip}]\nover a maximum of 30 hops:\n\n")

        obs = collect_observations(self.g, source=self.current_host, target=dest_name)
        active_p = obs.get("active_path") or obs.get("path")

        if not active_p:
            # Physical partition
            self._write("  1     *        *        *     Request timed out.\n", "error")
            self._write("  2     *        *        *     Request timed out.\n", "error")
            self._write("Trace complete (Destination unreachable).\n\n", "error")
            return

        # Step through hops in active route
        cum_lat = 0.0
        hop_idx = 1
        for u, v in zip(active_p, active_p[1:]):
            edge_d = self.g[u][v]
            st = edge_d.get("status", "UP")
            lat = edge_d.get("latency_ms", 2.0)
            cum_lat += lat

            if st == "DOWN":
                self._write(f"  {hop_idx:<3}   *        *        *     Request timed out [Link {u}-{v} is DOWN].\n", "error")
                self._write("Trace complete (Path broken).\n\n", "error")
                return

            v_ip = self.g.nodes[v].get("ip", "192.168.1.1")
            self._write(f"  {hop_idx:<3}  {cum_lat:<5.1f} ms {cum_lat+0.5:<5.1f} ms {cum_lat-0.3:<5.1f} ms  {v} [{v_ip}]\n", "success")
            hop_idx += 1

        self._write("\nTrace complete.\n\n", "info")

    def cmd_nslookup(self, args: List[str]):
        if not args:
            self._write("Usage: nslookup <hostname> (e.g., nslookup server.local)\n\n", "warning")
            return

        query_host = args[0].strip()
        dns_up = bool(self.g.graph.get("dns_available", True))

        self._write("Server:  dns.google\n")
        self._write("Address: 8.8.8.8\n\n")

        if not dns_up:
            self._write(f"DNS request timed out.\n    timeout was 2 seconds.\n*** Can't find {query_host}: No answer.\n\n", "error")
            return

        # DNS is available, resolve hostname
        resolved_ip = None
        clean_name = query_host.replace(".local", "").replace(".internal", "")
        for n, d in self.g.nodes(data=True):
            if n.lower() == clean_name.lower():
                resolved_ip = d.get("ip")
                break

        if resolved_ip:
            self._write("Non-authoritative answer:\n")
            self._write(f"Name:    {query_host}\n")
            self._write(f"Address: {resolved_ip}\n\n", "success")
        elif "google" in query_host:
            self._write("Non-authoritative answer:\n")
            self._write(f"Name:    {query_host}\n")
            self._write("Address: 142.250.190.46\n\n", "success")
        else:
            self._write(f"*** dns.google can't find {query_host}: Non-existent domain\n\n", "error")

    def cmd_diagnose(self):
        self._write("\n[+] Running network telemetry collection and root-cause diagnosis...\n", "info")
        obs = collect_observations(self.g, source=self.current_host)
        findings = diagnose(obs)
        report = format_diagnosis_report(findings)
        self._write(report + "\n\n")

    def cmd_recover(self):
        self._write("\n[+] Executing coordinated automated recovery and verification...\n", "info")
        res = recover(self.g, source=self.current_host)
        report = format_recovery_report(res)
        self._write(report + "\n\n")
        if self.on_state_change:
            self.on_state_change()
