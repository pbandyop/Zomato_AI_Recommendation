from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from src.phase2.preferences import UserPreferences


class SessionCreateResponse(BaseModel):
    session_id: str


class RecommendRequest(BaseModel):
    """Exactly one of `session_id` or `preferences` must be set."""

    session_id: str | None = None
    preferences: UserPreferences | None = None
    max_candidates: int = Field(default=30, ge=1, le=200)
    top_n: int = Field(default=10, ge=1, le=50)
    include_raw_llm: bool = False

    @model_validator(mode="after")
    def validate_exactly_one_source(self) -> "RecommendRequest":
        has_session = self.session_id is not None
        has_preferences = self.preferences is not None
        if has_session == has_preferences:
            raise ValueError(
                "Provide exactly one of session_id or preferences, not both or neither."
            )
        return self
