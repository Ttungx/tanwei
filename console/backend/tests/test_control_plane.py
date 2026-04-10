import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


with patch("pathlib.Path.mkdir", return_value=None):
    main = importlib.import_module("app.main")
    central_client = importlib.import_module("app.central_client")


class ControlPlaneApiTests(unittest.TestCase):
    def test_get_edges_proxies_control_plane_inventory(self):
        async def run_test():
            payload = [
                {
                    "edge_id": "edge1",
                    "display_name": "Edge 1",
                    "status": "online",
                    "location": "Lab A",
                    "last_reported_at": "2026-04-07T08:00:00Z",
                    "threat_count": 2,
                    "risk_level": "high",
                }
            ]

            with patch.object(main.central_agent_client, "list_edges", return_value=payload):
                response = await main.get_edges()

            self.assertEqual(response, payload)

        import asyncio

        asyncio.run(run_test())

    def test_get_latest_edge_report_returns_selected_edge_intel(self):
        async def run_test():
            payload = {
                "edge_id": "edge1",
                "report_id": "edge1-report-001",
                "generated_at": "2026-04-07T08:00:00Z",
                "summary": {
                    "headline": "2 threats detected",
                    "risk_level": "high",
                    "threat_count": 2,
                    "bandwidth_saved_percent": 81.4,
                },
                "report": {
                    "meta": {
                        "task_id": "edge1-task-1",
                        "timestamp": "2026-04-07T08:00:00Z",
                        "agent_version": "edge-agent-v1",
                        "processing_time_ms": 1420,
                    },
                    "statistics": {
                        "total_packets": 128,
                        "total_flows": 12,
                        "normal_flows_dropped": 10,
                        "anomaly_flows_detected": 2,
                        "svm_filter_rate": "83.33%",
                        "bandwidth_reduction": "81.4%",
                    },
                    "threats": [],
                    "metrics": {
                        "original_pcap_size_bytes": 4096,
                        "json_output_size_bytes": 762,
                        "bandwidth_saved_percent": 81.4,
                    },
                },
            }

            with patch.object(main.central_agent_client, "get_latest_report", return_value=payload):
                response = await main.get_latest_edge_report("edge1")

            self.assertEqual(response["edge_id"], "edge1")
            self.assertEqual(response["summary"]["risk_level"], "high")

        import asyncio

        asyncio.run(run_test())

    def test_get_edge_reports_returns_history_for_selected_edge(self):
        async def run_test():
            payload = [
                {
                    "edge_id": "edge1",
                    "report_id": "edge1-report-001",
                    "generated_at": "2026-04-07T08:00:00Z",
                    "summary": {
                        "headline": "2 threats detected",
                        "risk_level": "high",
                        "threat_count": 2,
                        "bandwidth_saved_percent": 81.4,
                    },
                    "report": {
                        "meta": {
                            "task_id": "edge1-task-1",
                            "timestamp": "2026-04-07T08:00:00Z",
                            "agent_version": "edge-agent-v1",
                            "processing_time_ms": 1420,
                        },
                        "statistics": {
                            "total_packets": 128,
                            "total_flows": 12,
                            "normal_flows_dropped": 10,
                            "anomaly_flows_detected": 2,
                            "svm_filter_rate": "83.33%",
                            "bandwidth_reduction": "81.4%",
                        },
                        "threats": [],
                        "metrics": {
                            "original_pcap_size_bytes": 4096,
                            "json_output_size_bytes": 762,
                            "bandwidth_saved_percent": 81.4,
                        },
                    },
                }
            ]

            with patch.object(main.central_agent_client, "list_edge_reports", return_value=payload):
                response = await main.get_edge_reports("edge1")

            self.assertEqual(len(response), 1)
            self.assertEqual(response[0]["report_id"], "edge1-report-001")

        import asyncio

        asyncio.run(run_test())

    def test_post_network_analyze_returns_central_analysis(self):
        async def run_test():
            payload = {
                "analysis_id": "network-analysis-001",
                "generated_at": "2026-04-07T09:00:00Z",
                "summary": {
                    "edge_count": 2,
                    "edges_with_alerts": 1,
                    "total_threats": 3,
                    "highest_risk_edge": "edge2",
                    "recommended_action": "Escalate edge2 for review",
                },
                "edges": [
                    {
                        "edge_id": "edge1",
                        "display_name": "Edge 1",
                        "threat_count": 0,
                        "risk_level": "low",
                        "generated_at": "2026-04-07T08:55:00Z",
                    },
                    {
                        "edge_id": "edge2",
                        "display_name": "Edge 2",
                        "threat_count": 3,
                        "risk_level": "high",
                        "generated_at": "2026-04-07T08:58:00Z",
                    },
                ],
            }

            with patch.object(main.central_agent_client, "analyze_network", return_value=payload):
                response = await main.analyze_network()

            self.assertEqual(response["summary"]["highest_risk_edge"], "edge2")

        import asyncio

        asyncio.run(run_test())


class CentralArchiveMappingTests(unittest.TestCase):
    def test_build_detection_result_from_archive_preserves_central_reporting_meta(self):
        payload = {
            "edge_id": "edge1",
            "report_id": "edge1-report-001",
            "reported_at": "2026-04-07T08:00:00Z",
            "report": {
                "meta": {
                    "central_reporting": {
                        "status": "uploaded",
                        "central_url": "http://central-agent:8003",
                        "central_report_id": "edge1-report-001",
                    }
                },
                "statistics": {
                    "total_packets": 128,
                    "total_flows": 12,
                    "anomaly_flows_detected": 2,
                },
                "metrics": {
                    "bandwidth_saved_percent": 81.4,
                },
                "threats": [],
            },
        }

        result = central_client.build_detection_result_from_archive(payload)

        self.assertEqual(result["meta"]["central_reporting"]["status"], "uploaded")
        self.assertEqual(
            result["meta"]["central_reporting"]["central_report_id"],
            "edge1-report-001",
        )
