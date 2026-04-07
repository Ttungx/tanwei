import importlib
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException


SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


def build_report(edge_id: str, report_id: str) -> dict:
    return {
        "schema_version": "v1",
        "report_id": report_id,
        "edge_id": edge_id,
        "producer": {
            "service": "edge-agent",
            "agent_version": "1.0.0",
            "reported_at": "2026-04-07T12:00:00Z",
        },
        "analysis_constraints": {
            "max_time_window_s": 60,
            "max_packet_count": 10,
            "max_token_length": 690,
        },
        "meta": {
            "site": "campus-core-a",
        },
        "statistics": {
            "total_flows": 12,
            "anomaly_flows_detected": 2,
        },
        "threats": [
            {
                "threat_id": "threat-001",
                "five_tuple": {
                    "src_ip": "10.0.0.10",
                    "dst_ip": "8.8.8.8",
                    "src_port": 50123,
                    "dst_port": 443,
                    "protocol": "TCP",
                },
                "svm_result": {
                    "label": "anomaly",
                    "confidence": 0.91,
                },
                "edge_classification": {
                    "primary_label": "Botnet",
                    "secondary_label": "C2 Beaconing",
                    "confidence": 0.88,
                    "model": "edge-llm",
                },
                "flow_metadata": {
                    "start_time": "2026-04-07T11:59:00Z",
                    "end_time": "2026-04-07T11:59:08Z",
                    "packet_count": 8,
                    "byte_count": 4120,
                    "avg_packet_size": 515.0,
                },
                "traffic_tokens": {
                    "encoding": "TrafficLLM",
                    "sequence": ["tok_184", "tok_033", "tok_912"],
                    "token_count": 128,
                    "truncated": True,
                },
            }
        ],
        "metrics": {
            "bandwidth_saved_percent": 78.5,
        },
    }


class ReportApiTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("app.main", None)
        self.module = importlib.import_module("app.main")
        self.module.reset_state()

    def test_ingest_report(self):
        payload = build_report("edge1", "report-001")
        body = self.module.ingest_report(self.module.EdgeIntelligenceReport(**payload))
        self.assertEqual(body["edge_id"], "edge1")
        self.assertEqual(body["report_id"], "report-001")

    def test_list_edges(self):
        self.module.ingest_report(self.module.EdgeIntelligenceReport(**build_report("edge1", "report-001")))
        self.module.ingest_report(self.module.EdgeIntelligenceReport(**build_report("edge2", "report-002")))
        body = self.module.list_edges()
        self.assertEqual(len(body["edges"]), 2)
        self.assertEqual(body["edges"][0]["edge_id"], "edge1")

    def test_latest_report(self):
        self.module.ingest_report(self.module.EdgeIntelligenceReport(**build_report("edge1", "report-001")))
        response = self.module.latest_edge_report("edge1")
        self.assertEqual(response["report_id"], "report-001")

    def test_rejects_raw_payload_fields(self):
        payload = build_report("edge1", "report-003")
        payload["threats"][0]["payload_hex"] = "deadbeef"
        with self.assertRaises(HTTPException) as exc:
            self.module.ingest_report(self.module.EdgeIntelligenceReport(**payload))
        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("forbidden", exc.exception.detail.lower())
