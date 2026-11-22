# Design and Development of an Intelligent Network Fault Injection, Root-Cause Diagnosis and Automated Recovery Framework

**An Advanced, Multi-Fault Computer Networks Simulation, Coordinated Self-Healing and Network Analytics System**

Built using Python, NetworkX, Tkinter, and Matplotlib.

---

## 1. Project Overview

This application demonstrates a complete, deterministic, and explainable network management and automated self-healing framework. Operating on a simulated network topology modeled in NetworkX, it provides an authentic Cisco Packet Tracer-style visual workspace alongside an authentic Windows CMD-style network terminal (`network_terminal.py`).

The framework executes a strictly decoupled operational lifecycle:

```text
Network Configuration -> Fault Injection -> Monitoring -> Diagnosis -> Recovery Planning -> Automated Execution -> Independent Verification -> Analytics & Audit
```

### Key Capabilities

- **Simultaneous Multi-Fault Injection:** Link cuts, invalid default gateways, DNS daemon failure, elevated latency (ms), and packet loss (0-100%) applied atomically with pre-validation and safe rollback.
- **Strictly Decoupled Telemetry Monitoring:** Collects raw observations without inspecting fault labels or ground-truth metadata.
- **Topology Partition Detection:** Employs graph connected components to detect network splits and isolated endpoints.
- **Calibrated Multi-Fault Diagnosis:** Evaluates all failure modes independently without early exit; emits structured `DIAG-XXXX` findings with calibrated confidence scores (1.0 direct certainty, 0.98 configuration audit, 0.95 active probe, 0.90 degraded telemetry).
- **Global Multi-Objective Recovery Planner:** Evaluates candidate routes using normalized multi-objective scoring balancing cost, latency, and packet loss:
  $$\text{Score}(r) = w_c \cdot \hat{C}(r) + w_l \cdot \hat{L}(r) + w_p \cdot \hat{P}(r)$$
- **Fault Bypass (Not Fake Repair):** Severed physical links remain strictly **DOWN** in the graph; service is maintained or restored by dynamically activating optimal alternative routes.
- **Hybrid Intelligent Decision Engine (`decision_engine.py`):** Calculates multi-factor risk scores (0-100) and supports `HYBRID` (default), `FULLY_MANUAL`, and `AUTOMATIC_SAFE` operating governance policies.
- **Network Analytics & Six Graphs (`analytics_engine.py`):** Live Matplotlib visualization featuring:
  1. Network Latency Trends (ms) across operational phases
  2. Packet Loss Analysis (%) across individual links and end-to-end
  3. Service Availability Timeline & Outage Tracking
  4. Fault Distribution by Category and Severity
  5. Recovery Performance & Mean Time to Recovery (MTTR)
  6. Candidate Route Latency & Cost Comparison
- **Windows CMD-Style Simulated Terminal (`network_terminal.py`):** Fully integrated command prompt supporting `ping`, `tracert`, `nslookup`, `ipconfig`, `show`, `diagnose`, `recover`, `approve`, `reject`, `execute`, and `monitor`.
- **Comprehensive Audit Logger (`audit_logger.py`):** Tracks unique execution IDs, timestamps, before/after metric deltas, and provides JSON/CSV export capabilities.

---

## 2. Project Directory Structure

