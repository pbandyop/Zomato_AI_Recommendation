from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from src.common.config import AppConfig
from src.phase2.preferences import UserPreferences
from src.phase2.session_store import PreferenceSessionStore
from src.phase3.retrieve import run_retrieval_for_preferences, run_retrieval_for_session
from src.phase4.rank_engine import run_phase4_recommendation
from src.phase4.models import Phase4Result


@dataclass(frozen=True)
class RecommendOutcome:
    """Phase 8: timing split between Phase 3 retrieval and Phase 4 Groq orchestration."""

    data: dict[str, Any]
    retrieval_ms: float
    ranking_ms: float


def phase4_result_to_api_dict(result: Phase4Result, *, include_raw: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "recommendations": [asdict(r) for r in result.recommendations],
        "applied_fallbacks": result.applied_fallbacks,
        "preferences_summary": result.preferences_summary,
        "model": result.model,
        "guardrail_notes": list(result.guardrail_notes),
    }
    if include_raw:
        payload["raw_llm_content"] = result.raw_llm_content
    return payload


def create_session(preferences: UserPreferences) -> str:
    from src.phase2.capture import capture_preferences

    outcome = capture_preferences(preferences.model_dump())
    return outcome.session_id


def recommend_from_preferences(
    preferences: UserPreferences,
    *,
    restaurant_df: pd.DataFrame,
    config: AppConfig,
    max_candidates: int,
    top_n: int,
    include_raw_llm: bool,
) -> RecommendOutcome:
    payload = preferences.model_dump()
    t0 = time.perf_counter()
    retrieval = run_retrieval_for_preferences(
        payload,
        max_candidates=max_candidates,
        restaurant_df=restaurant_df,
    )
    t1 = time.perf_counter()
    result = run_phase4_recommendation(
        preferences,
        retrieval,
        config=config,
        top_n=top_n,
    )
    t2 = time.perf_counter()
    return RecommendOutcome(
        data=phase4_result_to_api_dict(result, include_raw=include_raw_llm),
        retrieval_ms=(t1 - t0) * 1000.0,
        ranking_ms=(t2 - t1) * 1000.0,
    )


def recommend_from_session(
    session_id: str,
    *,
    restaurant_df: pd.DataFrame,
    config: AppConfig,
    max_candidates: int,
    top_n: int,
    include_raw_llm: bool,
) -> RecommendOutcome:
    store = PreferenceSessionStore()
    record = store.get(session_id)
    if record is None:
        raise KeyError(session_id)

    t0 = time.perf_counter()
    retrieval = run_retrieval_for_session(
        session_id,
        max_candidates=max_candidates,
        restaurant_df=restaurant_df,
    )
    t1 = time.perf_counter()
    result = run_phase4_recommendation(
        record.preferences,
        retrieval,
        config=config,
        top_n=top_n,
    )
    t2 = time.perf_counter()
    return RecommendOutcome(
        data=phase4_result_to_api_dict(result, include_raw=include_raw_llm),
        retrieval_ms=(t1 - t0) * 1000.0,
        ranking_ms=(t2 - t1) * 1000.0,
    )
