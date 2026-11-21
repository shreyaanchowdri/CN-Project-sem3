# Intelligent Network Fault Diagnosis and Automated Recovery Framework
## Cisco Packet Tracer-Style Network Simulation Workspace

An enterprise-ready, graph-based virtual network modeling, fault injection, observation-based root-cause diagnosis, and automated recovery platform built with Python, NetworkX, Tkinter, and Matplotlib.

Features a professional **Cisco Packet Tracer-inspired Network Simulation Workspace** layout with device palette categories (Routers, Switches, PCs, Laptops, Servers), interactive cable connection tools, device/link configuration inspectors, multi-path discovery, live route comparison matrix, explainable decision engine, and complete **keyboard-based Copy, Paste, Cut, Duplicate, Undo & Redo** operations.

---

## Key Features & Workspace Architecture

### 1. Cisco Packet Tracer-Style Main Interface Layout
- **Top Menu Bar**:
  - `File`: New Workspace (`Ctrl+N`), Open Topology (`Ctrl+O`), Save Topology (`Ctrl+S`), Export CSV, Exit.
  - `Edit`: Undo (`Ctrl+Z`), Redo (`Ctrl+Y`), Cut Device (`Ctrl+X`), Copy Device (`Ctrl+C`), Paste Device (`Ctrl+V`), Duplicate Device (`Ctrl+D`), Select All (`Ctrl+A`), Clear Selection (`Esc`), Delete Selected (`Del`), Reset to Default.
  - `View`: Zoom In (`Ctrl++`), Zoom Out (`Ctrl+-`), Fit to Screen (`Ctrl+0`), Toggle Grid Lines.
  - `Tools`: Select Tool (`S`), Move / Pan Tool (`M`), Cable Connection Tool (`C`), Delete Tool (`D`).
  - `Simulation`: Inject Active Fault Scenario, Monitor Network & Telemetry (`F5`), Automated Recovery & Verification (`F6`), Reset Simulation (`F4`).
  - `Help`: Cisco Packet Tracer Workspace Guide, About Intelligent Network Fault Framework.
- **Top Toolbar (Two-Row Responsive Layout)**:
  - **Row 1 — Workspace & Editing Tools**:
    - Direct tool selectors: `↖ Select`, `✥ Move`, `⚡ Connect` (Cable tool), `✖ Delete`.
    - Quick edit buttons: `↩ Undo`, `↪ Redo`, `📋 Copy`, `📥 Paste`, `⎘ Dup`.
    - Zoom & View controls: `🔍+ Zoom In`, `🔍- Zoom Out`, `⛶ Fit Screen`.
    - Real-time status text and live network health pill indicator (`HEALTHY`, `DEGRADED`, `CRITICAL`).
  - **Row 2 — Simulation & Diagnostics Control Strip**:
    - Full-width fault scenario dropdown (`width=30`, `height=6`) displaying all six complete scenario names without truncation.
    - Simulation action buttons: `⚡ Inject Fault`, `🔍 Monitor & Diagnose`, `🛡 Recover & Verify`, `🔄 Reset`.
    - Active engine telemetry & observation status indicator.
- **Left Sidebar — Network Device Palette**:
  - Device categories with distinct Cisco-style color coding:
    - **Routers**: Cisco 2911 ISR (`#15803d` Emerald Green)
    - **Switches**: Cisco Catalyst 2960 (`#d97706` Amber)
    - **End Devices**: Desktop Workstation PC (`#0284c7` Ocean Blue), Mobile Workstation Laptop (`#0284c7` Sky Blue), Enterprise Server (`#7c3aed` Purple)
  - One-click palette addition with auto-generated unique names (`Router1`, `Router2`, `Switch1`, `Switch2`, `PC1`, `PC2`, `Laptop1`, `Server1`).
- **Centre Workspace — Interactive Logical Canvas**:
  - Matplotlib canvas with Cisco Packet Tracer grid background.
  - Drag-and-drop device positioning with dynamic viewport margin expansion and group drag support.
  - Multi-cable visual rendering: Straight-Through (solid black), Cross-Over (dashed amber), Fiber (bright orange), Serial (crimson).
  - Live link state color badges: Green (`UP`), Red (`DOWN`), Orange (`DEGRADED`).
  - Circular port dots and luminous halo selection rings.
  - Mouse-wheel zoom in/out, pan workspace, fit to screen.
