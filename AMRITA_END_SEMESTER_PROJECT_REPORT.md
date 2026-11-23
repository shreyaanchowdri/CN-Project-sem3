AMRITA VISHWA VIDYAPEETHAM
School of Computing, Bengaluru
END-SEMESTER PROJECT REPORT
23AID206 – INTRODUCTION TO COMPUTER NETWORKS
____________________________________________________________________
PROJECT TITLE
Design and Development of an Intelligent Network Fault Injection, Root-Cause Diagnosis and Automated Recovery Framework

Submitted by:  
Shreyan Chowdhuri (Registration No: BL.EN.U4AIE23001)  
Academic Term: November 2026  
____________________________________________________________________
DECLARATION
We hereby declare that the project work presented in this report is our original work carried out as part of 23AID206 – Introduction to Computer Networks. All sources of information, references, software libraries, and theoretical frameworks used have been duly acknowledged and cited.

Student Signature(s): ______________________________________________  
Date: November 23, 2026  
____________________________________________________________________
EVALUATION SHEET
The Project work is evaluated on: ………………………………………………..

| Design & Simulator Selection (5) | Implementation (12) | Viva (5) | Viva (3) | Results & Inference (5) | Total (30) |
|---|---|---|---|---|---|
| | | | | | |

Faculty-in-Charge: ____________________________        Signature with Date: ______________
____________________________________________________________________
ABSTRACT
This project presents an Intelligent Network Fault Diagnosis and Automated Recovery Framework developed in Python using Tkinter, NetworkX, and Matplotlib. Combining an interactive logical topology workspace with a simulated command-line diagnostic terminal (network_terminal.py), the framework allows users to construct multi-hop topologies (such as PC1, PC2, routers R1–R3, and Server), select configurable source and destination endpoints (including PC1 -> Server and PC1 -> PC2), inject faults such as link failures (link down) and link packet loss, and execute a closed-loop Observe -> Diagnose -> Plan -> Recover -> Verify workflow.

During monitoring and diagnosis, the system evaluates measured telemetry—including reachability, latency, cumulative path packet loss (1 - Product(1 - p_i)), gateway and DNS status, and interface states—to identify primary root cause faults with confidence scores and supporting rule-based evidence without ground-truth cheating. During recovery and verification, it evaluates feasible alternatives, reports recovery unavailable when no viable or lower-loss path exists, simulates configurable probe-packet bursts (delivered, dropped due to loss, or unreachable) along the active path, and runs post-recovery verification checks with full execution reporting (EXEC-XXXX). The framework is thoroughly verified with an automated suite of 200 unit tests achieving a 100% pass rate.
____________________________________________________________________
TABLE OF CONTENTS
CHAPTER 1: INTRODUCTION .............................................................. 1
  1.1 Background ..................................................................... 1
  1.2 Motivation ..................................................................... 1
  1.3 Problem Statement .............................................................. 2
  1.4 Objectives ..................................................................... 2
  1.5 Scope .......................................................................... 2
CHAPTER 2: NETWORK DESIGN AND REQUIREMENTS ............................................ 3
  2.1 Overview of the Proposed Network ............................................... 3
  2.2 Network Requirements ........................................................... 3
  2.3 Network Devices and Components ................................................. 3
  2.4 Network Topology ............................................................... 4
  2.5 IP Addressing Scheme ........................................................... 4
  2.6 Protocols and Network Services ................................................. 5
CHAPTER 3: IMPLEMENTATION ............................................................ 6
  3.1 Tools and Environment .......................................................... 6
  3.2 Network Topology Implementation ................................................ 6
  3.3 Device Configuration ........................................................... 6
  3.4 IP Configuration ............................................................... 7
  3.5 Routing and Switching Configuration ............................................ 7
  3.6 Network Services Configuration ................................................. 7
  3.7 Implementation Evidence ........................................................ 8
