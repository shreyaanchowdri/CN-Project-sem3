# Project Report

## Title
**Design and Development of an Intelligent Network Fault Injection, Observation-Based Root-Cause Diagnosis and Automated Recovery Framework with a Cisco Packet Tracer-Style Network Simulation Workspace**

## Abstract
This project presents an interactive software framework for modelling computer networks, dynamically creating and configuring custom topologies in a Cisco Packet Tracer-style logical workspace, injecting controlled faults, collecting simulated telemetry observations, diagnosing likely root causes using explainable IF-THEN rules, executing automated recovery actions, and verifying post-recovery network conditions. 

The framework provides an engineering-grade desktop interface featuring a top menu bar, multi-tool toolbar (`Select`, `Move`, `Connect`, `Delete`, `Zoom`, `Fit`), a categorized network device palette (Routers, Switches, PCs, Laptops, Servers) with auto-generated unique naming, an interactive logical topology workspace with custom cable rendering and drag-and-drop repositioning, a dockable bottom panel for telemetry, diagnosis, multi-route evaluation, and event logs, and an inspector panel for device and link parameter management. 

The diagnosis engine operates strictly on raw telemetry observations and configuration data, maintaining complete architectural decoupling from injected fault labels. The implementation utilizes Python, NetworkX, Tkinter, and Matplotlib. It operates as a deterministic graph-based network simulation and does not require physical hardware or live packet forwarding.

---

## 1. Introduction
Computer networks depend upon sound topological design, consistent addressing, robust routing protocols, link availability, and operational supporting services such as DNS. A fault in any subsystem—such as a severed trunk link, a misconfigured default gateway, an unresponsive DNS resolver, or severe congestion leading to packet loss—can severely disrupt communication. Troubleshooting such issues in enterprise environments requires multi-layered observation: evaluating physical/data-link connectivity, verifying IP routing reachability, assessing end-to-end latency, and auditing DNS resolution.

This project delivers an interactive Cisco Packet Tracer-inspired simulation environment enabling students, instructors, and network engineers to visually construct complex network topologies, simulate hardware and protocol failures, observe telemetry metrics, and witness deterministic, explainable root-cause diagnosis and automated recovery in real time.

---

## 2. Problem Statement
Traditional network diagnosis in academic and enterprise labs is hindered by two distinct challenges:
1. **Tool Fragmentation & Usability Barriers**: Existing tools either provide abstract CLI-only simulation (e.g., standard Python scripts) or complex emulation requiring kernel virtualization and elevated privileges (e.g., Mininet, GNS3). Users require a lightweight, interactive visual environment with an intuitive Cisco Packet Tracer-style workflow (device palettes, cable connections, inspectors, and drag-and-drop placement).
2. **Artificial Coupling in Automated Diagnosis**: Many automated diagnostic prototypes rely on machine learning black boxes or cheat by directly reading injected fault labels. A genuine diagnostic engine must operate strictly on observable symptoms (link states, round-trip times, loss rates, configuration audits, DNS probes) without knowing which fault was injected.

---

## 3. Objectives
1. **Cisco Packet Tracer-Inspired Workspace**: Implement a desktop interface with a top menu bar, tool selectors (`Select`, `Move`, `Connect`, `Delete`), zoom/pan controls, a categorized device palette (Routers, Switches, PCs, Laptops, Servers), and a dockable telemetry/diagnosis/event panel.
2. **Dynamic Topology & Cable Management**: Provide two-click cable connection workflows supporting multiple cable types (Copper Straight-Through, Copper Cross-Over, Fiber, Serial) with strict duplicate and self-connection prevention.
3. **Interactive Visual Topology**: Enable smooth drag-and-drop positioning for all devices, dynamic viewport auto-expansion, status-coded links (Green `UP`, Red `DOWN`, Orange `DEGRADED`), and luminous selection halos.
4. **Device & Link Inspector**: Enable live inspection and modification of device configurations (Name, Type, IP, Subnet Mask, Gateway, DNS) and link parameters (Cable Type, Cost, Latency, Packet Loss, Status).
5. **Topology Persistence**: Enable JSON serialization and deserialization that faithfully restores device types, IP parameters, link attributes, and exact 2D workspace coordinates.
6. **Observation-Based Root-Cause Diagnosis**: Implement an independent diagnosis engine that analyzes strictly telemetry observations without reading injected fault labels or scenario names.
7. **Multi-Route Discovery & Evaluation**: Discover all simple loopless paths between arbitrary source and destination endpoints, calculating cumulative cost, total latency, and maximum loss.
8. **Automated Recovery & Verification**: Execute targeted repairs and failover routing based on diagnosed causes, followed by an independent post-recovery telemetry scan to verify IP reachability and DNS resolution.
9. **Cisco Packet Tracer-Style Productivity & Clipboard Operations**: Implement complete keyboard-driven workspace management including Copy (`Ctrl+C`), Paste (`Ctrl+V`), Cut (`Ctrl+X`), Duplicate (`Ctrl+D`), Select All (`Ctrl+A`), Multi-Selection (`Ctrl+Click`), and Multi-Level Undo/Redo (`Ctrl+Z` / `Ctrl+Y`) with safe text input protection.
10. **Rigorous Automated Testing**: Ensure 100% test pass rate across all functional modules, covering baseline routing, dynamic topologies, drag-and-drop, observation-based diagnosis, recovery, and GUI operations.