- **Right Sidebar — Inspector Pane**:
  - **Device Config Tab**: Inspect and edit Device Name, Device Type, IP Address, Subnet Mask, Default Gateway, DNS Server.
  - **Link Config Tab**: Inspect and edit Cable Type, Cost metric, Latency (ms), Packet Loss (%), and Operational Status (`UP`/`DOWN`).
  - **Network Overview Tab**: Route endpoint selectors (Source / Target) and live Device / Link tables.
- **Bottom Dockable Panel**:
  - `🩺 Diagnosis & Telemetry`: Structured telemetry observations and explainable IF-THEN diagnostic findings.
  - `🛡 Recovery & Verification`: Automated repairs, failover routes, and post-repair verification checks.
  - `𔔀 Multi-Route Matrix`: Complete route comparison table (Path, Cost, Latency, Loss, Availability, Selection) and explainable decision rationale.
  - `📊 Performance`: End-to-end latency, hop count, cost, loss, reachability, and diagnostic/recovery runtimes.
  - `📋 Event Log`: Monospace timestamped audit trail of all actions, tool switches, and simulation events.

---

## 2. Keyboard-Based Copy, Paste, Cut, Duplicate, Undo & Redo

### A. Copy Device — `Ctrl + C`
- Copies the complete configuration of selected device(s) into an internal clipboard.
- Supports all device types: PCs, Laptops, Routers, Switches, Servers.
- Preserves configuration properties (Device Type, IP address, Subnet Mask, Default Gateway, DNS Server).
- Strictly does not copy existing connections.

### B. Paste Device — `Ctrl + V`
- Creates independent devices from clipboard configurations with automatically generated unique IDs and names (e.g. copying `Router1` pastes as `Router2`, copying `PC1` pastes as `PC2`).
- Places newly created devices slightly offset from originals (`+0.5, -0.4`).
- Repeated `Ctrl+V` presses cascade down and right with fresh unique names (`PC2`, `PC3`, `PC4`, etc.).
- Newly pasted devices are fully independent: can be moved and connected freely.

### C. Cut Device — `Ctrl + X`
- Copies the selected device(s) to the clipboard and removes them from the topology.
- Safely severs and deletes connected links.
- Allows pasting the cut device(s) anywhere in the topology afterward.

### D. Duplicate Device — `Ctrl + D`
- One-touch duplication combining Copy and Paste into a single atomic action.
- Assigns a unique name, preserves configuration, and offsets placement.

### E. Multiple Selection (Ctrl+Click & Ctrl+A)
- Select multiple devices using `Ctrl+Click`. Selected devices display luminous halo rings.
- `Ctrl+A`: Select all devices on canvas.
- Group Drag-and-Drop: Dragging any selected device moves all selected devices together, strictly preserving their relative layout.
- Group Copy & Paste: `Ctrl+C` and `Ctrl+V` copy and paste all selected devices while maintaining their exact relative distances.
- Does not automatically replicate external connections.

### F. Undo (`Ctrl + Z`) and Redo (`Ctrl + Y`)
- Full snapshot stack (up to 30 states) capturing complete graph state, positions, attributes, and selections.
- Safely reverts and re-applies device additions, deletions, cuts, pastes, group drags, connection additions, and configuration modifications.

### G. Text Editing Safety
- Keyboard shortcuts intelligently detect active focus:
  - When typing in an IP address, Subnet Mask, Gateway, or text area, `Ctrl+C`, `Ctrl+V`, `Ctrl+X`, `Ctrl+Z`, `Ctrl+A`, and `Delete` operate exclusively on text and are never intercepted by workspace actions.
  - When the workspace canvas has focus, shortcuts trigger network topology operations.

---

## 3. Dynamic Connection Management
- **Interactive Cable Connection**:
  1. Activate the `⚡ Connect` tool.
  2. Click the source device on the canvas (highlighted with connection halo).
  3. Click the destination device.
  4. The connection is established immediately, drawing the link and opening the **Link Configuration Dialog** to set cable type, cost, latency, loss, and status.
- **Connection Types Supported**:
  - Copper Straight-Through
  - Copper Cross-Over
  - Fiber
  - Serial