CHAPTER 4: TESTING AND RESULTS ....................................................... 9
  4.1 Testing Methodology ............................................................ 9
  4.2 Connectivity Testing ........................................................... 9
  4.3 Simulation and Packet Analysis ................................................. 10
  4.4 Results and Observations ....................................................... 10
  4.5 Performance, Reliability, and Security Considerations .......................... 11
CHAPTER 5: CONCLUSION ................................................................ 12
  5.1 Summary ........................................................................ 12
  5.2 Learning Outcomes ............................................................... 12
  5.3 Limitations .................................................................... 12
  5.4 Future Enhancements ............................................................ 12
REFERENCES ........................................................................... 13
APPENDIX ............................................................................. 14
____________________________________________________________________
LIST OF FIGURES
- Figure 2.1: Diamond Core Multi-Path Network Architecture ............................. 4
- Figure 3.1: Logical Topology Workspace and 8-Card KPI Dashboard ...................... 8
- Figure 3.2: Simulated Command-Line Network Diagnostic Terminal (network_terminal.py) .. 8
- Figure 4.1: Automated Multi-Fault Diagnosis and Post-Recovery Verification View ....... 10
____________________________________________________________________
LIST OF TABLES
- Table 2.1: IP Addressing Scheme and Interface Assignments ............................ 5
- Table 4.1: Master Functional Test Results and Verification Status ...................... 11
____________________________________________________________________
CHAPTER 1: INTRODUCTION

1.1 Background
Computer networks connect end devices like PCs, laptops, and servers through routers and switches, allowing users to share resources, access internet services, and run distributed applications. In any real-world enterprise or campus network, maintaining reliable connectivity is critical. However, networks often face problems: cables get disconnected or cut, router interfaces fail, administrators accidentally type the wrong gateway IP, DNS servers crash, and links suffer from high delay or packet loss. To keep communication running smoothly, network engineers need tools that can quickly spot what went wrong, explain why it happened, and fix the route without causing further downtime.

1.2 Motivation
In most network environments, finding and fixing faults is still done manually. When a user reports that a server is down, an administrator has to open a terminal, run ping and traceroute commands across multiple hops, inspect router interfaces, and manually edit configuration tables. This takes valuable time and can lead to mistakes during complex multi-fault outages. While researchers have tried using machine learning for network management, black-box AI models often fail to explain why they chose a particular route and can behave unpredictably during new types of failures. At the same time, standard educational tools like Cisco Packet Tracer are built for manual student practice and do not have an autonomous self-healing engine. This motivated us to build a deterministic, rule-based framework that diagnoses faults using real observable network metrics and reroutes traffic automatically through healthy surviving paths.

1.3 Problem Statement
The main problem we address is how to automatically detect, diagnose, and recover from concurrent network failures in a multi-hop network without relying on black-box AI or unrealistic shortcuts. Specifically, our framework must handle multiple simultaneous faults (such as a cut cable and packet loss happening together), collect telemetry without 'cheating' (meaning it cannot simply look up the fault injection answer key), diagnose the actual root cause with clear confidence ratings, and reroute packets through working paths. If a cable is cut, the broken link must stay DOWN—the system cannot magically turn it back UP—and if all paths to a destination are broken, the system must honestly report that recovery is unavailable instead of claiming success.

1.4 Objectives
1. Build a software-based virtual network environment using NetworkX to model devices and links with realistic latency, cost, and packet loss attributes.
2. Simulate realistic network hardware including client PCs (PC1, PC2), Layer-3 routers (R1, R2, R3), and application servers with proper IPv4 addresses, subnet masks, default gateways, and DNS configuration.
3. Implement a transactional fault injection system that can inject single or batch faults (link cuts, wrong gateways, DNS crashes, high latency, packet loss) with snapshot rollback safety.
4. Develop a rule-based diagnostic engine that inspects observable telemetry in parallel and assigns calibrated confidence scores (0.90 to 1.00) to each detected fault.
5. Implement an automated recovery planner that uses multi-objective route optimization (balancing hop cost, latency, and packet loss) to reroute traffic around broken or lossy links.
6. Build an independent 7-point verification audit and probe packet generator (sending 5, 10, or 20 test packets) to verify actual delivery rates before committing a recovery.
7. Measure system performance, including diagnosis time (<1 ms), root-cause accuracy, and recovery time, validated across 200 automated unit tests.
8. Provide a dual user interface featuring an interactive Cisco Packet Tracer-style visual workspace and a simulated Windows CMD diagnostic terminal (network_terminal.py).

