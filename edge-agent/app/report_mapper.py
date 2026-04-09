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
    statistics = dict(result.get("statistics") or {})
    metrics = dict(result.get("metrics") or {})
    threats = result.get("threats") or []
    threat_count = int(statistics.get("anomaly_flows_detected", len(threats)) or 0)

    mapped_threats = []
    for threat in threats:
        classification = dict(threat.get("classification") or {})
        primary_label = classification.get("primary_label") or "Unknown"
        secondary_label = classification.get("secondary_label")
        raw_confidence = classification.get("confidence")
        normalized_confidence = None
        if raw_confidence not in (None, ""):
            try:
                normalized_confidence = float(raw_confidence)
            except (TypeError, ValueError):
                normalized_confidence = None
        confidence = normalized_confidence or 0.0
        five_tuple = dict(threat.get("five_tuple") or {})
        flow_metadata = dict(threat.get("flow_metadata") or {})
        token_info = dict(threat.get("token_info") or {})
        mapped_threats.append(
            {
                "threat_id": threat.get("id"),
                "title": primary_label,
                "severity": "high" if confidence >= 0.9 else "medium" if confidence >= 0.7 else "low",
                "confidence": normalized_confidence,
                "category": secondary_label or primary_label,
                "summary": secondary_label or "Edge-detected suspicious flow",
                "evidence": {
                    "five_tuple": five_tuple,
                    "flow_metadata": flow_metadata,
                    "traffic_tokens": token_info,
                    "edge_classification": dict(classification),
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
            },
            "threats": mapped_threats,
            "statistics": statistics,
            "metrics": metrics,
            "context": {
                "analysis_constraints": {
                    "max_time_window_s": max_time_window,
                    "max_packet_count": max_packet_count,
                    "max_token_length": max_token_length,
                },
            },
        },
    }
