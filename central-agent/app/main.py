from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from app.reasoner import ExternalLLMReasoner
from app.schemas import EdgeIntelligenceReport
from app.store import InMemoryCentralArchive


APP_VERSION = "1.0.0"
FORBIDDEN_FIELD_HINTS = {
    "pcap",
    "raw_pcap",
    "raw_packet",
    "raw_bytes",
    "payload",
    "payload_hex",
    "flow_text",
    "prompt",
    "stack_trace",
    "env",
}

archive = InMemoryCentralArchive()
reasoner = ExternalLLMReasoner()

app = FastAPI(
    title="Tanwei Central Agent",
    description="中心智能体服务，负责边缘情报归档、单 Edge 分析与全网综合研判",
    version=APP_VERSION,
)


def reset_state() -> None:
    archive.reset()


def _assert_no_forbidden_fields(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_FIELD_HINTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"forbidden raw field detected at {path}.{key}",
                )
            _assert_no_forbidden_fields(nested, f"{path}.{key}")
        return

    if isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_forbidden_fields(nested, f"{path}[{index}]")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "service": "central-agent", "version": APP_VERSION}


@app.post("/api/v1/reports")
def ingest_report(report: EdgeIntelligenceReport) -> dict[str, Any]:
    payload = report.model_dump()
    _assert_no_forbidden_fields(payload)
    stored = archive.add_report(payload)
    return {
        "status": "stored",
        "storage_state": "available_for_analysis",
        "edge_id": stored["edge_id"],
        "report_id": stored["report_id"],
    }


@app.get("/api/v1/edges")
def list_edges() -> dict[str, Any]:
    return {"edges": archive.list_edges()}


@app.get("/api/v1/edges/{edge_id}/reports")
def list_edge_reports(edge_id: str) -> dict[str, Any]:
    reports = archive.list_reports(edge_id)
    if not reports:
        raise HTTPException(status_code=404, detail="Edge reports not found")
    return {"edge_id": edge_id, "reports": reports}


@app.get("/api/v1/edges/{edge_id}/reports/latest")
def latest_edge_report(edge_id: str) -> dict[str, Any]:
    report = archive.latest_report(edge_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Edge report not found")
    return report


@app.post("/api/v1/edges/{edge_id}/analyze")
def analyze_single_edge(edge_id: str) -> dict[str, Any]:
    reports = archive.list_reports(edge_id)
    if not reports:
        raise HTTPException(status_code=404, detail="Edge report not found")

    try:
        analysis = reasoner.analyze_single_edge(edge_id, reports)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return archive.store_single_edge_analysis(edge_id, analysis)


@app.get("/api/v1/edges/{edge_id}/analysis")
def latest_single_edge_analysis(edge_id: str) -> dict[str, Any]:
    analysis = archive.latest_single_edge_analysis(edge_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Edge analysis not found")
    return analysis


@app.post("/api/v1/network/analyze")
def analyze_network() -> dict[str, Any]:
    reports = archive.all_latest_reports()
    if not reports:
        raise HTTPException(status_code=404, detail="No edge reports available")

    try:
        analysis = reasoner.analyze_network(reports)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return archive.store_network_analysis(analysis)


@app.get("/api/v1/network/analysis")
def latest_network_analysis() -> dict[str, Any]:
    analysis = archive.latest_network_analysis()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Network analysis not found")
    return analysis