1.5 Scope
The project covers local area network (LAN) access, multi-hop Layer-3 IP routing, ICMP reachability checks (ping and traceroute), simulated UDP DNS queries, and probabilistic packet loss calculations. We implemented our system in pure Python so that it runs locally on standard machines without requiring dedicated hardware, physical switches, or cloud accounts. The project focuses on intra-domain enterprise networks; inter-domain BGP internet peering and wireless radio frequency modeling are outside the current scope.
____________________________________________________________________
CHAPTER 2: NETWORK DESIGN AND REQUIREMENTS

2.1 Overview of the Proposed Network
The network we designed represents a typical enterprise setup. On the left side, client computers (PC1 and PC2) sit on an access subnet (192.168.1.0/24) where users work. These PCs connect to a local default gateway router (R1). In the center of the network, R1 connects to two separate core transit routers: Router R2 (the primary path) and Router R3 (the backup path). On the right side, both core routers connect to the Enterprise Server (172.16.0.10) hosting web and DNS services. This design provides two independent routes from the client computers to the server, allowing the network to survive if one path fails.

2.2 Network Requirements
- Functional Requirements: The system must allow users to add devices, connect links, inject faults, trigger automated diagnosis, calculate alternative routes, and run verification probes. It must support both a visual GUI and a command-line terminal.
- Non-Functional Requirements: The diagnostic engine must execute in under 1 millisecond. The self-healing logic must be completely deterministic (giving the same reliable result every time). It must be safe, rolling back changes if a recovery action fails, and easy to inspect without opaque machine learning.

2.3 Network Devices and Components
- PC1 & PC2 (Workstations): Desktop computers generating client requests. Configured with IPs 192.168.1.10 and 192.168.1.11, default gateway 192.168.1.1 (R1), and DNS server 192.168.1.1.
- Router R1 (Gateway Router): The first hop for local client traffic. It connects the 192.168.1.0/24 subnet to WAN transit links leading to R2 and R3.
- Router R2 (Primary Transit Router): Fast transit router (10.0.1.1/24) that forms the preferred primary route to the server due to lower latency.
- Router R3 (Backup Transit Router): Redundant transit router (10.0.2.1/24) that provides an alternate path to the server when R2 is unavailable or degraded.
- Server (Application Server): Hosts simulated DNS and web applications at 172.16.0.10.
- Virtual Links: Network connections with configurable link speed, latency (in ms), packet loss percentage (0% to 100%), and operational status (UP or DOWN).

2.4 Network Topology
We selected a diamond multi-path core topology because it provides full path redundancy. In this layout, traffic from PC1 to Server normally travels across the top path (PC1 -> R1 -> R2 -> Server), which has a total cost of 3 and 8 ms latency. If the link between R2 and Server is severed or has heavy packet loss, the network can reroute traffic across the bottom path (PC1 -> R1 -> R3 -> Server), which has a cost of 5 and 10 ms latency.

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
| Device / Host | Interface | IP Address | Subnet Mask / Prefix | Default Gateway |
|---|---|---|---|---|
| PC1 | eth0 | 192.168.1.10 | 255.255.255.0 (/24) | 192.168.1.1 |
| PC2 | eth0 | 192.168.1.11 | 255.255.255.0 (/24) | 192.168.1.1 |
| R1 | Fa0/0 (LAN) | 192.168.1.1 | 255.255.255.0 (/24) | N/A |
| R2 | Gi0/1 (WAN1) | 10.0.1.1 | 255.255.255.0 (/24) | N/A |
| Server | eth0 | 172.16.0.10 | 255.255.255.0 (/24) | 172.16.0.1 |

