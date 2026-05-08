from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


VALID_BUDGETS = {"low", "medium", "high"}
LOCATION_ALIASES = {
    "bengaluru": "bangalore",
    "blr": "bangalore",
    "new delhi": "delhi",
    "ncr": "delhi",
    "bombay": "mumbai",
    "calcutta": "kolkata",
}


def normalize_location(value: str) -> str:
    text = re.sub(r"\s+", " ", value.strip().lower())
    return LOCATION_ALIASES.get(text, text)


def normalize_cuisine(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


class UserPreferences(BaseModel):
    location: str = Field(min_length=2, description="Target city or locality")
    budget: str = Field(description="One of: low, medium, high")
    cuisines: list[str] = Field(min_length=1, description="Preferred cuisines")
    minimum_rating: float = Field(ge=0.0, le=5.0)
    additional_preferences: list[str] = Field(default_factory=list)

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        normalized = normalize_location(value)
        if len(normalized) < 2:
            raise ValueError("Location must be at least 2 characters")
        return normalized

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_BUDGETS:
            raise ValueError("Budget must be one of: low, medium, high")
        return normalized

    @field_validator("cuisines", mode="before")
    @classmethod
    def coerce_cuisines(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            parts = re.split(r"[,/|]", value)
            value = [part.strip() for part in parts if part.strip()]
        if not isinstance(value, list):
            raise ValueError("Cuisines must be a list or a delimited string")
        return value

    @field_validator("cuisines")
    @classmethod
    def validate_cuisines(cls, value: list[str]) -> list[str]:
        normalized = sorted({normalize_cuisine(item) for item in value if item.strip()})
        if not normalized:
            raise ValueError("At least one cuisine is required")
        return normalized

    @field_validator("additional_preferences", mode="before")
    @classmethod
    def coerce_additional_preferences(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = re.split(r"[,/|]", value)
            value = [part.strip() for part in parts if part.strip()]
        if not isinstance(value, list):
            raise ValueError("Additional preferences must be a list or string")
        return value

    @field_validator("additional_preferences")
    @classmethod
    def validate_additional_preferences(cls, value: list[str]) -> list[str]:
        return [re.sub(r"\s+", " ", item.strip().lower()) for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_business_rules(self) -> "UserPreferences":
        if self.budget == "low" and self.minimum_rating > 4.7:
            raise ValueError(
                "Combination is too restrictive: low budget with minimum rating > 4.7"
            )
        return self
