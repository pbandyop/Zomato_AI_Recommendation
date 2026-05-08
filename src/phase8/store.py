from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from src.phase8.schemas import FeedbackEventRequest, TelemetrySummary


class _ConnCtx:
    def __init__(self, path: Path, lock: threading.Lock) -> None:
        self._path = path
        self._lock = lock

    def __enter__(self) -> sqlite3.Connection:
        self._lock.acquire()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        return self._conn

    def __exit__(self, *_exc: Any) -> None:
        try:
            self._conn.commit()
        finally:
            self._conn.close()
            self._lock.release()


class Phase8Store:
    """SQLite persistence for Phase 8 feedback and recommendation telemetry."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path), check_same_thread=False) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS recommendation_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at REAL NOT NULL,
                    retrieval_ms REAL NOT NULL,
                    ranking_ms REAL NOT NULL,
                    num_results INTEGER NOT NULL,
                    groq_issue INTEGER NOT NULL DEFAULT 0,
                    guardrail_notes_json TEXT NOT NULL DEFAULT '[]',
                    prompt_version TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    recommendation_run_id TEXT,
                    event_type TEXT NOT NULL,
                    record_id INTEGER,
                    session_id TEXT,
                    client_meta_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_created
                    ON feedback_events (created_at);
                CREATE INDEX IF NOT EXISTS idx_runs_created
                    ON recommendation_runs (created_at);
                """
            )
            conn.commit()

    def record_recommendation_run(
        self,
        *,
        run_id: str,
        retrieval_ms: float,
        ranking_ms: float,
        num_results: int,
        groq_issue: bool,
        guardrail_notes: list[str],
        prompt_version: str,
    ) -> None:
        with _ConnCtx(self.db_path, self._lock) as conn:
            conn.execute(
                """
                INSERT INTO recommendation_runs (
                    run_id, created_at, retrieval_ms, ranking_ms, num_results,
                    groq_issue, guardrail_notes_json, prompt_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    time.time(),
                    retrieval_ms,
                    ranking_ms,
                    num_results,
                    1 if groq_issue else 0,
                    json.dumps(guardrail_notes),
                    prompt_version,
                ),
            )

    def add_feedback(self, payload: FeedbackEventRequest) -> int:
        with _ConnCtx(self.db_path, self._lock) as conn:
            cur = conn.execute(
                """
                INSERT INTO feedback_events (
                    created_at, recommendation_run_id, event_type,
                    record_id, session_id, client_meta_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    payload.recommendation_run_id,
                    payload.event_type,
                    payload.record_id,
                    payload.session_id,
                    json.dumps(payload.client_meta),
                ),
            )
            return int(cur.lastrowid)

    def summarize(self, *, window_hours: float) -> TelemetrySummary:
        cutoff = time.time() - max(window_hours, 0.001) * 3600.0
        with _ConnCtx(self.db_path, self._lock) as conn:
            rows = conn.execute(
                """
                SELECT COUNT(*) AS n,
                       AVG(retrieval_ms) AS avg_r,
                       AVG(ranking_ms) AS avg_rn,
                       SUM(groq_issue) AS gq
                FROM recommendation_runs WHERE created_at >= ?
                """,
                (cutoff,),
            ).fetchone()

            fb = conn.execute(
                """
                SELECT event_type, COUNT(*) AS c
                FROM feedback_events WHERE created_at >= ?
                GROUP BY event_type
                """,
                (cutoff,),
            ).fetchall()

            fb_total = conn.execute(
                "SELECT COUNT(*) FROM feedback_events WHERE created_at >= ?",
                (cutoff,),
            ).fetchone()

        runs = int(rows["n"] or 0)
        fb_count = int(fb_total[0] or 0)
        avg_r = rows["avg_r"]
        avg_rn = rows["avg_rn"]
        groq_issues = int(rows["gq"] or 0)

        by_type = {row["event_type"]: int(row["c"]) for row in fb}

        return TelemetrySummary(
            window_hours=window_hours,
            recommendation_runs=runs,
            feedback_events=fb_count,
            avg_retrieval_ms=float(avg_r) if avg_r is not None else None,
            avg_ranking_ms=float(avg_rn) if avg_rn is not None else None,
            feedback_by_type=by_type,
            runs_with_groq_issue=groq_issues,
        )