---

## 4. System Architecture

The framework is partitioned into four independent components with strictly decoupled data flow:

```
+-----------------------------------------------------------------------+
|                         Cisco Packet Tracer GUI                       |
|  (Menu Bar, Toolbar, Device Palette, Logical Workspace, Inspector)   |
|  - Clipboard Engine (Copy, Paste, Cut, Duplicate)                     |
|  - Multi-Selection (Ctrl+Click, Group Drag, Layout Preservation)      |
|  - State History Manager (Undo / Redo Stack)                          |
+-----------------------------------------------------------------------+
        |                                                 ^
        v                                                 |
+---------------------+     Virtual State     +-------------------------+
|   Fault Injection   | --------------------> |   Network Monitoring    |
|       Engine        |                       |   & Telemetry Engine    |
+---------------------+                       +-------------------------+
                                                           |
                                                Structured | Telemetry
                                               Observation | Data
                                                           v
+---------------------+     Targeted Repair   +-------------------------+
| Automated Recovery  | <-------------------- | Independent Observation |
| & Verification Eng. |      Action Plan      |   Root-Cause Diagnosis  |
+---------------------+                       +-------------------------+
```

### Module Breakdown:
1. **Network Model (`network_model.py`)**:
   - Manages NetworkX graph representation of nodes and edges.
   - Supports 5 device types: `PC`, `Laptop`, `Router`, `Switch`, `Server`.
   - Supports 4 connection types: `Copper Straight-Through`, `Copper Cross-Over`, `Fiber`, `Serial`.
   - Auto-generates unique device identifiers (`Router1`, `Switch1`, `PC1`, `Laptop1`, `Server1`).
   - Implements multi-route discovery using depth-first search of simple paths.
   - Evaluates path cost, latency, packet loss, and availability status (`Healthy`, `Degraded`, `Unavailable`).
   - Implements JSON serialization and deserialization for topology persistence.
2. **Fault Injection Engine (`fault_injection.py`)**:
   - Modifies virtual network state (e.g. marking links `DOWN`, changing host gateway to invalid router, disabling simulated DNS, inflating latency >100ms, or introducing packet loss >0%).
   - Supports default baseline scenarios as well as dynamic targeting of arbitrary user-created links and devices.
   - Operates strictly in the state domain and never passes fault metadata to the diagnosis engine.
3. **Monitoring & Telemetry Engine (`monitoring.py`)**:
   - Scans the network graph to produce a structured observation dictionary:
     - `reachability`: Boolean end-to-end path availability.
     - `down_links` & `down_edges`: Exact physical links with `status != 'UP'`.
     - `high_latency`: Links exceeding latency threshold (100 ms).
     - `packet_loss`: Links exceeding packet loss threshold (0.0%).
     - `invalid_gateways`: Configuration audit identifying nonexistent gateways, non-router gateways, or unreachable gateways.
     - `dns_ok`: Boolean DNS service availability.
     - `routes` & `route_selection`: Candidate paths, ranking, and optimal path selection.
4. **Independent Root-Cause Diagnosis Engine (`diagnostics.py`)**:
   - Evaluates raw observations using deterministic IF-THEN rules:
     - **Rule 1 (Link Failure)**: Triggered if `down_links` is non-empty. Confidence: 1.0 (100%).
     - **Rule 2 (Gateway Mismatch)**: Triggered if `invalid_gateways` audit fails. Confidence: 0.98 (98%).
     - **Rule 3 (DNS Failure)**: Triggered if `reachability` is True but `dns_ok` is False. Confidence: 0.95 (95%).
     - **Rule 4 (High Latency)**: Triggered if observed path/link latency > 100 ms. Confidence: 0.90 (90%).
     - **Rule 5 (Packet Loss)**: Triggered if observed path/link packet loss > 0%. Confidence: 0.92 (92%).
   - Emits rich `DiagnosticFinding` objects containing root cause, evidence, affected components, severity, confidence, and recommended action.