Table 2.1: Complete IPv4 Addressing Scheme.

2.6 Protocols and Network Services
- Ethernet (IEEE 802.3): Used at Layer 2 for frame delivery between connected nodes.
- IPv4: Used at Layer 3 for logical addressing, subnetting, and hop-by-hop packet routing.
- ICMP: Used for diagnostic testing; powers our ping reachability checks and traceroute hop tracking.
- DNS: Application-layer service running on the server over UDP port 53, resolving domain names like server.local.
- Multi-Objective Routing: Evaluates paths using a balanced formula that considers hop count, latency, and packet loss simultaneously.
____________________________________________________________________
CHAPTER 3: IMPLEMENTATION

3.1 Tools and Environment
We built the complete framework using Python 3.10 on Windows 11. We used NetworkX for managing the network graph and calculating connected components. For the graphical user interface, we used Tkinter to create a Cisco Packet Tracer-style visual canvas with custom drawing tools and an 8-tab operator notebook. We used Matplotlib to generate real-time analytics graphs showing latency, packet loss, and recovery time. We also used Python's built-in unittest module to write and run all 200 regression tests.

3.2 Network Topology Implementation
In network_model.py, we created the topology as an undirected graph using NetworkX. Devices are stored as nodes with their configuration details (IP address, subnet, gateway, device type). Links are stored as graph edges with attributes including cost, latency in milliseconds, packet loss percentage, and status ('UP' or 'DOWN'). On the Tkinter canvas, devices are rendered as interactive colored icons (blue for PCs, green for routers, purple for servers) with status lines connecting them. When links fail, they turn red; when they experience delay or packet loss, they display an amber warning halo.

3.3 Device Configuration
Users can configure devices either visually through the 'Device Config' panel or via the command line. In the visual panel, clicking on any PC, router, or server displays its parameters, allowing the operator to rename devices, edit IP addresses, change subnet masks, or update default gateways. Changes are immediately updated in the underlying NetworkX graph.

3.4 IP Configuration
IP configuration is handled in network_model.py. When a device is added or updated, the system checks whether its IP address and default gateway are valid. For example, if PC1 is set to 192.168.1.10 with gateway 192.168.1.1, the system verifies that both addresses belong to the same subnet. If someone configures an invalid gateway (such as 10.0.1.1 on a 192.168.1.0 subnet), the diagnostic engine flags a configuration error.

3.5 Routing and Switching Configuration
Routing discovery is handled by discover_routes(g, source, target). The algorithm finds all loop-free paths between the source and destination. To choose the best route, we calculate a multi-objective score for each path:
Score(r) = w_cost * Normalized_Cost + w_lat * Normalized_Latency + w_loss * Normalized_Loss
By balancing these three metrics, the network automatically picks the cleanest, fastest route rather than blindly choosing a path that might have heavy packet loss.

3.6 Network Services Configuration
We modeled DNS resolution by adding a global state variable g.graph['dns_available'] and a resolver probe. When PC1 tries to resolve server.local, the system checks if the DNS service is operational. If an operator injects a DNS failure, the service drops queries, causing nslookup to report a timeout while regular IP pinging continues to work.

3.7 Implementation Evidence
The running system provides an interactive dashboard with real-time KPI cards at the top, a visual network canvas in the center, configuration panels on the right, and an 8-tab reporting console at the bottom.

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
____________________________________________________________________
CHAPTER 4: TESTING AND RESULTS

