from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv


class ExternalLLMReasoner:
    def __init__(self) -> None:
        load_dotenv()
        self.base_url = (
            os.getenv("EXTERNAL_LLM_BASE_URL", "").strip()
            or os.getenv("CENTRAL_AGENT_BASEURL", "").strip()
        )
        self.api_key = (
            os.getenv("EXTERNAL_LLM_API_KEY", "").strip()
            or os.getenv("CENTRAL_AGENT_APIKEY", "").strip()
        )
        self.model = (
            os.getenv("EXTERNAL_LLM_MODEL", "").strip()
            or os.getenv("CENTRAL_AGENT_MODEL", "").strip()
            or "gpt-4.1-mini"
        )
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not self.base_url or not self.api_key:
            raise RuntimeError("External LLM is not configured")

        from openai import OpenAI

        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def _request_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        completion = client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                },
            ],
        )
        raw_content = completion.choices[0].message.content or "{}"
        payload = json.loads(raw_content)
        if "recommendations" in payload and not isinstance(payload["recommendations"], list):
            payload["recommendations"] = [str(payload["recommendations"])]
        return payload

    def analyze_single_edge(self, edge_id: str, reports: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = (
            "You are the central-agent for a campus-network multi-agent anomaly detection system. "
            "You receive only compressed structured JSON intelligence from edge agents. "
            "Never assume access to raw PCAP or raw payloads. "
            "Return JSON with keys: threat_level, summary, analysis, recommendations."
        )
        payload = {
            "mode": "single-edge",
            "edge_id": edge_id,
            "report_count": len(reports),
            "reports": reports,
        }
        result = self._request_json(prompt, payload)
        return {
            "mode": "single-edge",
            "edge_id": edge_id,
            "threat_level": result.get("threat_level", "unknown"),
            "summary": result.get("summary", ""),
            "analysis": result.get("analysis", ""),
            "recommendations": result.get("recommendations", []),
        }

    def analyze_network(self, reports: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = (
            "You are the central-agent for a campus-network multi-agent anomaly detection system. "
            "You receive only compressed structured JSON intelligence from multiple edge agents. "
            "Never assume access to raw PCAP or raw payloads. "
            "Return JSON with keys: threat_level, summary, analysis, recommendations."
        )
        payload = {
            "mode": "network-wide",
            "edge_count": len(reports),
            "reports": reports,
        }
        result = self._request_json(prompt, payload)
        return {
            "mode": "network-wide",
            "edge_count": len(reports),
            "threat_level": result.get("threat_level", "unknown"),
            "summary": result.get("summary", ""),
            "analysis": result.get("analysis", ""),
            "recommendations": result.get("recommendations", []),
        }
