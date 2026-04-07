from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ProducerInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    agent_version: str
    reported_at: str


class AnalysisConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_time_window_s: int
    max_packet_count: int
    max_token_length: int


class EdgeIntelligenceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    report_id: str
    edge_id: str
    producer: ProducerInfo
    analysis_constraints: AnalysisConstraints
    meta: dict[str, Any]
    statistics: dict[str, Any]
    threats: list[dict[str, Any]]
    metrics: dict[str, Any]
