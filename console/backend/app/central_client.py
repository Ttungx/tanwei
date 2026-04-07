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
            return self._get("/api/edges")
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for edge inventory, using fallback data: %s", exc)
            return build_mock_edges()

    def get_latest_report(self, edge_id: str) -> Dict[str, Any]:
        try:
            return self._get(f"/api/edges/{edge_id}/reports/latest")
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for latest report of %s, using fallback data: %s", edge_id, exc)
            return build_mock_latest_report(edge_id)

    def analyze_edge(self, edge_id: str) -> Dict[str, Any]:
        try:
            return self._post(f"/api/edges/{edge_id}/analyze")
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for edge analysis of %s, using fallback data: %s", edge_id, exc)
            return build_mock_latest_report(edge_id, triggered=True)

    def analyze_network(self) -> Dict[str, Any]:
        try:
            return self._post("/api/network/analyze")
        except requests.RequestException as exc:
            self.logger.warning("central-agent unavailable for network analysis, using fallback data: %s", exc)
            return build_mock_network_analysis()


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
