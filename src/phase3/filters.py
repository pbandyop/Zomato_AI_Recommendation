from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from src.phase2.preferences import UserPreferences


class BudgetFilterMode(str, Enum):
    STRICT = "strict"
    EXPANDED = "expanded"
    ANY = "any"


class LocationFilterMode(str, Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    ANY = "any"


@dataclass(frozen=True)
class FilterOptions:
    """Controls how hard constraints are applied before scoring."""

    require_cuisine_match: bool = True
    effective_min_rating: float = 0.0
    budget_mode: BudgetFilterMode = BudgetFilterMode.STRICT
    location_mode: LocationFilterMode = LocationFilterMode.EXACT


def _expanded_budget_buckets(user_budget: str) -> set[str]:
    if user_budget == "low":
        return {"low", "medium"}
    if user_budget == "medium":
        return {"low", "medium", "high"}
    return {"medium", "high"}


def _cuisine_match(restaurant_cuisines: str, preferred: list[str]) -> bool:
    if pd.isna(restaurant_cuisines) or not str(restaurant_cuisines).strip():
        return False
    text = str(restaurant_cuisines).lower()
    tokens = [t.strip() for t in text.split(",") if t.strip()]
    for pref in preferred:
        p = pref.lower()
        if p in text:
            return True
        if any(p in t or t in p for t in tokens if len(t) > 1 and len(p) > 1):
            return True
    return False


def apply_rule_based_filters(
    df: pd.DataFrame,
    preferences: UserPreferences,
    options: FilterOptions,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    mask = pd.Series(True, index=df.index)

    loc = preferences.location
    if options.location_mode == LocationFilterMode.EXACT:
        mask &= df["location"].astype(str).str.lower().str.strip() == loc
    elif options.location_mode == LocationFilterMode.CONTAINS:
        loc_lower = loc.lower()
        mask &= (
            df["location"].astype(str).str.lower().str.contains(loc_lower, regex=False, na=False)
            | (df["location"].astype(str).str.lower().str.strip() == loc_lower)
        )

    if options.budget_mode == BudgetFilterMode.STRICT:
        mask &= df["budget_bucket"].astype(str).str.lower() == preferences.budget
    elif options.budget_mode == BudgetFilterMode.EXPANDED:
        allowed = _expanded_budget_buckets(preferences.budget)
        mask &= df["budget_bucket"].astype(str).str.lower().isin(allowed)

    mask &= df["rating"].astype(float) >= options.effective_min_rating

    if options.require_cuisine_match:
        mask &= df["cuisines"].apply(
            lambda c: _cuisine_match(str(c) if pd.notna(c) else "", preferences.cuisines)
        )

    return df.loc[mask].copy()
