# Comprehensive Final Project Report

## Project Title
**Design and Development of an Intelligent Network Fault Injection, Root-Cause Diagnosis and Automated Recovery Framework**

---

## 1. Executive Summary & Abstract

Modern computer networks are complex, multi-tiered distributed systems where localized failures—ranging from physical trunk severance and default gateway misconfiguration to DNS resolver outages and quality degradation (excess latency, probabilistic packet loss)—can rapidly cascade into widespread service unavailability. Rapid resolution requires continuous telemetry monitoring, explainable root-cause diagnosis, multi-objective recovery planning, and verifiable self-healing.

This project delivers a comprehensive, enterprise-grade network simulation, diagnostic reasoning, and automated self-healing framework. Operating on a simulated network topology modeled in NetworkX, the system pairs an authentic **Cisco Packet Tracer-inspired visual workspace** with a standalone **Windows Command Prompt-style network terminal** (`network_terminal.py`). 

The architecture strictly decouples the operational lifecycle into modular stages:
1. **Network Modeling & Workspace**: Dynamic topology creation, device palettes, cable management, configuration inspectors, and clipboard operations.
2. **Transactional Multi-Fault Injection Engine (`scenario_manager.py`)**: Atomic multi-fault batch injection with pre-validation and rollback protection.
3. **Fault Instance Registry (`fault_registry.py`)**: Centralized lifecycle tracking with unique identifiers (`FLT-XXXX`, `SCN-XXXX`), completely isolated from diagnostic telemetry.
4. **Network Monitoring Module (`monitoring.py`)**: Pure telemetry collection without inspecting fault labels; graph connected component partition analysis; probabilistic packet loss modeling.
5. **Multi-Fault Root-Cause Diagnosis Engine (`diagnostics.py`)**: Simultaneous evaluation of all failure modes without early termination; calibrated confidence scores; distinction between root causes and secondary symptoms.
6. **Global Multi-Objective Recovery Planner (`recovery_planner.py`)**: Normalized route optimization balancing path cost, latency, and loss; dependency-ordered action scheduling.
7. **Coordinated Recovery Engine (`recovery.py`)**: Targeted configuration repair and fault bypass (failed physical links remain strictly **DOWN**); honest handling of partitions and unfeasible reroutes.
8. **Hybrid Intelligent Decision Engine (`decision_engine.py`)**: Risk assessment scoring (0–100) and multi-strategy generation under `HYBRID`, `FULLY_MANUAL`, and `AUTOMATIC_SAFE` operating policies.
9. **Clean Multi-Tab Operator Interface (`main.py`)**: 8 structured tabs (`Diagnosis & Telemetry`, `Recovery & Verification`, `Multi-Route Matrix`, `Performance`, `Event Log`, `Recovery Planner`, `Audit & Analytics`, and `Network Analytics & Trends`).
10. **Network Analytics Engine (`analytics_engine.py`)**: 6 Matplotlib visualization graphs, MTTR calculation, and CSV/PNG export capabilities.
11. **Post-Recovery Verification & Audit Logger (`audit_logger.py`)**: Independent four-point telemetry verification, metric deltas, and immutable audit history.

The framework is implemented in Python, NetworkX, Tkinter, and Matplotlib. It contains **zero black-box machine learning**, external datasets, or hardware dependencies. The entire regression suite comprises **192 automated unit tests** achieving a **100% pass rate**.

---

## 2. Mathematical Formulations & Algorithms

### 2.1 Multi-Objective Route Optimization
For candidate route $r \in \mathcal{R}_{\text{usable}}$, let $C(r)$ be cumulative hop cost, $L(r)$ be cumulative latency (ms), and $P(r)$ be probabilistic packet loss (%). Min-max normalization maps each metric to $[0, 1]$:
$$\hat{C}(r) = \frac{C(r) - C_{\min}}{C_{\max} - C_{\min} + \epsilon}, \quad \hat{L}(r) = \frac{L(r) - L_{\min}}{L_{\max} - L_{\min} + \epsilon}, \quad \hat{P}(r) = \frac{P(r) - P_{\min}}{P_{\max} - P_{\min} + \epsilon}$$

The multi-objective route score $\mathcal{S}(r)$ is computed using policy weights $(w_c, w_l, w_p)$:
$$\mathcal{S}(r) = w_c \cdot \hat{C}(r) + w_l \cdot \hat{L}(r) + w_p \cdot \hat{P}(r)$$
The optimal route $r^* = \arg\min_{r} \mathcal{S}(r)$ minimizes this multi-objective cost.