```text
├── main.py                     # Cisco Packet Tracer workspace GUI & 8-tab operator dashboard
├── network_terminal.py         # Windows CMD-style simulated network terminal
├── decision_engine.py          # Hybrid Self-Healing Decision Engine & Risk Assessment
├── analytics_engine.py         # Telemetry trends, MTTR analytics & 6-graph Matplotlib renderer
├── recovery_planner.py         # Multi-objective route optimization & dependency planning
├── recovery.py                 # Coordinated recovery engine & post-recovery verification
├── diagnostics.py              # Evidence-based root-cause diagnosis engine
├── monitoring.py               # Pure observation telemetry & partition detection
├── fault_registry.py           # Centralized fault lifecycle registry (FLT-XXXX, SCN-XXXX)
├── scenario_manager.py         # Atomic multi-fault batch injection & snapshot manager
├── network_model.py            # Graph topology model, routing discovery & device configuration
├── fault_injection.py          # Virtual fault state mutators & link property editors
├── metrics.py                  # End-to-end latency & probabilistic packet loss calculations
├── audit_logger.py             # Post-recovery verification logging & JSON/CSV exports
├── requirements.txt            # Python dependencies (networkx, matplotlib)
├── tests/
│   └── test_project.py         # Full 192-test comprehensive regression test suite
├── PROJECT_REPORT.md           # Master technical architecture & engineering documentation
├── TEST_RESULTS.txt            # Official 192/192 test pass log
└── FINAL_SUBMISSION_CHECKLIST.txt # Complete stage verification audit
```

---

## 3. Supported Fault Injection Scenarios

| Scenario | Target | Mechanism | Real-World Analog |
|---|---|---|---|
| **Link Failure** | Physical link (e.g., R1-R2) | Sets edge `status = "DOWN"` | Fiber severance / transceiver failure |
| **Wrong Gateway** | Host (e.g., PC1) | Sets invalid gateway IP | Misconfigured DHCP / manual typo |
| **DNS Failure** | Network service | Sets `dns_available = False` | Resolver daemon crash / port 53 unreachable |
| **High Latency** | Physical link (e.g., R1-R2) | Elevates edge `latency_ms` to 250ms | Bufferbloat / propagation delay |
| **Packet Loss** | Physical link (e.g., R1-R2) | Sets edge `packet_loss` to 40% | Dirty fiber / interface drops |
| **Atomic Multi-Fault** | Custom or predefined batch | Injects multiple faults atomically | Cascading infrastructure disaster |

---

## 4. Windows CMD-Style Simulated Terminal (`network_terminal.py`)

Access via the GUI toolbar button or keyboard shortcut **`Ctrl+T`**.

```text
======================================================================
SIMULATED NETWORK DIAGNOSTIC TERMINAL [Version 2.0.0]
Host: PC1 | IP: 192.168.1.10 | Gateway: 192.168.1.1
======================================================================
C:\NETWORK\PC1>
```

### Supported Commands

| Command | Example | Description |
|---|---|---|
| `help`, `?` | `help` | Shows available terminal commands |
| `cls`, `clear` | `cls` | Clears terminal screen |
| `hostname` | `hostname` | Displays active device context |
| `connect` | `connect Server` | Switches terminal context to another device |
| `ipconfig [/all]` | `ipconfig /all` | Displays IP, subnet mask, gateway, and DNS resolver |
| `ping` | `ping Server` | Sends ICMP Echo requests and reports round-trip time |
| `tracert` | `tracert Server` | Traces active forwarding hops to destination |
| `nslookup` | `nslookup server.local` | Resolves domain name using simulated DNS daemon |
| `show devices` | `show devices` | Lists all network devices and their interface IPs |
| `show links` | `show links` | Displays physical link states, latency, and loss |
| `show routes` | `show routes` | Displays discovered routes from current host |
| `show decisions` | `show decisions` | Displays all recovery decisions generated by Decision Engine |
| `show pending` | `show pending` | Displays decisions currently awaiting human operator approval |
| `show plan` | `show plan` | Displays pre-execution recovery plan and route rankings |
| `diagnose` | `diagnose` | Runs live observation-based root-cause diagnosis from CLI |
| `recover` | `recover` | Executes coordinated automated recovery from CLI |
| `approve` | `approve DEC-0001` | Approves pending recovery decision |
| `reject` | `reject DEC-0001 <reason>` | Rejects recovery decision with reason |
| `execute` | `execute DEC-0001` | Executes approved recovery decision with atomic rollback safety |
| `monitor` | `monitor FLT-0001` | Inspects real-time telemetry and state of specific fault |
| `exit` | `exit` | Closes terminal window |

---

