from __future__ import annotations

import logging
import os
import sqlite3
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .llm_client import ExternalLLMClient
from .models import (
    AnalysisResponse,
    EdgeAnalyzeRequest,
    EdgeListItem,
    EdgeListResponse,
    EdgeReportIn,
    EdgeReportsResponse,
    NetworkAnalyzeRequest,
    ReportEnvelope,
    ReportStoredResponse,
)
from .storage import ReportStore


def create_logger() -> logging.Logger:
    logger = logging.getLogger("central-agent")
    if logger.handlers:
        return logger

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


logger = create_logger()
store = ReportStore(os.getenv("CENTRAL_AGENT_DB_PATH", "/app/data/central-agent.db"))
llm_client = ExternalLLMClient()

app = FastAPI(
    title="Tanwei Central Agent",
    description="Cloud-side structured intelligence archive and analysis service",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    store.initialize()
    logger.info("central-agent store initialized")


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "service": "central-agent",
        "version": "1.0.0",
        "external_llm_configured": llm_client.configured,
    }


@app.post("/api/v1/reports", response_model=ReportStoredResponse, status_code=201)
async def create_report(request: EdgeReportIn) -> ReportStoredResponse:
    record = request.to_record()
    try:
        store.insert_report(record)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "REPORT_ID_CONFLICT",
                "message": f"Report `{record['report_id']}` already exists.",
            },
        ) from exc
    except Exception as exc:  # sqlite uniqueness or IO problems
        logger.exception("failed to store report")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "REPORT_STORE_FAILED",
                "message": f"Failed to store report: {exc}",
            },
        ) from exc

    return ReportStoredResponse(
        status="stored",
        report_id=record["report_id"],
        edge_id=record["edge_id"],
        reported_at=record["reported_at"],
        received_at=record["received_at"],
    )


@app.get("/api/v1/edges", response_model=EdgeListResponse)
async def list_edges() -> EdgeListResponse:
    return EdgeListResponse(edges=[EdgeListItem(**item) for item in store.list_edges()])


@app.get("/api/v1/edges/{edge_id}/reports", response_model=EdgeReportsResponse)
async def list_edge_reports(
    edge_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> EdgeReportsResponse:
    reports = [ReportEnvelope(**item) for item in store.list_reports(edge_id=edge_id, limit=limit)]
    return EdgeReportsResponse(edge_id=edge_id, reports=reports)


@app.get("/api/v1/edges/{edge_id}/reports/latest", response_model=ReportEnvelope)
async def latest_edge_report(edge_id: str) -> ReportEnvelope:
    report = store.latest_report(edge_id=edge_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "EDGE_REPORT_NOT_FOUND",
                "message": f"No reports found for edge_id `{edge_id}`.",
            },
        )
    return ReportEnvelope(**report)


@app.post("/api/v1/edges/{edge_id}/analyze", response_model=AnalysisResponse)
async def analyze_edge(edge_id: str, request: EdgeAnalyzeRequest) -> AnalysisResponse:
    reports = store.list_reports(edge_id=edge_id, limit=request.max_reports)
    if not reports:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "EDGE_REPORT_NOT_FOUND",
                "message": f"No reports found for edge_id `{edge_id}`.",
            },
        )

    intel_bundle = {
        "edge_id": edge_id,
        "instructions": request.instructions,
        "report_count": len(reports),
        "reports": [item["report"] for item in reports],
    }
    llm_result = await llm_client.analyze(scope="edge", question=request.question, intel_bundle=intel_bundle)
    return AnalysisResponse(
        analysis_id=str(uuid4()),
        scope="edge",
        edge_id=edge_id,
        edge_ids=[edge_id],
        analyzed_report_count=len(reports),
        provider_response_id=llm_result["provider_response_id"],
        model=llm_result["model"],
        analysis=llm_result["analysis"],
        source_reports=_source_refs(reports),
    )


@app.post("/api/v1/network/analyze", response_model=AnalysisResponse)
async def analyze_network(request: NetworkAnalyzeRequest) -> AnalysisResponse:
    report_map = store.network_reports(
        edge_ids=request.edge_ids or None,
        max_reports_per_edge=request.max_reports_per_edge,
    )
    if not report_map:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "NETWORK_REPORTS_NOT_FOUND",
                "message": "No archived reports found for the requested network scope.",
            },
        )

    flattened_reports = [report for reports in report_map.values() for report in reports]
    intel_bundle = {
        "instructions": request.instructions,
        "edge_count": len(report_map),
        "edges": {
            edge_id: [item["report"] for item in reports]
            for edge_id, reports in report_map.items()
        },
    }
    llm_result = await llm_client.analyze(scope="network", question=request.question, intel_bundle=intel_bundle)
    return AnalysisResponse(
        analysis_id=str(uuid4()),
        scope="network",
        edge_ids=list(report_map.keys()),
        analyzed_report_count=len(flattened_reports),
        provider_response_id=llm_result["provider_response_id"],
        model=llm_result["model"],
        analysis=llm_result["analysis"],
        source_reports=_source_refs(flattened_reports),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    payload = {"status": "error", **detail}
    return JSONResponse(status_code=exc.status_code, content=payload)


def _source_refs(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "report_id": report["report_id"],
            "edge_id": report["edge_id"],
            "reported_at": report["reported_at"],
            "source": report.get("source"),
        }
        for report in reports
    ]
