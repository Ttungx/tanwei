from __future__ import annotations

from copy import deepcopy
from typing import Any


class InMemoryCentralArchive:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._reports: dict[str, list[dict[str, Any]]] = {}
        self._single_edge_analyses: dict[str, dict[str, Any]] = {}
        self._network_analysis: dict[str, Any] | None = None

    def add_report(self, report: dict[str, Any]) -> dict[str, Any]:
        edge_id = report["edge_id"]
        edge_reports = self._reports.setdefault(edge_id, [])

        for index, existing in enumerate(edge_reports):
            if existing["report_id"] == report["report_id"]:
                edge_reports[index] = deepcopy(report)
                return deepcopy(edge_reports[index])

        edge_reports.append(deepcopy(report))
        return deepcopy(edge_reports[-1])

    def list_edges(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for edge_id in sorted(self._reports):
            reports = self._reports[edge_id]
            latest_report = reports[-1]
            latest_analysis = self._single_edge_analyses.get(edge_id)
            items.append(
                {
                    "edge_id": edge_id,
                    "report_count": len(reports),
                    "latest_report_id": latest_report["report_id"],
                    "latest_reported_at": latest_report["producer"]["reported_at"],
                    "latest_analysis_status": latest_analysis["analysis_state"] if latest_analysis else "idle",
                    "latest_threat_level": latest_analysis["threat_level"] if latest_analysis else None,
                }
            )
        return items

    def list_reports(self, edge_id: str) -> list[dict[str, Any]]:
        return deepcopy(self._reports.get(edge_id, []))

    def latest_report(self, edge_id: str) -> dict[str, Any] | None:
        reports = self._reports.get(edge_id, [])
        if not reports:
            return None
        return deepcopy(reports[-1])

    def all_latest_reports(self) -> list[dict[str, Any]]:
        latest_reports = []
        for edge_id in sorted(self._reports):
            latest_reports.append(deepcopy(self._reports[edge_id][-1]))
        return latest_reports

    def store_single_edge_analysis(self, edge_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(analysis)
        payload["analysis_state"] = "completed"
        self._single_edge_analyses[edge_id] = payload
        return deepcopy(payload)

    def latest_single_edge_analysis(self, edge_id: str) -> dict[str, Any] | None:
        analysis = self._single_edge_analyses.get(edge_id)
        return deepcopy(analysis) if analysis else None

    def store_network_analysis(self, analysis: dict[str, Any]) -> dict[str, Any]:
        payload = deepcopy(analysis)
        payload["analysis_state"] = "completed"
        self._network_analysis = payload
        return deepcopy(payload)

    def latest_network_analysis(self) -> dict[str, Any] | None:
        return deepcopy(self._network_analysis) if self._network_analysis else None
