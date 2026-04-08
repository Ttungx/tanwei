import logging
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class CentralAgentClient:
    def __init__(self, base_url: str, logger: logging.Logger):
        self.base_url = base_url.rstrip("/")
        self.logger = logger

    def _get(self, path: str) -> Any:
        response = requests.get(f"{self.base_url}{path}", timeout=30)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: Dict[str, Any] | None = None) -> Any:
        response = requests.post(f"{self.base_url}{path}", json=payload or {}, timeout=120)
        response.raise_for_status()
        return response.json()

    def list_edges(self) -> List[Dict[str, Any]]:
        try:
            payload = self._get("/api/v1/edges")
            edges = payload.get("edges", []) if isinstance(payload, dict) else payload
            normalized_edges: List[Dict[str, Any]] = []

            for edge in edges:
                edge_id = str(edge.get("edge_id", "")).strip()
                if not edge_id:
                    continue

                latest_report: Dict[str, Any] | None = None
                try:
                    latest_report = self._get(f"/api/v1/edges/{edge_id}/reports/latest")
                except requests.RequestException as exc:
                    self.logger.warning(
                        "central-agent missing latest report for %s, using archive summary only: %s",
                        edge_id,
                        exc,
                    )

                if latest_report:
                    latest_view = build_edge_latest_report(latest_report)
                    normalized_edges.append(
                        {
                            "edge_id": edge_id,
                            "display_name": build_display_name(edge_id),
                            "status": "online",
                            "location": "Central Archive",
                            "last_reported_at": latest_view["generated_at"],
                            "threat_count": latest_view["summary"]["threat_count"],
                            "risk_level": latest_view["summary"]["risk_level"],
                        }
                    )
                    continue

                normalized_edges.append(
                    {
                        "edge_id": edge_id,
                        "display_name": build_display_name(edge_id),
                        "status": "online",
                        "location": "Central Archive",
                        "last_reported_at": edge.get("latest_reported_at")
                        or edge.get("latest_received_at")
                        or utc_now_iso(),
                        "threat_count": 0,
                        "risk_level": "unknown",
                    }
                )

            return normalized_edges
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for edge inventory, using fallback data: %s", exc)
            return build_mock_edges()

    def get_latest_report(self, edge_id: str) -> Dict[str, Any]:
        try:
            payload = self._get(f"/api/v1/edges/{edge_id}/reports/latest")
            return build_edge_latest_report(payload)
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for latest report of %s, using fallback data: %s", edge_id, exc)
            return build_mock_latest_report(edge_id)

    def analyze_edge(self, edge_id: str) -> Dict[str, Any]:
        try:
            analysis = self._post(f"/api/v1/edges/{edge_id}/analyze")
            latest_report = self._get(f"/api/v1/edges/{edge_id}/reports/latest")
            headline = extract_analysis_summary(analysis)
            return build_edge_latest_report(latest_report, headline_override=headline)
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for edge analysis of %s, using fallback data: %s", edge_id, exc)
            return build_mock_latest_report(edge_id, triggered=True)

    def analyze_network(self) -> Dict[str, Any]:
        try:
            analysis = self._post("/api/v1/network/analyze")
            edge_inventory = self._get("/api/v1/edges")
            edge_rows = (
                edge_inventory.get("edges", [])
                if isinstance(edge_inventory, dict)
                else edge_inventory
            )

            requested_edge_ids = analysis.get("edge_ids") if isinstance(analysis, dict) else []
            selected_edge_ids = {
                str(edge_id).strip() for edge_id in requested_edge_ids if str(edge_id).strip()
            }

            edges: List[Dict[str, Any]] = []
            for edge in edge_rows:
                edge_id = str(edge.get("edge_id", "")).strip()
                if not edge_id:
                    continue
                if selected_edge_ids and edge_id not in selected_edge_ids:
                    continue

                try:
                    latest_report = self._get(f"/api/v1/edges/{edge_id}/reports/latest")
                except requests.RequestException as exc:
                    self.logger.warning(
                        "central-agent missing latest report during network analysis for %s: %s",
                        edge_id,
                        exc,
                    )
                    continue

                latest_view = build_edge_latest_report(latest_report)
                edges.append(
                    {
                        "edge_id": edge_id,
                        "display_name": build_display_name(edge_id),
                        "threat_count": latest_view["summary"]["threat_count"],
                        "risk_level": latest_view["summary"]["risk_level"],
                        "generated_at": latest_view["generated_at"],
                    }
                )

            if not edges:
                return build_mock_network_analysis()

            highest_risk = max(
                edges,
                key=lambda item: (item["threat_count"], item["risk_level"]),
            )
            recommended_actions = []
            if isinstance(analysis, dict):
                analysis_block = analysis.get("analysis", {})
                if isinstance(analysis_block, dict):
                    recommended_actions = analysis_block.get("recommended_actions") or []

            return {
                "analysis_id": analysis.get("analysis_id", "network-analysis"),
                "generated_at": utc_now_iso(),
                "summary": {
                    "edge_count": len(edges),
                    "edges_with_alerts": sum(1 for item in edges if item["threat_count"] > 0),
                    "total_threats": sum(item["threat_count"] for item in edges),
                    "highest_risk_edge": highest_risk["edge_id"],
                    "recommended_action": (
                        str(recommended_actions[0])
                        if recommended_actions
                        else f"Review {highest_risk['edge_id']} via central-agent"
                    ),
                },
                "edges": edges,
            }
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for network analysis, using fallback data: %s", exc)
            return build_mock_network_analysis()


