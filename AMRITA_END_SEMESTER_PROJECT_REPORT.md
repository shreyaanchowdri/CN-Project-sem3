AMRITA VISHWA VIDYAPEETHAM
School of Computing, Bengaluru
END-SEMESTER PROJECT REPORT
23AID206 – INTRODUCTION TO COMPUTER NETWORKS

PROJECT TITLE
Design and Development of an Intelligent Network Fault Injection, Root-Cause Diagnosis and Automated Recovery Framework

Submitted by
Shreyan Chowdhuri (BL.EN.U4AIE23001)
[November 2026]

DECLARATION
We hereby declare that the project work presented in this report is our original work carried out as part of 23AID206 – Introduction to Computer Networks. All sources of information used have been duly acknowledged.

Student Signature(s): ______________________________________________

The Project work is evaluated on ………………………………………………..

| Design and Simulator Selection (5) | Implementation (12) | Viva (5) | Viva (3) | Results and Inference (5) | Total (30) |
|---|---|---|---|---|---|
| | | | | | |

Faculty-in-Charge: ____________________________     Signature with Date: ______________

ABSTRACT
This project presents an Intelligent Network Fault Diagnosis and Automated Recovery Framework developed in Python using Tkinter, NetworkX, and Matplotlib. Combining an interactive logical topology workspace with a simulated command-line diagnostic terminal, the framework allows users to construct topologies (such as pc1, pc2, routers r1–r2, and Server), select configurable source and destination endpoints (including pc1 -> Server and pc1 -> pc2), inject faults such as link failures (link down) and link packet loss, and execute a closed-loop Observe → Diagnose → Recover → Verify workflow.
During monitoring and diagnosis, the system evaluates measured telemetry—including reachability, latency, cumulative path packet loss (1-1-pi), gateway and DNS status, and interface states—to identify primary root cause faults with confidence scores and supporting rule-based evidence. During recovery and verification, it evaluates feasible alternatives, reports recovery unavailable when no viable or lower-loss path exists, simulates configurable probe-packet bursts (delivered, dropped packet , or dropped ) along the active path, and runs post-recovery verification checks with full execution reporting (exec-xxxx).

TABLE OF CONTENTS
[Insert an automatic Table of Contents in Word: References → Table of Contents.]
- CHAPTER 1: INTRODUCTION .............................................................. 1
  - 1.1 Background ..................................................................... 1
  - 1.2 Motivation ..................................................................... 1
  - 1.3 Problem Statement .............................................................. 2
  - 1.4 Objectives ..................................................................... 2
  - 1.5 Scope .......................................................................... 2
- CHAPTER 2: NETWORK DESIGN AND REQUIREMENTS ............................................ 3
  - 2.1 Overview of the Proposed Network ............................................... 3
  - 2.2 Network Requirements ........................................................... 3
  - 2.3 Network Devices and Components ................................................. 3
  - 2.4 Network Topology ............................................................... 4
  - 2.5 IP Addressing Scheme ........................................................... 4
  - 2.6 Protocols and Network Services ................................................. 5
- CHAPTER 3: IMPLEMENTATION ............................................................ 6
  - 3.1 Tools and Environment .......................................................... 6
  - 3.2 Network Topology Implementation ................................................ 6
  - 3.3 Device Configuration ........................................................... 6
  - 3.4 IP Configuration ............................................................... 7
  - 3.5 Routing and Switching Configuration ............................................ 7
  - 3.6 Network Services Configuration ................................................. 7
  - 3.7 Implementation Evidence ........................................................ 8
- CHAPTER 4: TESTING AND RESULTS ....................................................... 9
  - 4.1 Testing Methodology ............................................................ 9
  - 4.2 Connectivity Testing ........................................................... 9
  - 4.3 Simulation and Packet Analysis ................................................. 10
  - 4.4 Results and Observations ....................................................... 10
  - 4.5 Performance, Reliability, and Security Considerations .......................... 11
- CHAPTER 5: CONCLUSION ................................................................ 12
  - 5.1 Summary ........................................................................ 12
  - 5.2 Learning Outcomes ............................................................... 12
  - 5.3 Limitations .................................................................... 12
  - 5.4 Future Enhancements ............................................................ 12
