import sys
import unittest
from pathlib import Path
from typing import Any

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from app.report_mapper import build_edge_report_payload


class ReportMapperTests(unittest.TestCase):
    FORBIDDEN_FIELDS = {
        "pcap",
        "pcapbase64",
        "pcapbytes",
        "pcapfile",
        "rawpcap",
        "payload",
        "payloadbase64",
        "payloadbytes",
        "payloadhex",
        "rawpayload",
        "rawpayloadhex",
        "rawpacket",
        "rawpackets",
        "rawbytes",
        "flowtext",
        "packetbytes",
        "packethex",
        "applicationpayload",
        "fulll7content",
    }

    def _assert_no_forbidden_fields(self, obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                normalized = "".join(ch.lower() for ch in key if ch.isalnum())
                if normalized in self.FORBIDDEN_FIELDS:
                    self.fail(f"Forbidden field detected: {key}")
                self._assert_no_forbidden_fields(value)
        elif isinstance(obj, list):
            for item in obj:
                self._assert_no_forbidden_fields(item)

    def test_build_edge_report_payload_matches_current_central_contract(self):
        result = {
            "meta": {
                "task_id": "task-123",
                "timestamp": "2026-04-08T09:30:00+00:00",
                "agent_version": "1.0.0",
                "processing_time_ms": 812,
            },
            "statistics": {
                "total_packets": 128,
                "total_flows": 12,
                "normal_flows_dropped": 10,
                "anomaly_flows_detected": 2,
                "svm_filter_rate": "83.33%",
                "bandwidth_reduction": "81.4%",
            },
            "threats": [
                {
                    "id": "threat-001",
                    "five_tuple": {
                        "src_ip": "10.0.0.5",
                        "dst_ip": "8.8.8.8",
                        "src_port": 50123,
                        "dst_port": 443,
                        "protocol": "TCP",
                    },
                    "classification": {
                        "primary_label": "Botnet",
                        "secondary_label": "C2 Beaconing",
                        "confidence": "0.91",
                        "model": "Qwen3.5-0.8B",
                    },
                    "flow_metadata": {
                        "packet_count": 8,
                        "byte_count": 4120,
                    },
                    "token_info": {
                        "token_count": 128,
                        "truncated": True,
                    },
                }
            ],
            "metrics": {
                "original_pcap_size_bytes": 4096,
                "json_output_size_bytes": 762,
                "bandwidth_saved_percent": 81.4,
            },
        }

        payload = build_edge_report_payload(
            result=result,
            edge_id="edge1",
            max_time_window=60,
            max_packet_count=10,
            max_token_length=690,
        )

        self.assertEqual(payload["edge_id"], "edge1")
        self.assertEqual(payload["report_id"], "task-123")
        self.assertEqual(payload["source"], "edge-agent")
        self.assertEqual(payload["intel"]["schema_version"], "edge-intel/v1")
        self.assertEqual(payload["intel"]["summary"]["threat_count"], 2)
        self.assertEqual(payload["intel"]["summary"]["risk_level"], "medium")
        self.assertEqual(payload["intel"]["metrics"]["bandwidth_saved_percent"], 81.4)
        self.assertEqual(payload["intel"]["threats"][0]["threat_id"], "threat-001")
        self.assertEqual(payload["intel"]["threats"][0]["confidence"], 0.91)
        self.assertEqual(
            payload["intel"]["threats"][0]["evidence"]["edge_classification"]["primary_label"],
            "Botnet",
        )
        self.assertEqual(
            payload["intel"]["context"]["analysis_constraints"],
            {
                "max_time_window_s": 60,
                "max_packet_count": 10,
                "max_token_length": 690,
            },
        )
        self._assert_no_forbidden_fields(payload)
