"""Independent Observation-Based Root-Cause Diagnosis Engine.

Uses explainable IF-THEN rules operating strictly on telemetry observations.
Does NOT access the graph object, injected fault labels, scenario metadata, or ground truth.
Does NOT activate routes or modify network state.
Supports multiple simultaneous fault detection, unique finding identifiers,
evidence-based confidence scoring, and correlation between root causes and secondary symptoms.
"""
import time
from typing import Any, Dict, List, Optional, Tuple, Union


class DiagnosticFinding(tuple):
    """Structured diagnostic finding with unique finding ID, root cause, supporting evidence,
    affected components, severity, calibrated confidence, network impact, reachability,
    alternative route count, finding type, and recommended recovery action.
    
    Inherits from tuple (root_cause, evidence) to guarantee 100% backward compatibility
    with legacy code and test suites that unpack (name, why) or index finding[0] / finding[1].
    """
    def __new__(
        cls,
        root_cause,
        evidence,
        affected_components=None,
        severity="HIGH",
        confidence=0.95,
        recommended_action="",
        network_impact="",
        endpoint_reachability="REACHABLE",
        healthy_alternative_routes=0,
        finding_id=None,
        fault_category=None,
        finding_type="ROOT_CAUSE",
        related_findings=None,
        diagnostic_timestamp=None
    ):
        obj = super().__new__(cls, (root_cause, evidence))
        obj.root_cause = str(root_cause)
        obj.evidence = str(evidence)
        obj.affected_components = list(affected_components) if affected_components is not None else []
        obj.severity = str(severity).upper()
        obj.confidence = float(confidence)
        obj.recommended_action = str(recommended_action)
        obj.network_impact = str(network_impact)
        obj.endpoint_reachability = str(endpoint_reachability).upper()
        obj.healthy_alternative_routes = int(healthy_alternative_routes)
        obj.finding_id = str(finding_id) if finding_id else "DIAG-UNKNOWN"
        obj.fault_category = str(fault_category or root_cause)
        obj.finding_type = str(finding_type).upper()
        obj.related_findings = list(related_findings) if related_findings else []
        obj.diagnostic_timestamp = float(diagnostic_timestamp) if diagnostic_timestamp is not None else time.time()
        return obj

    @property
    def fault_type(self) -> str:
        """Canonical fault type name."""
        return self.root_cause

    @property
    def affected_device_or_link(self) -> list:
        """Affected entity (device or link)."""
        return self.affected_components

    @property
    def recommended_corrective_action(self) -> str:
        """Recommended corrective action string."""
        return self.recommended_action

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation containing all structured diagnosis fields."""
        return {
            "finding_id": self.finding_id,
            "fault_type": self.fault_type,
            "fault_category": self.fault_category,
            "root_cause": self.root_cause,
            "finding_type": self.finding_type,
            "affected_device_or_link": self.affected_device_or_link,
            "affected_components": self.affected_components,
            "severity": self.severity,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "network_impact": self.network_impact,
            "endpoint_reachability": self.endpoint_reachability,
            "healthy_alternative_routes": self.healthy_alternative_routes,
            "recommended_corrective_action": self.recommended_corrective_action,
            "recommended_action": self.recommended_action,
            "related_findings": self.related_findings,
            "diagnostic_timestamp": self.diagnostic_timestamp
        }

    def __repr__(self) -> str:
        return (
            f"DiagnosticFinding(id='{self.finding_id}', root_cause='{self.root_cause}', "
            f"severity='{self.severity}', confidence={self.confidence:.0%}, "
            f"affected={self.affected_components}, type='{self.finding_type}')"
        )


def diagnose(o, latency_threshold=None, loss_threshold=None, topology_info=None):
    """Diagnose network root causes strictly using observation evidence.
    
    Operates strictly on telemetry observations, topology and device configs.
    Does NOT read injected scenario labels, GUI selections, or ground-truth variables.
    Evaluates all five IF-THEN diagnostic rules independently to detect multiple simultaneous faults.
    Assigns sequential finding IDs (DIAG-0001, DIAG-0002...) and correlates secondary symptoms.
    
    Parameters:
        o (dict): Structured observations from collect_observations().
        latency_threshold (float, optional): Custom latency threshold override in ms.
        loss_threshold (float, optional): Custom packet loss threshold override in %.
        topology_info (any, optional): Additional topology info if available.
        
    Returns:
        list[DiagnosticFinding]: List of structured diagnostic findings.
    """
    findings = []
    finding_counter = 0

    def next_finding_id():
        nonlocal finding_counter
        finding_counter += 1
        return f"DIAG-{finding_counter:04d}"

    # Extract general observation metrics
    reachability = o.get("reachability", False)
    routes = o.get("routes", [])
    healthy_cnt = o.get("healthy_routes_count")
    if healthy_cnt is None:
        healthy_cnt = len([r for r in routes if r.get("is_usable") and not r.get("is_degraded")])

    part_info = o.get("partition_analysis", {})
    is_partitioned = part_info.get("is_partitioned", False)
    comp_cnt = part_info.get("component_count", 1)
    partition_blocks_traffic = part_info.get("partition_blocks_traffic", False)

    link_finding_ids = []

    # -------------------------------------------------------------------------
    # Rule 1: Physical Link Failure Diagnosis
    # IF an observed link status is DOWN, THEN identify the exact failed link.
    # Evaluates every DOWN link independently (supports multiple link failures).
    # -------------------------------------------------------------------------
    down_links = o.get("down_links", [])
    if down_links:
        for link in down_links:
            fid = next_finding_id()
            link_finding_ids.append(fid)

            # Determine severity and impact based on actual network conditions
            if not reachability and healthy_cnt == 0:
                severity = "CRITICAL"
                impact = f"Complete network outage: failed link {link} isolates destination with 0 healthy alternate routes available."
                reach_status = "UNREACHABLE"
                rec_action = f"Keep failed link {link} marked DOWN; no alternative route exists, requires physical connection restoration."
            elif not reachability and healthy_cnt > 0:
                severity = "CRITICAL"
                impact = f"Active path interrupted by failed link {link}. Service degraded, but {healthy_cnt} healthy alternative route(s) exist for failover."
                reach_status = "UNREACHABLE"
                rec_action = f"Keep failed link {link} marked DOWN and activate available healthy alternate route in simulated forwarding state."
            else:
                severity = "HIGH" if healthy_cnt > 0 else "CRITICAL"
                impact = f"Link {link} is DOWN. Failover required; {healthy_cnt} healthy alternative route(s) available."
                reach_status = "REACHABLE" if reachability else "DEGRADED"
                rec_action = f"Keep failed link {link} marked DOWN and reroute traffic over available alternate path(s)."

            findings.append(DiagnosticFinding(
                finding_id=fid,
                root_cause="Link failure",
                evidence=f"IF link status is DOWN, THEN report link failure: {link}. Direct interface telemetry confirms the link is inactive and unable to forward frames.",
                affected_components=[link],
                severity=severity,
                confidence=1.0,  # 100% confidence: direct link status check proves link is DOWN
                recommended_action=rec_action,
                network_impact=impact,
                endpoint_reachability=reach_status,
                healthy_alternative_routes=healthy_cnt,
                fault_category="Physical Layer",
                finding_type="ROOT_CAUSE"
            ))

    # -------------------------------------------------------------------------
    # Rule 2: Incorrect Default Gateway Diagnosis
    # IF the configured gateway is invalid or cannot reach next-hop router,
    # THEN identify the affected endpoint and incorrect gateway.
    # -------------------------------------------------------------------------
    gateway_ok = o.get("gateway_ok", True)
    invalid_gateways = o.get("invalid_gateways", [])
    if not gateway_ok or invalid_gateways:
        if invalid_gateways:
            for ig in invalid_gateways:
                fid = next_finding_id()
                host = ig.get("host", "PC1")
                configured_gw = ig.get("configured_gateway", "Unknown")
                reason = ig.get("reason", f"Configured gateway '{configured_gw}' is invalid")
                findings.append(DiagnosticFinding(
                    finding_id=fid,
                    root_cause="Incorrect default gateway",
                    evidence=f"IF host gateway is invalid, THEN report invalid gateway: {host} -> {configured_gw}. {reason}. Host cannot route off-subnet traffic.",
                    affected_components=[host, str(configured_gw)],
                    severity="HIGH",
                    confidence=0.98,  # 98% confidence: configuration audit directly confirms mismatch/unreachability
                    recommended_action=f"Reconfigure {host} default gateway to the valid local router interface (R1 / 192.168.1.1).",
                    network_impact=f"Host {host} is isolated from remote subnets due to invalid default gateway '{configured_gw}' ({reason}).",
                    endpoint_reachability="UNREACHABLE",
                    healthy_alternative_routes=healthy_cnt,
                    fault_category="Network Configuration",
                    finding_type="ROOT_CAUSE"
                ))
        else:
            fid = next_finding_id()
            configured_gw = o.get("gateway", "Unknown")
            findings.append(DiagnosticFinding(
                finding_id=fid,
                root_cause="Incorrect default gateway",
                evidence=f"IF host gateway is invalid, THEN report invalid gateway: PC1 -> {configured_gw}. Configured gateway '{configured_gw}' is invalid. Host cannot route off-subnet traffic.",
                affected_components=["PC1", str(configured_gw)],
                severity="HIGH",
                confidence=0.98,
                recommended_action="Reconfigure PC1 default gateway to the valid local router interface (R1 / 192.168.1.1).",
                network_impact=f"Host PC1 is unable to route traffic beyond its local broadcast domain due to invalid gateway '{configured_gw}'.",
                endpoint_reachability="UNREACHABLE",
                healthy_alternative_routes=healthy_cnt,
                fault_category="Network Configuration",
                finding_type="ROOT_CAUSE"
            ))

    # -------------------------------------------------------------------------
    # Rule 3: DNS Service Failure Diagnosis
    # IF IP connectivity is operational but DNS resolution fails,
    # THEN diagnose DNS failure. Distinguish IP connectivity from DNS failure.
    # -------------------------------------------------------------------------
    dns_ok = o.get("dns_ok", True)
    dns_resolution = o.get("dns_resolution", True)
    if not dns_ok or not dns_resolution:
        fid = next_finding_id()
        ip_reachable = reachability or bool(o.get("path"))
        if ip_reachable:
            evidence_str = "IF DNS availability is false, THEN report name-resolution failure. Telemetry confirms underlying IP network connectivity is operational, but DNS resolution probe failed."
            impact_str = "Name-to-IP resolution probe failed while raw IP connectivity remains operational. Applications using hostnames cannot resolve destinations."
        else:
            evidence_str = "IF DNS availability is false, THEN report name-resolution failure. DNS resolution probe failed; host cannot resolve destination hostnames."
            impact_str = "DNS service resolution is non-operational; host cannot resolve domain names."

        findings.append(DiagnosticFinding(
            finding_id=fid,
            root_cause="DNS service failure",
            evidence=evidence_str,
            affected_components=["DNS Service", "Resolver"],
            severity="HIGH",
            confidence=0.95,  # 95% confidence: probe failed while IP transport was independently tested
            recommended_action="Restart simulated DNS service and verify client resolver daemon.",
            network_impact=impact_str,
            endpoint_reachability="REACHABLE" if ip_reachable else "UNREACHABLE",
            healthy_alternative_routes=healthy_cnt,
            fault_category="Application Services",
            finding_type="ROOT_CAUSE"
        ))

    # -------------------------------------------------------------------------
    # Rule 4: High Latency Diagnosis
    # IF observed latency exceeds threshold, THEN identify affected link or path.
    # Evaluates every high-latency link independently.
    # -------------------------------------------------------------------------
    high_latency = o.get("high_latency", [])
    lat_thresh = latency_threshold or o.get("latency_threshold", 100.0)
    for link, ms in high_latency:
        fid = next_finding_id()
        severity = "HIGH" if ms >= 200 else "WARNING"
        better_routes = [r for r in routes if r.get("is_usable") and r.get("latency_ms", 999.0) < ms]
        if better_routes:
            impact_str = f"Transmission delay on {link} ({ms} ms) exceeds threshold ({lat_thresh} ms). {len(better_routes)} alternative route(s) offer lower latency."
            rec_str = f"Reroute latency-sensitive traffic away from degraded link {link} through lower-latency path."
        else:
            impact_str = f"Transmission delay on {link} ({ms} ms) exceeds threshold ({lat_thresh} ms). No lower-latency alternative path is available."
            rec_str = f"Degraded link {link} cannot be bypassed via rerouting; physical link optimization required."

        findings.append(DiagnosticFinding(
            finding_id=fid,
            root_cause="High latency",
            evidence=f"IF link latency exceeds {lat_thresh} ms, THEN report high latency: {link} = {ms} ms. Measured RTT introduces transmission delay and buffering.",
            affected_components=[link],
            severity=severity,
            confidence=0.90,  # 90% confidence: measured telemetry exceeds baseline threshold
            recommended_action=rec_str,
            network_impact=impact_str,
            endpoint_reachability="DEGRADED" if reachability else "UNREACHABLE",
            healthy_alternative_routes=len(better_routes),
            fault_category="Performance Degradation",
            finding_type="ROOT_CAUSE"
        ))

    # -------------------------------------------------------------------------
    # Rule 5: Packet Loss Diagnosis
    # IF observed packet loss exceeds threshold, THEN identify affected link.
    # Evaluates every lossy link independently.
    # -------------------------------------------------------------------------
    packet_loss = o.get("packet_loss", [])
    loss_thresh = loss_threshold if loss_threshold is not None else o.get("loss_threshold", 0.0)
    for link, pct in packet_loss:
        fid = next_finding_id()
        severity = "CRITICAL" if pct >= 30.0 else "HIGH"
        better_routes = [r for r in routes if r.get("is_usable") and r.get("max_loss", 100.0) < pct]
        if better_routes:
            impact_str = f"Packet loss on {link} ({pct}%) causes frame drops and TCP retransmissions. {len(better_routes)} alternative lossless path(s) available."
            rec_str = f"Reroute traffic away from lossy link {link} to lossless alternate routes."
        else:
            impact_str = f"Packet loss on {link} ({pct}%) causes frame drops. No alternative route with lower packet loss exists."
            rec_str = f"Degraded link {link} cannot be bypassed via rerouting; physical link maintenance required."

        findings.append(DiagnosticFinding(
            finding_id=fid,
            root_cause="Packet loss",
            evidence=f"IF link packet loss is above {loss_thresh}%, THEN report packet loss: {link} = {pct}%. Telemetry indicates excessive frame drops and retransmissions.",
            affected_components=[link],
            severity=severity,
            confidence=0.92,  # 92% confidence: statistical drop observed over probe window
            recommended_action=rec_str,
            network_impact=impact_str,
            endpoint_reachability="DEGRADED" if reachability else "UNREACHABLE",
            healthy_alternative_routes=len(better_routes),
            fault_category="Performance Degradation",
            finding_type="ROOT_CAUSE"
        ))

    # -------------------------------------------------------------------------
    # Secondary Symptom Analysis: Network Partitioning
    # If network is partitioned and isolates source/destination, correlate with root causes.
    # -------------------------------------------------------------------------
    if is_partitioned and partition_blocks_traffic:
        fid = next_finding_id()
        src = o.get("source", "Source")
        dst = o.get("target", "Destination")
        isolated_list = part_info.get("isolated_devices", [])
        isolated_text = f" Isolated nodes: {', '.join(isolated_list)}." if isolated_list else ""
        findings.append(DiagnosticFinding(
            finding_id=fid,
            root_cause="Network partition",
            evidence=f"Operational graph analysis detects {comp_cnt} disconnected segments. {src} and {dst} belong to different partitions.{isolated_text}",
            affected_components=part_info.get("contributing_failed_links", []),
            severity="CRITICAL",
            confidence=1.0,
            recommended_action="Execute coordinated multi-link recovery plan or alternative path activation to reconnect partitioned segments.",
            network_impact=f"Traffic between {src} and {dst} is completely blocked due to network partitioning caused by severed links.",
            endpoint_reachability="UNREACHABLE",
            healthy_alternative_routes=0,
            fault_category="Topology Connectivity",
            finding_type="SECONDARY_SYMPTOM",
            related_findings=link_finding_ids
        ))

    # -------------------------------------------------------------------------
    # Baseline Normal Operation (No Fault Detected)
    # -------------------------------------------------------------------------
    if not findings:
        fid = next_finding_id()
        findings.append(DiagnosticFinding(
            finding_id=fid,
            root_cause="No fault detected",
            evidence="IF all monitored conditions are normal, THEN report no fault detected. All physical links, gateway reachability, and DNS probes are healthy.",
            affected_components=[],
            severity="INFO",
            confidence=1.0,
            recommended_action="Maintain normal baseline monitoring.",
            network_impact="All monitored network interfaces, links, routing configurations, and services operate within nominal parameters.",
            endpoint_reachability="REACHABLE",
            healthy_alternative_routes=healthy_cnt,
            fault_category="Nominal Operation",
            finding_type="ROOT_CAUSE"
        ))

    return findings


def format_diagnosis_report(findings):
    """Format root-cause diagnostic findings into a clean, structured text report (Report B).
    
    Presents detected faults, unique finding IDs, supporting evidence, confidence,
    severity, impact, and recommendations.
    """
    total_findings = len(findings)
    critical_findings = sum(1 for f in findings if getattr(f, "severity", "HIGH") == "CRITICAL")
    
    def _is_baseline(f):
        rc = getattr(f, "root_cause", f[0] if isinstance(f, (list, tuple)) and len(f) > 0 else "")
        sev = getattr(f, "severity", "HIGH")
        return sev == "INFO" or rc == "No fault detected"

    root_causes = [
        f for f in findings
        if getattr(f, "finding_type", "ROOT_CAUSE") == "ROOT_CAUSE" and not _is_baseline(f)
    ]
    symptoms = [f for f in findings if getattr(f, "finding_type", "ROOT_CAUSE") == "SECONDARY_SYMPTOM"]

    lines = [
        "=== ROOT-CAUSE DIAGNOSIS REPORT ===",
        f"Total Diagnostic Findings : {total_findings}",
        f"Critical Findings         : {critical_findings}",
        f"Root Causes Identified    : {len(root_causes)}",
        f"Secondary Symptoms        : {len(symptoms)}\n"
    ]

    for f in findings:
        fid = getattr(f, "finding_id", "DIAG-0000")
        root_cause = getattr(f, "root_cause", f[0])
        evidence = getattr(f, "evidence", f[1])
        severity = getattr(f, "severity", "HIGH")
        conf = getattr(f, "confidence", 0.95)
        aff = getattr(f, "affected_components", [])
        rec_act = getattr(f, "recommended_action", "")
        impact = getattr(f, "network_impact", "")
        reach = getattr(f, "endpoint_reachability", "REACHABLE")
        alt_routes = getattr(f, "healthy_alternative_routes", 0)
        ftype = getattr(f, "finding_type", "ROOT_CAUSE")

        lines.append(f"[{fid}] {root_cause} [{severity} | Confidence: {conf:.0%} | Type: {ftype}]")
        if aff:
            lines.append(f"  • Affected Components : {', '.join(str(a) for a in aff)}")
        lines.append(f"  • Supporting Evidence : {evidence}")
        if impact:
            lines.append(f"  • Network Impact      : {impact}")
        lines.append(f"  • Reachability State  : {reach} ({alt_routes} healthy alternate route(s))")
        if rec_act:
            lines.append(f"  • Recommended Action  : {rec_act}")
        lines.append("")

    return "\n".join(lines).rstrip()


# Public alias
generate_diagnosis_report = format_diagnosis_report
