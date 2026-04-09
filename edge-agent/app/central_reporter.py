from __future__ import annotations

from typing import Any

import httpx


class CentralReporter:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def report(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url:
            return {
                "status": "disabled",
                "message": "CENTRAL_AGENT_URL is empty; skipping upload.",
            }

        url = f"{self.base_url}/api/v1/reports"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
            return {
                "status": body.get("status", "stored"),
                "report_id": body.get("report_id"),
                "edge_id": body.get("edge_id"),
                "reported_at": body.get("reported_at"),
                "received_at": body.get("received_at"),
            }
        except httpx.HTTPStatusError as exc:
            message = _extract_central_message(exc.response)
            if exc.response.status_code == 409:
                return {
                    "status": "conflict",
                    "error_code": "REPORT_ID_CONFLICT",
                    "message": message,
                }
            return {
                "status": "failed",
                "error_code": "CENTRAL_REPORT_UPLOAD_FAILED",
                "message": message,
            }
        except Exception as exc:  # pragma: no cover - defensive best-effort handling
            return {
                "status": "failed",
                "error_code": "CENTRAL_REPORT_UPLOAD_FAILED",
                "message": str(exc),
            }


def _extract_central_message(response: httpx.Response) -> str:
    default = f"central-agent returned HTTP {response.status_code}"
    try:
        body = response.json()
    except ValueError:
        return response.text or default

    if isinstance(body, dict):
        for key in ("message", "detail", "error", "title"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, list):
                items = [str(item) for item in value if item]
                if items:
                    return "; ".join(items)
        errors = body.get("errors")
        if isinstance(errors, dict):
            nested = _flatten_error_dict(errors)
            if nested:
                return nested
    if isinstance(body, list):
        entries = [str(item) for item in body if item]
        if entries:
            return "; ".join(entries)
    if isinstance(body, str) and body:
        return body
    return response.text or default


def _flatten_error_dict(errors: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key, value in errors.items():
        if isinstance(value, str):
            parts.append(f"{key}: {value}")
        elif isinstance(value, list):
            joined = "; ".join(str(item) for item in value if item)
            if joined:
                parts.append(f"{key}: {joined}")
    return "; ".join(parts) if parts else None