- **Constraint Enforcement**:
  - Strictly prevents invalid self-connections (connecting a device to itself).
  - Strictly prevents duplicate connections between the same pair of devices.

---

## 4. Multiple-Route Discovery, Comparison & Selection
- **Multi-Path Discovery**: Discovers all simple loopless paths between any selected source and destination using NetworkX.
- **Route Comparison Matrix**: Displays all discovered routes side-by-side with Route Cost, Total Latency, Maximum Packet Loss, Availability Status (`Healthy`, `Degraded`, `Unavailable`), and Selection Indicator (`★ YES` / `NO`).
- **Explainable Selection Decision**: Rule-based decision engine evaluates paths against link health, latency thresholds, packet loss, and cost, generating clear plain-English selection rationales.

---

## 5. Observation-Based Root-Cause Diagnosis
- **Strict Architectural Independence**:
  - Fault Injection Engine only modifies virtual network state.
  - Monitoring Engine gathers raw telemetry and configuration data.
  - Diagnosis Engine receives strictly observations and graph configuration—never reading scenario names or fault labels.
- **Supported Diagnostic Scenarios**:
  1. *Link failure*: Inspects actual link status and connectivity (`status == 'DOWN'`).
  2. *Wrong default gateway*: Compares host gateway configuration with valid topology/configuration and tests gateway reachability.
  3. *DNS failure*: Distinguishes operational IP connectivity from failed DNS probe.
  4. *High latency*: Compares observed path/link latency with configurable threshold (>100ms).
  5. *Packet loss*: Compares observed packet-loss percentage with configurable threshold (>0%).
- **Calibrated Confidence**: Conclusive hardware link state reports 100%, configuration audits report 98%, probe verifications report 95%, and sampled latency/loss metrics report 90–92%.

---

## 6. Automated Recovery and Verification
- **Diagnosis-Driven Action Plan**:
  - Bypasses failed links by recalculating optimal paths over alternate healthy routes.
  - Corrects mismatched default gateways across affected PCs and Laptops.
  - Restores simulated DNS service.
  - Diverts traffic away from degraded high-latency or high-loss links.
- **Independent Post-Recovery Verification**:
  - Performs an independent telemetry scan post-recovery.
  - Verifies both IP-level reachability and DNS name resolution before declaring recovery verified.

---

## Installation & Setup on Windows

Open PowerShell in this project folder and run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

*Note: If PowerShell script execution policy restricts activation, simply install dependencies and run directly:*
```powershell
python -m pip install -r requirements.txt
python main.py
```

---

## Keyboard Shortcuts Reference

| Shortcut | Context | Action |
| :--- | :--- | :--- |
| `Ctrl+C` | Workspace Canvas | Copy selected device(s) configuration to clipboard |
| `Ctrl+V` | Workspace Canvas | Paste device(s) from clipboard with unique name & offset |
| `Ctrl+X` | Workspace Canvas | Cut selected device(s) and sever links |
| `Ctrl+D` | Workspace Canvas | Duplicate selected device(s) with unique name |
| `Ctrl+Z` | Workspace Canvas | Undo last topology action |
| `Ctrl+Y` | Workspace Canvas | Redo last undone action |
| `Ctrl+A` | Workspace Canvas | Select all devices |
| `Delete` | Workspace Canvas | Delete selected device(s) or link |
| `Escape` | Workspace Canvas | Clear selection / Cancel active tool |
| `Ctrl+N` | Anywhere | New Workspace |
| `Ctrl+O` | Anywhere | Open / Load Topology JSON |
| `Ctrl+S` | Anywhere | Save Topology JSON |
| `Ctrl++` | Anywhere | Zoom In |
| `Ctrl+-` | Anywhere | Zoom Out |
| `Ctrl+0` | Anywhere | Fit Workspace to Screen |
| `F5` | Anywhere | Monitor Network & Run Diagnosis |
| `F6` | Anywhere | Run Automated Recovery & Verification |
| `F4` | Anywhere | Reset Simulation to Baseline |
| `S` / `M` / `C` / `D` | Workspace Canvas | Switch to Select, Move, Connect, Delete Tool |

---

## Test Suite Execution

Run the complete test suite with verbose output:

```powershell
python -m unittest discover -s tests -v
```

