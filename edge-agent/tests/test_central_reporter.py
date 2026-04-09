import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from app.central_reporter import CentralReporter


class CentralReporterTests(unittest.IsolatedAsyncioTestCase):
    async def test_report_returns_disabled_when_base_url_missing(self):
        reporter = CentralReporter(base_url="", timeout_seconds=5.0)
        result = await reporter.report({"edge_id": "edge1", "intel": {}})
        self.assertEqual(result["status"], "disabled")

    async def test_report_returns_stored_on_201(self):
        payload = {"edge_id": "edge1", "intel": {"foo": "bar"}}
        request = httpx.Request(
            "POST",
            "http://central-agent:8003/api/v1/reports",
            json=payload,
        )
        response = httpx.Response(
            201,
            json={
                "status": "stored",
                "report_id": "task-123",
                "edge_id": "edge1",
                "reported_at": "2026-04-08T09:30:00+00:00",
                "received_at": "2026-04-08T09:30:01+00:00",
            },
            request=request,
        )
        post_mock = AsyncMock(return_value=response)
        with patch("app.central_reporter.httpx.AsyncClient.post", new=post_mock):
            reporter = CentralReporter(base_url="http://central-agent:8003", timeout_seconds=5.0)
            result = await reporter.report(payload)
        post_mock.assert_awaited_once_with("http://central-agent:8003/api/v1/reports", json=payload)
        self.assertEqual(
            result,
            {
                "status": "stored",
                "report_id": "task-123",
                "edge_id": "edge1",
                "reported_at": "2026-04-08T09:30:00+00:00",
                "received_at": "2026-04-08T09:30:01+00:00",
            },
        )

    async def test_report_returns_conflict_on_409(self):
        request = httpx.Request(
            "POST",
            "http://central-agent:8003/api/v1/reports",
        )
        response = httpx.Response(
            409,
            json={"detail": "duplicate"},
            request=request,
        )
        post_mock = AsyncMock(return_value=response)
        payload = {"edge_id": "edge1", "intel": {}}
        with patch("app.central_reporter.httpx.AsyncClient.post", new=post_mock):
            reporter = CentralReporter(base_url="http://central-agent:8003", timeout_seconds=5.0)
            result = await reporter.report(payload)
        post_mock.assert_awaited_once_with("http://central-agent:8003/api/v1/reports", json=payload)
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["error_code"], "REPORT_ID_CONFLICT")
        self.assertEqual(result["message"], "duplicate")

    async def test_report_returns_failed_instead_of_raising_on_network_error(self):
        with patch(
            "app.central_reporter.httpx.AsyncClient.post",
            side_effect=httpx.ConnectError("boom"),
        ):
            reporter = CentralReporter(base_url="http://central-agent:8003", timeout_seconds=5.0)
            result = await reporter.report({"edge_id": "edge1", "intel": {}})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "CENTRAL_REPORT_UPLOAD_FAILED")

    async def test_report_returns_failed_on_http_status_error(self):
        payload = {"edge_id": "edge1", "intel": {"foo": "bar"}}
        request = httpx.Request(
            "POST",
            "http://central-agent:8003/api/v1/reports",
            json=payload,
        )
        response = httpx.Response(
            500,
            json={"message": "unexpected server error"},
            request=request,
        )
        post_mock = AsyncMock(return_value=response)
        with patch("app.central_reporter.httpx.AsyncClient.post", new=post_mock):
            reporter = CentralReporter(base_url="http://central-agent:8003", timeout_seconds=5.0)
            result = await reporter.report(payload)
        post_mock.assert_awaited_once_with("http://central-agent:8003/api/v1/reports", json=payload)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "CENTRAL_REPORT_UPLOAD_FAILED")
        self.assertIn("unexpected server error", result["message"])
