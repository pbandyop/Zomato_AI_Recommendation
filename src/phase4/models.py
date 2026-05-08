from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RankedRecommendation:
    """One recommendation after LLM + guardrails."""

    rank: int
    record_id: int | None
    restaurant_name: str
    location: str
    cuisines: str
    estimated_cost: float | None
    budget_bucket: str | None
    rating: float
    match_score: float
    explanation: str
    confidence: float


@dataclass(frozen=True)
class Phase4Result:
    recommendations: list[RankedRecommendation]
    applied_fallbacks: list[str]
    preferences_summary: dict
    model: str
    guardrail_notes: tuple[str, ...] = ()
    raw_llm_content: str | None = None
    availability_message: str | None = None