All 62 unit tests pass (100% pass rate):
- Baseline topology structure and shortest path calculation
- Standard fault injection and scenario resets
- Device addition, duplicate prevention, and invalid type rejection
- Essential baseline device protection (prevents accidental deletion of `PC1`, `R1`, `R2`, `R3`, `Server`)
- Device removal and link disconnection
- Self-connection and duplicate connection prevention
- Device renaming, IP configuration, and link attribute editing
- Topology JSON serialization and faithful restoration
- Custom device participation in shortest path routing
- Network performance metrics calculation
- Interactive drag-and-drop repositioning for baseline and custom devices
- Accurate preservation of dragged coordinates across JSON save and load
- Multiple-route discovery for baseline and multi-path custom networks
- Route comparison metrics (cost, total latency, packet loss, availability)
- Optimal route selection under baseline, link failure, high latency, and packet loss
- Route ranking using total link cost with latency as tie-breaker
- Strict exclusion of failed links (`status != 'UP'`) from route selection
- Route selection when all candidate routes are degraded or all links are down
- Complete architectural independence between fault injection, monitoring, diagnosis, and recovery
- Diagnosis engine producing identical findings regardless of injected fault label or decoy tampering
- Detection of DOWN links strictly from link-state observations with 100% confidence
- Detection of invalid gateways from configuration audit observations
- Detection of DNS failure distinguishing IP reachability from DNS probe failure
- Measurement-based diagnosis of high latency and packet loss with calibrated confidence levels
- Simultaneous multiple-fault detection producing comprehensive multi-finding reports
- Automated recovery executing targeted repairs strictly from diagnosed root causes without scenario labels
- Verification of network health improvement via independent post-recovery observation collection
- Auto-generation of unique device names for all palette categories (Router, Switch, PC, Laptop, Server)
- Laptop end-device support in topology, addressing, and route discovery
- Cable connection tool workflow with connection types (Straight-Through, Cross-Over, Fiber, Serial)
- Dynamic fault injection targeting arbitrary user-created links and devices
- Observation-based root-cause diagnosis on dynamic topologies
- Automated recovery and verification on dynamic topologies
- GUI tool switching (`select`, `connect`, `delete`, `move`) and zoom/pan functionality
- Device and link Inspector parameter editing and real-time canvas updates
- JSON save/load preserving Laptops, custom connection types, and 2D canvas coordinates
- Copy and paste single device preserving configuration properties without copying links
- Repeated pasting generating cascading offsets and strictly unique names
- Cut device removing device and links from topology with subsequent paste support
- Quick duplicate operation (`Ctrl+D`) preserving configuration with unique names
- Multiple selection (`Ctrl+Click`) and group copy/paste preserving relative layout
- Undo (`Ctrl+Z`) and Redo (`Ctrl+Y`) for device addition, removal, and link connection
- Keyboard shortcut text field safety (native text copy/paste/undo when typing in entries)
- Full fault injection coverage for all six UI scenarios with canonical backend mapping
- Fault dropdown UI verification with width 30, height 6, and untruncated display of all six options

---

## Project Structure

```text
├── diagnostics.py          # Independent observation-based IF-THEN root-cause diagnostic engine
├── fault_injection.py      # Virtual fault state modifier supporting dynamic links/devices
├── main.py                 # Cisco Packet Tracer workspace GUI with Copy/Paste/Undo/Redo
├── metrics.py              # Performance metrics (reachability, cost, latency, loss, timings)
├── monitoring.py           # Network telemetry engine collecting structured observations
├── network_model.py        # Graph model, multi-path discovery, route selection, JSON save/load
├── recovery.py             # Automated repair routines driven by diagnosed root causes
├── requirements.txt        # Project dependencies (networkx, matplotlib)
├── README.md               # User manual, feature documentation, and test guide
├── PROJECT_REPORT.md       # Comprehensive academic project report
├── TEST_RESULTS.txt        # Latest test execution output (60 passing tests)
└── tests/
    └── test_project.py     # Comprehensive automated test suite (60 tests)
```

---

## Technical Scope & Limitations
- This system implements a simulated graph-based network model utilizing NetworkX and Matplotlib.
- It calculates routing, simulates link health, and executes diagnostic logic without requiring physical hardware, root privileges, or real packet-level emulation (e.g. Mininet).
- The framework adheres strictly to deterministic algorithmic routing and explainable IF-THEN rules with zero black-box machine learning.