### 2.2 Probabilistic End-to-End Packet Loss
For path $r = (e_1, e_2, \dots, e_k)$ where link $e_i$ has independent drop probability $p_i \in [0, 1]$:
$$P(\text{Delivery}) = \prod_{i=1}^{k} (1 - p_i) \implies P(\text{e2e Loss}) = 1 - \prod_{i=1}^{k} (1 - p_i)$$

### 2.3 Calibrated Diagnostic Confidence
Diagnostic findings assign calibrated confidence scores based on evidentiary certainty:
- **Direct Physical Observation (Link Status == DOWN)**: $C = 1.00$
- **Configuration Interface Audit (Default Gateway Mismatch)**: $C = 0.98$
- **Simulated DNS Resolver Probe Failure**: $C = 0.95$
- **Degraded Telemetry (Latency > Threshold, Loss > Threshold)**: $C = 0.90$

### 2.4 Multi-Factor Risk Assessment Scoring
$$\text{RiskScore} = \text{Base}(10) + \Delta_{\text{Severity}} + \Delta_{\text{Reversibility}} + \Delta_{\text{RouteQuality}} + \Delta_{\text{Scope}}$$
- $\Delta_{\text{Severity}}$: CRITICAL (+25), HIGH (+15), MEDIUM (+5)
- $\Delta_{\text{Reversibility}}$: Non-Reversible (+30), Reversible (+0)
- $\Delta_{\text{RouteQuality}}$: Route Loss $> 20\%$ (+25), Latency $> 150\text{ms}$ (+20)
- Policy Threshold: If $\text{RiskScore} \le 40$, the action is classified as `AUTO_EXECUTE`; if $> 40$, it requires explicit human operator approval (`REQUIRES_APPROVAL`).

---

## 3. System Architecture & Modular Design

```
+---------------------------------------------------------------------------------------------------+
|                                  INTEGRATED USER INTERFACES                                       |
|  • Cisco Packet Tracer Logical Topology Workspace (Palette, Cables, Inspectors, Halos, Undo/Redo) |
|  • 8-Card Responsive KPI Management Bar (Devices, Links, Faults, Crit, Avail, Health, Route)      |
|  • Interactive Intelligent Recovery Center (Investigate, Generate, Compare, Approve, Execute)     |
|  • 6-Graph Network Analytics Visualizer (Latency, Loss, Availability, Distribution, MTTR, Route)  |
|  • Windows CMD-Style Simulated Network Terminal (ping, tracert, nslookup, ipconfig, show, diag)   |
+---------------------------------------------------------------------------------------------------+
                               |                                              ^
                               | Trigger Batch Injection                      | Fresh Telemetry & Audit
                               v                                              |
+-----------------------------------------------+             +-------------------------------------+
|        TRANSACTIONAL FAULT INJECTION          |             |     STAGE 1: ADVANCED MONITORING    |
|   • Pre-Injection Batch Validation            | Snapshot    | • Pure Telemetry Collection         |
|   • MultiFaultScenario Builder & Preview      | ----------> | • Partition Detection (Connected)   |
|   • Atomic Rollback on Failure                |             | • Probabilistic Loss P(e2e loss)    |
+-----------------------------------------------+             +-------------------------------------+
                               |                                                 |
                               v                                                 v Raw Observations (Dict)
+-----------------------------------------------+             +-------------------------------------+
|           CENTRALIZED FAULT REGISTRY          |             |     STAGE 2: ROOT-CAUSE DIAGNOSIS   |
|   • Unique IDs: FLT-XXXX, SCN-XXXX            |             | • All 5 Failure Modes Evaluated     |
|   • Lifecycle: ACTIVE, RESOLVED, CANCELLED    |             | • Calibrated Confidence (0.90-1.0)  |
|   • Strictly Isolated from Diagnostics        |             | • ROOT_CAUSE vs SECONDARY_SYMPTOM   |
+-----------------------------------------------+             +-------------------------------------+
                                                                                 |
                                                                                 v Diagnostic Findings
+-----------------------------------------------+             +-------------------------------------+
|      STAGE 4: COORDINATED RECOVERY ENGINE     |             |      STAGE 3: RECOVERY PLANNER      |
|   • Gateway Repair -> DNS -> Route Activation | <---------- | • Multi-Objective Route Scoring     |
|   • Fault Bypass: Failed Links Kept DOWN      | Planned     | • Dependency-Ordered Action Sequence|
|   • Service Maintained (0 Actions)            | Strategy    | • Strictly Read-Only Planning       |
+-----------------------------------------------+             +-------------------------------------+
        |                                                                        ^
        v Executed Actions & Snapshot Safety                                     |
+--------------------------------------------------------------------------------+------------------+
|                     HYBRID INTELLIGENT SELF-HEALING DECISION ENGINE                              |
|   • Governance Policies: HYBRID (Default), FULLY_MANUAL, AUTOMATIC_SAFE                           |
|   • Multi-Factor Risk Assessment Scoring (0 - 100)                                                 |
|   • Multi-Strategy Generation (Primary Optimal, Secondary Alternative, Conservative Isolation)   |
|   • Preconditions Verification, Human-in-the-Loop Approvals & Atomic Rollback Protection          |
+---------------------------------------------------------------------------------------------------+
                               |
                               v
+---------------------------------------------------------------------------------------------------+
|                     POST-RECOVERY INDEPENDENT VERIFICATION & AUDIT LOGGING                        |
|   • Fresh Telemetry Observation Scan (Report D)                                                   |
|   • Decoupled Status: Service Availability (AVAILABLE/UNAVAILABLE) vs Health (HEALTHY/DEGRADED)   |
|   • AuditRecord Tracking (Execution ID, Timestamp, Metric Deltas, Rollback Flags, Durations)      |
|   • Comprehensive JSON Serialization and CSV Historical Analytics Export                          |
+---------------------------------------------------------------------------------------------------+
```

