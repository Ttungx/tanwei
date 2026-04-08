import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


def build_report_payload(edge_id: str, report_id: str) -> dict:
    return {
        "edge_id": edge_id,
        "report_id": report_id,
        "source": "edge-agent",
        "intel": {
            "summary": {"headline": "Suspicious traffic detected"},
            "threats": [
                {
                    "threat_id": "threat-001",
                    "title": "Beaconing pattern",
                    "severity": "high",
                    "confidence": 0.91,
                    "category": "c2",
                    "summary": "Periodic outbound callbacks observed",
                    "evidence": {
                        "five_tuple": {
                            "src_ip": "10.0.0.5",
                            "dst_ip": "8.8.8.8",
                            "src_port": 50123,
                            "dst_port": 443,
                            "protocol": "TCP",
                        }
                    },
                }
            ],
            "statistics": {"total_flows": 12, "anomaly_flows_detected": 1},
            "metrics": {"bandwidth_saved_percent": 78.5},
            "tags": ["lab"],
            "context": {"site": "rack-a"},
        },
    }


class CentralAgentApiTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "central-agent.db"
        os.environ["CENTRAL_AGENT_DB_PATH"] = str(self.db_path)
        sys.modules.pop("app.main", None)
        self.main = importlib.import_module("app.main")
        self.main.store = self.main.ReportStore(str(self.db_path))

        import asyncio

        asyncio.run(self.main.startup_event())

    def tearDown(self):
        sys.modules.pop("app.main", None)
        os.environ.pop("CENTRAL_AGENT_DB_PATH", None)
        self.tmpdir.cleanup()

    def test_create_report_and_query_latest_report(self):
        async def run_test():
            payload = build_report_payload("edge1", "report-001")
            created = await self.main.create_report(self.main.EdgeReportIn(**payload))
            latest = await self.main.latest_edge_report("edge1")
            edges = await self.main.list_edges()

            self.assertEqual(created.status, "stored")
            self.assertEqual(created.edge_id, "edge1")
            self.assertEqual(latest.edge_id, "edge1")
            self.assertEqual(latest.report_id, "report-001")
            self.assertEqual(edges.edges[0].edge_id, "edge1")
            self.assertEqual(edges.edges[0].report_count, 1)

        import asyncio

        asyncio.run(run_test())

    def test_create_report_rejects_raw_payload_like_fields(self):
        payload = build_report_payload("edge1", "report-raw")
        payload["intel"]["context"]["payload_hex"] = "deadbeef"

        with self.assertRaises(ValueError):
            self.main.EdgeReportIn(**payload)

    def test_analyze_edge_and_network_use_llm_client_with_archived_reports(self):
        async def run_test():
            await self.main.create_report(
                self.main.EdgeReportIn(**build_report_payload("edge1", "report-001"))
            )
            await self.main.create_report(
                self.main.EdgeReportIn(**build_report_payload("edge2", "report-002"))
            )

            self.main.llm_client.analyze = AsyncMock(
                side_effect=[
                    {
                        "provider_response_id": "resp-edge",
                        "model": "mock-edge-model",
                        "analysis": {
                            "summary": "edge summary",
                            "findings": ["beaconing"],
                            "recommended_actions": ["investigate edge1"],
                            "confidence_notes": "high confidence",
                        },
                    },
                    {
                        "provider_response_id": "resp-network",
                        "model": "mock-network-model",
                        "analysis": {
                            "summary": "network summary",
                            "findings": ["cross-edge pattern"],
                            "recommended_actions": ["contain affected edges"],
                            "confidence_notes": "moderate confidence",
                        },
                    },
                ]
            )

            edge_analysis = await self.main.analyze_edge(
                "edge1",
                self.main.EdgeAnalyzeRequest(),
            )
            network_analysis = await self.main.analyze_network(
                self.main.NetworkAnalyzeRequest(),
            )

            self.assertEqual(edge_analysis.scope, "edge")
            self.assertEqual(edge_analysis.edge_id, "edge1")
            self.assertEqual(edge_analysis.analyzed_report_count, 1)
            self.assertEqual(network_analysis.scope, "network")
            self.assertEqual(sorted(network_analysis.edge_ids), ["edge1", "edge2"])
            self.assertEqual(network_analysis.analyzed_report_count, 2)
            self.assertEqual(self.main.llm_client.analyze.await_count, 2)

        import asyncio

        asyncio.run(run_test())