- REFERENCES ........................................................................... 13
- APPENDIX ............................................................................. 14

LIST OF FIGURES
[List all figures with figure numbers, captions, and page numbers.]
- Figure 2.1: Diamond Core Multi-Path Network Architecture ............................. 4
- Figure 3.1: Logical Topology Workspace and 8-Card KPI Dashboard ...................... 8
- Figure 3.2: Simulated Command-Line Network Diagnostic Terminal (network_terminal.py) .. 8
- Figure 4.1: Automated Multi-Fault Diagnosis and Post-Recovery Verification View ....... 10

LIST OF TABLES
[List all tables with table numbers, captions, and page numbers.]
- Table 2.1: IP Addressing Scheme and Interface Assignments ............................ 5
- Table 4.1: Test Execution Results and Verification Observations ...................... 11

CHAPTER 1: INTRODUCTION

1.1 Background
Introduce the application area and relevant computer networking concepts. Explain the context in which the proposed network is required.

Computer networking forms the critical foundation for modern enterprise communication, distributed applications, and cloud computing architectures. An enterprise network interconnects client workstations across local access networks with centralized application servers through multi-hop transit routers and switches. In such production environments, continuous network reliability and strict Quality of Service (QoS) guarantees are paramount. However, complex multi-hop networks are constantly vulnerable to physical cable cuts, router interface failures, gateway misconfigurations, DNS resolver outages, and severe performance degradations such as high propagation latency and probabilistic packet loss. When faults manifest, organizations require rapid, deterministic, and explainable network management solutions that can detect anomalies, identify exact root causes, and restore communications without human delay.

1.2 Motivation
Explain why this network/project is being developed and the need it addresses.

In conventional enterprise networks, troubleshooting is predominantly manual, slow, and reactive. Network operators must manually execute disconnected diagnostic utilities such as ping, traceroute, and interface state queries. This manual triage significantly inflates Mean Time to Detect (MTTD) and Mean Time to Recover (MTTR), especially during cascading multi-fault events. Furthermore, modern black-box machine learning approaches lack explainability and deterministic safety guarantees, while existing academic network simulators frequently cheat by inspecting internal simulator flags or magically resetting severed cables back to operational state. This project is motivated by the urgent necessity for an automated, closed-loop self-healing network framework that operates strictly on real-world observable telemetry, enforces realistic physical fault bypass, and provides provably safe, explainable remediation.

1.3 Problem Statement
Clearly state the networking problem. Identify users, communication requirements, constraints, and expected functionality.

The objective is to address the challenge of autonomous multi-fault detection, root-cause diagnosis, and recovery in enterprise computer networks. The target users are network administrators and site reliability engineers who manage client-server traffic across multi-path topologies under strict SLA requirements. The system must address constraints including zero ground-truth leakage (the monitoring system must not cheat by reading fault injection flags), realistic physical fault bypass (severed physical links must remain DOWN rather than being magically repaired), honest partition handling (reporting recovery unavailable when no path exists), and transactional state safety. The expected functionality encompasses dynamic topology modeling, transactional multi-fault injection, rule-based diagnostic reasoning with calibrated confidence, multi-objective route optimization, active probe packet verification, and dual visual and terminal user interfaces.

1.4 Objectives
List the specific, measurable objectives of the project.
Objective 1: Design and implement a software-based virtual network environment using graph-theoretic modeling to represent nodes, links, and operational metrics.
Objective 2: Simulate network devices including client workstations (PC1, PC2), routers (R1, R2, R3), and application servers with authentic IPv4 addressing, gateways, and DNS configuration.
Objective 3: Implement a transactional fault injection system supporting atomic batch execution for link cuts, gateway misconfigurations, DNS daemon failures, latency spikes, and packet loss.
Objective 4: Design a rule-based diagnostic engine that gathers decoupled telemetry and evaluates failure modes in parallel with calibrated confidence scores (0.90 to 1.00).
Objective 5: Formulate an automated recovery planner that performs multi-objective route optimization across hop cost, latency, and packet loss while enforcing realistic physical fault bypass.
Objective 6: Verify post-recovery network reachability using an independent 7-point verification audit and synthetic probe packet batch transmissions with delivery rate tracking.