---

## 4. Summary of Completed Project Stages (Stages 0 through 10)

### Stage 0: Architecture Mapping & Baseline Verification
- Verified default baseline topology: 5 devices (`PC1`, `R1`, `R2`, `R3`, `Server`) and 5 links.
- Verified all 88 baseline unit tests passing without modifications or deletions.
- Created immutable checkpoint: `checkpoint_stage0/`.

### Stage 1: Data Model, Fault Registry & Lifecycle Management
- Implemented `fault_registry.py` with `FaultRecord`, `FaultStatus`, and `FaultRegistry`.
- Implemented unique sequential IDs: `FLT-XXXX` for fault instances, `SCN-XXXX` for scenarios.
- Implemented formal state transitions: `ACTIVE` $\rightarrow$ `RESOLVED` / `CANCELLED` / `SUPPRESSED`.
- Enforced complete isolation: diagnostic engine cannot read the registry.
- Total tests: **100 / 100 PASSED** | Checkpoint: `checkpoint_stage1/`.

### Stage 2: Multi-Fault Injection Engine & Atomic Transactions
- Implemented `scenario_manager.py` with `inject_fault_batch`, `capture_network_snapshot`, `restore_network_snapshot`.
- Implemented pre-injection validation rejecting conflicting link failures, nonexistent hosts, and out-of-range parameters (loss $<0$ or $>100$, negative latency).
- Implemented atomic rollback: any failure restores exact network snapshot.
- Total tests: **112 / 112 PASSED** | Checkpoint: `checkpoint_stage2/`.

### Stage 3: Advanced Monitoring & Partition Detection
- Enhanced `monitoring.py` to collect telemetry without reading fault labels.
- Implemented NetworkX connected components topology partition detection.
- Implemented probabilistic end-to-end packet loss calculation.
- Total tests: **121 / 121 PASSED** | Checkpoint: `checkpoint_stage3/`.

### Stage 4: Multi-Fault Evidence-Based Root-Cause Diagnosis
- Enhanced `diagnostics.py` to evaluate all 5 failure modes simultaneously without early exit.
- Implemented calibrated confidence levels ($1.0, 0.98, 0.95, 0.90$).
- Structured output format into Report A (Monitoring Telemetry) and Report B (Diagnostic Findings).
- Total tests: **128 / 128 PASSED** | Checkpoint: `checkpoint_stage4/`.

### Stage 5: Intelligent Global Recovery Planner
- Implemented `recovery_planner.py` with `RecoveryPlan`, `RecoveryAction`, and `RecoveryDecision`.
- Multi-objective route scoring combining cost, latency, and loss.
- Dependency-ordered actions: Gateway repaired before DNS; DNS before path activation.
- Strictly read-only: planner never mutates the graph.
- Total tests: **136 / 136 PASSED** | Checkpoint: `checkpoint_stage5/`.

### Stage 6: Coordinated Automated Recovery Engine
- Enhanced `recovery.py` to execute coordinated recovery actions in dependency order.
- Fault bypass: failed physical links strictly remain in the **DOWN** state after rerouting.
- Service Maintained: when an alternate route already avoids the failed link, zero actions are executed (`actions_count = 0`).
- Total tests: **143 / 143 PASSED** | Checkpoint: `checkpoint_stage6/`.

