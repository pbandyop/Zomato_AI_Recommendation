from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FeedbackEventType = Literal["impression", "click", "like", "dislike", "select"]


class FeedbackEventRequest(BaseModel):
    """User interaction tied to a recommendation run (from response header `X-Recommendation-Run-Id`)."""

    recommendation_run_id: str | None = Field(
        default=None,
        description="Opaque id from the recommend response; optional for anonymous clicks.",
    )
    event_type: FeedbackEventType
    record_id: int | None = Field(
        default=None,
        description="Restaurant record_id when the event refers to a specific card.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional Phase 2 session id if the client created one.",
    )
    client_meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional client context (e.g. viewport, UI version).",
    )


class FeedbackEventResponse(BaseModel):
    stored: bool
    event_id: int


class TelemetrySummary(BaseModel):
    window_hours: float
    recommendation_runs: int
    feedback_events: int
    avg_retrieval_ms: float | None
    avg_ranking_ms: float | None
    feedback_by_type: dict[str, int]
    runs_with_groq_issue: int
