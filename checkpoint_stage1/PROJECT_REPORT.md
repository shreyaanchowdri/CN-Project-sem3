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

## 4. System Architecture: Strict Four-Stage Separation

The framework is partitioned into four strictly separated, modular stages with clean decoupled data flow:

```
+-----------------------------------------------------------------------------------------+
|                                Cisco Packet Tracer GUI                                  |
|   (Menu Bar, Toolbar, Device Palette, Logical Workspace, Multi-Route Matrix, Inspector) |
+-----------------------------------------------------------------------------------------+
        |                                                                 ^
        | 1. Trigger Injection / Manual Actions                           | 4. Fresh Telemetry
        v                                                                 |    & Verification
+---------------------------+       Virtual State        +--------------------------------+
|   Fault Injection Engine  | -------------------------> | STAGE 1: NETWORK MONITORING    |
|   (Virtual State Changes) |                            | (Telemetry Observations Only)  |
+---------------------------+                            +--------------------------------+
                                                                         |
                                                                         | Raw Observations (Dict)
                                                                         v
+---------------------------+    Targeted Corrective     +--------------------------------+
| STAGE 3 & 4: AUTOMATED    | <------------------------- | STAGE 2: ROOT-CAUSE DIAGNOSIS  |
| RECOVERY & VERIFICATION   |       Action Findings      | (Independent IF-THEN Rules,    |
| (State Change & Re-probe) |                            | Multi-Fault Detection Engine)  |
+---------------------------+                            +--------------------------------+
```

### Four-Stage Architecture Breakdown:

1. **Stage 1: Network Monitoring Module (`monitoring.py`)**:
   - Answers: *"What is happening in the network?"*
   - Strictly derived from actual simulated network telemetry observations without inspecting injected fault names or metadata.
   - Observes: device status, link status, link latencies, link packet loss, endpoint reachability, available paths (`routes`), default gateway validity, DNS resolution status, end-to-end latency, and healthy alternative routes count.
   - Strictly decoupled: does NOT diagnose root causes, recommend recovery, activate routes, or alter network state.
   - Formats dedicated **Report A: Network Monitoring Report**.

2. **Stage 2: Independent Root-Cause Diagnosis Module (`diagnostics.py`)**:
   - Answers: *"Why is the network experiencing this condition?"*
   - Operates strictly on monitoring telemetry, topology, and device configurations. Does NOT read or inspect injected fault names, scenario identifiers, or ground truth.
   - Evaluates all five independent IF-THEN rules without stopping after the first detected fault:
     - **Rule 1 (Link Failure)**: Triggered when observed link status is DOWN. Determines affected link, endpoint connectivity impact, and available alternative routes.
     - **Rule 2 (Wrong Default Gateway)**: Triggered when host gateway configuration is invalid or does not provide next-hop router connectivity. Distinguishes gateway misconfiguration from unrelated link failures.
     - **Rule 3 (DNS Service Failure)**: Triggered when IP connectivity is operational but DNS resolution probe fails.
     - **Rule 4 (High Latency)**: Triggered when observed latency exceeds threshold. Determines whether an alternative path offers lower latency.
     - **Rule 5 (Packet Loss)**: Triggered when observed packet loss exceeds threshold. Determines whether an alternative path offers lower loss.
   - Emits structured `DiagnosticFinding` objects containing: `fault_type`, `affected_device_or_link`, `severity` (CRITICAL, HIGH, MEDIUM, LOW, INFO), `evidence`, calibrated `confidence`, `network_impact`, `endpoint_reachability`, `healthy_alternative_routes`, and `recommended_corrective_action`.
   - Formats dedicated **Report B: Root-Cause Diagnosis Report**.