4.1 Testing Methodology
We tested the system in two complementary ways. First, we wrote a comprehensive automated test suite in tests/test_project.py consisting of 200 unit tests. These tests systematically check every feature: single link failures, wrong gateways, DNS crashes, high latency, packet loss, network partitions, and rollback safety. Second, we performed manual testing in the GUI and Windows CMD terminal, verifying that every button, dropdown, and terminal command produces the exact expected network behavior.

4.2 Connectivity Testing
We tested connectivity from PC1 to Server across different operational states:
- Normal Baseline: Running 'ping Server' sent 4 ICMP packets with 4 replies received, 0% packet loss, and an average round-trip time of 8.0 ms. The traceroute showed hops: PC1 -> R1 -> R2 -> Server.
- Broken Primary Link: When link R2-Server was severed, the recovery engine rerouted traffic over R3. Running 'ping Server' immediately succeeded over the backup route with hops: PC1 -> R1 -> R3 -> Server.
- Complete Partition: When both R2-Server and R3-Server were cut, 'ping Server' reported 100% packet loss and the diagnostic engine correctly reported that the destination was unreachable.

4.3 Simulation and Packet Analysis
When an operator clicks 'Recover & Verify', the system sends a configurable burst of probe packets (5, 10, or 20) from the selected source to destination. In our degraded path test, we configured link R2-Server with 33.0% packet loss. Transmitting 5 probe packets resulted in:
- Packet #1: DROPPED_PACKET_LOSS (due to 33% link loss)
- Packet #2: DELIVERED (RTT: 7.9 ms)
- Packet #3: DELIVERED (RTT: 8.2 ms)
- Packet #4: DELIVERED (RTT: 8.0 ms)
- Packet #5: DROPPED_PACKET_LOSS (due to 33% link loss)
This resulted in exactly 3 delivered packets out of 5 (60.0% delivery rate), showing that our probabilistic packet loss model mirrors real physical drops.

4.4 Results and Observations
The framework was tested against six core functional test scenarios. In every test case, the system diagnosed the fault correctly and took the appropriate recovery action.

| Test ID | Test Description | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| TC-01 | Baseline Nominal Connectivity | PC1 to Server reachable via R2; 0% loss; RTT 8ms | Reachable via R1-R2-Server; 0% loss; 8.0ms RTT | PASS |
| TC-02 | Physical Link Failure (R2-Server) | Failover to alternate route R1-R3-Server; R2-Server stays DOWN | Rerouted over R3; R2-Server remains DOWN | PASS |
| TC-03 | Invalid Gateway Injection | Diagnosed (98% confidence); restored to valid router R1 | Gateway corrected to R1; 100% reachability | PASS |
| TC-04 | DNS Daemon Crash Injection | Diagnosed (95% confidence); service restarted | Resolver restored; nslookup succeeds | PASS |
| TC-05 | Degraded Packet Loss (33%) | Evaluates lower-loss alternate route; maintains surviving path | Surviving route maintained; degraded health reported | PASS |
| TC-06 | Complete Network Partition | R2 & R3 down; reports RECOVERY UNAVAILABLE with 0 actions | RECOVERY UNAVAILABLE; 0 redundant actions | PASS |

Table 4.1: Master Functional Test Results and Verification Status.

4.5 Performance, Reliability, and Security Considerations
- Performance: Diagnosis and recovery planning execute in under 1 millisecond (measured at 0.000656 s and 0.000677 s), providing instantaneous real-time feedback.
- Reliability: Our 7-point independent audit tests reachability, gateway validity, DNS, route isolation, latency, and packet loss before declaring a fix verified. If an action fails, a snapshot rollback automatically restores the network.
- Security: The fault registry is completely isolated from the monitoring system, ensuring that diagnosis cannot be influenced by hidden fault tags.
____________________________________________________________________
CHAPTER 5: CONCLUSION

