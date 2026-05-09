from __future__ import annotations

import logging
import re
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
                    require_cuisine_match=True,
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
                require_cuisine_match=True,
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
                require_cuisine_match=True,
                effective_min_rating=max(MIN_RATING_FLOOR, base_rating - 1.0),
                budget_mode=BudgetFilterMode.EXPANDED,
                location_mode=LocationFilterMode.CONTAINS,
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

    if not _catalog_lists_requested_location(working, preferences):
        logger.info(
            "Requested location=%r does not overlap any catalogue location tokens",
            preferences.location,
        )
        return RetrievalResult(
            candidates=[],
            applied_fallbacks=["location_not_found"],
            candidate_count_before_cap=0,
            preferences_summary=_prefs_summary(preferences),
            availability_message=_location_not_found_message(),
        )

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
            logger.info(
                "Strict retrieval empty but rows exist without cuisine match; skipping cross-cuisine results"
            )
            return RetrievalResult(
                candidates=[],
                applied_fallbacks=["cuisine_not_available"],
                candidate_count_before_cap=0,
                preferences_summary=_prefs_summary(preferences),
                availability_message=_cuisine_not_found_message(),
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
            return RetrievalResult(
                candidates=[],
                applied_fallbacks=["no_matches"],
                candidate_count_before_cap=0,
                preferences_summary=_prefs_summary(preferences),
                availability_message=_filters_exhausted_message(),
            )

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


def _cuisine_not_found_message() -> str:
    """Shown when we refuse cross-cuisine fallbacks or have no cuisine-aligned rows."""
    return "Sorry, restaurants for the requested cuisine were not found."


def _location_not_found_message() -> str:
    return "Location not found."


def _filters_exhausted_message() -> str:
    return "No matching restaurants were found for your filters."


def _catalog_lists_requested_location(df: pd.DataFrame, preferences: UserPreferences) -> bool:
    """
    True if the user's location string overlaps the dataset location field in a way retrievals
    can honor (exact, substring, multi-token, or a catalogue token contained in user's text).

    Covers neighbourhood rows (btm), city names substring in locality (Bangalore),
    and multi-token queries ("electronic city").
    """

    raw = preferences.location.strip().lower()
    if len(raw) < 2:
        return False

    col_series = df["location"].astype(str).str.lower().str.strip().replace({"nan": ""})
    nonempty = col_series[col_series.str.len() > 0]

    if nonempty.eq(raw).any():
        return True

    escaped = re.escape(raw)
    if nonempty.str.fullmatch(escaped, na=False).any():
        return True

    mask = nonempty.str.contains(escaped, regex=True, na=False)
    if mask.any():
        return True

    for tok in re.split(r"[,\s]+", raw):
        tl = tok.strip()
        if len(tl) < 3:
            continue
        et = re.escape(tl)
        if nonempty.eq(tl).any() or nonempty.str.contains(et, regex=True, na=False).any():
            return True

    for rl in nonempty.unique():
        if not isinstance(rl, str):
            rl = str(rl)
        rls = rl.strip().lower()
        if len(rls) >= 4 and rls and rls in raw:
            return True

    return False


def _prefs_summary(preferences: UserPreferences) -> dict:
    return {
        "location": preferences.location,
        "budget": preferences.budget,
        "cuisines": preferences.cuisines,
        "minimum_rating": preferences.minimum_rating,
        "additional_preferences": preferences.additional_preferences,
    }
