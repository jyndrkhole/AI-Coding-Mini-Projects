"""SQLite history. The payload is the validated report JSON."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.models import AnalysisReport


class AnalysisStore:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists analyses (
                    id text primary key,
                    ticker text not null,
                    company_name text not null,
                    created_at text not null,
                    rating text not null,
                    payload text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, report: AnalysisReport) -> None:
        payload = report.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                insert into analyses (id, ticker, company_name, created_at, rating, payload)
                values (?, ?, ?, ?, ?, ?)
                """,
                (report.id, report.ticker, report.company_name, report.created_at, report.rating.label, payload),
            )

    def list_recent(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select id, ticker, company_name, created_at, rating
                from analyses
                order by created_at desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, report_id: str) -> AnalysisReport | None:
        with self._connect() as conn:
            row = conn.execute("select payload from analyses where id = ?", (report_id,)).fetchone()
        if row is None:
            return None
        return AnalysisReport.model_validate_json(row["payload"])