3. **Stage 3: Fault-Specific Automated Recovery Engine (`recovery.py`)**:
   - Does NOT use alternative-route selection as a universal solution.
   - Implements five distinct, fault-specific recovery strategies:
     - **Link Failure Recovery**: Keeps failed link marked DOWN; discovers available healthy alternative routes; activates the best route in simulated forwarding state (`active_path`); reports recovery unavailable if no alternate route exists.
     - **Wrong Default Gateway Recovery**: Dynamically identifies the correct gateway from topology and addressing; updates the host's configuration; does not reroute around gateway errors or modify unrelated devices.
     - **DNS Service Recovery**: Restores simulated DNS service availability and validates resolver settings.
     - **High Latency Recovery**: Evaluates alternative routes and activates an alternative route ONLY if it strictly improves end-to-end latency; otherwise honestly reports optimization unavailable.
     - **Packet Loss Recovery**: Evaluates alternative routes and activates an alternative route ONLY if it strictly reduces packet loss; otherwise honestly reports recovery unavailable.
   - Records before-and-after states for every corrective action executed.
   - Formats dedicated **Report C: Automated Recovery Report**.

4. **Stage 4: Independent Post-Recovery Verification (`recovery.py`)**:
   - Collects fresh observations post-recovery: endpoint IP reachability, DNS resolution, default gateway validity, active route forwarding status, and performance metrics.
   - Validates fault-specific recovery outcomes (e.g. failed link remains DOWN after failover, gateway validated, DNS operational, latency/loss improved).
   - Generates explicit statuses: `ACTION EXECUTED`, `VERIFICATION PASSED / FAILED`, and `OVERALL RECOVERY STATUS`.
   - Formats dedicated **Report D: Post-Recovery Verification Report**.

5. **Route Discovery vs. Route Activation Separation (`network_model.py`)**:
   - **Discovered Routes**: Loopless candidate paths identified during monitoring.
   - **Recommended Route**: Optimal route evaluated by selection policy.
   - **Activated Route**: Explicit route currently active in simulated forwarding state (`active_path`), activated exclusively by the Recovery engine.

---

## 5. Experimental Results & Verification

The framework was comprehensively validated across 88 automated unit tests executed via Python's standard `unittest` discovery runner:

```text
Ran 88 tests in 26.574s

OK
```

### Verified Test Areas:
1. **Preserved Original Capabilities (64 Tests)**: Cisco Packet Tracer workspace tools, drag-and-drop repositioning, cable connect/disconnect, device/link inspectors, copy/paste/cut/duplicate/undo/redo, zoom/pan, topology JSON serialization, and dynamic custom topologies.
2. **Redesigned Architecture Validation (24 Tests)**:
   - No-fault baseline monitoring, diagnosis, recovery, and verification.
   - Each of the five individual fault scenarios.
   - Multiple simultaneous faults evaluated independently without early stopping.
   - Complete diagnosis independence from injected fault labels and decoy metadata.
   - Evidence-based diagnosis with calibrated confidence values.
   - Severity and network impact classification reflecting actual redundancy.
   - Route discovery without route activation.
   - Route activation exclusively during recovery.
   - Dynamic gateway restoration derived from connected router topology.
   - DNS restoration and independent verification separate from IP connectivity.
   - Latency improvement verification and optimization unavailable reporting.
   - Packet-loss improvement verification and recovery unavailable reporting.
   - Honest reporting of recovery unavailable when no alternative route exists.
   - Prevention of false success reporting on failed recovery.
   - Verification that failed links strictly remain DOWN after failover.
   - Deterministic and consistent diagnosis across repeated executions.
   - Zero side-effects on unrelated network state during recovery.
   - Fresh post-recovery observations and distinct four-report generation.
   - **Service Maintained When Alternate Route Active**: Detects when active forwarding route already avoids failed link; does not perform redundant route changes; reports `SERVICE MAINTAINED`.
   - **Failover Route Activation**: Only switches routes when active route is broken.
   - **Failed Link Without Alternative Route**: Reports `RECOVERY UNAVAILABLE` with `service_availability = UNAVAILABLE` and `network_health = CRITICAL`.
   - **Strict Corrective Action Counting**: Verification is never counted as recovery; zero fake "Baseline verification" actions.
   - **Distinct Service Availability & Network Health**: Accurately reports `AVAILABLE` vs `UNAVAILABLE` and `HEALTHY` vs `DEGRADED` (failed links cause `DEGRADED` health even when alternate routes maintain service) vs `CRITICAL`.
   - Verification that failed links strictly remain DOWN after failover.
   - Deterministic and consistent diagnosis across repeated executions.
   - Zero side-effects on unrelated network state during recovery.
   - Fresh post-recovery observations and distinct four-report generation.

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
