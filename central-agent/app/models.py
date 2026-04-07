from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .security import validate_structured_intel


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ThreatItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threat_id: str | None = Field(default=None, max_length=128)
    title: str = Field(..., min_length=1, max_length=256)
    severity: str | None = Field(default=None, max_length=64)
    confidence: float | None = Field(default=None, ge=0, le=1)
    category: str | None = Field(default=None, max_length=128)
    summary: str | None = Field(default=None, max_length=4000)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evidence")
    @classmethod
    def validate_evidence(cls, value: dict[str, Any]) -> dict[str, Any]:
        validate_structured_intel(value)
        return value


class EdgeReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="edge-intel/v1", max_length=64)
    summary: dict[str, Any] = Field(default_factory=dict)
    threats: list[ThreatItem] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("summary", "statistics", "metrics", "context")
    @classmethod
    def validate_intel_blocks(cls, value: Any) -> Any:
        validate_structured_intel(value)
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        validate_structured_intel(value)
        return value


class EdgeReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(..., min_length=1, max_length=128)
    report_id: str | None = Field(default=None, max_length=128)
    source: str = Field(default="edge-agent", max_length=128)
    reported_at: datetime | None = None
    intel: EdgeReportPayload = Field(default_factory=EdgeReportPayload)

    @field_validator("edge_id", "source")
    @classmethod
    def strip_text_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field must not be empty.")
        return value

    def to_record(self) -> dict[str, Any]:
        reported_at = self.reported_at or datetime.now(timezone.utc)
        return {
            "report_id": self.report_id or str(uuid4()),
            "edge_id": self.edge_id,
            "source": self.source,
            "reported_at": reported_at.isoformat(),
            "received_at": utc_now_iso(),
            "report": self.intel.model_dump(mode="json"),
        }


class EdgeAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(default="Summarize the most important risks and response priorities for this edge.")
    instructions: str = Field(default="")
    max_reports: int = Field(default=5, ge=1, le=50)

    @field_validator("question", "instructions")
    @classmethod
    def strip_prompts(cls, value: str) -> str:
        return value.strip()


class NetworkAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_ids: list[str] = Field(default_factory=list)
    question: str = Field(default="Compare edges, identify correlated risks, and recommend network-wide response priorities.")
    instructions: str = Field(default="")
    max_reports_per_edge: int = Field(default=3, ge=1, le=20)

    @field_validator("question", "instructions")
    @classmethod
    def strip_network_prompts(cls, value: str) -> str:
        return value.strip()

    @field_validator("edge_ids")
    @classmethod
    def validate_edge_ids(cls, value: list[str]) -> list[str]:
        cleaned = []
        seen: set[str] = set()
        for item in value:
            edge_id = item.strip()
            if not edge_id:
                raise ValueError("edge_ids must not contain empty values.")
            if edge_id in seen:
                continue
            seen.add(edge_id)
            cleaned.append(edge_id)
        return cleaned


class ReportStoredResponse(BaseModel):
    status: str
    report_id: str
    edge_id: str
    reported_at: str
    received_at: str


class ReportEnvelope(BaseModel):
    report_id: str
    edge_id: str
    source: str | None = None
    reported_at: str
    received_at: str
    report: EdgeReportPayload


class EdgeListItem(BaseModel):
    edge_id: str
    report_count: int
    latest_reported_at: str | None = None
    latest_received_at: str | None = None


class AnalysisResponse(BaseModel):
    analysis_id: str
    scope: str
    edge_id: str | None = None
    edge_ids: list[str] = Field(default_factory=list)
    analyzed_report_count: int
    provider_response_id: str | None = None
    model: str
    analysis: dict[str, Any]
    source_reports: list[dict[str, Any]]


class EdgeListResponse(BaseModel):
    edges: list[EdgeListItem]


class EdgeReportsResponse(BaseModel):
    edge_id: str
    reports: list[ReportEnvelope]
