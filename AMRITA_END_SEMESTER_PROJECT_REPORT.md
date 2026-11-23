# AMRITA VISHWA VIDYAPEETHAM
### School of Computing, Bengaluru
### END-SEMESTER PROJECT REPORT
**23AID206 – INTRODUCTION TO COMPUTER NETWORKS**

---

## PROJECT TITLE
**Design and Development of an Intelligent Network Fault Injection, Root-Cause Diagnosis and Automated Recovery Framework**

**Submitted by:**  
**Shreyan Chowdhuri** (Registration No: `BL.EN.U4AIE23001` / *Enter Reg No*)  

**Academic Term:** November 2026  

---

### DECLARATION
We hereby declare that the project work presented in this report is our original work carried out as part of **23AID206 – Introduction to Computer Networks**. All sources of information, references, software libraries, and theoretical frameworks used have been duly acknowledged and cited.

**Student Signature(s):** ______________________________________________  
**Date:** November 23, 2026  

---

### EVALUATION SHEET
The Project work is evaluated on: ………………………………………………..

| Design & Simulator Selection (5) | Implementation (12) | Viva (5) | Viva (3) | Results & Inference (5) | Total (30) |
|---|---|---|---|---|---|
| | | | | | |

**Faculty-in-Charge:** ____________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Signature with Date:** ______________

---

## ABSTRACT
This project presents an Intelligent Network Fault Diagnosis and Automated Recovery Framework developed in Python using Tkinter, NetworkX, and Matplotlib. Combining an interactive Cisco Packet Tracer-style logical topology workspace with a simulated Windows command-line diagnostic terminal (`network_terminal.py`), the framework allows users to construct multi-hop topologies (such as `PC1`, `PC2`, routers `R1`–`R3`, and `Server`), select configurable source and destination endpoints (including `PC1` $\rightarrow$ `Server`, `PC1` $\rightarrow$ `PC2`, and local loopback), inject heterogeneous single and multi-fault scenarios, and execute a closed-loop **Observe $\rightarrow$ Diagnose $\rightarrow$ Plan $\rightarrow$ Recover $\rightarrow$ Verify** operational workflow.

During monitoring and diagnosis, the system evaluates real-time telemetry—including end-to-end reachability, latency, probabilistic path packet loss ($P_{\text{loss}} = 1 - \prod(1 - p_i)$), gateway validity, DNS availability, and physical interface states—to identify primary root causes with calibrated confidence scores ($0.90\text{--}1.00$) and explainable rule-based evidence without ground-truth cheating. During recovery and verification, the framework optimizes alternative routes using multi-objective Pareto scoring (balancing cost, latency, and loss), enforces realistic physical fault bypass (severed links remain strictly `DOWN`), truthfully reports `RECOVERY UNAVAILABLE` when partitions exist, transmits configurable probe-packet bursts ($5$, $10$, or $20$ packets) along the active path, and executes a rigorous 7-point post-recovery verification audit with execution reporting (`EXEC-XXXX`). The framework is validated across a 200-test automated regression suite achieving a $100\%$ pass rate with zero errors.

---

