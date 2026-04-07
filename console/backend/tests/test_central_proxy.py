import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class CentralProxyTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("app.main", None)
        with patch("pathlib.Path.mkdir", return_value=None):
            self.module = importlib.import_module("app.main")

    @patch("app.central_client.list_edges", return_value={"edges": [{"edge_id": "edge1"}]})
    def test_list_edges_proxy(self, _mock_list):
        response = self.module.get_edges()
        self.assertEqual(response["edges"][0]["edge_id"], "edge1")

    @patch(
        "app.central_client.get_latest_report",
        return_value={"edge_id": "edge1", "report_id": "report-001"},
    )
    def test_latest_report_proxy(self, _mock_latest):
        response = self.module.get_latest_edge_report("edge1")
        self.assertEqual(response["report_id"], "report-001")

    @patch(
        "app.central_client.analyze_edge",
        return_value={"mode": "single-edge", "edge_id": "edge1", "threat_level": "high"},
    )
    def test_single_edge_analysis_proxy(self, _mock_analyze):
        response = self.module.analyze_single_edge("edge1")
        self.assertEqual(response["edge_id"], "edge1")

    @patch(
        "app.central_client.get_latest_edge_analysis",
        return_value={"mode": "single-edge", "edge_id": "edge1", "analysis_state": "completed"},
    )
    def test_latest_single_edge_analysis_proxy(self, _mock_latest):
        response = self.module.get_latest_edge_analysis("edge1")
        self.assertEqual(response["analysis_state"], "completed")

    @patch(
        "app.central_client.analyze_network",
        return_value={"mode": "network-wide", "edge_count": 2, "threat_level": "critical"},
    )
    def test_network_analysis_proxy(self, _mock_analyze):
        response = self.module.analyze_full_network()
        self.assertEqual(response["edge_count"], 2)

    @patch(
        "app.central_client.get_latest_network_analysis",
        return_value={"mode": "network-wide", "analysis_state": "completed"},
    )
    def test_latest_network_analysis_proxy(self, _mock_latest):
        response = self.module.get_latest_network_analysis()
        self.assertEqual(response["analysis_state"], "completed")
