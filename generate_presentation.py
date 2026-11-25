"""generate_presentation.py
Generates a formal, professional, university-grade PowerPoint presentation
(15 slides) for the Computer Networks End-Semester Project:
'Intelligent Network Fault Diagnosis and Automated Recovery Framework'
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Color Palette
    C_NAVY = RGBColor(11, 37, 69)       # #0B2545 - Deep Primary Header
    C_COBALT = RGBColor(30, 64, 175)    # #1E40AF - Secondary Brand
    C_SLATE_BG = RGBColor(248, 250, 252)# #F8FAFC - Slide Background
    C_CARD_BG = RGBColor(255, 255, 255) # Pure White Cards
    C_CARD_BORDER = RGBColor(226, 232, 240) # #E2E8F0 - Subtle Card Border
    C_TEXT_MAIN = RGBColor(15, 23, 42)  # #0F172A - Body Text
    C_TEXT_MUTED = RGBColor(71, 85, 105)# #475569 - Secondary Subtitle
    C_GREEN = RGBColor(16, 185, 129)    # #10B981 - Success
    C_AMBER = RGBColor(217, 119, 6)     # #D97706 - Warning / Degraded
    C_RED = RGBColor(220, 38, 38)       # #DC2626 - Critical / Fault
    C_BLUE = RGBColor(2, 132, 199)      # #0284C7 - Info / Telemetry

    blank_layout = prs.slide_layouts[6]

    def set_slide_background(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, title, category="23AID206 COMPUTER NETWORKS | PROJECT DEFENSE"):
        # Top accent bar
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = C_COBALT
        bar.line.fill.background()

        # Category pill / label
        tx_cat = slide.shapes.add_textbox(Inches(0.8), Inches(0.28), Inches(11.5), Inches(0.3))
        tf_cat = tx_cat.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(9.5)
        p_cat.font.bold = True
        p_cat.font.color.rgb = C_COBALT

        # Title
        tx_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.5), Inches(0.65))
        tf_title = tx_title.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = C_NAVY

        # Subtle divider line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.22), Inches(11.733), Inches(0.02))
        line.fill.solid()
        line.fill.fore_color.rgb = C_CARD_BORDER
        line.line.fill.background()

    def add_card(slide, left, top, width, height, title=None, border_color=C_CARD_BORDER, bg_color=C_CARD_BG):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)

        if title:
            tx = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), Inches(0.4))
            tf = tx.text_frame
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = C_NAVY
        return card

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Executive Theme)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, C_NAVY)

    # Decorative geometric header block
    dec = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.8), Inches(13.333), Inches(0.7))
    dec.fill.solid()
    dec.fill.fore_color.rgb = C_COBALT
    dec.line.fill.background()

    # Title box
    tx1 = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(3.2))
    tf1 = tx1.text_frame
    tf1.word_wrap = True

    p_badge = tf1.paragraphs[0]
    p_badge.text = "AMRITA VISHWA VIDYAPEETHAM  |  DEPARTMENT OF ARTIFICIAL INTELLIGENCE & DATA SCIENCE"
    p_badge.font.size = Pt(11)
    p_badge.font.bold = True
    p_badge.font.color.rgb = RGBColor(147, 197, 253) # Light Blue
    p_badge.space_after = Pt(14)

    p_main = tf1.add_paragraph()
    p_main.text = "Intelligent Network Fault Diagnosis &\nAutomated Recovery Framework"
    p_main.font.size = Pt(32)
    p_main.font.bold = True
    p_main.font.color.rgb = RGBColor(255, 255, 255)
    p_main.space_after = Pt(14)

    p_sub = tf1.add_paragraph()
    p_sub.text = "A Deterministic, Graph-Theoretic, Zero-ML Self-Healing Network Management Architecture"
    p_sub.font.size = Pt(15)
    p_sub.font.color.rgb = RGBColor(226, 232, 240)
    p_sub.space_after = Pt(28)

    # Metadata Card at bottom
    m_tx = s1.shapes.add_textbox(Inches(1.0), Inches(5.1), Inches(11.3), Inches(1.4))
    m_tf = m_tx.text_frame
    m_p1 = m_tf.paragraphs[0]
    m_p1.text = "Course: 23AID206 - Computer Networks (End-Semester Project Evaluation)"
    m_p1.font.size = Pt(12)
    m_p1.font.bold = True
    m_p1.font.color.rgb = RGBColor(255, 255, 255)

    m_p2 = m_tf.add_paragraph()
    m_p2.text = "Focus Areas: Dynamic Routing • Telemetry Observability • Rule-Based Diagnosis • Multi-Objective Recovery • 7-Point Audit"
    m_p2.font.size = Pt(11)
    m_p2.font.color.rgb = RGBColor(148, 163, 184)

    # =========================================================================
    # SLIDE 2: Problem Statement & Motivation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, C_SLATE_BG)
    add_header(s2, "Problem Statement & Project Motivation", "Chapter 1: Background & Need")

    # Card 1: Traditional NOC Challenges
    c1 = add_card(s2, Inches(0.8), Inches(1.45), Inches(3.7), Inches(5.5), "Traditional NOC Limitations")
    tx = s2.shapes.add_textbox(Inches(0.95), Inches(2.05), Inches(3.4), Inches(4.7))
    tf = tx.text_frame
    tf.word_wrap = True
    points1 = [
        ("Manual & Reactive Triage:", "Operators manually execute disconnected ping, tracert, and interface queries after outages happen."),
        ("Inflated MTTD & MTTR:", "Human diagnostic latency inflates Mean Time to Detect and Mean Time to Recover, causing enterprise downtime."),
        ("Multi-Layer Heterogeneity:", "Simultaneous physical link cuts, DNS crashes, and gateway misconfigurations confuse manual triage."),
        ("Single Point of Failure:", "Without automated path discovery, failover is sluggish and prone to routing loops.")
    ]
    for i, (hd, bd) in enumerate(points1):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"• {hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT_MAIN
        p.space_after = Pt(10)

    # Card 2: Pitfalls of Black-Box AI / ML
    c2 = add_card(s2, Inches(4.8), Inches(1.45), Inches(3.7), Inches(5.5), "The Problem with 'Black-Box' ML")
    tx = s2.shapes.add_textbox(Inches(4.95), Inches(2.05), Inches(3.4), Inches(4.7))
    tf = tx.text_frame
    tf.word_wrap = True
    points2 = [
        ("Zero Explainability:", "Deep Learning models cannot provide verifiable proof chains required for mission-critical core routing."),
        ("Training Data Hunger:", "Requires millions of historical failure samples that are rarely available for custom enterprise topologies."),
        ("Hallucination & Instability:", "Unseen topological shifts cause neural nets to generate non-existent paths or route loops."),
        ("Heavy Computational Overhead:", "Inference latency violates sub-second network self-healing requirements.")
    ]
    for i, (hd, bd) in enumerate(points2):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"• {hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT_MAIN
        p.space_after = Pt(10)

    # Card 3: Our Proposed Solution
    c3 = add_card(s2, Inches(8.8), Inches(1.45), Inches(3.7), Inches(5.5), "Our Self-Healing Solution", border_color=C_COBALT)
    tx = s2.shapes.add_textbox(Inches(8.95), Inches(2.05), Inches(3.4), Inches(4.7))
    tf = tx.text_frame
    tf.word_wrap = True
    points3 = [
        ("Deterministic Expert System:", "Rule-based mathematical reasoning delivering 100% reproducible diagnostic findings."),
        ("Pure Telemetry-Driven:", "Observer never cheats by reading injected fault metadata or scenario labels."),
        ("Atomic Multi-Objective Failover:", "Evaluates candidate routes by latency, cost, and loss without restoring dead cables."),
        ("Rigorous Independent Audit:", "Validates repairs using live 5-packet probe bursts and a 7-point verification gate.")
    ]
    for i, (hd, bd) in enumerate(points3):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"✔ {hd} {bd}"
        p.font.size = Pt(10)
        p.font.color.rgb = C_TEXT_MAIN
        p.space_after = Pt(10)

    # =========================================================================
    # SLIDE 3: Project Objectives & Architectural Pillars
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, C_SLATE_BG)
    add_header(s3, "Project Objectives & Technical Pillars", "Chapter 1: Goals & Scope")

    pillars = [
        ("1. Graph Network Modeling", "Build an authoritative virtual network using NetworkX modeling Layer-2 switching, Layer-3 routing, interfaces, propagation latency, and probabilistic link loss.", C_COBALT),
        ("2. Transactional Fault Injection", "Support atomic injection of heterogeneous faults (link cuts, gateway misconfigurations, DNS crashes, high latency, loss) with snapshot-based state rollback.", C_RED),
        ("3. Telemetry & Observation Engine", "Derive all network metrics strictly from operational graph state. Zero state-leakage from ground truth metadata or scenario labels.", C_BLUE),
        ("4. Explainable Diagnosis Engine", "Implement forward-chaining expert rules yielding mathematically calibrated confidence ratings (0.90 to 1.00) with explicit evidentiary rationale.", C_AMBER),
        ("5. Multi-Objective Route Failover", "Evaluate Pareto-optimal alternate routes considering Cost, Latency, Loss, and Hop Count. Severed links remain strictly DOWN; traffic is routed around faults.", C_GREEN),
        ("6. 7-Point Independent Verification", "Execute active probe packet bursts (5, 10, 20 packets) and a 7-point verification audit confirming reachability, isolation, and service bounds.", C_COBALT),
    ]

    for idx, (title, desc, accent) in enumerate(pillars):
        row = idx // 3
        col = idx % 3
        x = Inches(0.8 + col * 4.0)
        y = Inches(1.5 + row * 2.7)
        add_card(s3, x, y, Inches(3.75), Inches(2.4), title, border_color=accent)
        tx = s3.shapes.add_textbox(x + Inches(0.15), y + Inches(0.55), Inches(3.45), Inches(1.7))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(10.5)
        p.font.color.rgb = C_TEXT_MAIN

    # =========================================================================
    # SLIDE 4: Core Network Topology & Architecture
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, C_SLATE_BG)
    add_header(s4, "Core Network Architecture & Diamond Topology", "Chapter 2: Network Design")

    # Left Card: Topology Specifications
    add_card(s4, Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.5), "Diamond Core Multi-Path Architecture")
    tx_top = s4.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.7))
    tf_top = tx_top.text_frame
    tf_top.word_wrap = True
    top_specs = [
        ("Access Layer Subnet:", "Hosts PC1 (192.168.1.10) and PC2 (192.168.1.20) on 192.168.1.0/24."),
        ("Primary Gateway Router (R1):", "Local default gateway (192.168.1.1) bridging client LAN to core transit paths."),
        ("Dual Transit Core Routers:", "R2 (Primary path, 10.0.1.1) and R3 (Secondary/backup path, 10.0.2.1)."),
        ("Enterprise Server Farm:", "Centralized application and DNS server (172.16.0.10) on 172.16.0.0/24."),
        ("Primary Active Route:", "PC1 -> R1 -> R2 -> Server (Total Cost: 3, Latency: 8.0 ms, Loss: 0.0%)."),
        ("Secondary Backup Route:", "PC1 -> R1 -> R3 -> Server (Total Cost: 5, Latency: 10.0 ms, Loss: 0.0%).")
    ]
    for i, (hd, bd) in enumerate(top_specs):
        p = tf_top.paragraphs[0] if i == 0 else tf_top.add_paragraph()
        p.text = f"• {hd} {bd}"
        p.font.size = Pt(10.5)
        p.space_after = Pt(9)

    # Right Card: Visual Flow & Design Highlights
    add_card(s4, Inches(6.8), Inches(1.45), Inches(5.7), Inches(5.5), "Architectural Design Highlights")
    tx_r = s4.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.7))
    tf_r = tx_r.text_frame
    tf_r.word_wrap = True
    highlights = [
        ("Multi-Path Redundancy:", "Ensures zero single points of failure between client workstations and enterprise services."),
        ("Metric Diversity:", "R1-R2 path is prioritized for low latency (3ms) and lowest cost (1). R1-R3 path provides resilient hot standby (Cost 2, 4ms)."),
        ("Realistic Link Attributes:", "Every edge models propagation latency (ms), administrative cost, status (UP/DOWN), and packet loss (%)."),
        ("Layer-2 / Layer-3 Independence:", "Handles device renaming, dynamic IP re-assignment, and link disconnection on the fly."),
        ("Packet Tracer Interoperability:", "Canvas coordinates, device icons, halo selection indicators, and cable port configurations mirror Cisco Packet Tracer.")
    ]
    for i, (hd, bd) in enumerate(highlights):
        p = tf_r.paragraphs[0] if i == 0 else tf_r.add_paragraph()
        p.text = f"✔ {hd} {bd}"
        p.font.size = Pt(10.5)
        p.space_after = Pt(11)

    # =========================================================================
    # SLIDE 5: IPv4 Addressing Scheme & Interface Mapping
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, C_SLATE_BG)
    add_header(s5, "Complete IPv4 Addressing Scheme & Interface Allocations", "Chapter 2: Addressing Plan")

    # Table of IP Scheme
    add_card(s5, Inches(0.8), Inches(1.45), Inches(11.733), Inches(4.1), "Table 2.1: Master Interface & IP Address Allocation Scheme")
    
    rows, cols = 8, 6
    tbl_shape = s5.shapes.add_table(rows, cols, Inches(1.0), Inches(2.05), Inches(11.333), Inches(3.2))
    tbl = tbl_shape.table
    tbl.columns[0].width = Inches(1.4)
    tbl.columns[1].width = Inches(2.0)
    tbl.columns[2].width = Inches(1.8)
    tbl.columns[3].width = Inches(1.9)
    tbl.columns[4].width = Inches(1.8)
    tbl.columns[5].width = Inches(2.433)

    headers = ["Device", "Port / Interface", "IPv4 Address", "Subnet Mask", "Default Gateway", "Function / Role"]
    for c, h in enumerate(headers):
        cell = tbl.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

    data = [
        ["PC1", "eth0 / Fa0", "192.168.1.10", "255.255.255.0 (/24)", "192.168.1.1", "Client Workstation 1"],
        ["PC2", "eth0 / Fa0", "192.168.1.20", "255.255.255.0 (/24)", "192.168.1.1", "Client Workstation 2"],
        ["R1", "Fa0/0 (LAN Port)", "192.168.1.1", "255.255.255.0 (/24)", "N/A (Router)", "Primary Subnet Gateway"],
        ["R1", "Gi0/1, Gi0/2 (WAN)", "10.0.1.2, 10.0.2.2", "255.255.255.0 (/24)", "N/A (Router)", "Core Transit Uplinks"],
        ["R2", "Gi0/1, Gi0/2", "10.0.1.1, 172.16.0.1", "255.255.255.0 (/24)", "N/A (Router)", "Primary Transit Core"],
        ["R3", "Gi0/1, Gi0/2", "10.0.2.1, 172.16.0.2", "255.255.255.0 (/24)", "N/A (Router)", "Backup Transit Core"],
        ["Server", "eth0 / Fa0", "172.16.0.10", "255.255.255.0 (/24)", "172.16.0.1", "Data & DNS Server"]
    ]
    for r, row in enumerate(data, start=1):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_TEXT_MAIN
            if r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249)

    # Explanation Callout below table
    c_note = add_card(s5, Inches(0.8), Inches(5.7), Inches(11.733), Inches(1.3), "Key Networking Note: Dual-Mode Gateway & Interface Principles", border_color=C_BLUE)
    tx_note = s5.shapes.add_textbox(Inches(0.95), Inches(6.05), Inches(11.4), Inches(0.85))
    tf_note = tx_note.text_frame
    tf_note.word_wrap = True
    p_n = tf_note.paragraphs[0]
    p_n.text = "• Hosts (PC1, PC2) require a local IPv4 gateway (192.168.1.1) to forward packets off-subnet.\n• Routers route packets dynamically using internal Routing Tables and Next-Hop IP addresses (hence Default Gateway = N/A)."
    p_n.font.size = Pt(10)
    p_n.font.color.rgb = C_TEXT_MAIN

    # =========================================================================
    # SLIDE 6: Software Architecture & Decoupled Lifecycle
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, C_SLATE_BG)
    add_header(s6, "Modular Software Architecture & Decoupled Lifecycle", "Chapter 3: System Design")

    stages = [
        ("1. INJECT", "Atomic fault injection modifies virtual graph (status, gateway, latency, loss, DNS).", C_RED),
        ("2. OBSERVE", "Telemetry engine passive collection & active probe bursts. Reads zero fault metadata.", C_BLUE),
        ("3. DIAGNOSE", "Rule-based expert system evaluates conditions in parallel. Produces calibrated confidence.", C_AMBER),
        ("4. PLAN", "Global recovery planner creates coordinated actions and Pareto-optimal routes.", C_COBALT),
        ("5. RECOVER", "Transactional execution of failover, gateway repair, or DNS restoration with snapshot safety.", C_GREEN),
        ("6. VERIFY", "Independent 7-point verification audit and live 5-packet burst delivery measurement.", C_NAVY)
    ]

    for idx, (st_name, st_desc, st_col) in enumerate(stages):
        x = Inches(0.8 + idx * 1.98)
        card = add_card(s6, x, Inches(1.5), Inches(1.85), Inches(2.5), None, border_color=st_col)
        tx = s6.shapes.add_textbox(x + Inches(0.1), Inches(1.65), Inches(1.65), Inches(2.2))
        tf = tx.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = st_name
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = st_col
        p1.space_after = Pt(8)
        p2 = tf.add_paragraph()
        p2.text = st_desc
        p2.font.size = Pt(9.5)
        p2.font.color.rgb = C_TEXT_MAIN

    # Bottom Architecture Card
    add_card(s6, Inches(0.8), Inches(4.3), Inches(11.733), Inches(2.7), "Core Architectural Strengths")
    tx_arch = s6.shapes.add_textbox(Inches(1.0), Inches(4.75), Inches(11.3), Inches(2.1))
    tf_arch = tx_arch.text_frame
    tf_arch.word_wrap = True
    arch_bullets = [
        ("Strict Telemetry Isolation:", "The diagnostic engine is mathematically isolated from fault injection. Findings are deduced purely from observed telemetry anomalies."),
        ("No Early Short-Circuiting:", "Link failure, wrong gateway, DNS crash, high latency, and loss are evaluated concurrently to discover all simultaneous root causes."),
        ("Transactional Snapshot Safety:", "Full graph topology snapshot is recorded prior to executing recovery. If any repair fails audit, state rolls back automatically to prevent corruption."),
        ("Zero State Leakage:", "Fresh execution contexts on every run ensure past failures never bleed into subsequent baseline observations.")
    ]
    for i, (hd, bd) in enumerate(arch_bullets):
        p = tf_arch.paragraphs[0] if i == 0 else tf_arch.add_paragraph()
        p.text = f"✔ {hd} {bd}"
        p.font.size = Pt(10.5)
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 7: Telemetry Observation & Multi-Link Analytics
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, C_SLATE_BG)
    add_header(s7, "Telemetry Observation & Probabilistic Loss Modeling", "Chapter 3: Telemetry Engine")

    # Left: Passive & Active Telemetry
    add_card(s7, Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.5), "Passive & Active Telemetry Mechanisms")
    tx_tel = s7.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.3), Inches(4.7))
    tf_tel = tx_tel.text_frame
    tf_tel.word_wrap = True
    tel_points = [
        ("Passive Link-State Monitoring:", "Directly monitors administrative and physical interface states across all nodes (detects UP vs. DOWN)."),
        ("Hop-by-Hop Propagation Latency:", "Computes cumulative end-to-end latency along active paths: L_{total} = sum(latency_i). Flags breaches exceeding 50 ms."),
        ("Synthetic Active Probe Bursts:", "Transmits configurable batches (5, 10, 20 packets) measuring exact round-trip times and per-packet delivery rates."),
        ("DNS Service Resolution Probing:", "Validates client resolver queries against simulated DNS daemon availability on port 53."),
        ("Disjoint Network Partition Isolation:", "Evaluates connected components via Breadth-First Search (BFS) to distinguish link cuts from total endpoint isolation.")
    ]
    for i, (hd, bd) in enumerate(tel_points):
        p = tf_tel.paragraphs[0] if i == 0 else tf_tel.add_paragraph()
        p.text = f"• {hd} {bd}"
        p.font.size = Pt(10.5)
        p.space_after = Pt(10)

    # Right: Probabilistic Packet Loss Formulation
    add_card(s7, Inches(6.8), Inches(1.45), Inches(5.7), Inches(5.5), "Probabilistic Packet Loss Modeling", border_color=C_BLUE)
    tx_loss = s7.shapes.add_textbox(Inches(7.0), Inches(2.05), Inches(5.3), Inches(4.7))
    tf_loss = tx_loss.text_frame
    tf_loss.word_wrap = True

    p = tf_loss.paragraphs[0]
    p.text = "Mathematical Formulation for End-to-End Loss:"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(8)

    p_eq = tf_loss.add_paragraph()
    p_eq.text = "P(End-to-End Loss) = 1 - ∏ (1 - p_i)\nwhere p_i = individual link drop probability."
    p_eq.font.size = Pt(11.5)
    p_eq.font.bold = True
    p_eq.font.color.rgb = C_COBALT
    p_eq.space_after = Pt(14)

    loss_bullets = [
        ("Authentic Statistical Independence:", "Converts percentage loss per link into independent success probabilities, multiplies them, and computes the complement."),
        ("Realistic Drop Simulation:", "Per-packet uniform random sampling generates stochastic drop events matching real-world router buffer overflows."),
        ("Degraded vs. Dead Paths:", "Allows the framework to analyze paths that remain technically UP but operate in severe packet-dropping degradation (e.g., 33% or 42% loss)."),
        ("Validation in Testing:", "Proven by empirical delivery: a 42% loss path yields exactly 3/5 delivered packets (60%), matching mathematical probability.")
    ]
    for hd, bd in loss_bullets:
        p = tf_loss.add_paragraph()
        p.text = f"✔ {hd} {bd}"
        p.font.size = Pt(10)
        p.space_after = Pt(8)

    # =========================================================================
    # SLIDE 8: Explainable Diagnostic Engine (Rule-Based Expert System)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, C_SLATE_BG)
    add_header(s8, "Explainable Root-Cause Diagnosis (Expert System)", "Chapter 3: Diagnostics")

    # Table of Diagnostic Rules
    add_card(s8, Inches(0.8), Inches(1.45), Inches(11.733), Inches(5.5), "Deterministic Diagnostic Production Rules & Calibrated Confidence")
    
    rows, cols = 5, 5
    tbl_diag = s8.shapes.add_table(rows, cols, Inches(1.0), Inches(2.1), Inches(11.333), Inches(4.5))
    tbd = tbl_diag.table
    tbd.columns[0].width = Inches(1.4)
    tbd.columns[1].width = Inches(3.2)
    tbd.columns[2].width = Inches(3.0)
    tbd.columns[3].width = Inches(1.4)
    tbd.columns[4].width = Inches(2.333)

    d_headers = ["Rule ID", "Telemetry Trigger Condition", "Diagnosed Root Cause", "Confidence", "Recommended Recovery Action"]
    for c, h in enumerate(d_headers):
        cell = tbd.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

    d_data = [
        ["Rule 1: Link Cut", "Link status == DOWN on active or alternate forwarding path", "Link failure", "99% (0.99)", "Failover rerouting around severed link"],
        ["Rule 2: Gateway", "Configured host gateway is nonexistent, off-subnet, or unreachable", "Incorrect default gateway", "98% (0.98)", "Reconfigure host default gateway to valid local router R1 (192.168.1.1)"],
        ["Rule 3: DNS Crash", "Underlying IP transport operational, but DNS resolution probe fails", "DNS service failure", "95% (0.95)", "Restart simulated DNS resolver daemon (port 53)"],
        ["Rule 4: Degraded", "Cumulative path latency > 50ms OR probabilistic packet loss > 10%", "High latency / Packet loss", "92% (0.92)", "Shift traffic to lower-latency / zero-loss alternate route"]
    ]
    for r, row in enumerate(d_data, start=1):
        for c, val in enumerate(row):
            cell = tbd.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_TEXT_MAIN
            if r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249)

    # =========================================================================
    # SLIDE 9: Global Recovery Planner & Multi-Objective Optimization
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9, C_SLATE_BG)
    add_header(s9, "Global Recovery Planner & Multi-Objective Routing", "Chapter 3: Recovery Planning")

    # Left: Action Dependencies
    add_card(s9, Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.5), "Dependency-Aware Coordinated Recovery Plan")
    tx_plan = s9.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.3), Inches(4.7))
    tf_plan = tx_plan.text_frame
    tf_plan.word_wrap = True
    plan_points = [
        ("Priority 1: Route Activation (Failover):", "If links are cut or degraded, the planner selects the optimal surviving path first. All routing needs collapse into ONE atomic route switch."),
        ("Priority 2: Gateway Restoration:", "Restores host default gateway to the directly connected router interface before testing DNS resolution."),
        ("Priority 3: DNS Service Restoration:", "Restarts DNS resolver daemon. Has explicit dependency on functional IP transport and gateway."),
        ("Preconditions & Safety Checks:", "Every action verifies required topology conditions before execution; unsafe mutations are rejected.")
    ]
    for i, (hd, bd) in enumerate(plan_points):
        p = tf_plan.paragraphs[0] if i == 0 else tf_plan.add_paragraph()
        p.text = f"• {hd} {bd}"
        p.font.size = Pt(10.5)
        p.space_after = Pt(12)

    # Right: Pareto Multi-Objective Optimization
    add_card(s9, Inches(6.8), Inches(1.45), Inches(5.7), Inches(5.5), "Pareto Multi-Objective Route Scoring", border_color=C_GREEN)
    tx_score = s9.shapes.add_textbox(Inches(7.0), Inches(2.05), Inches(5.3), Inches(4.7))
    tf_score = tx_score.text_frame
    tf_score.word_wrap = True

    p = tf_score.paragraphs[0]
    p.text = "Mathematical Objective Function:"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_NAVY
    p.space_after = Pt(8)

    p_fn = tf_score.add_paragraph()
    p_fn.text = "Score = w_1·Cost + w_2·Latency + w_3·Loss + w_4·Hops\nOptimal Candidate = argmin(Score)"
    p_fn.font.size = Pt(11.5)
    p_fn.font.bold = True
    p_fn.font.color.rgb = C_COBALT
    p_fn.space_after = Pt(14)

    score_bullets = [
        ("Zero 'Magic' Cable Repairs:", "If link R1-R2 is cut, it stays strictly DOWN. The optimizer shifts active forwarding traffic to alternate transit router R3."),
        ("Latency vs. Loss Tradeoffs:", "In high-loss scenarios, the optimizer accurately trades a slightly longer hop count for a zero-loss communication path."),
        ("Candidate Route Discovery:", "Discovers all simple loop-free paths using modified depth-first graph traversal (DFS)."),
        ("Live Telemetry Synchronization:", "Route metrics are recomputed with live interface measurements before final activation.")
    ]
    for hd, bd in score_bullets:
        p = tf_score.add_paragraph()
        p.text = f"✔ {hd} {bd}"
        p.font.size = Pt(10)
        p.space_after = Pt(9)

    # =========================================================================
    # SLIDE 10: Authentic Physical Fault Bypass & Partition Handling
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10, C_SLATE_BG)
    add_header(s10, "Authentic Fault Bypass & Honest Partition Handling", "Chapter 3: Recovery Principles")

    cards10 = [
        ("Authentic Fault Bypass", "• Severed links remain strictly DOWN.\n• No 'fake' software toggles.\n• Real-world physical fidelity.\n• Traffic is rerouted across alternate paths (R1->R3->Server).", C_RED),
        ("Decoupling Availability & Health", "• Service Available: Client can successfully communicate with Server.\n• Network Health: Flagged DEGRADED because backup or degraded link is active.\n• Clear distinction prevents false optimism.", C_AMBER),
        ("Honest Partition Reporting", "• If all access links to Server are DOWN, recovery is impossible.\n• Reports RECOVERY UNAVAILABLE with 0 corrective actions executed.\n• Prevents fake repair claims.", C_COBALT)
    ]

    for idx, (t, b, c) in enumerate(cards10):
        x = Inches(0.8 + idx * 4.0)
        add_card(s10, x, Inches(1.45), Inches(3.75), Inches(5.5), t, border_color=c)
        tx = s10.shapes.add_textbox(x + Inches(0.15), Inches(2.1), Inches(3.45), Inches(4.6))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = b
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_MAIN
        p.line_spacing = 1.3

    # =========================================================================
    # SLIDE 11: 7-Point Independent Verification Audit
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11, C_SLATE_BG)
    add_header(s11, "7-Point Independent Verification Audit Engine", "Chapter 3: Verification & Auditing")

    add_card(s11, Inches(0.8), Inches(1.45), Inches(11.733), Inches(5.5), "7-Point Post-Recovery Verification Gate")

    rows, cols = 8, 4
    tbl_v = s11.shapes.add_table(rows, cols, Inches(1.0), Inches(2.05), Inches(11.333), Inches(4.6))
    tv = tbl_v.table
    tv.columns[0].width = Inches(2.5)
    tv.columns[1].width = Inches(3.8)
    tv.columns[2].width = Inches(2.8)
    tv.columns[3].width = Inches(2.233)

    v_headers = ["Audit Check", "Verification Condition", "Expected Criteria", "Evaluation Outcome"]
    for c, h in enumerate(v_headers):
        cell = tv.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

    v_data = [
        ["1. Endpoint IP Reachability", "Source endpoint has operational path to Destination", "Path exists in graph", "PASS (Verified)"],
        ["2. DNS Resolution Service", "Simulated DNS daemon responds to name queries", "dns_available == True", "PASS (Verified)"],
        ["3. Default Gateway Validity", "Gateway IP belongs to connected router on local subnet", "gateway_ok == True", "PASS (Verified)"],
        ["4. Active Route Integrity", "Active forwarding path is continuous and loop-free", "path_is_usable == True", "PASS (Verified)"],
        ["5. Failed Link Isolation", "Active route completely avoids all DOWN links", "No edges with status DOWN", "PASS (Verified)"],
        ["6. End-to-End Latency Bound", "Cumulative propagation latency <= threshold", "Latency <= 100.0 ms", "PASS (Verified)"],
        ["7. Packet Loss Compliance", "Probabilistic path loss within operational bounds", "Path loss <= 50.0%", "PASS (Verified)"]
    ]
    for r, row in enumerate(v_data, start=1):
        for c, val in enumerate(row):
            cell = tv.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.color.rgb = C_GREEN if "PASS" in val else C_TEXT_MAIN
            p.font.bold = True if "PASS" in val else False
            if r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249)

    # =========================================================================
    # SLIDE 12: Dual User Interfaces (Visual GUI & CMD Terminal)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12, C_SLATE_BG)
    add_header(s12, "Interactive User Interface Architecture", "Chapter 3: Interfaces")

    # Left: Visual Canvas
    add_card(s12, Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.5), "Cisco Packet Tracer Visual Workspace", border_color=C_COBALT)
    tx_ui = s12.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.3), Inches(4.7))
    tf_ui = tx_ui.text_frame
    tf_ui.word_wrap = True
    ui_pts = [
        ("Interactive Canvas:", "Full drag-and-drop device palette (Routers, Switches, PCs, Laptops, Servers) with coordinate persistence."),
        ("Connection Management:", "Dedicated cable connect tool supporting Copper Straight-Through, Cross-Over, Fiber, and Serial."),
        ("Dynamic Inspector Panel:", "Right-hand panel for real-time device configuration (IP, mask, gateway, DNS) and link parameters (latency, loss, cost)."),
        ("Scenario Bar & Action Buttons:", "Toolbar controls for Inject Fault, Monitor & Diagnose, Recover & Verify, Reset, and Terminal."),
        ("8-Tab Operator Notebook:", "Dedicated tabs for Telemetry, Recovery, Route Matrix, Performance, Event Log, Recovery Planner, Audit, and Trends.")
    ]
    for i, (hd, bd) in enumerate(ui_pts):
        p = tf_ui.paragraphs[0] if i == 0 else tf_ui.add_paragraph()
        p.text = f"✔ {hd} {bd}"
        p.font.size = Pt(10)
        p.space_after = Pt(8)

    # Right: CMD Terminal
    add_card(s12, Inches(6.8), Inches(1.45), Inches(5.7), Inches(5.5), "Windows CMD Simulated Terminal", border_color=C_NAVY)
    tx_cmd = s12.shapes.add_textbox(Inches(7.0), Inches(2.05), Inches(5.3), Inches(4.7))
    tf_cmd = tx_cmd.text_frame
    tf_cmd.word_wrap = True
    cmd_pts = [
        ("Authentic Windows Prompt:", "Simulated CLI window with Microsoft Windows banner, cursor, and command history (Up/Down arrows)."),
        ("ping <target> [-n count]:", "Transmits live ICMP echo requests with per-packet latency, RTT jitter, and packet loss statistics."),
        ("tracert <target>:", "Displays hop-by-hop layer-3 IP traversal across intermediate routers with latency timing."),
        ("ipconfig [/all]:", "Inspects host IPv4 address, subnet mask, default gateway, and DNS server."),
        ("nslookup <domain>:", "Simulates DNS A-record queries against the enterprise server resolver."),
        ("diagnose / recover:", "Direct CLI triggers to run root-cause diagnosis and execute multi-objective recovery.")
    ]
    for i, (hd, bd) in enumerate(cmd_pts):
        p = tf_cmd.paragraphs[0] if i == 0 else tf_cmd.add_paragraph()
        p.text = f"✔ {hd} {bd}"
        p.font.size = Pt(10)
        p.space_after = Pt(7)

    # =========================================================================
    # SLIDE 13: Experimental Results & Benchmarks (Figure 4.1)
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13, C_SLATE_BG)
    add_header(s13, "Experimental Evaluation & Benchmark Scenarios", "Chapter 4: Testing & Results")

    # Left: Test Summary Table
    add_card(s13, Inches(0.8), Inches(1.45), Inches(5.6), Inches(5.5), "Scenario Test Matrix (TC-01 to TC-05)")
    rows, cols = 6, 4
    tbl_tc = s13.shapes.add_table(rows, cols, Inches(0.95), Inches(2.05), Inches(5.3), Inches(4.6))
    ttc = tbl_tc.table
    ttc.columns[0].width = Inches(1.1)
    ttc.columns[1].width = Inches(1.8)
    ttc.columns[2].width = Inches(1.3)
    ttc.columns[3].width = Inches(1.1)

    tc_heads = ["Test ID", "Scenario Description", "Delivery Rate", "Outcome"]
    for c, h in enumerate(tc_heads):
        cell = ttc.cell(0, c)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)

    tc_data = [
        ["TC-01", "Baseline Healthy Path", "100.0% (5/5)", "HEALTHY"],
        ["TC-02", "Primary Link DOWN (R1-R2)", "100.0% (5/5)", "RECOVERY VERIFIED"],
        ["TC-03", "42% Loss on Primary Path", "60.0% (3/5)", "SERVICE MAINTAINED"],
        ["TC-04", "High Loss Bottleneck (90%)", "10.0% (1/10)", "RECOVERY UNAVAILABLE"],
        ["TC-05", "Target Server Total Isolation", "0.0% (0/5)", "RECOVERY UNAVAILABLE"]
    ]
    for r, row in enumerate(tc_data, start=1):
        for c, val in enumerate(row):
            cell = ttc.cell(r, c)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(8.5)
            p.font.color.rgb = C_TEXT_MAIN
            if r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(241, 245, 249)

    # Right: Embed Figure 4.1 Image if exists, else card
    fig_path = "figure_4_1_delivery_rate.png"
    add_card(s13, Inches(6.6), Inches(1.45), Inches(5.9), Inches(5.5), "Figure 4.1: Probe Packet Delivery Across Scenarios", border_color=C_COBALT)
    if os.path.exists(fig_path):
        s13.shapes.add_picture(fig_path, Inches(6.8), Inches(2.1), width=Inches(5.5))
    else:
        tx_f = s13.shapes.add_textbox(Inches(6.8), Inches(2.2), Inches(5.5), Inches(4.0))
        tx_f.text_frame.paragraphs[0].text = "Figure 4.1 Bar Chart (TC-01: 100%, TC-02: 100%, TC-03: 60%, TC-04: 10%, TC-05: 0%)"

    # =========================================================================
    # SLIDE 14: Quality Assurance & 207 Automated Unit Tests
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    set_slide_background(s14, C_SLATE_BG)
    add_header(s14, "Quality Assurance & Unit Test Verification Suite", "Chapter 4: Verification")

    # Metrics Card at Top
    c_kpi = add_card(s14, Inches(0.8), Inches(1.45), Inches(11.733), Inches(1.4), None, border_color=C_GREEN)
    tx_kpi = s14.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(11.3), Inches(1.2))
    tf_kpi = tx_kpi.text_frame
    p_kpi = tf_kpi.paragraphs[0]
    p_kpi.text = "207 Automated Unit Tests Passed (100% Pass Rate) | 0 Errors | 0 Failures | Execution Time: 16.6s"
    p_kpi.font.size = Pt(15)
    p_kpi.font.bold = True
    p_kpi.font.color.rgb = C_GREEN

    p_subkpi = tf_kpi.add_paragraph()
    p_subkpi.text = "Continuous test coverage across 10 distinct development checkpoints verifying topological, diagnostic, and recovery safety."
    p_subkpi.font.size = Pt(11)
    p_subkpi.font.color.rgb = C_TEXT_MUTED

    # 4 Test Categories
    cats = [
        ("Topology & Device Tests", "• Baseline graph construction\n• Dynamic device add/remove\n• Protected baseline validation\n• Dual-mode IPv4 Gateway resolution\n• Device renaming & port safety", C_COBALT),
        ("Fault & Telemetry Tests", "• Transactional multi-fault injection\n• Telemetry observer isolation\n• Decoupled fault label masking\n• Probabilistic packet loss calculations\n• Connected component partition check", C_BLUE),
        ("Diagnostic & Planning Tests", "• Forward-chaining rule triggers\n• Calibrated confidence verification\n• Simultaneous multi-fault discovery\n• Dependency-ordered action trees\n• Pareto multi-objective scoring", C_AMBER),
        ("Verification & UI Tests", "• 7-point independent audit gate\n• Active probe packet bursts\n• Transactional snapshot rollback\n• Terminal CMD ping/tracert parsing\n• Matplotlib 6-graph canvas rendering", C_GREEN)
    ]
    for idx, (t, b, c) in enumerate(cats):
        x = Inches(0.8 + idx * 3.0)
        add_card(s14, x, Inches(3.1), Inches(2.8), Inches(3.85), t, border_color=c)
        tx = s14.shapes.add_textbox(x + Inches(0.12), Inches(3.7), Inches(2.55), Inches(3.1))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = b
        p.font.size = Pt(9.5)
        p.font.color.rgb = C_TEXT_MAIN
        p.line_spacing = 1.3

    # =========================================================================
    # SLIDE 15: Conclusion & Future Scope (Closing Executive Slide)
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    set_slide_background(s15, C_NAVY)

    # Decorative bottom accent
    dec15 = s15.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.8), Inches(13.333), Inches(0.7))
    dec15.fill.solid()
    dec15.fill.fore_color.rgb = C_COBALT
    dec15.line.fill.background()

    # Left: Summary
    tx15_l = s15.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(5.5), Inches(5.2))
    tf15_l = tx15_l.text_frame
    tf15_l.word_wrap = True

    p = tf15_l.paragraphs[0]
    p.text = "Key Project Achievements"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(14)

    achievements = [
        "Delivered a complete, deterministic, zero-ML autonomic self-healing network management architecture.",
        "Combined academic algorithmic rigor (NetworkX, Pareto optimization) with Cisco Packet Tracer interactivity.",
        "Proved authentic physical fault bypass: severed links remain strictly DOWN while traffic shifts to surviving paths.",
        "Enforced transparent decision explainability through calibrated confidence scoring (0.90 to 1.00).",
        "Achieved 100% pass rate across 207 automated unit tests with sub-millisecond reasoning latency."
    ]
    for ach in achievements:
        p = tf15_l.add_paragraph()
        p.text = f"✔  {ach}"
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor(226, 232, 240)
        p.space_after = Pt(10)

    # Right: Future Scope & Q&A
    tx15_r = s15.shapes.add_textbox(Inches(7.0), Inches(1.2), Inches(5.3), Inches(5.2))
    tf15_r = tx15_r.text_frame
    tf15_r.word_wrap = True

    p = tf15_r.paragraphs[0]
    p.text = "Future Directions & Defense"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(14)

    future = [
        "SDN Controller Integration: Interfacing with OpenFlow / P4 programmable hardware planes.",
        "BGP Autonomous System Peering: Extending multi-objective recovery across inter-domain WAN boundaries.",
        "Adaptive Anomaly Baselines: Dynamic threshold calibration using Kalman filters for fluctuating traffic volumes."
    ]
    for f in future:
        p = tf15_r.add_paragraph()
        p.text = f"→  {f}"
        p.font.size = Pt(11)
        p.font.color.rgb = RGBColor(203, 213, 225)
        p.space_after = Pt(12)

    p_qa = tf15_r.add_paragraph()
    p_qa.text = "\nThank You!\nOpen for Questions & Live Demonstration"
    p_qa.font.size = Pt(16)
    p_qa.font.bold = True
    p_qa.font.color.rgb = RGBColor(56, 189, 248) # Sky blue accent

    # Save
    out_path = "Computer_Networks_End_Semester_Presentation.pptx"
    prs.save(out_path)
    print(f"Presentation successfully created at: {out_path}")
    return out_path

if __name__ == "__main__":
    create_presentation()