5.1 Summary
In this project, we successfully built and validated a complete network fault diagnosis and automated recovery framework. By combining a Cisco Packet Tracer-style visual canvas with a simulated Windows CMD terminal, we demonstrated how an enterprise network can detect faults, diagnose root causes with calibrated confidence, and reroute traffic around severed links. All ten project objectives were accomplished, and the implementation passed all 200 automated regression tests with a 100% pass rate.

5.2 Learning Outcomes
Working on this project provided valuable practical networking and engineering experience:
- Gained a deep understanding of Layer-2 switching, Layer-3 IPv4 subnetting, and routing table structures.
- Learned how to mathematically calculate cumulative packet loss across multi-hop paths and implement multi-objective route selection.
- Experienced the importance of building transparent, rule-based diagnostic systems that can be easily inspected and understood.
- Strengthened Python development skills, including graph algorithms in NetworkX, GUI design in Tkinter, and comprehensive automated unit testing.

5.3 Limitations
- The network currently runs inside a software graph simulation rather than directly configuring physical Cisco routers or switches.
- We focused on enterprise intra-domain routing rather than exterior BGP routing between different internet service providers.
- Latency and loss thresholds are set to static values rather than learning from changing day-to-night traffic patterns.

5.4 Future Enhancements
- Connecting our recovery engine to real Software-Defined Networking (SDN) controllers using OpenFlow or P4 so it can program physical switches.
- Expanding the routing logic to handle BGP multi-homing across multiple autonomous systems.
- Adding adaptive baseline monitoring that automatically adjusts threshold warnings as traffic volumes fluctuate during the day.
____________________________________________________________________
REFERENCES
1. J. F. Kurose and K. W. Ross, Computer Networking: A Top-Down Approach, 8th ed., Pearson, 2021.
2. A. S. Tanenbaum, N. Feamster, and D. J. Wetherall, Computer Networks, 6th ed., Pearson, 2021.
3. NetworkX Developers, “NetworkX: Network Analysis in Python,” Documentation, 2024. [https://networkx.org/]
4. Cisco Systems, “Cisco Packet Tracer User Guide,” Cisco Networking Academy, 2023. [https://www.netacad.com/]
5. Python Software Foundation, “Tkinter — Python interface to Tcl/Tk,” Python Documentation, 2024. [https://docs.python.org/3/library/tkinter.html]
____________________________________________________________________
APPENDIX
Appendix A: Official Automated Test Execution Summary
Ran 200 tests in 17.822s
OK (Pass Rate: 100.0%, Failures: 0, Errors: 0)
Stages Verified:
- Stage 0: Architecture & Baseline Regression (88 Tests) - PASS
- Stage 1: Data Model, Fault Registry & Lifecycle (12 Tests) - PASS
- Stage 2: Multi-Fault Injection Engine & Atomic Batches (12 Tests) - PASS
- Stage 3: Advanced Monitoring & Partition Detection (9 Tests) - PASS
- Stage 4: Multi-Fault Evidence-Based Root-Cause Diagnosis (7 Tests) - PASS
- Stage 5: Intelligent Global Recovery Planner (8 Tests) - PASS
- Stage 6: Coordinated Automated Recovery Engine (7 Tests) - PASS
- Stage 7: Post-Recovery Verification & Audit Logging (12 Tests) - PASS
- Stage 8: Interactive Operator Dashboard (15 Tests) - PASS
- Stage 9: Windows CMD-Style Network Terminal (12 Tests) - PASS
- Stage 10: Demonstration Scenarios A through H (18 Tests) - PASS

Appendix B: Simulated Terminal (network_terminal.py) Commands
- ping <host>: Transmits ICMP Echo requests and reports round-trip time.
- tracert <host>: Traces active forwarding hops to destination.
- nslookup <domain>: Resolves domain name using simulated DNS daemon.
- ipconfig [/all]: Displays IP, subnet mask, gateway, and DNS resolver.
- show devices / links / routes: Displays active topology state and routing paths.
- diagnose / recover: Triggers observation-based diagnosis and coordinated recovery.