### Stage 7: Post-Recovery Verification, Analytics & Audit Engine
- Implemented `audit_logger.py` with `AuditRecord` and `AuditLogger`.
- Implemented structured independent verification (Report D).
- Implemented before/after metric delta calculations and JSON/CSV export.
- Total tests: **150 / 150 PASSED** | Checkpoint: `checkpoint_stage7/`.

### Stage 8: Professional Network Management Dashboard
- Implemented 8-card responsive KPI dashboard bar in `main.py`.
- Added Multi-Fault Injection Scenario Builder tab.
- Added Active Faults registry viewer tab with individual resolution.
- Added Pre-Execution Recovery Planner inspection tab.
- Added Audit History filterable table with export actions.
- Total tests: **155 / 155 PASSED** | Checkpoint: `checkpoint_stage8/`.

### Stage 9: Windows CMD-Style Simulated Network Terminal
- Implemented `network_terminal.py` with authentic Windows Command Prompt styling (`C:\NETWORK\<host>>`).
- Supported network commands: `ping`, `tracert`, `nslookup`, `ipconfig`, `show`, `diagnose`, `recover`.
- Bound terminal launcher to **`Ctrl+T`** and toolbar button.
- Total tests: **162 / 162 PASSED** | Checkpoint: `checkpoint_stage9/`.

### Stage 10: Hybrid Decision Engine, 6 Graphs & Demonstrations
- Implemented `decision_engine.py`: Multi-factor risk scoring, governance policies (`HYBRID`, `FULLY_MANUAL`, `AUTOMATIC_SAFE`), and multi-strategy generation.
- Integrated Decision Engine with terminal commands (`approve`, `reject`, `execute`, `show decisions`, `show pending`) and clean GUI notebook lineup.
- Implemented `analytics_engine.py` and `_build_network_analytics_tab` in `main.py`: 6 live Matplotlib graphs with non-overlapping subplot layout, MTTR calculation, and CSV/PNG export.
- Implemented end-to-end Demonstration Scenarios A through H.
- Total tests: **192 / 192 PASSED (100% OK)** | Checkpoint: `checkpoint_stage10/`.

---

## 5. Verification Results and Demonstration Scenarios (A through H)

The automated test suite (`tests/test_project.py`) validates all demonstration scenarios:

- **Scenario A (Multiple Link Failures):**
  - Severed links `R1-R2` and secondary connections simultaneously.
  - Telemetry detected severed links; diagnosis identified both root causes; partition analysis verified alternative route availability.
  - Failover activated `PC1 -> R1 -> R3 -> Server`; failed links remained **DOWN**; verification passed.
- **Scenario B (Combined Fault Types):**
  - Injected Link Failure (`R1-R2`), DNS Failure, and Wrong Default Gateway simultaneously.
  - Diagnosis produced 3 independent findings. Recovery executed actions in strict priority order (Gateway $\rightarrow$ DNS $\rightarrow$ Reroute).
  - Verification confirmed gateway restored to `R1`, DNS set to `True`, and traffic rerouted via `R3`.
- **Scenario C (Partial Recovery & Partition):**
  - Severed all links to `Server` (`R2-Server` and `R3-Server`) and misconfigured `PC1`'s gateway.
  - Gateway repair executed cleanly, but physical partition blocked end-to-end reachability.
  - System reported `RECOVERY UNAVAILABLE` / `PARTIAL RECOVERY` with `service_availability = UNAVAILABLE` without falsely rolling back the gateway repair.
- **Scenario D (Service Already Maintained):**
  - Cut `R1-R3` while primary traffic was active on `PC1 -> R1 -> R2 -> Server`.
  - Recovery verified that the active route avoided the failed link; executed **0 corrective actions**; reported `SERVICE MAINTAINED` with `network_health = DEGRADED`.
- **Scenario E (Multiple Packet Loss Links):**
  - Injected $30\%$ loss on `R1-R2` and $40\%$ loss on `R2-Server`.
  - Probabilistic path loss calculated as $1 - (1-0.3)(1-0.4) = 58\%$.
  - Multi-objective planner rerouted traffic to clean alternative route `R1-R3-Server` with $0\%$ loss.
- **Scenario F (Fallback and Rollback Safety):**
  - Tested controlled failure where verification failed; network state restored cleanly to pre-execution snapshot with zero residual side-effects.
- **Scenario G (Terminal & Dashboard State Consistency):**
  - Demonstrated running CLI commands (`ping`, `tracert`, `show routes`, `diagnose`, `approve`, `execute`) in `network_terminal.py`.
  - Verified that all state changes reflected instantaneously in the visual GUI dashboard.
- **Scenario H (Professional Dashboard Integration):**
  - Validated all 8 KPI cards, multi-fault injection builder, recovery planner, interactive recovery center, 6 analytics graphs, and audit history views.