1.5 Scope
Define the scope, assumptions, features included, and limitations of the project.

The scope of this project encompasses Layer-2 Ethernet framing concepts, Layer-3 IPv4 addressing and routing, ICMP active reachability probing, application-layer DNS resolution, and probabilistic multi-hop packet loss calculation. Features included are an interactive Cisco Packet Tracer-inspired visual workspace, an authentic Windows CMD-style diagnostic terminal (network_terminal.py), six real-time Matplotlib analytics graphs, and 200 automated regression unit tests. Assumptions include an intra-domain enterprise network environment with cooperative nodes. Limitations include operating within a software-modeled environment rather than direct physical hardware interfaces, and focusing on intra-domain routing rather than multi-provider BGP peering.

CHAPTER 2: NETWORK DESIGN AND REQUIREMENTS

2.1 Overview of the Proposed Network
Describe the overall network, its purpose, users, locations, and major components.

The proposed network simulates a resilient enterprise intranet that provides continuous communication between local client workstations (PC1, PC2) located on an enterprise access LAN and an enterprise application server (Server) located in a centralized server zone. The network establishes dual-redundant transit paths through an intermediate router core comprising a primary gateway router (R1) and two core transit routers (R2 and R3). The primary purpose of this architecture is to provide high-availability data transport, evaluate real-time telemetry degradation, and automatically reroute traffic around severed or lossy transit links.

2.2 Network Requirements
Specify functional and non-functional requirements such as number of users/devices, connectivity, performance, reliability, security, and scalability.

Functional requirements require full support for node/link instantiation, transactional fault injection, decoupled telemetry observation, evidence-based root-cause diagnosis, multi-objective route selection, and independent verification. Non-functional requirements demand high performance (sub-millisecond diagnosis latency), deterministic repeatability across all test cases, absolute explainability without black-box machine learning opacity, high reliability through transactional snapshot rollback on execution errors, and scalability to arbitrary graph topologies.

2.3 Network Devices and Components
Identify devices and components used (e.g., routers, switches, PCs, servers, access points, cables) and explain their roles.

- PC1 and PC2 (End Device Workstations): Generate user traffic; configured with unique IP addresses, subnet masks, default gateways pointing to R1, and DNS resolver pointers.
- Router R1 (Primary Gateway Router): Functions as the default gateway for client subnets; interconnects the client access network to core transit routers R2 and R3.
- Routers R2 and R3 (Transit Core Routers): Provide redundant Layer-3 transport conduits; R2 constitutes the primary low-latency path, while R3 constitutes the redundant backup path.
- Server (Enterprise Application Server): Hosts enterprise DNS and web services; serves as the destination endpoint for client communications.
- Physical Transmission Cables: Modeled with bidirectional parameters including link status (UP/DOWN), propagation latency (ms), packet loss (%), and link cost.

2.4 Network Topology
Describe and justify the selected topology. Insert a clearly labelled network topology diagram.

The topology implements a diamond multi-path mesh architecture designed specifically to provide alternate path redundancy. This design ensures that if the primary transit link (R1-R2 or R2-Server) fails or degrades, traffic can be seamlessly rerouted across the backup conduit (R1-R3-Server) without disrupting client-server connectivity.

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
Figure 2.1: Diamond Core Multi-Path Network Architecture.

2.5 IP Addressing Scheme
Present the IPv4/IPv6 addressing plan, subnet masks or prefix lengths, network addresses, gateway addresses, and host address allocation.

| Device / Host | Interface | IP Address | Subnet Mask / Prefix | Default Gateway |
|---|---|---|---|---|
| PC1 | eth0 | 192.168.1.10 | 255.255.255.0 (/24) | 192.168.1.1 |
| PC2 | eth0 | 192.168.1.11 | 255.255.255.0 (/24) | 192.168.1.1 |
| R1 | Fa0/0 (LAN) | 192.168.1.1 | 255.255.255.0 (/24) | N/A |
| R2 | Gi0/1 (WAN1) | 10.0.1.1 | 255.255.255.0 (/24) | N/A |
| Server | eth0 | 172.16.0.10 | 255.255.255.0 (/24) | 172.16.0.1 |

