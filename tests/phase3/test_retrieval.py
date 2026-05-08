from __future__ import annotations

import pandas as pd

from src.phase2.preferences import UserPreferences
from src.phase3.filters import (
    BudgetFilterMode,
    FilterOptions,
    LocationFilterMode,
    apply_rule_based_filters,
)
from src.phase3.fallback import retrieve_candidates


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "record_id": 1,
                "restaurant_name": "Spice Hub",
                "location": "bangalore",
                "cuisines": "north indian, chinese",
                "estimated_cost": 600.0,
                "budget_bucket": "medium",
                "rating": 4.2,
                "source": "test",
            },
            {
                "record_id": 2,
                "restaurant_name": "Only South",
                "location": "bangalore",
                "cuisines": "south indian",
                "estimated_cost": 400.0,
                "budget_bucket": "low",
                "rating": 4.5,
                "source": "test",
            },
            {
                "record_id": 3,
                "restaurant_name": "Delhi Bytes",
                "location": "delhi",
                "cuisines": "north indian",
                "estimated_cost": 900.0,
                "budget_bucket": "medium",
                "rating": 4.0,
                "source": "test",
            },
        ]
    )


def test_apply_rule_based_filters_strict() -> None:
    df = _sample_df()
    prefs = UserPreferences.model_validate(
        {
            "location": "Bangalore",
            "budget": "medium",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )
    options = FilterOptions(
        require_cuisine_match=True,
        effective_min_rating=4.0,
        budget_mode=BudgetFilterMode.STRICT,
        location_mode=LocationFilterMode.EXACT,
    )
    out = apply_rule_based_filters(df, prefs, options)
    assert len(out) == 1
    assert int(out.iloc[0]["record_id"]) == 1


def test_retrieve_candidates_falls_back_when_cuisine_mismatch() -> None:
    df = _sample_df()
    prefs = UserPreferences.model_validate(
        {
            "location": "bangalore",
            "budget": "low",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )
    # Strict: wants north indian + low budget + bangalore + rating>=4 -> row 2 is south indian only
    result = retrieve_candidates(df, prefs, max_candidates=10)
    assert result.candidate_count_before_cap >= 1
    assert result.applied_fallbacks == ["relaxed_cuisine"]
    ids = {c["record_id"] for c in result.candidates}
    assert 2 in ids


def test_retrieve_empty_dataframe() -> None:
    df = pd.DataFrame(
        columns=[
            "record_id",
            "restaurant_name",
            "location",
            "cuisines",
            "estimated_cost",
            "budget_bucket",
            "rating",
            "source",
        ]
    )
    prefs = UserPreferences.model_validate(
        {
            "location": "bangalore",
            "budget": "medium",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )
    result = retrieve_candidates(df, prefs)
    assert result.candidates == []
    assert result.applied_fallbacks == ["empty_dataset"]
