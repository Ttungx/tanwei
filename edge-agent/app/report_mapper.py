from __future__ import annotations

from typing import Any


def _derive_risk_level(threat_count: int) -> str:
    if threat_count >= 3:
        return "high"
    if threat_count >= 1:
        return "medium"
    return "low"


def build_edge_report_payload(
    result: dict[str, Any],
    *,
    edge_id: str,
    max_time_window: int,
    max_packet_count: int,
    max_token_length: int,
) -> dict[str, Any]:
    meta = result.get("meta") or {}
    statistics = result.get("statistics") or {}
    metrics = result.get("metrics") or {}
    threats = result.get("threats") or []
    threat_count = int(statistics.get("anomaly_flows_detected", len(threats)) or 0)

    mapped_threats = []
    for threat in threats:
        classification = threat.get("classification") or {}
        primary_label = classification.get("primary_label") or "Unknown"
        secondary_label = classification.get("secondary_label")
        confidence = float(classification.get("confidence") or 0.0)
        mapped_threats.append(
            {
                "threat_id": threat.get("id"),
                "title": primary_label,
                "severity": "high" if confidence >= 0.9 else "medium" if confidence >= 0.7 else "low",
                "confidence": classification.get("confidence"),
                "category": secondary_label or primary_label,
                "summary": secondary_label or "Edge-detected suspicious flow",
                "evidence": {
                    "five_tuple": threat.get("five_tuple") or {},
                    "flow_metadata": threat.get("flow_metadata") or {},
                    "traffic_tokens": threat.get("token_info") or {},
                    "edge_classification": classification,
                },
            }
        )

    return {
        "edge_id": edge_id,
        "report_id": meta.get("task_id"),
        "source": "edge-agent",
        "reported_at": meta.get("timestamp"),
        "intel": {
            "schema_version": "edge-intel/v1",
            "summary": {
                "headline": f"{threat_count} threat(s) detected on {edge_id}",
                "risk_level": _derive_risk_level(threat_count),
                "threat_count": threat_count,
                "bandwidth_saved_percent": metrics.get("bandwidth_saved_percent", 0.0),
            },
            "threats": mapped_threats,
            "statistics": statistics,
            "metrics": metrics,
            "tags": ["edge-agent", "auto-report"],
            "context": {
                "task_id": meta.get("task_id"),
                "agent_version": meta.get("agent_version"),
                "processing_time_ms": meta.get("processing_time_ms"),
                "analysis_constraints": {
                    "max_time_window_s": max_time_window,
                    "max_packet_count": max_packet_count,
                    "max_token_length": max_token_length,
                },
            },
        },
    }