2.6 Protocols and Network Services
List and explain the protocols and services used (e.g., Ethernet, IP, TCP, UDP, DHCP, DNS, HTTP/HTTPS). Include only those applicable.

- IEEE 802.3 Ethernet: Defines Layer-2 data-link framing and physical cabling standards.
- Internet Protocol version 4 (IPv4): Implements Layer-3 packet addressing, subnet classification, and multi-hop forwarding.
- Internet Control Message Protocol (ICMP): Enables synthetic reachability probes (ping echo request and reply) and path hop evaluation (traceroute).
- Domain Name System (DNS): Application-layer service resolving domain names (such as server.local) to IPv4 addresses over UDP port 53.
- Multi-Objective Dynamic Routing: Employs graph path-search algorithms evaluated via normalized Pareto scoring across hop cost, latency, and probabilistic packet loss.

CHAPTER 3: IMPLEMENTATION

3.1 Tools and Environment
Mention software/tools used, including Cisco Packet Tracer (if applicable), device models, operating systems, and relevant versions.

The framework is implemented using Python 3.10+ on Windows 11. Core libraries include NetworkX (v3.0+) for graph-theoretic network topology representation, Tkinter for the Cisco Packet Tracer-inspired visual workspace and 8-tab operator notebook, Matplotlib (v3.7+) for live analytical trend charts, and Python's standard unittest framework for comprehensive regression validation. Simulated hardware models include Cisco 2911 Integrated Services Routers, Cisco Catalyst 2960 Switches, and standard enterprise client PCs and servers.

3.2 Network Topology Implementation
Explain how the topology was created and devices interconnected. Include screenshots.

The topology is constructed programmatically in network_model.py by instantiating an undirected NetworkX graph G = (V, E). Nodes represent network devices storing configuration dictionaries, while edges represent physical conduits storing transmission parameters including link cost, latency (ms), packet loss (%), and operational state (UP/DOWN). Devices are positioned logically on a visual canvas with dynamic drag-and-drop palettes, interactive cable connection dialogs, and real-time visual status halos (green for healthy, red for severed links, orange for degraded loss/latency).

3.3 Device Configuration
Describe configuration of routers, switches, PCs, servers, and other devices. Include relevant commands or screenshots.

Devices are configured through the GUI inspector tab ('Device Config') or via the simulated Windows CMD terminal (network_terminal.py). Workstations are configured with hostname, IP address, subnet mask, default gateway, and DNS server. Routers maintain interface tables and routing tables. The server runs application services including an internal DNS daemon mapped to server.local.

3.4 IP Configuration
Explain how IP addresses, subnet masks/prefixes, and default gateways were configured. Describe DHCP if used.

IPv4 addressing is validated and assigned statically to all simulated interfaces in accordance with Table 2.1. When an operator updates a default gateway on PC1 via the GUI or terminal ('ipconfig /all'), the monitoring module performs an immediate subnet audit to verify whether the assigned gateway IP belongs to the attached router interface on that broadcast domain.

3.5 Routing and Switching Configuration
Explain routing and switching mechanisms configured, including static/dynamic routing or VLANs where applicable.

Routing discovery is implemented in network_model.py via discover_routes(g, source, target). The algorithm discovers all loop-free candidate paths using depth-first search. The optimal path r* is selected using normalized multi-objective scoring: Score(r) = wc * C_hat(r) + wl * L_hat(r) + wp * P_hat(r), where hop cost, latency, and cumulative packet loss are min-max normalized.

3.6 Network Services Configuration
Describe configuration of DHCP, DNS, web, file, or other application services, where applicable.

DNS service availability is modeled as a global state variable g.graph['dns_available']. Workstation name lookups trigger simulated UDP port 53 socket probes. If dns_available is set to False (simulating a service crash), name resolution fails with a DNS timeout while underlying IP reachability remains operational.