## TABLE OF CONTENTS
1. [CHAPTER 1: INTRODUCTION](#chapter-1-introduction)
   - 1.1 Background
   - 1.2 Motivation
   - 1.3 Problem Statement
   - 1.4 Objectives
   - 1.5 Scope
2. [CHAPTER 2: NETWORK DESIGN AND REQUIREMENTS](#chapter-2-network-design-and-requirements)
   - 2.1 Overview of the Proposed Network
   - 2.2 Network Requirements
   - 2.3 Network Devices and Components
   - 2.4 Network Topology
   - 2.5 IP Addressing Scheme
   - 2.6 Protocols and Network Services
3. [CHAPTER 3: IMPLEMENTATION](#chapter-3-implementation)
   - 3.1 Tools and Environment
   - 3.2 Network Topology Implementation
   - 3.3 Device Configuration
   - 3.4 IP Configuration
   - 3.5 Routing and Switching Configuration
   - 3.6 Network Services Configuration
   - 3.7 Implementation Evidence
4. [CHAPTER 4: TESTING AND RESULTS](#chapter-4-testing-and-results)
   - 4.1 Testing Methodology
   - 4.2 Connectivity Testing
   - 4.3 Simulation and Packet Analysis
   - 4.4 Results and Observations
   - 4.5 Performance, Reliability, and Security Considerations
5. [CHAPTER 5: CONCLUSION](#chapter-5-conclusion)
   - 5.1 Summary
   - 5.2 Learning Outcomes
   - 5.3 Limitations
   - 5.4 Future Enhancements
6. [REFERENCES](#references)
7. [APPENDIX](#appendix)

---

## LIST OF FIGURES
* **Figure 2.1:** Diamond Core Multi-Path Network Architecture with Dual Redundant Transit Routers (`R2`, `R3`).
* **Figure 3.1:** Cisco Packet Tracer-Style Visual Workspace with Responsive KPI Bar and 8-Tab Operator Notebook.
* **Figure 3.2:** Windows CMD-Style Simulated Diagnostic Terminal (`network_terminal.py`) executing `ping` and `tracert`.
* **Figure 3.3:** Six Real-Time Telemetry Analytics Graphs (Latency, Packet Loss, Availability, Outages, MTTR, Route Comparison).
* **Figure 4.1:** Automated Multi-Fault Diagnosis and Degraded Service Maintenance Verification Screen.

---

## LIST OF TABLES
* **Table 2.1:** Complete IPv4 Addressing Scheme, Subnet Masks, Gateways, and Interface Allocations.
* **Table 2.2:** Network Protocols and Layered Communication Services Implemented.
* **Table 3.1:** Software Architecture and Module Responsibility Mapping.
* **Table 4.1:** Master Functional Test Results and Verification Status (TC-01 to TC-08).
* **Table 4.2:** 7-Point Independent Verification Audit Criteria and Outcomes.

---

# CHAPTER 1: INTRODUCTION

### 1.1 Background
Computer networks form the fundamental communications backbone for modern distributed applications, enterprise computing, and cloud data centers. In these environments, communication depends upon a tightly coordinated stack of protocols operating across physical links, switching fabrics, network routing planes, and application services. As networks expand in complexity and scale, they are subjected to diverse hardware failures, physical cable cuts, transceivers burning out, administrative misconfigurations (such as incorrect default gateways or erroneous subnet masks), DNS daemon crashes, bufferbloat latency spikes, and interface packet dropping. Ensuring high network reliability requires continuous telemetry monitoring, explainable root-cause diagnosis, and rapid remediation to prevent localized failures from escalating into catastrophic service outages.

### 1.2 Motivation
In traditional Network Operations Centers (NOC), network triage is largely manual, reactive, and slow. Operators sequentially execute disconnected command-line diagnostics such as `ping`, `traceroute`, and SNMP interface queries to locate problems. This manual approach inflates the Mean Time to Detect (MTTD) and Mean Time to Recover (MTTR). While recent academic research has explored autonomic self-healing using deep learning, these black-box AI models lack interpretability, demand massive training datasets, and can behave unpredictably during unseen topological shifts. Furthermore, educational network simulators (such as standard Packet Tracer scripts) frequently compromise architectural fidelity by "cheating"—inspecting internal software fault variables rather than real telemetry—and perform "fake repairs" by magically toggling severed cables back to `UP`. There is a compelling need for a deterministic, fully explainable, zero-machine-learning self-healing network management framework that operates on pure telemetry and performs authentic physical fault bypass.

### 1.3 Problem Statement
The objective is to design, implement, and validate an automated network simulation, fault injection, root-cause diagnosis, and self-healing framework capable of handling concurrent, heterogeneous network anomalies. The system must support diverse end devices, intermediate switches, multi-interface routers, and enterprise servers. It must decouple fault injection from telemetry observation, evaluate all failure modes in parallel without early short-circuiting, assign mathematically calibrated evidentiary confidence scores ($0.90\text{--}1.00$), reroute traffic across optimal alternative paths using multi-objective optimization, truthfully report when complete network partitions render recovery unfeasible, and verify network restoration through active probe packet bursts and a 7-point independent audit.

### 1.4 Objectives
1. **Design a software-based virtual network environment:** Develop an authoritative, graph-theoretic network model using NetworkX to simulate nodes and links with real-world latency, cost, and loss attributes.
2. **Simulate network devices and physical links:** Model computers (`PC1`, `PC2`), routers (`R1`–`R3`), switches, and enterprise servers with full IP addressing, gateway, and DNS configuration.
3. **Implement a transactional fault injection system:** Build an atomic batch fault injection engine supporting link cuts, invalid gateways, DNS outages, latency spikes, and packet loss with rollback safety.
4. **Support diverse network failure scenarios:** Allow single and simultaneous combinations of physical, configuration, and performance faults.
5. **Design an explainable, rule-based diagnostic engine:** Formulate deterministic diagnostic algorithms that produce calibrated confidence ratings without black-box ML.
6. **Gather and analyze real-time diagnostic telemetry:** Collect passive interface metrics and active synthetic probes without reading ground-truth fault injection flags.
7. **Recommend and execute remedial solutions:** Formulate dependency-ordered recovery plans and compute optimal alternative routes using multi-objective Pareto optimization.
8. **Verify network resolution through active connectivity testing:** Execute an independent 7-point post-recovery verification audit and transmit live probe packet batches ($5$, $10$, or $20$ packets) with round-trip tracking.
9. **Evaluate framework performance:** Measure root-cause accuracy, false positive rate, diagnostic latency, and recovery MTTR across 200 automated unit tests.
10. **Provide an interactive visual and command-line user interface:** Deliver an interactive Cisco Packet Tracer-style visual canvas paired with an authentic Windows CMD-style simulated diagnostic terminal.

### 1.5 Scope
The project encompasses Layer-2 switching concepts, Layer-3 IP addressing, static and dynamic multi-path routing, ICMP active probing, DNS client-server resolution, and probabilistic packet loss modeling. The implementation is self-contained in pure Python without external cloud or hardware dependencies. It assumes intra-domain enterprise network boundaries. Physical hardware provisioning, BGP inter-domain autonomous system peering, and wireless RF fading channels are outside the current scope.

---

# CHAPTER 2: NETWORK DESIGN AND REQUIREMENTS

### 2.1 Overview of the Proposed Network
The proposed network models an enterprise intranet connecting client workstations (`PC1`, `PC2`) situated on an access subnet to an enterprise application server (`Server`) situated in a centralized data center network. Interconnection is achieved through a multi-path core topology featuring a primary gateway router (`R1`) and two redundant transit routers (`R2` and `R3`), establishing redundant primary and backup paths.

### 2.2 Network Requirements
* **Functional Requirements:** Dynamic node and link addition/deletion; atomic multi-fault injection; passive and active telemetry monitoring; rule-based root-cause diagnosis; multi-objective route failover; post-recovery verification; and dual visual/terminal user interfaces.
* **Non-Functional Requirements:** Deterministic execution (100% reproducible outcomes); sub-millisecond diagnosis time; zero machine learning overhead; modular architectural decoupling; and transactional state safety with automated snapshot rollback on failure.

### 2.3 Network Devices and Components
* **End Workstations (`PC1`, `PC2`, `Laptop`):** Generate network traffic; configured with IPv4 addresses, subnet masks, default gateways pointing to `R1`, and DNS resolver addresses.
* **Primary Gateway Router (`R1`):** Serves as the default gateway for local client subnets; evaluates routing paths across core transit routers.
* **Transit Core Routers (`R2`, `R3`):** Provide redundant Layer-3 transit conduits between `R1` and the data center network (`R2` represents the primary path; `R3` represents the secondary/backup path).
* **Enterprise Application Server (`Server`):** Acts as the target destination hosting enterprise HTTP and DNS services.
* **Transmission Links:** Bidirectional physical conduits parameterized by operational status (`UP`/`DOWN`), propagation latency ($L \in [1, 500]\text{ ms}$), probabilistic drop rate ($p \in [0.0, 1.0]$), and cost.

### 2.4 Network Topology
The core baseline topology adopts a **Diamond Multi-Path Core Architecture**:

```
                 +-------------------+
                 |    Router R2      |
                 | (Primary Transit) |
                 |    10.0.1.1/24    |
                 +-------------------+
                /                     \
   [Cost 1, 3ms]                       [Cost 1, 3ms]
              /                         \
+-----------+                             +---------------+
|  Host PC1 |---[Cost 1, 2ms]---+         | Server (SRV)  |
| 192.168.1.10                   |         | 172.16.0.10   |
+-----------+                    |         +---------------+
                                 v          /
                 +-------------------+     /
                 |    Router R1      |    /
                 | (Default Gateway) |   /
                 |   192.168.1.1/24  |  /
                 +-------------------+ /
                        \             /
                   [Cost 2, 4ms]  [Cost 2, 4ms]
                          \         /
                 +-------------------+
                 |    Router R3      |
                 | (Backup Transit)  |
                 |    10.0.2.1/24    |
                 +-------------------+
```
*Figure 2.1: Diamond Core Multi-Path Network Architecture.*

*Primary Forwarding Route:* `PC1 -> R1 -> R2 -> Server` (Total Cost: 3, Latency: 8.0 ms, Loss: 0.0%)  
*Backup Forwarding Route:* `PC1 -> R1 -> R3 -> Server` (Total Cost: 5, Latency: 10.0 ms, Loss: 0.0%)

### 2.5 IP Addressing Scheme

| Device / Host | Interface | IP Address | Subnet Mask / Prefix | Default Gateway | Function / Role |
|---|---|---|---|---|---|
| **PC1** | eth0 | 192.168.1.10 | 255.255.255.0 (/24) | 192.168.1.1 | Client Workstation 1 |
| **PC2** | eth0 | 192.168.1.11 | 255.255.255.0 (/24) | 192.168.1.1 | Client Workstation 2 |
| **R1** | Fa0/0 (LAN) | 192.168.1.1 | 255.255.255.0 (/24) | N/A | Local Subnet Gateway |
| **R1** | Gi0/1 (WAN1) | 10.0.1.2 | 255.255.255.0 (/24) | N/A | Primary Transit Uplink |
| **R1** | Gi0/2 (WAN2) | 10.0.2.2 | 255.255.255.0 (/24) | N/A | Backup Transit Uplink |
| **R2** | Gi0/1 (WAN1) | 10.0.1.1 | 255.255.255.0 (/24) | N/A | Primary Transit Core |
| **R2** | Gi0/2 (LAN) | 172.16.0.1 | 255.255.255.0 (/24) | N/A | Server Subnet Uplink |
| **R3** | Gi0/1 (WAN2) | 10.0.2.1 | 255.255.255.0 (/24) | N/A | Backup Transit Core |
| **R3** | Gi0/2 (LAN) | 172.16.1.1 | 255.255.255.0 (/24) | N/A | Server Subnet Uplink |
| **Server** | eth0 | 172.16.0.10 | 255.255.255.0 (/24) | 172.16.0.1 | Enterprise Data Server |

*Table 2.1: Complete IPv4 Addressing Scheme.*

### 2.6 Protocols and Network Services
* **Ethernet (IEEE 802.3):** Layer-2 data link framing, cable typing (Copper Straight-Through, Cross-Over, Fiber).
* **Internet Protocol version 4 (IPv4):** Layer-3 addressing, subnetting, and hop-by-hop forwarding.
* **Internet Control Message Protocol (ICMP):** Echo Request/Reply active probing for reachability and RTT measurement.
* **Domain Name System (DNS):** Application-layer name resolution mapping `server.local` to `172.16.0.10` over UDP port 53.
* **Dynamic Routing Optimization:** Multi-objective shortest path routing based on Dijkstra's algorithm augmented with normalized latency and probabilistic loss scoring.

---

# CHAPTER 3: IMPLEMENTATION

### 3.1 Tools and Environment
* **Programming Language:** Python 3.10+ (Standard Library: `tkinter`, `json`, `time`, `math`, `unittest`).
* **Graph Modeling Engine:** `networkx` (v3.0+) for topology representation and connected-component analysis.
* **Data Visualization:** `matplotlib` (v3.7+) embedded within Tkinter canvas frames.
* **Development Environment:** Visual Studio Code / Antigravity IDE on Windows 11.

### 3.2 Network Topology Implementation
The network graph $G = (V, E)$ is instantiated using `network_model.py`. Nodes $v \in V$ store configuration dictionaries, while edges $e = (u, v) \in E$ store transmission parameters:
```python
g.add_node("PC1", type="PC", ip="192.168.1.10", subnet_mask="255.255.255.0", gateway="R1")
g.add_edge("R1", "R2", cost=1, latency_ms=3.0, packet_loss=0.0, status="UP")
```

### 3.3 Device Configuration
Devices support dynamic parameter configuration via GUI inspectors (`Device Config` tab) and terminal commands. Workstations possess default gateway pointers; routers maintain forwarding tables; servers host DNS daemons.

### 3.4 IP Configuration
IP address assignment and validation are enforced through `network_model.py`. When a host default gateway is modified, the diagnostic engine audits whether the gateway IP matches the router interface on the host's broadcast domain.

### 3.5 Routing and Switching Configuration
Routing discovery is implemented in `network_model.py` using `discover_routes(g, source, target)`. The algorithm discovers all loop-free candidate paths using depth-first search. The optimal path $r^*$ is selected via normalized multi-objective scoring:
$$\mathcal{S}(r) = w_c \cdot \hat{C}(r) + w_l \cdot \hat{L}(r) + w_p \cdot \hat{P}(r)$$
where hop cost $\hat{C}$, latency $\hat{L}$, and loss $\hat{P}$ are min-max normalized.

### 3.6 Network Services Configuration
DNS service availability is modeled as a global state variable `g.graph["dns_available"]`. Workstation name lookups trigger simulated UDP port 53 socket probes. If `dns_available == False`, resolution fails with `DNS_TIMEOUT`.

### 3.7 Implementation Evidence

```
+----------------------------------------------------------------------------------------------------+
| Cisco Packet Tracer - Intelligent Network Fault Diagnosis & Recovery Workspace                     |
+----------------------------------------------------------------------------------------------------+
| [Select] [Move] [Connect] [Delete] | Undo Redo Copy Paste | [Source: PC1] [Target: Server] [Pkt: 5]|
+----------------------------------------------------------------------------------------------------+
| DEVICES: 5 | LINKS: 5 | FAULTS: 0 | CRITICAL: 0 | AVAILABILITY: AVAILABLE | HEALTH: DEGRADED           |
+----------------------------------------------------------------------------------------------------+
| (Visual Topology Canvas)                               | (Right Inspector: Device & Link Config)   |
|   PC1 [192.168.1.10] ---> R1 [192.168.1.1]             | Selected Link: R2 <-> Server              |
|                             /         \                | Status: UP | Loss: 33.0% | Latency: 3ms   |
|                 (R2: 33% Loss)       (R3: DOWN)        | [Apply Changes] [Disconnect Link]         |
|                             \         /                +-------------------------------------------+
|                          Server [172.16.0.10]          | (Tabs: Overview | Multi-Fault | Active)   |
+----------------------------------------------------------------------------------------------------+
| (Bottom Operator Tabs: Diagnosis & Telemetry | Recovery & Verification | Analytics & Trends)       |
| === AUTOMATED RECOVERY REPORT ===                                                                  |
| Recovery Status : SERVICE MAINTAINED | Actions Executed : 0                                         |
| Reason : A surviving alternative route was active, but operates in degraded condition.             |
| Probe Transmission : 5 sent, 3 delivered, 2 dropped (60.0% delivery rate)                          |
+----------------------------------------------------------------------------------------------------+
```
*Figure 3.1: Diagrammatic Layout of the Running GUI Application.*

---

# CHAPTER 4: TESTING AND RESULTS

### 4.1 Testing Methodology
The framework was evaluated through a two-tiered testing methodology:
1. **Automated Unit & Regression Suite (`tests/test_project.py`):** 200 automated test cases exercising all functional modules across 10 stages (Stages 0 through 10).
2. **Interactive GUI & Terminal Scenario Verification:** Live execution of Demonstration Scenarios A through H, evaluating visual halo indicators, real-time Matplotlib trends, and CMD CLI responsiveness.

### 4.2 Connectivity Testing
Connectivity testing was executed from `network_terminal.py` and GUI action bars across nominal, degraded, and partitioned states:
* `ping Server`: Nominal baseline yields $100\%$ delivery (4 packets transmitted, 4 received, RTT $\approx 8\text{ ms}$).
* `tracert Server`: Traces active forwarding hops (`192.168.1.1` $\rightarrow$ `10.0.1.1` $\rightarrow$ `172.16.0.10`).
* `nslookup server.local`: Resolves to `172.16.0.10` via simulated resolver `192.168.1.1:53`.

### 4.3 Simulation and Packet Analysis
When `Recover & Verify` executes, the system transmits a configurable burst of probe packets ($5$, $10$, or $20$) from `Source` to `Target`. During degraded operation on `R2-Server` ($33\%$ packet loss), probe packets #1 and #5 drop with `DROPPED_PACKET_LOSS`, while packets #2, #3, and #4 deliver with RTT $\approx 8.0\text{ ms}$ ($60\%$ delivery rate), confirming probabilistic fidelity.

### 4.4 Results and Observations

| Test ID | Test Description | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| **TC-01** | Baseline Nominal Connectivity | PC1 $\rightarrow$ Server reachable via R2; 0% loss; RTT 8ms | Reachable via R1-R2-Server; 0% loss; 8.0ms RTT | **PASS** |
| **TC-02** | Physical Link Failure (`R2-Server`) | Failover to alternate route R1-R3-Server; R2-Server stays DOWN | Rerouted over R3; R2-Server remains DOWN | **PASS** |
| **TC-03** | Invalid Gateway Injection | Diagnosed (98% confidence); restored to valid router R1 | Gateway corrected to R1; 100% reachability | **PASS** |
| **TC-04** | DNS Daemon Crash Injection | Diagnosed (95% confidence); service restarted | Resolver restored; nslookup succeeds | **PASS** |
| **TC-05** | Degraded Packet Loss (33%) | Evaluates lower-loss alternate route; maintains surviving path | Reroutes if alternate path is cleaner; verifies loss | **PASS** |
| **TC-06** | Complete Network Partition | R2 & R3 down; reports `RECOVERY UNAVAILABLE` with 0 actions | `RECOVERY UNAVAILABLE`; honest partition report | **PASS** |
| **TC-07** | Custom Probe Bursts (5, 10, 20) | Transmits exact requested packet volume with drop logs | Transmitted exact count; per-packet tracking | **PASS** |
| **TC-08** | Same-Node Loopback (`PC1 -> PC1`) | Treated cleanly as local loopback (0.1ms, 0% loss) | `PC1 (Local Loopback)` verified with 100% delivery | **PASS** |

*Table 4.1: Master Functional Test Results.*

### 4.5 Performance, Reliability, and Security Considerations
* **Performance:** Sub-millisecond diagnostic reasoning ($<0.001\text{ s}$ execution time).
* **Reliability:** 7-point independent verification audit confirms IP reachability, DNS, gateway, path isolation, latency ($\le 100\text{ ms}$), and loss bounds. Transactional snapshot rollback ensures the network never remains in an inconsistent state if an action fails.
* **Security:** Centralized fault registry is read-isolated from monitoring and diagnostic telemetry to prevent ground-truth data poisoning.

---

# CHAPTER 5: CONCLUSION

### 5.1 Summary
This project successfully designed, implemented, and validated an Intelligent Network Fault Diagnosis and Automated Recovery Framework. The system combines an interactive Cisco Packet Tracer-style visual workspace with a Windows CMD-style simulated network terminal. Operating on a NetworkX graph topology, the framework enforces a complete, strictly decoupled **Observe $\rightarrow$ Diagnose $\rightarrow$ Plan $\rightarrow$ Recover $\rightarrow$ Verify** lifecycle. Key accomplishments include atomic multi-fault injection, rule-based root-cause diagnosis with calibrated confidence scoring ($0.90\text{--}1.00$), multi-objective route optimization, true physical fault bypass (severed links remain strictly `DOWN`), honest partition reporting, and post-recovery probe packet verification. The framework achieved a $100\%$ pass rate across all 200 automated unit tests.

### 5.2 Learning Outcomes
* Deepened practical understanding of Layer-2/Layer-3 network architectures, routing tables, and metric calculations.
* Mastered probabilistic packet loss modeling ($P = 1 - \prod(1 - p_i)$) and multi-objective Pareto optimization in traffic engineering.
* Developed expertise in building decoupled, explainable expert diagnostic systems without black-box machine learning opacity.
* Gained hands-on experience in graphical GUI engineering (Tkinter canvas manipulation), terminal command parsing, and automated software testing.

### 5.3 Limitations
* Operates within a software-simulated graph environment rather than direct physical hardware interfaces.
* Focuses on intra-domain enterprise topologies rather than inter-domain BGP autonomous systems.
* Currently models static heuristic latency and loss thresholds rather than dynamic time-series baselines.

### 5.4 Future Enhancements
* Integrating physical Software-Defined Networking (SDN) controllers via OpenFlow or P4 programmable data planes.
* Extending multi-objective recovery to support BGP multi-homing across diverse Autonomous Systems.
* Incorporating statistical anomaly detection (e.g., Kalman filtering) to dynamically adjust operational thresholds based on fluctuating day/night traffic patterns.

---

## REFERENCES
1. J. F. Kurose and K. W. Ross, *Computer Networking: A Top-Down Approach*, 8th ed., Pearson, 2021.
2. A. S. Tanenbaum, N. Feamster, and D. J. Wetherall, *Computer Networks*, 6th ed., Pearson, 2021.
3. NetworkX Developers, "NetworkX: Network Analysis in Python," Documentation, 2024. [https://networkx.org/](https://networkx.org/)
4. Cisco Systems, "Cisco Packet Tracer User Guide," Cisco Networking Academy, 2023.
5. Python Software Foundation, "Tkinter — Python interface to Tcl/Tk," Python 3.10 Documentation, 2024.

---

## APPENDIX

### Appendix A: Official Automated Test Execution Summary
```text
======================================================================
Ran 200 tests in 17.822s

OK (Pass Rate: 100.0%, Failures: 0, Errors: 0)
======================================================================
Stages Verified:
- Stage 0: Architecture & Baseline Regression (88 Tests)
- Stage 1: Data Model, Fault Registry & Lifecycle (12 Tests)
- Stage 2: Multi-Fault Injection Engine & Atomic Batches (12 Tests)
- Stage 3: Advanced Monitoring & Partition Detection (9 Tests)
- Stage 4: Multi-Fault Evidence-Based Root-Cause Diagnosis (7 Tests)
- Stage 5: Intelligent Global Recovery Planner (8 Tests)
- Stage 6: Coordinated Automated Recovery Engine (7 Tests)
- Stage 7: Post-Recovery Verification & Audit Logging (12 Tests)
- Stage 8: Interactive Operator Dashboard (15 Tests)
- Stage 9: Windows CMD-Style Network Terminal (12 Tests)
- Stage 10: Demonstration Scenarios A through H (18 Tests)
```

### Appendix B: Simulated Terminal Command Reference (`network_terminal.py`)
* `help` / `?`: Displays all available CLI commands.
* `hostname`: Prints the active host context (e.g., `PC1`).
* `connect <node>`: Switches active device context (e.g., `connect Server`).
* `ipconfig [/all]`: Displays IP, subnet mask, default gateway, and DNS server.
* `ping <target>`: Transmits 4 ICMP echo request packets and measures round-trip time.
* `tracert <target>`: Traces active routing hops to destination.
* `nslookup <domain>`: Performs DNS name resolution query.
* `show devices` / `show links` / `show routes`: Inspects live graph topology state.
* `diagnose`: Triggers live telemetry monitoring and root-cause diagnosis.
* `recover`: Executes coordinated self-healing and post-recovery verification.
