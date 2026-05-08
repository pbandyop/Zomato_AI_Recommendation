from __future__ import annotations

import logging

from src.common.config import AppConfig, load_config
from src.phase2.preferences import UserPreferences
from src.phase3.fallback import RetrievalResult
from src.phase4.groq_client import groq_chat_completion
from src.phase4.guardrails import apply_guardrails, fallback_rankings
from src.phase4.models import Phase4Result
from src.phase4.parser import parse_ranking_response
from src.phase4.prompt_builder import build_ranking_messages

logger = logging.getLogger(__name__)


def run_phase4_recommendation(
    preferences: UserPreferences,
    retrieval: RetrievalResult,
    *,
    config: AppConfig | None = None,
    top_n: int = 10,
) -> Phase4Result:
    cfg = config or load_config()

    if not retrieval.candidates:
        return Phase4Result(
            recommendations=[],
            applied_fallbacks=list(retrieval.applied_fallbacks),
            preferences_summary=dict(retrieval.preferences_summary),
            model=cfg.groq_model,
            guardrail_notes=("no_candidates",),
            raw_llm_content=None,
        )

    messages = build_ranking_messages(
        preferences,
        retrieval.candidates,
        applied_fallbacks=list(retrieval.applied_fallbacks),
    )

    notes: list[str] = []
    raw_content: str | None = None

    try:
        raw_content = groq_chat_completion(messages, config=cfg)
    except ValueError as exc:
        logger.warning("Groq configuration error: %s", exc)
        recs = fallback_rankings(retrieval.candidates, limit=top_n)
        return Phase4Result(
            recommendations=recs,
            applied_fallbacks=list(retrieval.applied_fallbacks),
            preferences_summary=dict(retrieval.preferences_summary),
            model=cfg.groq_model,
            guardrail_notes=(f"groq_config:{exc}",),
            raw_llm_content=None,
        )
    except Exception as exc:
        logger.exception("Groq request failed: %s", exc)
        recs = fallback_rankings(retrieval.candidates, limit=top_n)
        return Phase4Result(
            recommendations=recs,
            applied_fallbacks=list(retrieval.applied_fallbacks),
            preferences_summary=dict(retrieval.preferences_summary),
            model=cfg.groq_model,
            guardrail_notes=(f"groq_error:{exc}",),
            raw_llm_content=raw_content,
        )

    try:
        parsed = parse_ranking_response(raw_content)
    except Exception as exc:
        logger.warning("Failed to parse LLM JSON: %s", exc)
        recs = fallback_rankings(retrieval.candidates, limit=top_n)
        return Phase4Result(
            recommendations=recs,
            applied_fallbacks=list(retrieval.applied_fallbacks),
            preferences_summary=dict(retrieval.preferences_summary),
            model=cfg.groq_model,
            guardrail_notes=(f"parse_error:{exc}",),
            raw_llm_content=raw_content,
        )

    recs, guard_notes = apply_guardrails(parsed, retrieval.candidates)
    notes.extend(guard_notes)

    if not recs:
        logger.warning("Guardrails removed all LLM rows; using fallback ordering")
        recs = fallback_rankings(retrieval.candidates, limit=top_n)
        notes.append("guardrails_empty_fallback")

    recs = recs[:top_n]

    return Phase4Result(
        recommendations=recs,
        applied_fallbacks=list(retrieval.applied_fallbacks),
        preferences_summary=dict(retrieval.preferences_summary),
        model=cfg.groq_model,
        guardrail_notes=tuple(notes),
        raw_llm_content=raw_content,
    )
