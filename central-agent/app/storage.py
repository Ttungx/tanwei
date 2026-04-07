from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class ReportStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    edge_id TEXT NOT NULL,
                    source TEXT,
                    reported_at TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reports_edge_reported_at ON reports(edge_id, reported_at DESC)"
            )
            connection.commit()

    def insert_report(self, record: dict[str, Any]) -> None:
        payload_json = json.dumps(record["report"], ensure_ascii=False, sort_keys=True)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reports(report_id, edge_id, source, reported_at, received_at, report_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record["report_id"],
                    record["edge_id"],
                    record.get("source"),
                    record["reported_at"],
                    record["received_at"],
                    payload_json,
                ),
            )
            connection.commit()

    def list_edges(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT edge_id,
                       COUNT(*) AS report_count,
                       MAX(reported_at) AS latest_reported_at,
                       MAX(received_at) AS latest_received_at
                FROM reports
                GROUP BY edge_id
                ORDER BY edge_id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_reports(self, edge_id: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT report_id, edge_id, source, reported_at, received_at, report_json
                FROM reports
                WHERE edge_id = ?
                ORDER BY reported_at DESC, received_at DESC
                LIMIT ?
                """,
                (edge_id, limit),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def latest_report(self, edge_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT report_id, edge_id, source, reported_at, received_at, report_json
                FROM reports
                WHERE edge_id = ?
                ORDER BY reported_at DESC, received_at DESC
                LIMIT 1
                """,
                (edge_id,),
            ).fetchone()
        return self._decode_row(row) if row else None

    def network_reports(
        self,
        edge_ids: list[str] | None,
        max_reports_per_edge: int,
    ) -> dict[str, list[dict[str, Any]]]:
        selected_edge_ids = edge_ids or [item["edge_id"] for item in self.list_edges()]
        report_map: dict[str, list[dict[str, Any]]] = {}
        for edge_id in selected_edge_ids:
            reports = self.list_reports(edge_id=edge_id, limit=max_reports_per_edge)
            if reports:
                report_map[edge_id] = reports
        return report_map

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _decode_row(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["report_json"])
        return {
            "report_id": row["report_id"],
            "edge_id": row["edge_id"],
            "source": row["source"],
            "reported_at": row["reported_at"],
            "received_at": row["received_at"],
            "report": payload,
        }
