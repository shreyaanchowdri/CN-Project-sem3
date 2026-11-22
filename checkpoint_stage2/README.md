# Intelligent Network Fault Diagnosis and Automated Recovery Framework
## Cisco Packet Tracer-Style Network Simulation Workspace

An enterprise-ready, graph-based virtual network modeling, fault injection, observation-based root-cause diagnosis, and automated recovery platform built with Python, NetworkX, Tkinter, and Matplotlib.

Features a professional **Cisco Packet Tracer-inspired Network Simulation Workspace** layout with device palette categories (Routers, Switches, PCs, Laptops, Servers), interactive cable connection tools, device/link configuration inspectors, multi-path discovery, live route comparison matrix, explainable decision engine, and complete **keyboard-based Copy, Paste, Cut, Duplicate, Undo & Redo** operations.



---

## Project Structure

```text
├── diagnostics.py          # Independent observation-based IF-THEN root-cause diagnostic engine (Stage 2)
├── fault_injection.py      # Virtual fault state modifier supporting dynamic links/devices
├── main.py                 # Cisco Packet Tracer workspace GUI with Copy/Paste/Undo/Redo
├── metrics.py              # Performance metrics (reachability, cost, latency, loss, timings)
├── monitoring.py           # Network telemetry engine collecting structured observations (Stage 1)
├── network_model.py        # Graph model, forwarding state, multi-path discovery, route selection
├── recovery.py             # Fault-specific recovery & post-recovery verification engine (Stages 3 & 4)
├── requirements.txt        # Project dependencies (networkx, matplotlib)
├── README.md               # User manual, feature documentation, and test guide
├── PROJECT_REPORT.md       # Comprehensive academic project report
├── TEST_RESULTS.txt        # Latest test execution output (88 passing tests)
└── tests/
    └── test_project.py     # Comprehensive automated test suite (88 tests)
```

---

## Technical Scope & Limitations
- This system implements a simulated graph-based network model utilizing NetworkX and Matplotlib.
- It calculates routing, simulates link health, and executes diagnostic logic without requiring physical hardware, root privileges, or real packet-level emulation (e.g. Mininet).
- The framework adheres strictly to deterministic algorithmic routing and explainable IF-THEN rules with zero black-box machine learning.