def build_display_name(edge_id: str) -> str:
    return edge_id.replace("_", " ").replace("-", " ").strip().title()


def extract_analysis_summary(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    analysis = payload.get("analysis")
    if isinstance(analysis, dict):
        summary = analysis.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()

    return None


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def derive_risk_level(threat_count: int, explicit_level: Any = None) -> str:
    if isinstance(explicit_level, str) and explicit_level.strip():
        return explicit_level.strip().lower()
    if threat_count >= 3:
        return "high"
    if threat_count >= 1:
        return "medium"
    return "low"


def build_detection_result_from_archive(report_envelope: Dict[str, Any]) -> Dict[str, Any]:
    report = clone_payload(report_envelope.get("report") or {})
    threats = report.get("threats") or []
    mapped_threats = []

    for index, threat in enumerate(threats, start=1):
        evidence = threat.get("evidence") or {}
        flow_metadata = evidence.get("flow_metadata") or threat.get("flow_metadata") or {}
        token_info = evidence.get("traffic_tokens") or threat.get("traffic_tokens") or {}
        edge_classification = threat.get("edge_classification") or {}
        svm_result = threat.get("svm_result") or {}
        primary_label = (
            edge_classification.get("primary_label")
            or threat.get("category")
            or threat.get("title")
            or "Unknown"
        )
        secondary_label = (
            edge_classification.get("secondary_label")
            or threat.get("summary")
            or threat.get("severity")
            or ""
        )

        mapped_threats.append(
            {
                "id": threat.get("threat_id") or threat.get("id") or f"{report_envelope.get('edge_id', 'edge')}-threat-{index:03d}",
                "five_tuple": evidence.get("five_tuple") or threat.get("five_tuple") or {},
                "classification": {
                    "primary_label": str(primary_label),
                    "secondary_label": str(secondary_label),
                    "confidence": coerce_float(
                        edge_classification.get("confidence")
                        or svm_result.get("confidence")
                        or threat.get("confidence")
                    ),
                    "model": str(
                        edge_classification.get("model")
                        or report.get("context", {}).get("model_version")
                        or report_envelope.get("source")
                        or "central-agent-archive"
                    ),
                },
                "flow_metadata": {
                    "start_time": flow_metadata.get("start_time") or report_envelope.get("reported_at") or utc_now_iso(),
                    "end_time": flow_metadata.get("end_time") or report_envelope.get("reported_at") or utc_now_iso(),
                    "packet_count": coerce_int(flow_metadata.get("packet_count")),
                    "byte_count": coerce_int(flow_metadata.get("byte_count")),
                    "avg_packet_size": coerce_float(flow_metadata.get("avg_packet_size")),
                },
                "token_info": {
                    "token_count": coerce_int(token_info.get("token_count")),
                    "truncated": bool(token_info.get("truncated", False)),
                },
            }
        )

    statistics = report.get("statistics") or {}
    metrics = report.get("metrics") or {}
    anomaly_flows = coerce_int(
        statistics.get("anomaly_flows_detected"),
        default=len(mapped_threats),
    )
    total_flows = coerce_int(statistics.get("total_flows"), default=max(anomaly_flows, 0))
    bandwidth_saved_percent = coerce_float(metrics.get("bandwidth_saved_percent"))
    processing_time_ms = coerce_int(metrics.get("processing_time_ms"))

    return {
        "meta": {
            "task_id": report_envelope.get("report_id") or "central-archive",
            "timestamp": report_envelope.get("reported_at") or report_envelope.get("received_at") or utc_now_iso(),
            "agent_version": str(
                report.get("context", {}).get("model_version")
                or report_envelope.get("source")
                or "central-agent-archive"
            ),
            "processing_time_ms": processing_time_ms,
        },
        "statistics": {
            "total_packets": coerce_int(statistics.get("total_packets")),
            "total_flows": total_flows,
            "normal_flows_dropped": max(total_flows - anomaly_flows, 0),
            "anomaly_flows_detected": anomaly_flows,
            "svm_filter_rate": str(
                statistics.get("svm_filter_rate")
                or (f"{((max(total_flows - anomaly_flows, 0) / total_flows) * 100):.1f}%" if total_flows else "0.0%")
            ),
            "bandwidth_reduction": str(
                statistics.get("bandwidth_reduction") or f"{bandwidth_saved_percent:.1f}%"
            ),
        },
        "threats": mapped_threats,
        "metrics": {
            "original_pcap_size_bytes": coerce_int(metrics.get("original_pcap_size_bytes")),
            "json_output_size_bytes": coerce_int(metrics.get("json_output_size_bytes")),
            "bandwidth_saved_percent": bandwidth_saved_percent,
        },
    }


def build_edge_latest_report(
    report_envelope: Dict[str, Any],
    headline_override: str | None = None,
) -> Dict[str, Any]:
    detection_result = build_detection_result_from_archive(report_envelope)
    report = report_envelope.get("report") or {}
    summary = report.get("summary") or {}
    threat_count = detection_result["statistics"]["anomaly_flows_detected"]

    return {
        "edge_id": report_envelope.get("edge_id"),
        "report_id": report_envelope.get("report_id"),
        "generated_at": report_envelope.get("reported_at") or report_envelope.get("received_at") or utc_now_iso(),
        "summary": {
            "headline": headline_override
            or summary.get("headline")
            or f"{threat_count} threats detected on {report_envelope.get('edge_id')}",
            "risk_level": derive_risk_level(threat_count, summary.get("risk_level")),
            "threat_count": threat_count,
            "bandwidth_saved_percent": detection_result["metrics"]["bandwidth_saved_percent"],
        },
        "report": detection_result,
    }


def build_mock_edges() -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return [
        {
            "edge_id": "edge1",
            "display_name": "Edge 1",
            "status": "online",
            "location": "Singapore Rack A",
            "last_reported_at": now.isoformat().replace("+00:00", "Z"),
            "threat_count": 2,
            "risk_level": "high",
        },
        {
            "edge_id": "edge2",
            "display_name": "Edge 2",
            "status": "online",
            "location": "Singapore Rack B",
            "last_reported_at": (now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
            "threat_count": 0,
            "risk_level": "low",
        },
    ]


def build_mock_detection_result(edge_id: str, triggered: bool = False) -> Dict[str, Any]:
    is_primary = edge_id == "edge1"
    now_iso = utc_now_iso()
    threat_count = 1 if triggered else (2 if is_primary else 0)
    total_flows = 96 if is_primary else 64
    dropped_flows = total_flows - threat_count
    bandwidth_saved_percent = 81.3 if triggered else (87.5 if is_primary else 93.4)

    threats = []
    if threat_count > 0:
        threats = [
            {
                "id": f"{edge_id}-threat-001",
                "five_tuple": {
                    "src_ip": "10.0.0.1" if is_primary else "10.0.0.9",
                    "src_port": 443,
                    "dst_ip": "10.0.0.8" if is_primary else "10.0.0.22",
                    "dst_port": 58000 if is_primary else 49152,
                    "protocol": "TCP",
                },
                "classification": {
                    "primary_label": "C2",
                    "secondary_label": "Beaconing" if is_primary else "Suspicious",
                    "confidence": 0.92 if is_primary else 0.81,
                    "model": "edge-agent-v1",
                },
                "flow_metadata": {
                    "start_time": now_iso,
                    "end_time": now_iso,
                    "packet_count": 12,
                    "byte_count": 2048,
                    "avg_packet_size": 170.6,
                },
                "token_info": {
                    "token_count": 88,
                    "truncated": False,
                },
            }
        ]

    return {
        "meta": {
            "task_id": f"{edge_id}-task-refresh" if triggered else f"{edge_id}-task-latest",
            "timestamp": now_iso,
            "agent_version": "edge-agent-v1",
            "processing_time_ms": 3100 if triggered else 4200,
        },
        "statistics": {
            "total_packets": total_flows * 32,
            "total_flows": total_flows,
            "normal_flows_dropped": dropped_flows,
            "anomaly_flows_detected": threat_count,
            "svm_filter_rate": f"{(dropped_flows / total_flows) * 100:.1f}%",
            "bandwidth_reduction": f"{bandwidth_saved_percent:.1f}%",
        },
        "threats": threats,
        "metrics": {
            "original_pcap_size_bytes": total_flows * 32768,
            "json_output_size_bytes": int(total_flows * 32768 * (1 - bandwidth_saved_percent / 100)),
            "bandwidth_saved_percent": bandwidth_saved_percent,
        },
    }


def build_mock_latest_report(edge_id: str, triggered: bool = False) -> Dict[str, Any]:
    edge = next((item for item in build_mock_edges() if item["edge_id"] == edge_id), None)
    if edge is None:
        edge = {
            "edge_id": edge_id,
            "display_name": edge_id.upper(),
            "status": "unknown",
            "location": "Unregistered",
            "last_reported_at": utc_now_iso(),
            "threat_count": 0,
            "risk_level": "unknown",
        }

    report = build_mock_detection_result(edge_id, triggered=triggered)
    generated_at = report["meta"]["timestamp"]
    threat_count = report["statistics"]["anomaly_flows_detected"]
    risk_level = "medium" if triggered and threat_count > 0 else edge["risk_level"]

    return {
        "edge_id": edge_id,
        "report_id": f"{edge_id}-report-refresh" if triggered else f"{edge_id}-report-latest",
        "generated_at": generated_at,
        "summary": {
            "headline": (
                f"manual analysis finished for {edge_id}"
                if triggered
                else f"{threat_count} threats detected on {edge_id}"
            ),
            "risk_level": risk_level,
            "threat_count": threat_count,
            "bandwidth_saved_percent": report["metrics"]["bandwidth_saved_percent"],
        },
        "report": report,
    }


def build_mock_network_analysis() -> Dict[str, Any]:
    edges = build_mock_edges()
    latest_reports = [build_mock_latest_report(edge["edge_id"]) for edge in edges]
    highest_risk = max(latest_reports, key=lambda item: item["summary"]["threat_count"])
    now_iso = utc_now_iso()

    return {
        "analysis_id": "network-analysis-fallback",
        "generated_at": now_iso,
        "summary": {
            "edge_count": len(edges),
            "edges_with_alerts": sum(1 for item in latest_reports if item["summary"]["threat_count"] > 0),
            "total_threats": sum(item["summary"]["threat_count"] for item in latest_reports),
            "highest_risk_edge": highest_risk["edge_id"],
            "recommended_action": f"Escalate {highest_risk['edge_id']} for human review",
        },
        "edges": [
            {
                "edge_id": edge["edge_id"],
                "display_name": edge["display_name"],
                "threat_count": report["summary"]["threat_count"],
                "risk_level": report["summary"]["risk_level"],
                "generated_at": report["generated_at"],
            }
            for edge, report in zip(edges, latest_reports)
        ],
    }


def clone_payload(payload: Any) -> Any:
    return deepcopy(payload)
