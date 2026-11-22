# Design and Development of an Intelligent Network Fault Injection, Root-Cause Diagnosis and Automated Recovery Framework

**An Advanced, Multi-Fault Computer Networks Simulation, Coordinated Self-Healing and Network Analytics System**

Built using Python, NetworkX, Tkinter, and Matplotlib.

---

## 1. Project Overview

This application demonstrates a complete, deterministic, and explainable network management and automated self-healing framework. Operating on a simulated network topology modeled in NetworkX, it provides an authentic Cisco Packet Tracer-style visual workspace alongside an authentic Windows CMD-style network terminal (`network_terminal.py`).

The framework executes a strictly decoupled operational lifecycle:
```
Network Configuration ➔ Fault Injection ➔ Monitoring ➔ Diagnosis ➔ Recovery Planning ➔ Interactive Decision / Execution ➔ Independent Verification ➔ Analytics & Audit
```

### Key Capabilities
- **Simultaneous Multi-Fault Injection:** Link cuts, invalid default gateways, DNS daemon failure, elevated latency (ms), and packet loss (0–100%) applied atomically with pre-validation and safe rollback.
- **Strictly Decoupled Telemetry Monitoring:** Collects raw observations without inspecting fault labels or ground-truth metadata.
- **Topology Partition Detection:** Employs graph connected components to detect network splits and isolated endpoints.
- **Calibrated Multi-Fault Diagnosis:** Evaluates all failure modes independently without early exit; emits structured `DIAG-XXXX` findings with calibrated confidence scores (1.0 direct certainty, 0.98 configuration audit, 0.95 active probe, 0.90 degraded telemetry).
- **Global Multi-Objective Recovery Planner:** Evaluates candidate routes using normalized multi-objective scoring balancing cost, latency, and packet loss:
  $$\text{Score}(r) = w_c \cdot \hat{C}(r) + w_l \cdot \hat{L}(r) + w_p \cdot \hat{P}(r)$$
- **Fault Bypass (Not Fake Repair):** Severed physical links remain strictly **DOWN** in the graph; service is maintained or restored by dynamically activating optimal alternative routes.
- **Hybrid Intelligent Decision Engine (`decision_engine.py`):** Calculates multi-factor risk scores (0–100) and supports `HYBRID` (default), `FULLY_MANUAL`, and `AUTOMATIC_SAFE` operating governance policies.
- **Interactive Recovery Center GUI:** Enables network engineers to investigate networks, generate alternative strategies, compare trade-offs, approve/reject operations, execute approved actions, and inspect diagnostic evidence.
- **Network Analytics & Six Graphs (`analytics_engine.py`):** Live Matplotlib visualization featuring:
  1. Network Latency Trends (ms) across operational phases
  2. Packet Loss Analysis (%) across individual links and end-to-end
  3. Service Availability Timeline & Outage Tracking
  4. Fault Distribution by Category and Severity
  5. Recovery Performance & Mean Time to Recovery (MTTR)
  6. Multi-Objective Route Comparison (Cost vs Latency)
- **Windows CMD-Style Simulated Terminal (`network_terminal.py`):** Fully integrated command prompt supporting `ping`, `tracert`, `nslookup`, `ipconfig`, `show`, `diagnose`, `recover`, `approve`, `reject`, `execute`, and `monitor`.
- **Comprehensive Audit Logger (`audit_logger.py`):** Tracks unique execution IDs, timestamps, before/after metric deltas, and provides JSON/CSV export capabilities.

---

## 2. Project Directory Structure

```text
├── main.py                     # Cisco Packet Tracer workspace GUI & Dashboard
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
├── metrics.py                  # Network performance metrics calculator
├── audit_logger.py             # Execution audit recorder, history manager & CSV/JSON export
├── TEST_RESULTS.txt            # Full test suite execution log (184 / 184 tests passed)
├── FINAL_SUBMISSION_CHECKLIST.txt # Complete stage verification checklist
├── README.md                   # This comprehensive manual and architectural guide
├── PROJECT_REPORT.md           # Formal academic final report and viva documentation
└── tests/
    └── test_project.py         # Complete automated test suite (184 tests across Stages 0–10)
```

