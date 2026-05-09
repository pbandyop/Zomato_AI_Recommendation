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


def test_retrieve_candidates_no_cross_cuisine_when_strict_empty() -> None:
    df = _sample_df()
    prefs = UserPreferences.model_validate(
        {
            "location": "bangalore",
            "budget": "low",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )
    # Strict: north indian + low + bangalore + rating>=4 matches nothing; south-indian row matches if cuisine ignored
    result = retrieve_candidates(df, prefs, max_candidates=10)
    assert result.candidates == []
    assert result.applied_fallbacks == ["cuisine_not_available"]
    assert result.availability_message == (
        "Sorry, restaurants for the requested cuisine were not found."
    )


def test_retrieve_candidates_unknown_location() -> None:
    df = _sample_df()
    prefs = UserPreferences.model_validate(
        {
            "location": "Seattle",
            "budget": "medium",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )
    result = retrieve_candidates(df, prefs, max_candidates=10)
    assert result.candidates == []
    assert result.applied_fallbacks == ["location_not_found"]
    assert result.availability_message == "Location not found."


def test_city_name_substring_still_known_location() -> None:
    """e.g. 'Bangalore' when rows list neighbourhoods but some entries mention the city."""

    df = pd.DataFrame(
        [
            {
                "record_id": 101,
                "restaurant_name": "City Mention",
                "location": "btm bangalore",
                "cuisines": "south indian",
                "estimated_cost": 400.0,
                "budget_bucket": "medium",
                "rating": 4.1,
                "source": "test",
            },
        ]
    )
    prefs = UserPreferences.model_validate(
        {
            "location": "Bangalore",
            "budget": "medium",
            "cuisines": ["south indian"],
            "minimum_rating": 4.0,
        }
    )
    result = retrieve_candidates(df, prefs, max_candidates=10)
    assert result.candidate_count_before_cap >= 1


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
