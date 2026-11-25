"""generate_clean_deck.py
Generates an elegant, highly readable 15-slide presentation strictly following
the user's structure for 'Design and Development of an Intelligent Network Fault Injection,
Root-Cause Diagnosis and Automated Recovery Framework'.

Features:
- Clean, uncluttered layouts (no excessive boxes/tables).
- High-contrast typography: Titles 26-30pt, Body 14-18pt.
- Dedicated, styled screenshot placeholder containers on slides where images are recommended.
- Embeds actual Figure 4.1 benchmark image on Slide 13.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Color Palette
    C_NAVY = RGBColor(11, 37, 69)        # #0B2545 - Deep Navy
    C_COBALT = RGBColor(30, 64, 175)     # #1E40AF - Accent Cobalt
    C_BG = RGBColor(248, 250, 252)       # #F8FAFC - Soft Slate Background
    C_CARD = RGBColor(255, 255, 255)     # White Card
    C_BORDER = RGBColor(203, 213, 225)   # #CBD5E1 - Card Border
    C_TEXT = RGBColor(15, 23, 42)        # #0F172A - Main Text
    C_MUTED = RGBColor(71, 85, 105)      # #475569 - Subtext
    C_GREEN = RGBColor(16, 185, 129)     # #10B981 - Green
    C_AMBER = RGBColor(217, 119, 6)      # #D97706 - Amber
    C_BLUE = RGBColor(2, 132, 199)       # #0284C7 - Blue
    C_SHOT_BG = RGBColor(241, 245, 249)  # Screenshot frame background

    blank_layout = prs.slide_layouts[6]

    def set_bg(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_top_bar(slide, slide_num, title, section):
        # Top banner line
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = C_COBALT
        bar.line.fill.background()

        # Section pill
        tx_sec = slide.shapes.add_textbox(Inches(0.8), Inches(0.28), Inches(10.0), Inches(0.28))
        tf_sec = tx_sec.text_frame
        p_sec = tf_sec.paragraphs[0]
        p_sec.text = f"{section.upper()}  |  SLIDE {slide_num} OF 15"
        p_sec.font.size = Pt(9.5)
        p_sec.font.bold = True
        p_sec.font.color.rgb = C_COBALT

        # Main Title
        tx_t = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.733), Inches(0.65))
        tf_t = tx_t.text_frame
        p_t = tf_t.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(22)
        p_t.font.bold = True
        p_t.font.color.rgb = C_NAVY

        # Subtle divider
        div = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.22), Inches(11.733), Inches(0.015))
        div.fill.solid()
        div.fill.fore_color.rgb = C_BORDER
        div.line.fill.background()

    def add_card(slide, left, top, width, height, title=None, border_color=C_BORDER, bg_color=C_CARD):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)

        if title:
            tx = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.18), width - Inches(0.5), Inches(0.4))
            tf = tx.text_frame
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = C_NAVY
        return card

    def add_screenshot_placeholder(slide, left, top, width, height, label, instruction):
        """Creates a professional frame indicating where to insert an application screenshot."""
        frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        frame.fill.solid()
        frame.fill.fore_color.rgb = C_SHOT_BG
        frame.line.color.rgb = C_COBALT
        frame.line.width = Pt(1.5)

        # Header tag
        tag = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Inches(0.42))
        tag.fill.solid()
        tag.fill.fore_color.rgb = C_NAVY
        tag.line.fill.background()

        tx_tag = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.06), width - Inches(0.3), Inches(0.3))
        p_tag = tx_tag.text_frame.paragraphs[0]
        p_tag.text = f"📸 {label.upper()}"
        p_tag.font.size = Pt(9.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = RGBColor(255, 255, 255)

        # Instruction text in center
        tx_body = slide.shapes.add_textbox(left + Inches(0.3), top + Inches(0.8), width - Inches(0.6), height - Inches(1.0))
        tf = tx_body.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = "[ RECOMMENDED SCREENSHOT PLACEMENT ]"
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = C_COBALT
        p1.alignment = PP_ALIGN.CENTER
        p1.space_after = Pt(8)

        p2 = tf.add_paragraph()
        p2.text = instruction
        p2.font.size = Pt(10)
        p2.font.color.rgb = C_MUTED
        p2.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1, C_NAVY)

    # Accent bottom bar
    dec1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.8), Inches(13.333), Inches(0.7))
    dec1.fill.solid()
    dec1.fill.fore_color.rgb = C_COBALT
    dec1.line.fill.background()

    # Title & Metadata in clean central box
    tx1 = s1.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(11.333), Inches(5.2))
    tf1 = tx1.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "AMRITA VISHWA VIDYAPEETHAM  |  DEPARTMENT OF ARTIFICIAL INTELLIGENCE & DATA SCIENCE"
    p0.font.size = Pt(11)
    p0.font.bold = True
    p0.font.color.rgb = RGBColor(147, 197, 253)
    p0.space_after = Pt(16)

    p_title = tf1.add_paragraph()
    p_title.text = "Design and Development of an Intelligent Network Fault Injection,\nRoot-Cause Diagnosis and Automated Recovery Framework"
    p_title.font.size = Pt(26)
    p_title.font.bold = True
    p_title.font.color.rgb = RGBColor(255, 255, 255)
    p_title.space_after = Pt(14)

    p_sub = tf1.add_paragraph()
    p_sub.text = "End-Semester Project Presentation  •  Course Code: 23AID206 Computer Networks"
    p_sub.font.size = Pt(14)
    p_sub.font.color.rgb = RGBColor(226, 232, 240)
    p_sub.space_after = Pt(28)

    p_meta1 = tf1.add_paragraph()
    p_meta1.text = "Team Members: [Student Name(s) & USN / Register Numbers]"
    p_meta1.font.size = Pt(12)
    p_meta1.font.bold = True
    p_meta1.font.color.rgb = RGBColor(255, 255, 255)
    p_meta1.space_after = Pt(4)

    p_meta2 = tf1.add_paragraph()
    p_meta2.text = "Project Guide: [Faculty Guide Name & Designation]  |  Academic Year: 2024–2025"
    p_meta2.font.size = Pt(11)
    p_meta2.font.color.rgb = RGBColor(148, 163, 184)

    # =========================================================================
    # SLIDE 2: Introduction
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2, C_BG)
    add_top_bar(s2, 2, "Introduction: Autonomic Network Fault Management", "Overview")

    # Left: 5 Concise Bullet Points
    add_card(s2, Inches(0.8), Inches(1.5), Inches(6.8), Inches(5.4), "Background & The Core Idea")
    tx2 = s2.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(6.3), Inches(4.6))
    tf2 = tx2.text_frame
    tf2.word_wrap = True
    intro_pts = [
        "Computer networks are mission-critical for modern enterprise communication, data centers, and distributed cloud computing.",
        "Network anomalies (cable cuts, misconfigured gateways, daemon crashes) degrade performance and cause severe service outages.",
        "Traditional troubleshooting relies on manual monitoring, reactive CLI commands, and slow trial-and-error inspection.",
        "Pinpointing true root causes among overlapping symptoms is time-consuming and inflates Mean Time to Recover (MTTR).",
        "Proposed Framework: An intelligent simulation environment that injects controlled faults, observes behavior via pure telemetry, diagnoses root causes, and verifies automated recovery."
    ]
    for i, pt in enumerate(intro_pts):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        p.text = f"•  {pt}"
        p.font.size = Pt(12)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(12)

    # Right: Workflow Diagram Box
    add_card(s2, Inches(7.8), Inches(1.5), Inches(4.733), Inches(5.4), "End-to-End Autonomic Workflow", border_color=C_COBALT)
    tx_wf = s2.shapes.add_textbox(Inches(8.05), Inches(2.1), Inches(4.2), Inches(4.6))
    tf_wf = tx_wf.text_frame
    tf_wf.word_wrap = True

    steps = [
        ("1. Network Topology", "Virtual network model (PCs, routers, servers)"),
        ("2. Fault Injection", "Atomic injection of link cuts, bad gateways, DNS crashes"),
        ("3. Telemetry Monitoring", "Passive metrics & active synthetic probe packet bursts"),
        ("4. Root-Cause Diagnosis", "Rule-based expert inference with calibrated confidence"),
        ("5. Recovery & Failover", "Multi-objective optimal route activation without magic repairs"),
        ("6. Post-Recovery Verification", "Independent 7-point audit & packet delivery validation")
    ]
    for i, (hd, desc) in enumerate(steps):
        p = tf_wf.paragraphs[0] if i == 0 else tf_wf.add_paragraph()
        p.text = f"▼  {hd}"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_COBALT
        p_sub = tf_wf.add_paragraph()
        p_sub.text = f"    {desc}"
        p_sub.font.size = Pt(9.5)
        p_sub.font.color.rgb = C_MUTED
        p_sub.space_after = Pt(6)

    # =========================================================================
    # SLIDE 3: Problem Statement
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3, C_BG)
    add_top_bar(s3, 3, "Problem Statement & Operational Challenges", "Problem Formulation")

    # Top: 5 Core Challenges
    add_card(s3, Inches(0.8), Inches(1.5), Inches(11.733), Inches(3.6), "Key Challenges in Modern Network Triage")
    tx3 = s3.shapes.add_textbox(Inches(1.05), Inches(2.05), Inches(11.2), Inches(2.9))
    tf3 = tx3.text_frame
    tf3.word_wrap = True
    challenges = [
        ("Service Availability Impact:", "Hardware failures and configuration drifts immediately isolate endpoints and degrade throughput."),
        ("Multi-Fault Concurrency:", "Multiple heterogeneous faults often occur simultaneously (e.g. physical cable cut + DNS daemon crash), confusing naive single-fault detectors."),
        ("Symptom vs. Root Cause:", "Monitoring observations show symptoms (packet drops, timeouts), but identifying the exact underlying origin requires formal evidentiary correlation."),
        ("Manual Diagnosis Latency:", "Manual operator commands (ping, tracert) significantly inflate MTTD and MTTR during critical enterprise outages."),
        ("Side-Effect Risks:", "Blind or uncoordinated recovery actions can introduce routing loops, state corruption, or secondary outages.")
    ]
    for i, (hd, bd) in enumerate(challenges):
        p = tf3.paragraphs[0] if i == 0 else tf3.add_paragraph()
        p.text = f"•  {hd} {bd}"
        p.font.size = Pt(11.5)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(6)

    # Bottom: Formal Problem Statement Callout
    add_card(s3, Inches(0.8), Inches(5.3), Inches(11.733), Inches(1.6), "Formal Problem Statement", border_color=C_COBALT)
    tx_ps = s3.shapes.add_textbox(Inches(1.05), Inches(5.75), Inches(11.2), Inches(1.0))
    tf_ps = tx_ps.text_frame
    tf_ps.word_wrap = True
    p_ps = tf_ps.paragraphs[0]
    p_ps.text = '"Develop an intelligent simulation framework that can inject network faults, monitor network behaviour, identify root causes, evaluate recovery strategies, and verify network recovery."'
    p_ps.font.size = Pt(13)
    p_ps.font.bold = True
    p_ps.font.color.rgb = C_NAVY

    # =========================================================================
    # SLIDE 4: Objectives
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4, C_BG)
    add_top_bar(s4, 4, "Project Objectives & Scope", "Objectives")

    # 2-column clean card grid for the 9 objectives
    obj_left = [
        ("1. Configurable Topology", "Design and simulate a dynamic, graph-based network topology using NetworkX."),
        ("2. Diverse Fault Injection", "Inject 5 distinct physical, configuration, and performance fault scenarios."),
        ("3. Telemetry Monitoring", "Continuously observe link states, hop latency, packet loss, and partition status."),
        ("4. Rule-Based Diagnosis", "Accurately deduce root causes with calibrated confidence ratings (0.90 to 1.00)."),
        ("5. Concurrent Fault Detection", "Discover multiple simultaneous anomalies without early short-circuiting.")
    ]
    obj_right = [
        ("6. Strategy Generation", "Formulate and rank Pareto-optimal multi-objective recovery alternatives."),
        ("7. Coordinated Execution", "Execute approved corrective actions with transactional snapshot rollback safety."),
        ("8. Independent Verification", "Validate network restoration via active probe packets and a 7-point audit gate."),
        ("9. Performance Evaluation", "Evaluate system reliability using MTTD, MTTR, loss bounds, and test suites.")
    ]

    add_card(s4, Inches(0.8), Inches(1.5), Inches(5.7), Inches(5.4), "Design, Diagnosis & Fault Objectives")
    tx_ol = s4.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.2), Inches(4.6))
    tf_ol = tx_ol.text_frame
    tf_ol.word_wrap = True
    for i, (hd, bd) in enumerate(obj_left):
        p = tf_ol.paragraphs[0] if i == 0 else tf_ol.add_paragraph()
        p.text = f"✔  {hd}\n    {bd}"
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(8)

    add_card(s4, Inches(6.8), Inches(1.5), Inches(5.733), Inches(5.4), "Recovery, Verification & Metrics Objectives")
    tx_or = s4.shapes.add_textbox(Inches(7.05), Inches(2.1), Inches(5.2), Inches(4.6))
    tf_or = tx_or.text_frame
    tf_or.word_wrap = True
    for i, (hd, bd) in enumerate(obj_right):
        p = tf_or.paragraphs[0] if i == 0 else tf_or.add_paragraph()
        p.text = f"✔  {hd}\n    {bd}"
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(10)

    # =========================================================================
    # SLIDE 5: Existing System vs. Proposed System
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5, C_BG)
    add_top_bar(s5, 5, "Comparative Analysis: Existing vs. Proposed Framework", "System Comparison")

    add_card(s5, Inches(0.8), Inches(1.5), Inches(11.733), Inches(4.2), "Key Architectural Differences")

    rows, cols = 7, 3
    tbl_shape = s5.shapes.add_table(rows, cols, Inches(1.0), Inches(2.05), Inches(11.333), Inches(3.4))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(3.2)
    tbl.columns[1].width = Inches(4.0)
    tbl.columns[2].width = Inches(4.133)

    t_heads = ["Evaluation Aspect", "Existing Approach", "Proposed Framework"]
    for c, h in enumerate(t_heads):
        cell = tbl.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

    comp_data = [
        ["Network Monitoring", "Manual ping / tracert commands after complaints", "Automated passive telemetry & active synthetic probing"],
        ["Fault Identification", "Manual interpretation of disconnected CLI logs", "Deterministic rule-based diagnosis with confidence scoring"],
        ["Fault Simulation", "Limited, static, or ad-hoc manual scripts", "Controlled atomic multi-fault injection with rollback safety"],
        ["Recovery Decisions", "Manual trial-and-error network configuration", "Multi-objective strategy evaluation (Cost, Latency, Loss)"],
        ["Post-Repair Verification", "Informal ping check or assumed operational status", "Rigorous 7-point independent audit & probe packet bursts"],
        ["Performance Metrics", "Difficult to measure or manually estimated", "Automated telemetry time-series, MTTR tracking, and charts"]
    ]
    for r, row in enumerate(comp_data, start=1):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(10)
            p.font.color.rgb = C_TEXT
            if r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249)

    # Key Advantage Callout
    add_card(s5, Inches(0.8), Inches(5.9), Inches(11.733), Inches(1.1), None, border_color=C_GREEN)
    tx_adv = s5.shapes.add_textbox(Inches(1.05), Inches(6.05), Inches(11.2), Inches(0.8))
    tf_adv = tx_adv.text_frame
    p_adv = tf_adv.paragraphs[0]
    p_adv.text = "Key Advantage: The proposed system uniquely integrates fault injection, observation, root-cause diagnosis, recovery planning, and independent verification into one unified, explainable autonomic environment."
    p_adv.font.size = Pt(11)
    p_adv.font.bold = True
    p_adv.font.color.rgb = C_NAVY

    # =========================================================================
    # SLIDE 6: System Architecture (KEY SLIDE)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6, C_BG)
    add_top_bar(s6, 6, "System Architecture: Decoupled Autonomic Modules", "Core Architecture")

    # Module Pipeline Diagram (9 connected cards)
    modules = [
        ("1. Topology Module", "NetworkX virtual graph & nodes"),
        ("2. Fault Injection", "Atomic fault scenarios & registry"),
        ("3. Monitoring Module", "Telemetry & multi-link metrics"),
        ("4. Diagnosis Engine", "Rule-based root-cause inferencing"),
        ("5. Recovery Planner", "Multi-objective candidate routing"),
        ("6. Decision Engine", "Autonomous vs manual approval"),
        ("7. Recovery Execution", "Failover & transactional rollback"),
        ("8. Verification Gate", "7-point independent audit"),
        ("9. Analytics & Audit", "MTTR tracking & historical log")
    ]

    for idx, (m_title, m_sub) in enumerate(modules):
        row = idx // 3
        col = idx % 3
        x = Inches(0.8 + col * 4.0)
        y = Inches(1.5 + row * 1.55)
        add_card(s6, x, y, Inches(3.75), Inches(1.35), None, border_color=C_COBALT)
        tx_m = s6.shapes.add_textbox(x + Inches(0.15), y + Inches(0.15), Inches(3.45), Inches(1.05))
        tf_m = tx_m.text_frame
        p1 = tf_m.paragraphs[0]
        p1.text = m_title
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = C_NAVY
        p2 = tf_m.add_paragraph()
        p2.text = m_sub
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_MUTED

    # Bottom Architectural Note
    add_card(s6, Inches(0.8), Inches(6.3), Inches(11.733), Inches(0.9), None, border_color=C_BLUE)
    tx_flow = s6.shapes.add_textbox(Inches(1.0), Inches(6.4), Inches(11.3), Inches(0.7))
    tf_flow = tx_flow.text_frame
    p_f = tf_flow.paragraphs[0]
    p_f.text = "Strict Telemetry Decoupling: Observations feed into Diagnosis → Findings feed into Recovery Planning → Outcomes are verified through an independent audit. The observer NEVER reads injected fault labels."
    p_f.font.size = Pt(10.5)
    p_f.font.bold = True
    p_f.font.color.rgb = C_NAVY

    # =========================================================================
    # SLIDE 7: Network Topology and Fault Injection
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7, C_BG)
    add_top_bar(s7, 7, "Network Topology & Controlled Fault Injection", "Network Modeling")

    # Left: Explanation of Topology and 5 Faults
    add_card(s7, Inches(0.8), Inches(1.5), Inches(6.0), Inches(5.5), "Configurable Network & 5 Fault Scenarios")
    tx7 = s7.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.5), Inches(4.7))
    tf7 = tx7.text_frame
    tf7.word_wrap = True
    top_bullets = [
        ("Graph Representation:", "Modeled via NetworkX with Layer-2 switching and Layer-3 IP addressing, subnetting, and gateway parameters."),
        ("Physical Device Entities:", "Workstations (PC1, PC2), Gateway Router (R1), Transit Core Routers (R2, R3), and Server (Server)."),
        ("Dual Core Paths:", "Primary path via R2 (8ms, Cost 3) and secondary backup path via R3 (10ms, Cost 5)."),
        ("Five Supported Fault Scenarios:", ""),
        ("  1. Link Failure:", "Severing physical links (status = DOWN)."),
        ("  2. Wrong Default Gateway:", "Misconfiguring host gateway to invalid or off-subnet router."),
        ("  3. DNS Failure:", "Crashing simulated port-53 DNS resolver daemon."),
        ("  4. High Latency:", "Injecting severe propagation delay (> 50 ms)."),
        ("  5. Packet Loss:", "Stochastic buffer drop rates (10% to 90%).")
    ]
    for i, (hd, bd) in enumerate(top_bullets):
        p = tf7.paragraphs[0] if i == 0 else tf7.add_paragraph()
        p.text = f"{hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(4)

    # Right: Screenshot Placeholder
    add_screenshot_placeholder(
        s7, Inches(7.1), Inches(1.5), Inches(5.433), Inches(5.5),
        "Main Network Topology GUI",
        "Place screenshot of the Cisco Packet Tracer canvas showing the 6 devices (PC1, R1, R2, R3, Server, PC2) with link labels, halo selection, and IP annotations."
    )

    # =========================================================================
    # SLIDE 8: Network Monitoring Module
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8, C_BG)
    add_top_bar(s8, 8, "Network Monitoring & Observability Engine", "Monitoring")

    # Left: Monitoring Capabilities
    add_card(s8, Inches(0.8), Inches(1.5), Inches(6.0), Inches(5.5), "Telemetry Collection & Metric Analysis")
    tx8 = s8.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.5), Inches(4.7))
    tf8 = tx8.text_frame
    tf8.word_wrap = True
    mon_pts = [
        ("Interface State Monitoring:", "Passively tracks administrative and physical link states (UP / DOWN) across all connections."),
        ("End-to-End Reachability:", "Evaluates source-to-destination path continuity and active forwarding paths."),
        ("Default Gateway Validation:", "Audits host gateway against connected router interface IPs and local subnet masks."),
        ("DNS Service Probes:", "Verifies resolution responsiveness against the simulated local resolver daemon."),
        ("Latency & Loss Measurement:", "Measures cumulative RTT and probabilistic packet loss: P = 1 - ∏(1 - p_i)."),
        ("Network Partition Analysis:", "Uses graph connectivity algorithms (BFS) to isolate partitioned network segments."),
        ("Crucial Distinction:", "Monitoring only observes WHAT is happening in the network; it does not decide the root cause.")
    ]
    for i, (hd, bd) in enumerate(mon_pts):
        p = tf8.paragraphs[0] if i == 0 else tf8.add_paragraph()
        p.text = f"•  {hd} {bd}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(7)

    # Right: Screenshot Placeholder
    add_screenshot_placeholder(
        s8, Inches(7.1), Inches(1.5), Inches(5.433), Inches(5.5),
        "Monitoring Report Dashboard",
        "Place screenshot of the 'Diagnosis & Telemetry' bottom tab showing the live observations table, link metrics, and gateway audit logs."
    )

    # =========================================================================
    # SLIDE 9: Root-Cause Diagnosis Engine (KEY SLIDE)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_bg(s9, C_BG)
    add_top_bar(s9, 9, "Rule-Based Root-Cause Diagnosis Engine", "Diagnosis Engine")

    # Left: Explanation & Example Mapping Table
    add_card(s9, Inches(0.8), Inches(1.5), Inches(6.2), Inches(5.5), "Deterministic Diagnostic Production Rules")
    tx9 = s9.shapes.add_textbox(Inches(1.05), Inches(2.05), Inches(5.7), Inches(1.6))
    tf9 = tx9.text_frame
    tf9.word_wrap = True
    diag_pts = [
        "Analyzes monitoring observations using deterministic forward-chaining rules.",
        "Distinguishes primary root causes from downstream secondary symptoms.",
        "Produces calibrated confidence scores (0.90 to 0.99) with explicit evidence chains.",
        "Evaluates multiple simultaneous faults concurrently without early exit."
    ]
    for i, pt in enumerate(diag_pts):
        p = tf9.paragraphs[0] if i == 0 else tf9.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(10)
        p.space_after = Pt(3)

    # Mini Table on Left
    tbl_d_shape = s9.shapes.add_table(6, 3, Inches(1.0), Inches(3.85), Inches(5.8), Inches(2.9))
    td = tbl_d_shape.table
    td.columns[0].width = Inches(2.4)
    td.columns[1].width = Inches(2.1)
    td.columns[2].width = Inches(1.3)

    td_h = ["Observation", "Diagnosed Root Cause", "Confidence"]
    for c, h in enumerate(td_h):
        cell = td.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

    td_rows = [
        ["Link status == DOWN", "Link Failure", "99% (0.99)"],
        ["Gateway invalid / off-subnet", "Wrong Default Gateway", "98% (0.98)"],
        ["IP operational, DNS fails", "DNS Service Failure", "95% (0.95)"],
        ["Cumulative latency > 50ms", "High Latency", "92% (0.92)"],
        ["Path loss > 10%", "Packet Loss", "92% (0.92)"]
    ]
    for r, row in enumerate(td_rows, start=1):
        for c, val in enumerate(row):
            cell = td.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(8.5)
            p.font.color.rgb = C_TEXT
            if r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249)

    # Right: Screenshot Placeholder
    add_screenshot_placeholder(
        s9, Inches(7.3), Inches(1.5), Inches(5.233), Inches(5.5),
        "Root-Cause Diagnosis Report",
        "Place screenshot of the Diagnostic Findings panel showing the diagnosed root causes, confidence levels (98%, 95%), and recommended actions."
    )

    # =========================================================================
    # SLIDE 10: Intelligent Recovery Planning and Decision Engine (KEY SLIDE)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_bg(s10, C_BG)
    add_top_bar(s10, 10, "Intelligent Recovery Planning & Decision Engine", "Recovery Planning")

    # Left: Recovery Planning Details
    add_card(s10, Inches(0.8), Inches(1.5), Inches(6.0), Inches(5.5), "Multi-Objective Planning & Autonomic Decisions")
    tx10 = s10.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.5), Inches(4.7))
    tf10 = tx10.text_frame
    tf10.word_wrap = True
    rec_pts = [
        ("Multi-Objective Route Selection:", "Discovers candidate paths and ranks them using Pareto objective scoring: Score = w1·Cost + w2·Latency + w3·Loss + w4·Hops."),
        ("Action Dependencies:", "Prioritizes route failover before host gateway re-assignment, and gateway validity before DNS service restart."),
        ("Precondition & Safety Verification:", "Evaluates graph connectivity before mutating state; unsafe actions are rejected."),
        ("Autonomous Decision Modes:", "Supports Fully Autonomous (auto-execute), Semi-Autonomous (interactive approval), and Manual Approval."),
        ("Decision Dispositions:", "Auto Execute, Requires Approval, Monitor Only, or Blocked."),
        ("Key Technical Principle:", "The system does NOT blindly execute every action. It assesses risk, evaluates alternatives, and acts only when necessary.")
    ]
    for i, (hd, bd) in enumerate(rec_pts):
        p = tf10.paragraphs[0] if i == 0 else tf10.add_paragraph()
        p.text = f"•  {hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(7)

    # Right: Screenshot Placeholder
    add_screenshot_placeholder(
        s10, Inches(7.1), Inches(1.5), Inches(5.433), Inches(5.5),
        "Recovery Strategy & Planner",
        "Place screenshot of the 'Recovery Planner' tab showing candidate route comparisons (latency, cost, hops) and the action sequence table."
    )

    # =========================================================================
    # SLIDE 11: Automated Recovery and Post-Recovery Verification (KEY SLIDE)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_bg(s11, C_BG)
    add_top_bar(s11, 11, "Automated Recovery & 7-Point Verification Audit", "Recovery & Verification")

    # Left: Process & 7-Point Audit
    add_card(s11, Inches(0.8), Inches(1.5), Inches(6.0), Inches(5.5), "Recovery Lifecycle & 7-Point Audit Gate")
    tx11 = s11.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.5), Inches(4.7))
    tf11 = tx11.text_frame
    tf11.word_wrap = True
    audit_pts = [
        ("Recovery Execution Steps:", "1. Parse findings → 2. Select strategy → 3. Validate preconditions → 4. Execute atomic actions → 5. Record state snapshot."),
        ("7-Point Independent Verification Checks:", ""),
        ("  1. Endpoint IP Connectivity", "(Path exists in graph: PASS)"),
        ("  2. DNS Resolution Service", "(dns_available == True: PASS)"),
        ("  3. Default Gateway Validity", "(Reachable local router IP: PASS)"),
        ("  4. Active Forwarding Route", "(Continuous, loop-free path: PASS)"),
        ("  5. Failed Link Isolation", "(All DOWN links strictly avoided: PASS)"),
        ("  6. Latency Compliance", "(End-to-end latency <= 100ms: PASS)"),
        ("  7. Packet Loss Compliance", "(Path loss within operational limits: PASS)"),
        ("Honest Outcomes:", "Restores service, maintains surviving degraded path, or reports RECOVERY UNAVAILABLE if completely partitioned.")
    ]
    for i, (hd, bd) in enumerate(audit_pts):
        p = tf11.paragraphs[0] if i == 0 else tf11.add_paragraph()
        p.text = f"{hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(4)

    # Right: Screenshot Placeholder
    add_screenshot_placeholder(
        s11, Inches(7.1), Inches(1.5), Inches(5.433), Inches(5.5),
        "Recovery & Verification Reports",
        "Place screenshot of the 'Recovery & Verification' tab showing probe packet delivery logs (5/5 delivered) and the 7-Point Verification checklist (all PASS)."
    )

    # =========================================================================
    # SLIDE 12: Graphical User Interface and Network Terminal
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_bg(s12, C_BG)
    add_top_bar(s12, 12, "Interactive GUI & Simulated Windows CMD Terminal", "User Interfaces")

    # Left: Explanation of Dual Interface
    add_card(s12, Inches(0.8), Inches(1.5), Inches(6.0), Inches(5.5), "Dual Operational Interfaces")
    tx12 = s12.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.5), Inches(4.7))
    tf12 = tx12.text_frame
    tf12.word_wrap = True
    ui_bullets = [
        ("Cisco Packet Tracer Visual Workspace:", "Interactive drag-and-drop canvas, cable connection tool, dynamic inspector panel (IP, mask, gateway, latency, loss), and 8-tab operator notebook."),
        ("Real-Time KPI Status Bar:", "Visual badges displaying live Device Count, Link Count, Faults, Critical Outages, Service Availability, and Health."),
        ("Simulated Windows CMD Terminal:", "Authentic Windows Command Prompt operating directly on the live virtual topology."),
        ("Supported Terminal Commands:", ""),
        ("  • ping <target> [-n count]:", "ICMP echo probes with RTT jitter"),
        ("  • tracert <target>:", "Hop-by-hop layer-3 router traversal"),
        ("  • nslookup <domain>:", "Simulated DNS address resolution"),
        ("  • ipconfig [/all]:", "Host IP, subnet, gateway, DNS inspection"),
        ("  • show devices / links / routes:", "Topology inspection"),
        ("  • diagnose / recover:", "Direct CLI triggers for self-healing")
    ]
    for i, (hd, bd) in enumerate(ui_bullets):
        p = tf12.paragraphs[0] if i == 0 else tf12.add_paragraph()
        p.text = f"{hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(4)

    # Right: Screenshot Placeholder
    add_screenshot_placeholder(
        s12, Inches(7.1), Inches(1.5), Inches(5.433), Inches(5.5),
        "GUI & Network Terminal",
        "Place screenshot showing the Cisco Packet Tracer canvas side-by-side with the open black Windows CMD Network Terminal executing ping and tracert."
    )

    # =========================================================================
    # SLIDE 13: Performance Evaluation and Analytics
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_bg(s13, C_BG)
    add_top_bar(s13, 13, "Performance Evaluation & Telemetry Analytics", "Performance & Analytics")

    # Left: Quantitative Metrics
    add_card(s13, Inches(0.8), Inches(1.5), Inches(5.8), Inches(5.5), "Framework Performance Metrics")
    tx13 = s13.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.3), Inches(4.7))
    tf13 = tx13.text_frame
    tf13.word_wrap = True
    perf_pts = [
        ("Diagnostic Reasoning Time:", "< 0.001 seconds (sub-millisecond evaluation)."),
        ("Mean Time to Recover (MTTR):", "< 0.002 seconds execution latency."),
        ("Root-Cause Detection Accuracy:", "100% across all individual & multi-fault scenarios."),
        ("False-Positive Rate:", "0.0% during nominal baseline monitoring."),
        ("Six Telemetry Analytics Graphs:", "Full Matplotlib visualization panel:"),
        ("  1. Latency Trends:", "Hop-by-hop & end-to-end latency"),
        ("  2. Packet Loss Analysis:", "Link vs path drop percentages"),
        ("  3. Service Availability:", "Binary uptime step timeline"),
        ("  4. Fault Distribution:", "Categorization by severity & type"),
        ("  5. MTTR & Recovery:", "Success rate & recovery times"),
        ("  6. Route Comparison:", "Candidate latency & cost scoring")
    ]
    for i, (hd, bd) in enumerate(perf_pts):
        p = tf13.paragraphs[0] if i == 0 else tf13.add_paragraph()
        p.text = f"• {hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(4)

    # Right: Embed Actual Figure 4.1 Benchmark Graph
    fig_path = "figure_4_1_delivery_rate.png"
    add_card(s13, Inches(6.9), Inches(1.5), Inches(5.633), Inches(5.5), "Figure 4.1: Probe Delivery Rate Across Scenarios", border_color=C_COBALT)
    if os.path.exists(fig_path):
        s13.shapes.add_picture(fig_path, Inches(7.05), Inches(2.1), width=Inches(5.333))
    else:
        add_screenshot_placeholder(
            s13, Inches(6.9), Inches(1.5), Inches(5.633), Inches(5.5),
            "Analytics Graphs / Figure 4.1",
            "Place screenshot of Figure 4.1 or the 6-graph Matplotlib analytics panel."
        )

    # =========================================================================
    # SLIDE 14: Testing and Results
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    set_bg(s14, C_BG)
    add_top_bar(s14, 14, "Testing Methodology & Experimental Results", "Testing & Results")

    # Left: Test Scenarios Evaluated
    add_card(s14, Inches(0.8), Inches(1.5), Inches(6.0), Inches(5.5), "Comprehensive Test Scenarios Evaluated")
    tx14 = s14.shapes.add_textbox(Inches(1.05), Inches(2.1), Inches(5.5), Inches(4.7))
    tf14 = tx14.text_frame
    tf14.word_wrap = True
    test_pts = [
        ("Individual Fault Scenarios:", "Verified Link Failure, Wrong Default Gateway, DNS Failure, High Latency (>50ms), and Packet Loss (>10%)."),
        ("Simultaneous Multi-Fault Scenarios:", "Tested Link Failure + DNS Failure; Link Failure + Wrong Gateway; and 3-way concurrent fault combinations."),
        ("Network Partition Resilience:", "Verified honest partition reporting (RECOVERY UNAVAILABLE) when all paths are severed."),
        ("Multi-Tier Testing Suite:", "Unit testing, integration testing, regression testing, and post-recovery verification."),
        ("Confirmed Test Result:", "207 / 207 Automated Unit Tests Passed (100% Pass Rate, 0 Failures, 0 Errors in 16.6 seconds)."),
        ("Report Baseline Note:", "Includes all 184 core baseline tests plus 23 dynamic endpoint and IPv4 gateway interoperability tests.")
    ]
    for i, (hd, bd) in enumerate(test_pts):
        p = tf14.paragraphs[0] if i == 0 else tf14.add_paragraph()
        p.text = f"•  {hd} {bd}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = C_TEXT
        p.space_after = Pt(7)

    # Right: Screenshot Placeholder for Test Execution
    add_screenshot_placeholder(
        s14, Inches(7.1), Inches(1.5), Inches(5.433), Inches(5.5),
        "Test Execution Output",
        "Place screenshot of the PowerShell / CMD terminal running 'python -m unittest discover -s tests' showing all tests running with the final line: 'Ran 207 tests in 16.6s ... OK'."
    )

    # =========================================================================
    # SLIDE 15: Conclusion and Future Scope
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    set_bg(s15, C_NAVY)

    # Accent bottom bar
    dec15 = s15.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.8), Inches(13.333), Inches(0.7))
    dec15.fill.solid()
    dec15.fill.fore_color.rgb = C_COBALT
    dec15.line.fill.background()

    # Left: Conclusion
    tx15_c = s15.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(5.5), Inches(5.2))
    tf15_c = tx15_c.text_frame
    tf15_c.word_wrap = True

    p = tf15_c.paragraphs[0]
    p.text = "Project Summary & Conclusion"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(14)

    concl_items = [
        "Developed an integrated, self-healing network simulation framework combining Packet Tracer interactivity with algorithmic rigor.",
        "Implemented controlled atomic fault injection and pure telemetry observation with zero ground-truth leakage.",
        "Built a deterministic, explainable rule-based root-cause diagnosis engine with calibrated confidence scoring (0.90 to 1.00).",
        "Engineered Pareto multi-objective recovery planning with authentic physical fault bypass (severed links stay strictly DOWN).",
        "Integrated an independent 7-point verification audit and dual GUI/terminal interfaces, achieving 100% test pass rate."
    ]
    for itm in concl_items:
        p = tf15_c.add_paragraph()
        p.text = f"✔  {itm}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = RGBColor(226, 232, 240)
        p.space_after = Pt(8)

    # Right: Future Scope & Q&A
    tx15_f = s15.shapes.add_textbox(Inches(7.0), Inches(1.2), Inches(5.3), Inches(5.2))
    tf15_f = tx15_f.text_frame
    tf15_f.word_wrap = True

    p = tf15_f.paragraphs[0]
    p.text = "Future Scope"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(14)

    future_items = [
        "SDN Hardware Integration: Interfacing with physical OpenFlow and P4 programmable data planes.",
        "BGP Multi-Homing: Extending multi-objective recovery across inter-domain Autonomous Systems.",
        "Predictive Anomaly Detection: Implementing Kalman filtering for dynamic day/night traffic threshold adaptation.",
        "Large-Scale Topologies: Scaling graph analytics to data-center Fat-Tree topologies with hundreds of nodes."
    ]
    for itm in future_items:
        p = tf15_f.add_paragraph()
        p.text = f"→  {itm}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = RGBColor(203, 213, 225)
        p.space_after = Pt(8)

    p_qa = tf15_f.add_paragraph()
    p_qa.text = "\nThank You!\nOpen for Questions & Live Demonstration"
    p_qa.font.size = Pt(16)
    p_qa.font.bold = True
    p_qa.font.color.rgb = RGBColor(56, 189, 248)

    # Save presentation
    out_file = "Design_and_Development_of_Intelligent_Network_Fault_Framework_15_Slides.pptx"
    prs.save(out_file)
    print(f"Clean 15-slide presentation saved to: {out_file}")
    return out_file

if __name__ == "__main__":
    build_presentation()