---

## 3. Operational Stages Overview

| Stage | Name / Scope | Primary Artifacts | Status | Test Coverage |
|---|---|---|---|---|
| **Stage 0** | Inspection & Baseline Verification | `network_model.py`, `tests/` | **COMPLETE** | 88 / 88 Passed |
| **Stage 1** | Data Model & Fault Registry | `fault_registry.py` | **COMPLETE** | 12 Tests (100 Total) |
| **Stage 2** | Multi-Fault Injection Engine & Batch Transactions | `scenario_manager.py` | **COMPLETE** | 12 Tests (112 Total) |
| **Stage 3** | Advanced Monitoring & Partition Detection | `monitoring.py` | **COMPLETE** | 9 Tests (121 Total) |
| **Stage 4** | Multi-Fault Root-Cause Diagnosis | `diagnostics.py` | **COMPLETE** | 7 Tests (128 Total) |
| **Stage 5** | Intelligent Global Recovery Planner | `recovery_planner.py` | **COMPLETE** | 8 Tests (136 Total) |
| **Stage 6** | Coordinated Automated Recovery Engine | `recovery.py` | **COMPLETE** | 7 Tests (143 Total) |
| **Stage 7** | Verification, Analytics & Audit Engine | `audit_logger.py` | **COMPLETE** | 7 Tests (150 Total) |
| **Stage 8** | Professional Dashboard Upgrade | `main.py` | **COMPLETE** | 5 Tests (155 Total) |
| **Stage 9** | Windows CMD Network Terminal | `network_terminal.py` | **COMPLETE** | 7 Tests (162 Total) |
| **Stage 10** | Hybrid Decision Engine, 6 Graphs & Demonstrations | `decision_engine.py`, `analytics_engine.py` | **COMPLETE** | 22 Tests (**184 Total**) |

---

## 4. Simulated Terminal Command Reference

Launch the terminal via the GUI toolbar or keyboard shortcut **`Ctrl+T`**.

| Command | Syntax / Example | Description |
|---|---|---|
| `help` | `help` or `?` | Displays full command list and descriptions |
| `cls` | `cls` or `clear` | Clears terminal text buffer |
| `hostname` | `hostname` | Displays the currently selected host context |
| `connect` | `connect Server` | Switches terminal context to specified device |
| `ipconfig` | `ipconfig /all` | Displays IPv4, Netmask, Gateway, and DNS server |
| `ping` | `ping Server` | Sends 4 simulated ICMP echo requests with latency and loss |
| `tracert` | `tracert Server` | Traces multi-hop routing path with per-hop RTT |
| `nslookup` | `nslookup server.local` | Queries simulated DNS resolver for hostname IP |
| `show devices` | `show devices` | Lists all topology nodes, types, IPs, gateways, and states |
| `show links` | `show links` | Lists physical links, link status, latency (ms), and loss (%) |
| `show routes` | `show routes` | Displays discovered candidate routes from current host |
| `show decisions`| `show decisions` | Displays all recovery decisions generated by Decision Engine |
| `show pending` | `show pending` | Displays decisions currently awaiting human operator approval |
| `show plan` | `show plan` | Displays pre-execution recovery plan and route rankings |
| `diagnose` | `diagnose` | Runs live observation-based root-cause diagnosis from CLI |
| `recover` | `recover` | Executes coordinated automated recovery from CLI |
| `approve` | `approve DEC-0001` | Approves pending recovery decision |
| `reject` | `reject DEC-0001 <reason>`| Rejects recovery decision with reason |
| `execute` | `execute DEC-0001` | Executes approved recovery decision with atomic rollback safety |
| `monitor` | `monitor FLT-0001` | Inspects real-time telemetry and state of specific fault |
| `exit` | `exit` | Closes terminal window |

---

## 5. Demonstration Scenarios (A through H)

The system includes automated tests and GUI workflows for all 8 demonstration scenarios:

- **Scenario A (Multiple Link Failures):** Injects multiple link cuts. Demonstrates partition analysis, candidate route discovery, and coordinated failover activation bypassing failed links while keeping them strictly DOWN.
- **Scenario B (Combined Fault Types):** Injects Link Failure + DNS Failure + Wrong Default Gateway simultaneously. Demonstrates independent multi-fault diagnosis and coordinated recovery executing repairs in strict dependency order (Gateway $\rightarrow$ DNS $\rightarrow$ Reroute).
- **Scenario C (Partial Recovery):** Injects severed links causing complete partition alongside a gateway fault. Demonstrates that the gateway is corrected, but end-to-end service reports `RECOVERY UNAVAILABLE` / `PARTIAL RECOVERY` with `service_availability = UNAVAILABLE`.
- **Scenario D (Service Already Maintained):** Injects a link failure on an inactive link not traversed by current traffic. Demonstrates that zero unnecessary corrective actions are executed (`actions_count = 0`), reporting `SERVICE MAINTAINED` with degraded redundancy health.
- **Scenario E (Multiple Packet Loss Links):** Injects packet loss across multiple links. Demonstrates probabilistic loss calculation $P(\text{loss}) = 1 - \prod (1 - p_i)$ and multi-objective failover to a clean 0% loss alternative path.
- **Scenario F (Fallback and Rollback):** Demonstrates transaction safety; if post-recovery verification detects an anomaly, the network state safely rolls back to pre-execution snapshot.
- **Scenario G (Terminal & Dashboard Consistency):** Proves that running commands in the terminal (`ping`, `tracert`, `show routes`, `diagnose`, `recover`) operates on the identical live NetworkX graph visualized in the GUI dashboard.
- **Scenario H (Professional Dashboard Integration):** Demonstrates the unified dashboard: 8 KPI cards, Multi-Fault builder, Active Faults table, Pre-execution Recovery Planner, Interactive Recovery Center, Network Analytics graphs, and Audit History.

---

## 6. How to Run and Verify

### Prerequisites
- Python 3.10+
- Dependencies: `networkx`, `matplotlib`

```powershell
pip install networkx matplotlib
```

### Run Full Regression Test Suite
Execute all 184 unit tests across Stages 0 through 10:
```powershell
python -m unittest discover -s tests -v
```
**Expected Result:**
```text
Ran 184 tests in ~16-20s
OK
```

### Launch the Visual Application
```powershell
python main.py
```

### Quick Demonstration Guide in GUI
1. **Launch Application:** `python main.py`
2. **Inject Multi-Fault Scenario:** Navigate to the **Multi-Fault** tab in the left panel. Select `"Demo: Combined Link Failure + DNS Failure"` and click **⚡ Inject Predefined Batch**.
3. **Inspect Active Faults:** View the **Active Faults** tab in the left panel to inspect registered fault IDs (`FLT-XXXX`).
4. **Investigate via Interactive Recovery Center:** Click the **🛡️ Interactive Recovery Center** tab at the bottom. Click **🔍 Investigate Network**.
5. **Compare Strategies:** Click **⚖️ Compare Strategies** to review the risk score, expected latency, packet loss, and trade-offs.
6. **Approve & Execute:** Select Strategy 1, click **✅ Approve**, then click **⚡ Execute Approved Action**.
7. **Verify Post-Recovery State:** Click **🧪 Verify** to view fresh independent verification measurements (0% loss, restored DNS, failed link isolated DOWN).
8. **View 6 Analytics Graphs:** Click the **📊 Network Analytics & Trends** tab to inspect live latency trends, packet loss bars, availability timeline, fault distribution, recovery MTTR, and route costs.
9. **Launch Terminal:** Press **`Ctrl+T`** or click **💻 Terminal** in the toolbar. Type `ping Server`, `tracert Server`, or `show decisions`.
10. **Export Audit & Telemetry:** Click **📥 Export CSV** in the Audit or Analytics tabs to save persistent run records.
#   C N - p r o j e c t - s e m - 3  
 