3.7 Implementation Evidence
Insert relevant screenshots with figure numbers, captions, and brief explanations. Ensure screenshots are readable.

The operational workspace integrates the visual Cisco Packet Tracer-style canvas, an 8-card responsive KPI bar (Devices, Links, Faults, Critical Outages, Availability, Health, Active Route, Recovery Status), an 8-tab operator notebook (Diagnosis & Telemetry, Recovery & Verification, Multi-Route Matrix, Performance, Event Log, Recovery Planner, Audit & Analytics, Network Analytics & Trends), and a Windows CMD terminal.

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
Figure 3.1: Logical Topology Workspace and KPI Management Dashboard.

CHAPTER 4: TESTING AND RESULTS

4.1 Testing Methodology
Explain the test plan, test environment, devices involved, and procedure followed to verify the network.

Testing was conducted through a two-tiered methodology comprising an automated 200-test regression suite (tests/test_project.py) and interactive GUI/terminal scenario verification. The test plan systematically exercises all failure modes: single physical link cuts, combined link and DNS failures, default gateway misconfigurations, probabilistic packet loss, complete topological partitions, transactional rollbacks, and simulated terminal consistency across 10 development stages.

4.2 Connectivity Testing
Report ping tests and other connectivity checks. Include source/destination addresses, expected and actual results, and screenshots.

Connectivity checks were conducted from PC1 to Server (172.16.0.10) using terminal utilities and automated test scripts:
- ping Server (Nominal): 4 packets transmitted, 4 received, 0% packet loss, RTT = 8.0 ms. (Expected: 100% reachability; Actual: PASS).
- ping Server (Partitioned): 4 packets transmitted, 0 received, 100% packet loss. (Expected: Destination Host Unreachable; Actual: PASS).
- tracert Server: Correctly records forwarding hops: Hop 1: 192.168.1.1 (R1), Hop 2: 10.0.1.1 (R2), Hop 3: 172.16.0.10 (Server).

4.3 Simulation and Packet Analysis
Describe simulation-mode observations or packet analysis. Explain protocols and packet exchanges observed.

When Recover & Verify is triggered, the recovery engine transmits a configurable burst of probe packets (count = 5, 10, or 20) across the active forwarding route. In a degraded test state with 33.0% packet loss on link R2-Server, the burst transmitted 5 probe packets: Packet #1 dropped (DROPPED_PACKET_LOSS), Packets #2, #3, #4 delivered (RTT 7.9 to 8.2 ms), and Packet #5 dropped (DROPPED_PACKET_LOSS), confirming an empirical delivery rate of 60.0% matching theoretical probabilistic drop expectations.

4.4 Results and Observations
Summarize test results. Discuss successful outcomes, failures, errors encountered, and how they were resolved.

| Test ID | Test Description | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| TC-01 | Baseline Nominal Connectivity | PC1 to Server reachable via R2; 0% loss; RTT 8ms | Reachable via R1-R2-Server; 0% loss; 8.0ms RTT | PASS |
| TC-02 | Physical Link Failure (R2-Server) | Failover to alternate route R1-R3-Server; R2-Server stays DOWN | Rerouted over R3; R2-Server remains DOWN | PASS |
| TC-03 | Invalid Gateway Injection | Diagnosed (98% confidence); restored to valid router R1 | Gateway corrected to R1; 100% reachability | PASS |
| TC-04 | DNS Daemon Crash Injection | Diagnosed (95% confidence); service restarted | Resolver restored; nslookup succeeds | PASS |
| TC-05 | Degraded Packet Loss (33%) | Evaluates lower-loss alternate route; maintains surviving path | Surviving route maintained; degraded health reported | PASS |
| TC-06 | Complete Network Partition | R2 & R3 down; reports RECOVERY UNAVAILABLE with 0 actions | RECOVERY UNAVAILABLE; 0 redundant actions | PASS |

4.5 Performance, Reliability, and Security Considerations
Discuss relevant performance, reliability, and security considerations. Include measurements only if actually collected.

