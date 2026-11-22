"""Independent Observation-Based Root-Cause Diagnosis Engine.
Uses explainable IF-THEN rules operating strictly on telemetry observations.
Does NOT access the graph object, injected fault labels, scenario metadata, or ground truth.
"""

class DiagnosticFinding(tuple):
    """Structured diagnostic finding with root cause, supporting evidence, affected components,
    severity, calibrated confidence, and recommended recovery action.
    
    Inherits from tuple (root_cause, evidence) to guarantee 100% backward compatibility
    with legacy code and test suites that unpack (name, why) or index finding[0] / finding[1].
    """
    def __new__(cls, root_cause, evidence, affected_components=None, severity="HIGH", confidence=0.95, recommended_action=""):
        obj = super().__new__(cls, (root_cause, evidence))
        obj.root_cause = root_cause
        obj.evidence = evidence
        obj.affected_components = affected_components if affected_components is not None else []
        obj.severity = severity
        obj.confidence = confidence
        obj.recommended_action = recommended_action
        return obj
        

    def to_dict(self):
        """Return dictionary representation of diagnostic finding."""
        return {
            "root_cause": self.root_cause,
            "evidence": self.evidence,
            "affected_components": self.affected_components,
            "severity": self.severity,
            "confidence": self.confidence,
            "recommended_action": self.recommended_action
        }

    def __repr__(self):
        return (f"DiagnosticFinding(root_cause='{self.root_cause}', severity='{self.severity}', "
                f"confidence={self.confidence:.0%}, affected={self.affected_components})")


def diagnose(o, latency_threshold=None, loss_threshold=None):
    """Diagnose network root causes strictly using observation evidence.
    
    Does NOT read injected scenario labels, GUI selections, or ground-truth variables.
    Supports multiple simultaneous findings.
    
    Parameters:
        o (dict): Structured observations from collect_observations().
        latency_threshold (float, optional): Custom latency threshold override in ms.
        loss_threshold (float, optional): Custom packet loss threshold override in %.
        
    Returns:
        list[DiagnosticFinding]: List of structured diagnostic findings.
    """
    findings = []

    # 1. Physical Link Failure Diagnosis
    down_links = o.get("down_links", [])
    if down_links:
        for link in down_links:
            findings.append(DiagnosticFinding(
                root_cause="Link failure",
                evidence=f"IF a link status is DOWN, THEN report link failure: {link}. Direct interface telemetry confirms the link is inactive and unable to forward frames.",
                affected_components=[link],
                severity="CRITICAL",
                confidence=1.0,  # 100% confidence justified: direct hardware status check proves link is DOWN
                recommended_action=f"Keep failed link {link} marked DOWN and reroute traffic over available alternate path(s)."
            ))

    # 2. Incorrect Default Gateway Diagnosis
    gateway_ok = o.get("gateway_ok", True)
    invalid_gateways = o.get("invalid_gateways", [])
    if not gateway_ok or invalid_gateways:
        host = invalid_gateways[0]["host"] if invalid_gateways else "PC1"
        configured_gw = invalid_gateways[0]["configured_gateway"] if invalid_gateways else o.get("gateway", "Unknown")
        reason = invalid_gateways[0]["reason"] if invalid_gateways else f"Configured gateway '{configured_gw}' is invalid"
        findings.append(DiagnosticFinding(
            root_cause="Incorrect default gateway",
            evidence=f"IF PC1 gateway is not R1, THEN report invalid gateway (observed {configured_gw}). {reason}. Host cannot route off-subnet traffic.",
            affected_components=[host, str(configured_gw)],
            severity="HIGH",
            confidence=0.98,  # 98% confidence: configuration audit directly identifies mismatch/unreachability
            recommended_action=f"Reconfigure {host} default gateway to the valid local router interface (R1 / 192.168.1.1)."
        ))

    # 3. DNS Service Failure Diagnosis
    dns_ok = o.get("dns_ok", True)
    dns_resolution = o.get("dns_resolution", True)
    if not dns_ok or not dns_resolution:
        # Distinguish IP connectivity from DNS failure
        ip_reachable = o.get("reachability", False) or bool(o.get("path"))
        if ip_reachable:
            evidence_str = "IF DNS availability is false, THEN report name-resolution failure. Telemetry confirms underlying IP network connectivity is operational, but DNS resolution probe failed."
        else:
            evidence_str = "IF DNS availability is false, THEN report name-resolution failure. DNS resolution probe failed; host cannot resolve destination hostnames."
        findings.append(DiagnosticFinding(
            root_cause="DNS service failure",
            evidence=evidence_str,
            affected_components=["DNS Service", "Resolver"],
            severity="HIGH",
            confidence=0.95,  # 95% confidence: probe failed while IP transport was independently tested
            recommended_action="Restart simulated DNS service and verify client resolver daemon."
        ))

    # 4. High Latency Diagnosis
    high_latency = o.get("high_latency", [])
    lat_thresh = latency_threshold or o.get("latency_threshold", 100.0)
    for link, ms in high_latency:
        severity = "HIGH" if ms >= 200 else "WARNING"
        findings.append(DiagnosticFinding(
            root_cause="High latency",
            evidence=f"IF link latency exceeds {lat_thresh} ms, THEN report high latency: {link} = {ms} ms. Measured RTT introduces transmission delay and buffering.",
            affected_components=[link],
            severity=severity,
            confidence=0.90,  # 90% confidence: measured telemetry exceeds baseline threshold
            recommended_action=f"Reroute latency-sensitive traffic away from degraded link {link} through lower-latency path."
        ))

    # 5. Packet Loss Diagnosis
    packet_loss = o.get("packet_loss", [])
    loss_thresh = loss_threshold if loss_threshold is not None else o.get("loss_threshold", 0.0)
    for link, pct in packet_loss:
        severity = "CRITICAL" if pct >= 30.0 else "HIGH"
        findings.append(DiagnosticFinding(
            root_cause="Packet loss",
            evidence=f"IF link packet loss is above {loss_thresh}%, THEN report packet loss: {link} = {pct}%. Telemetry indicates excessive frame drops and retransmissions.",
            affected_components=[link],
            severity=severity,
            confidence=0.92,  # 92% confidence: statistical drop observed over probe window
            recommended_action=f"Reroute traffic away from lossy link {link} to lossless alternate routes."
        ))

    # 6. Baseline Normal Operation (No Fault Detected)
    if not findings:
        findings.append(DiagnosticFinding(
            root_cause="No fault detected",
            evidence="IF all monitored conditions are normal, THEN report no fault detected. All physical links, gateway reachability, and DNS probes are healthy.",
            affected_components=[],
            severity="INFO",
            confidence=1.0,
            recommended_action="Maintain normal baseline monitoring."
        ))

    return findings
