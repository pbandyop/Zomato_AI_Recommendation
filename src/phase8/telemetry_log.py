from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("phase8.telemetry")


def log_recommendation_completion(
    *,
    recommendation_run_id: str,
    retrieval_ms: float,
    ranking_ms: float,
    num_results: int,
    groq_issue: bool,
    prompt_version: str,
    **extra: Any,
) -> None:
    payload = {
        "event": "recommendation_completed",
        "recommendation_run_id": recommendation_run_id,
        "retrieval_ms": round(retrieval_ms, 3),
        "ranking_ms": round(ranking_ms, 3),
        "num_results": num_results,
        "groq_issue": groq_issue,
        "prompt_version": prompt_version,
        **extra,
    }
    logger.info("%s", json.dumps(payload, separators=(",", ":"), default=str))


def log_feedback_ingested(
    *,
    event_id: int,
    recommendation_run_id: str | None,
    event_type: str,
    record_id: int | None,
) -> None:
    payload = {
        "event": "feedback_ingested",
        "feedback_event_id": event_id,
        "recommendation_run_id": recommendation_run_id,
        "feedback_type": event_type,
        "record_id": record_id,
    }
    logger.info("%s", json.dumps(payload, separators=(",", ":"), default=str))