## 5. Demonstration Scenarios (A through H)

The system includes automated tests and GUI workflows for all 8 demonstration scenarios:

- **Scenario A (Multiple Link Failures):** Injects multiple link cuts. Demonstrates partition analysis, candidate route discovery, and coordinated failover activation bypassing failed links while keeping them strictly DOWN.
- **Scenario B (Combined Fault Types):** Injects Link Failure + DNS Failure + Wrong Default Gateway simultaneously. Demonstrates independent multi-fault diagnosis and coordinated recovery executing repairs in strict dependency order (Gateway -> DNS -> Reroute).
- **Scenario C (Partial Recovery):** Injects severed links causing complete partition alongside a gateway fault. Demonstrates that the gateway is corrected, but end-to-end service reports `RECOVERY UNAVAILABLE` / `PARTIAL RECOVERY` with `service_availability = UNAVAILABLE`.
- **Scenario D (Service Already Maintained):** Injects a link failure on an inactive link not traversed by current traffic. Demonstrates that zero unnecessary corrective actions are executed (`actions_count = 0`), reporting `SERVICE MAINTAINED` with degraded redundancy health.
- **Scenario E (Multiple Packet Loss Links):** Injects packet loss across multiple links. Demonstrates probabilistic loss calculation $P(\text{loss}) = 1 - \prod (1 - p_i)$ and multi-objective failover to a clean 0% loss alternative path.
- **Scenario F (Fallback and Rollback):** Demonstrates transaction safety; if post-recovery verification detects an anomaly, the network state safely rolls back to the pre-execution snapshot.
- **Scenario G (Terminal & Dashboard Consistency):** Proves that running commands in the terminal (`ping`, `tracert`, `show routes`, `diagnose`, `recover`) operates on the identical live NetworkX graph visualized in the GUI dashboard.
- **Scenario H (Professional Dashboard Integration):** Demonstrates the unified dashboard: 8 KPI cards, Multi-Fault builder, Active Faults table, Pre-execution Recovery Planner, Network Analytics graphs, and Audit History.

---

## 6. How to Run and Verify

### Prerequisites

- Python 3.10+
- Dependencies: `networkx`, `matplotlib`

```powershell
pip install -r requirements.txt
```

### Run Full Regression Test Suite

Execute all 192 unit tests across Stages 0 through 10:

```powershell
python -m unittest discover -s tests -v
```

**Expected Result:**
```text
Ran 192 tests in ~50-60s
OK
```

### Launch the Visual Application

```powershell
python main.py
```

### Quick Demonstration Guide in GUI

1. **Launch Application:** Run `python main.py`.
2. **Inject Multi-Fault Scenario:** Navigate to the **Multi-Fault** tab in the left panel. Select `"Demo: Combined Link Failure + DNS Failure"` and click **Inject Predefined Batch**.
3. **Inspect Active Faults:** View the **Active Faults** tab in the left panel to inspect registered fault IDs (`FLT-XXXX`).
4. **Inspect Diagnosis:** Switch to the **Diagnosis & Telemetry** tab at the bottom to view root causes and telemetry.
5. **Inspect Recovery Plan:** Switch to the **Recovery Planner** tab to see candidate route rankings and scheduled actions.
6. **Trigger Recovery:** Click **Auto-Heal / Recover** in the top action bar to execute coordinated failover and repairs.
7. **Verify Post-Recovery State:** View the **Recovery & Verification** tab for independent verification measurements (traffic restored, failed links isolated DOWN).
8. **View 6 Analytics Graphs:** Click the **Network Analytics & Trends** tab to inspect live latency trends, packet loss bars, availability timeline, fault distribution, recovery MTTR, and route costs.
9. **Launch Terminal:** Press **`Ctrl+T`** or click **Terminal** in the toolbar. Type `ping Server`, `tracert Server`, or `show decisions`.
10. **Export Audit & Telemetry:** Click **Export CSV** in the Audit or Analytics tabs to save persistent run records.