---

## 6. Official Test Suite Execution Summary

```text
======================================================================
TEST EXECUTION REPORT
Framework: Python unittest
Working Directory: Network_Fault_Diagnosis_Backup
======================================================================

Ran 192 tests in 65.279s

OK

Test Breakdown by Module:
• FrameworkTests (Baseline Topology, Palette, GUI, Inspectors, Clipboard): 88 tests (PASSED)
• Stage1FaultRegistryTests (IDs, Lifecycle Transitions, Clear): 12 tests (PASSED)
• Stage2MultiFaultInjectionTests (Batch Injection, Pre-validation, Rollback): 12 tests (PASSED)
• Stage3MonitoringAndPartitionTests (Partition Analysis, Probabilistic Loss): 9 tests (PASSED)
• Stage4MultiFaultDiagnosisTests (Calibrated Confidence, Independence): 7 tests (PASSED)
• Stage5RecoveryPlannerTests (Multi-objective Route Scoring, Dependencies): 8 tests (PASSED)
• Stage6CoordinatedRecoveryTests (Fault Bypass, Service Maintained): 7 tests (PASSED)
• Stage7VerificationAndAuditTests (Audit Logging, Deltas, JSON/CSV Export): 7 tests (PASSED)
• Stage8DashboardTests (KPI Cards, Multi-Fault Builder UI, Planner View): 5 tests (PASSED)
• Stage9TerminalTests (CMD Prompt, ping, tracert, nslookup, ipconfig, CLI): 7 tests (PASSED)
• Stage10DecisionEngineTests (Risk Scoring, Policies, Approvals, Rollback): 6 tests (PASSED)
• Stage10AnalyticsEngineTests (Telemetry Trends, MTTR, 6 Graphs, Exports): 5 tests (PASSED)
• Stage10InteractiveRecoveryCenterUITests (Recovery Center Controls): 3 tests (PASSED)
• Stage10DemonstrationScenariosTests (Scenarios A through H End-to-End): 8 tests (PASSED)
• SurgicalBugFixPassTests (Action Count, Deduplication, Degraded Bypass, Telemetry, Recovery Center Callbacks): 8 tests (PASSED)
----------------------------------------------------------------------
TOTAL PASS RATE: 100% (192 Passed, 0 Failures, 0 Errors)
```

---

## 7. Viva Defense & Technical Q&A

**Q1: How does your system distinguish between a root cause and a secondary symptom?**  
*Answer:* Secondary symptoms (such as an endpoint becoming unreachable or a network partition) are consequences of underlying topological or protocol failures. The monitoring module identifies that a link is physically DOWN or a gateway IP is mismatched. The diagnostic engine maps the physical link severance or gateway misconfiguration as the `ROOT_CAUSE`, while classifying the resulting partition as a `SECONDARY_SYMPTOM`.

**Q2: Why does traffic failover keep the failed link DOWN instead of marking it UP?**  
*Answer:* A self-healing network reroutes traffic *around* physical damage (fault bypass); it cannot physically repair a severed cable or damaged transceiver. Reporting the failed link as UP would be a dangerous false positive. Our framework activates an alternative forwarding path while keeping the damaged link in its actual DOWN state, correctly categorizing overall network health as `DEGRADED`.

**Q3: How does the Multi-Objective Route Planner prevent routing loops?**  
*Answer:* Route discovery utilizes NetworkX simple paths algorithms (`all_simple_paths`), which by definition explore only loopless, acyclic candidate paths. Candidate routes are then filtered by physical usability and scored using normalized cost, latency, and loss weights.

**Q4: How does the Hybrid Decision Engine determine whether to execute automatically or request approval?**  
*Answer:* Under the default `HYBRID` policy, the decision engine computes a multi-factor risk score ($0–100$) based on fault severity, reversibility, route quality, and affected subsystem scope. If the risk score $\le 40$ and the action is fully reversible (e.g., standard gateway correction or switching to an operational clean backup route), the action is classified as `AUTO_EXECUTE`. If the risk score $> 40$ or causes operational disruption, it enters the `REQUIRES_APPROVAL` queue, requiring explicit operator consent before execution.

---

## 8. Conclusion

The Intelligent Network Fault Injection, Root-Cause Diagnosis and Automated Recovery Framework successfully provides an advanced, explainable, and production-grade Computer Networks simulation system. By integrating transactional multi-fault injection, decoupled telemetry monitoring, calibrated root-cause diagnosis, multi-objective route planning, hybrid decision-making, an authentic Windows CMD terminal, and live 6-graph network analytics, the framework fulfills all academic and technical objectives with 100% test verification.