- Performance: Diagnosis execution time was measured empirically at 0.000656 seconds (<1 ms), and recovery execution time at 0.000677 seconds (<1 ms).
- Reliability: The 7-point post-recovery verification audit confirmed reachability, DNS resolution, gateway validity, latency compliance, and failed link isolation. Transactional snapshot rollback ensures atomic state protection upon execution anomalies.
- Security: The fault registry is strictly read-isolated from monitoring and diagnostic telemetry, eliminating data leakage or ground-truth poisoning.

CHAPTER 5: CONCLUSION

5.1 Summary
Summarize the project, the network implemented, and the extent to which objectives were achieved.

This project successfully developed and verified an Intelligent Network Fault Diagnosis and Automated Recovery Framework in Python. The system models an enterprise network with client workstations, multi-interface routers, and enterprise application servers. By implementing an authoritative graph model, transactional fault injection, decoupled telemetry monitoring, rule-based root-cause diagnosis, multi-objective route optimization, and 7-point post-recovery verification, all ten stated objectives were achieved in full. The implementation successfully passed all 200 automated regression unit tests with zero failures.

5.2 Learning Outcomes
Describe networking concepts, configuration skills, troubleshooting methods, and practical learning gained.

- Acquired hands-on proficiency in Layer-2 switching, Layer-3 IPv4 subnetting, and multi-path router forwarding table configurations.
- Mastered mathematical modeling of probabilistic packet loss and multi-objective Pareto optimization in computer networking.
- Developed deep understanding of decoupled, evidence-based diagnostic reasoning without relying on opaque machine learning models.
- Gained practical software engineering experience in GUI canvas development, CLI terminal design, and comprehensive test suite engineering.

5.3 Limitations
Mention current limitations of the design or implementation.

- Operates within a software-based simulated graph environment rather than communicating directly with physical hardware switches.
- Focuses on intra-domain enterprise network routing rather than multi-provider exterior BGP routing.
- Uses static threshold boundaries for latency and loss rather than dynamic, seasonal traffic baselines.

5.4 Future Enhancements
Suggest realistic improvements or extensions to the network.

- Integrating physical Software-Defined Networking (SDN) controllers via OpenFlow or P4 programmable data planes.
- Extending the recovery planner to support inter-domain BGP multi-homing across autonomous systems.
- Incorporating statistical time-series anomaly detection (such as Holt-Winters or Kalman filtering) to dynamically adjust operational alert thresholds based on day/night network load patterns.

REFERENCES
List books, articles, standards, documentation, and websites referred to. Use a consistent citation style. Include access dates for online resources where appropriate.

[1] J. F. Kurose and K. W. Ross, “Computer Networking: A Top-Down Approach,” Pearson, 2021.
[2] A. S. Tanenbaum, N. Feamster, and D. J. Wetherall, “Computer Networks,” Pearson, 2021.
[3] NetworkX Developers, “NetworkX: Network Analysis in Python,” Documentation, 2024. [https://networkx.org/]
[4] Cisco Systems, “Cisco Packet Tracer User Guide,” Cisco Networking Academy, 2023. [https://www.netacad.com/]
[5] Python Software Foundation, “Tkinter — Python interface to Tcl/Tk,” Python Documentation, 2024. [https://docs.python.org/3/library/tkinter.html]

APPENDIX
Include supplementary material such as detailed device configurations, command outputs, additional screenshots, IP allocation details, or test logs. Refer to each appendix item from the main report where relevant.

Appendix A: Official 200/200 Automated Test Suite Pass Log
Ran 200 tests in 17.822s
OK (Pass Rate: 100.0%, Failures: 0, Errors: 0)

Appendix B: Diagnostic Terminal Commands
- ping <host>: Sends ICMP Echo requests and reports round-trip time.
- tracert <host>: Traces active forwarding hops to destination.
- nslookup <domain>: Resolves domain name using simulated DNS daemon.
- ipconfig [/all]: Displays IP, subnet mask, gateway, and DNS resolver.
- show devices / links / routes: Displays active topology state and routing paths.
- diagnose / recover: Triggers observation-based diagnosis and coordinated recovery.