5. **Automated Recovery and Verification Engine (`recovery.py`)**:
   - Translates diagnosed root causes into targeted simulated repairs:
     - Corrects default gateways across affected PCs and Laptops.
     - Restores simulated DNS service.
     - Reroutes traffic over alternate healthy paths avoiding failed or degraded links.
   - Executes an independent post-repair observation scan, verifying both IP connectivity and DNS resolution.
6. **User Interface & Workspace Management (`main.py`)**:
   - Complete Cisco Packet Tracer visual environment with tool modes (`select`, `move`, `connect`, `delete`), zoom/pan controls, device palette, real-time Matplotlib canvas, inspector panels, and multi-tab bottom output.
   - **Responsive Two-Row Toolbar**: Organizes controls into Tier 1 (workspace editing, clipboard shortcuts, zoom, health pill badge) and Tier 2 (simulation control strip with full-width scenario dropdown `width=30`, `height=6` displaying all six fault scenarios cleanly without button collision).
   - **Internal Clipboard Architecture**: Supports Copy (`Ctrl+C`), Paste (`Ctrl+V`), Cut (`Ctrl+X`), and Duplicate (`Ctrl+D`). Deep-copies device configurations while isolating clipboard instances from existing links. Repeated pastes employ cascading coordinate offsets with auto-incremented naming.
   - **Multiple Selection**: Enables `Ctrl+Click` multi-node selection, highlighted with dual luminous selection halos. Supports group drag-and-drop and group copy/paste while strictly preserving relative $(dx, dy)$ spatial topology.
   - **Undo/Redo State History**: Manages a 30-level reversible snapshot stack (`Ctrl+Z`, `Ctrl+Y`) tracking device creations, removals, link connections, cuts, and repositioning.
   - **Text Input Focus Safety Guard**: Dispatches keyboard shortcuts selectively, preventing canvas shortcut interception while users edit entry boxes or parameter fields.

---

## 5. Experimental Results & Verification

The framework was rigorously validated across 62 automated unit tests executed via Python's standard `unittest` discovery runner:

```text
Ran 62 tests in 20.323s

OK
```

### Verified Functional Areas:
1. **Cisco Packet Tracer Usability**: Palette auto-naming, Laptop device integration, cable connection workflow, duplicate/self-connection prevention, tool switching, zoom in/out, fit to screen, device and link Inspector editing.
2. **Workspace Productivity & Clipboard Operations**: Copy/paste single and multiple devices with configuration retention, zero link duplication, repeated paste cascading offsets, cut device and incident links, duplicate device, undo/redo state restoration, and text field keyboard event isolation.
3. **Simulation & Fault Scenario Controls**: Full fault dropdown coverage for all six UI scenarios (`No Fault – Healthy Baseline`, `Link Failure`, `Wrong Default Gateway`, `DNS Service Failure`, `High Network Latency`, `Packet Loss`), complete name visibility with width 30 and height 6, canonical backend mapping, and non-overlapping responsive layout.
4. **Dynamic Topologies**: Custom device addition/removal, connection creation/disconnection, dynamic route discovery, and JSON save/load coordinate preservation.
5. **Observation-Based Diagnosis**: Zero reliance on scenario labels, resilience to fake decoy labels, calibrated confidence levels, and multi-fault detection.
6. **Automated Recovery**: Targeted configuration repairs, backup path failover, and dual IP/DNS post-recovery verification.

---

## 6. Technical Limitations & Scope
- **Graph Simulation**: Network state is modeled mathematically as a graph via NetworkX. The system does not configure real hardware interfaces or emit live Ethernet packets.
- **Deterministic Rules**: Diagnosis is 100% deterministic and explainable without probabilistic machine learning.
- **Platform Compatibility**: Built with cross-platform Python 3.10+, Tkinter, and Matplotlib, running natively without requiring administrative privileges.

---

## 7. Conclusion
The Intelligent Network Fault Diagnosis and Automated Recovery Framework successfully merges the intuitive layout of Cisco Packet Tracer with an explainable, observation-based root-cause diagnosis engine and automated recovery system. It provides a complete educational platform for network modeling, fault injection, telemetry monitoring, multi-path routing, and automated network self-healing.
