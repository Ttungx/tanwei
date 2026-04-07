from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import HTTPException


class ExternalLLMClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("EXTERNAL_LLM_BASE_URL", "").strip()
        self.api_key = os.getenv("EXTERNAL_LLM_API_KEY", "").strip()
        self.model = os.getenv("EXTERNAL_LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        self.timeout_seconds = float(os.getenv("EXTERNAL_LLM_TIMEOUT_SECONDS", "45"))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def analyze(
        self,
        scope: str,
        question: str,
        intel_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.configured:
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "EXTERNAL_LLM_NOT_CONFIGURED",
                    "message": "Set EXTERNAL_LLM_BASE_URL and EXTERNAL_LLM_API_KEY before calling analysis endpoints.",
                },
            )

        system_prompt = (
            "You are the Tanwei central analyst. "
            "You receive only structured security intelligence from multiple edge deployments. "
            "Never assume access to raw packet payloads. "
            "Return strict JSON with keys: summary, findings, recommended_actions, confidence_notes."
        )
        user_prompt = json.dumps(
            {
                "scope": scope,
                "question": question,
                "intel_bundle": intel_bundle,
            },
            ensure_ascii=False,
        )

        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self._chat_completions_url(), json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "EXTERNAL_LLM_UNAVAILABLE",
                    "message": f"External LLM returned HTTP {exc.response.status_code}.",
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "EXTERNAL_LLM_UNAVAILABLE",
                    "message": f"External LLM request failed: {exc}",
                },
            ) from exc

        content = self._extract_content(data)
        parsed_content = self._parse_content(content)
        return {
            "provider_response_id": data.get("id"),
            "model": data.get("model", self.model),
            "analysis": parsed_content,
        }

    def _chat_completions_url(self) -> str:
        trimmed = self.base_url.rstrip("/")
        if trimmed.endswith("/chat/completions"):
            return trimmed
        return f"{trimmed}/chat/completions"

    def _extract_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "EXTERNAL_LLM_INVALID_RESPONSE",
                    "message": "External LLM response did not contain choices.",
                },
            )

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            return "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            ).strip()
        return str(content).strip()

    def _parse_content(self, content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {
                "summary": content,
                "findings": [],
                "recommended_actions": [],
                "confidence_notes": "The external model did not return valid JSON; raw_text contains the original answer.",
            }

        if not isinstance(parsed, dict):
            return {
                "summary": str(parsed),
                "findings": [],
                "recommended_actions": [],
                "confidence_notes": "The external model returned non-object JSON.",
            }

        return {
            "summary": parsed.get("summary", ""),
            "findings": parsed.get("findings", []),
            "recommended_actions": parsed.get("recommended_actions", []),
            "confidence_notes": parsed.get("confidence_notes", ""),
        }
