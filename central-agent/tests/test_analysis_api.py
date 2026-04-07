import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from test_reports_api import build_report


SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))


class AnalysisApiTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("app.main", None)
        self.module = importlib.import_module("app.main")
        self.module.reset_state()
        self.module.ingest_report(self.module.EdgeIntelligenceReport(**build_report("edge1", "report-001")))
        self.module.ingest_report(self.module.EdgeIntelligenceReport(**build_report("edge2", "report-002")))

    @patch("app.main.reasoner.analyze_single_edge")
    def test_single_edge_analysis(self, mock_analyze):
        mock_analyze.return_value = {
            "mode": "single-edge",
            "edge_id": "edge1",
            "threat_level": "high",
            "summary": "edge1 has recurring beaconing",
            "analysis": "suspicious outbound periodicity detected",
            "recommendations": ["isolate host", "check DNS and proxy logs"],
        }
        body = self.module.analyze_single_edge("edge1")
        self.assertEqual(body["mode"], "single-edge")
        self.assertEqual(body["edge_id"], "edge1")

    @patch("app.main.reasoner.analyze_network")
    def test_network_analysis(self, mock_analyze):
        mock_analyze.return_value = {
            "mode": "network-wide",
            "edge_count": 2,
            "threat_level": "critical",
            "summary": "multi-edge beaconing cluster detected",
            "analysis": "edge1 and edge2 share overlapping outbound indicators",
            "recommendations": ["segment affected VLAN", "review egress policy"],
        }
        body = self.module.analyze_network()
        self.assertEqual(body["mode"], "network-wide")
        self.assertEqual(body["edge_count"], 2)

    @patch("app.main.reasoner.analyze_single_edge")
    def test_latest_single_edge_analysis(self, mock_analyze):
        mock_analyze.return_value = {
            "mode": "single-edge",
            "edge_id": "edge1",
            "threat_level": "medium",
            "summary": "edge1 shows intermittent suspicious traffic",
            "analysis": "anomaly score remains elevated over baseline",
            "recommendations": ["increase telemetry retention"],
        }
        self.module.analyze_single_edge("edge1")
        body = self.module.latest_single_edge_analysis("edge1")
        self.assertEqual(body["mode"], "single-edge")
        self.assertEqual(body["analysis_state"], "completed")

    @patch("app.main.reasoner.analyze_network")
    def test_latest_network_analysis(self, mock_analyze):
        mock_analyze.return_value = {
            "mode": "network-wide",
            "edge_count": 2,
            "threat_level": "high",
            "summary": "correlated anomalies across multiple edges",
            "analysis": "overlapping indicators persist in latest window",
            "recommendations": ["escalate incident response"],
        }
        self.module.analyze_network()
        body = self.module.latest_network_analysis()
        self.assertEqual(body["mode"], "network-wide")
        self.assertEqual(body["analysis_state"], "completed")
