from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from src.phase2.preferences import UserPreferences
from src.phase3.filters import (
    BudgetFilterMode,
    FilterOptions,
    LocationFilterMode,
    apply_rule_based_filters,
)
from src.phase3.preprocess import (
    add_retrieval_scores,
    dataframe_to_llm_records,
    sort_by_match_score,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_CANDIDATES = 30
MIN_RATING_FLOOR = 3.0


@dataclass(frozen=True)
class RetrievalResult:
    """Shortlist for Phase 4 plus transparency on relaxations used."""

    candidates: list[dict]
    applied_fallbacks: list[str]
    candidate_count_before_cap: int
    preferences_summary: dict
    availability_message: str | None = None


@dataclass
class _Attempt:
    label: str
    options: FilterOptions


def _build_fallback_attempts(preferences: UserPreferences) -> list[_Attempt]:
    base_rating = preferences.minimum_rating
    attempts: list[_Attempt] = []

    attempts.append(
        _Attempt(
            "strict",
            FilterOptions(
                require_cuisine_match=True,
                effective_min_rating=base_rating,
                budget_mode=BudgetFilterMode.STRICT,
                location_mode=LocationFilterMode.EXACT,
            ),
        )
    )
    attempts.append(
        _Attempt(
            "relaxed_cuisine",
            FilterOptions(
                require_cuisine_match=False,
                effective_min_rating=base_rating,
                budget_mode=BudgetFilterMode.STRICT,
                location_mode=LocationFilterMode.EXACT,
            ),
        )
    )

    seen_ratings: set[float] = {base_rating}
    for step in (0.5, 1.0, 1.5):
        relaxed = round(max(MIN_RATING_FLOOR, base_rating - step), 2)
        if relaxed in seen_ratings:
            continue
        seen_ratings.add(relaxed)
        attempts.append(
            _Attempt(
                f"relaxed_rating_to_{relaxed:.1f}",
                FilterOptions(
                    require_cuisine_match=False,
                    effective_min_rating=relaxed,
                    budget_mode=BudgetFilterMode.STRICT,
                    location_mode=LocationFilterMode.EXACT,
                ),
            )
        )

    attempts.append(
        _Attempt(
            "expanded_budget",
            FilterOptions(
                require_cuisine_match=False,
                effective_min_rating=max(MIN_RATING_FLOOR, base_rating - 1.0),
                budget_mode=BudgetFilterMode.EXPANDED,
                location_mode=LocationFilterMode.EXACT,
            ),
        )
    )
    attempts.append(
        _Attempt(
            "location_contains",
            FilterOptions(
                require_cuisine_match=False,
                effective_min_rating=max(MIN_RATING_FLOOR, base_rating - 1.0),
                budget_mode=BudgetFilterMode.EXPANDED,
                location_mode=LocationFilterMode.CONTAINS,
            ),
        )
    )
    attempts.append(
        _Attempt(
            "last_resort_global_top_rating",
            FilterOptions(
                require_cuisine_match=False,
                effective_min_rating=MIN_RATING_FLOOR,
                budget_mode=BudgetFilterMode.ANY,
                location_mode=LocationFilterMode.ANY,
            ),
        )
    )
    return attempts


def retrieve_candidates(
    df: pd.DataFrame,
    preferences: UserPreferences,
    *,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> RetrievalResult:
    if df.empty:
        return RetrievalResult(
            candidates=[],
            applied_fallbacks=["empty_dataset"],
            candidate_count_before_cap=0,
            preferences_summary=_prefs_summary(preferences),
            availability_message=None,
        )

    required_cols = {
        "record_id",
        "restaurant_name",
        "location",
        "cuisines",
        "estimated_cost",
        "budget_bucket",
        "rating",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")

    working = df.copy()
    attempts = _build_fallback_attempts(preferences)

    strict_filtered = apply_rule_based_filters(working, preferences, attempts[0].options)
    if len(strict_filtered) > 0:
        selected = strict_filtered
        applied = [attempts[0].label]
        logger.info(
            "Retrieval succeeded with strategy=%s rows=%s",
            attempts[0].label,
            len(strict_filtered),
        )
    else:
        cuisine_relaxed = apply_rule_based_filters(working, preferences, attempts[1].options)
        if len(cuisine_relaxed) > 0:
            message = _cuisine_not_available_message(preferences.cuisines)
            logger.info(
                "Strict retrieval empty but rows exist without cuisine match; skipping cross-cuisine results"
            )
            return RetrievalResult(
                candidates=[],
                applied_fallbacks=["cuisine_not_available"],
                candidate_count_before_cap=0,
                preferences_summary=_prefs_summary(preferences),
                availability_message=message,
            )

        applied: list[str] = []
        selected: pd.DataFrame | None = None
        for attempt in attempts[2:]:
            filtered = apply_rule_based_filters(working, preferences, attempt.options)
            if len(filtered) > 0:
                selected = filtered
                applied = [attempt.label]
                logger.info(
                    "Retrieval succeeded with strategy=%s rows=%s",
                    attempt.label,
                    len(filtered),
                )
                break

        if selected is None:
            selected = working.iloc[0:0].copy()
            applied = ["no_matches"]

    scored = add_retrieval_scores(selected, preferences)
    ranked = sort_by_match_score(scored)
    count_before_cap = len(ranked)
    records = dataframe_to_llm_records(ranked, max_candidates)

    return RetrievalResult(
        candidates=records,
        applied_fallbacks=applied,
        candidate_count_before_cap=count_before_cap,
        preferences_summary=_prefs_summary(preferences),
        availability_message=None,
    )


def _cuisine_not_available_message(cuisines: list[str]) -> str:
    parts = [c.strip() for c in cuisines if c and str(c).strip()]
    if not parts:
        return "Restaurant with your requested cuisine is not available."
    if len(parts) == 1:
        return f"Restaurant with the '{parts[0]}' cuisine is not available."
    labels = "', '".join(parts)
    return f"Restaurant with the '{labels}' cuisines is not available."


def _prefs_summary(preferences: UserPreferences) -> dict:
    return {
        "location": preferences.location,
        "budget": preferences.budget,
        "cuisines": preferences.cuisines,
        "minimum_rating": preferences.minimum_rating,
        "additional_preferences": preferences.additional_preferences,
    }
