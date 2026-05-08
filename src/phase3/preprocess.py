from __future__ import annotations

from typing import Any

import pandas as pd

from src.phase2.preferences import UserPreferences


def _cuisine_overlap_score(restaurant_cuisines: str, preferred: list[str]) -> float:
    if pd.isna(restaurant_cuisines) or not str(restaurant_cuisines).strip():
        return 0.0
    text = str(restaurant_cuisines).lower()
    hits = sum(1 for p in preferred if p.lower() in text)
    return float(hits)


def add_retrieval_scores(df: pd.DataFrame, preferences: UserPreferences) -> pd.DataFrame:
    """Comparable scores for ranking and LLM context (numeric, deterministic)."""
    if df.empty:
        return df

    out = df.copy()
    out["_cuisine_overlap"] = out["cuisines"].apply(
        lambda c: _cuisine_overlap_score(str(c) if pd.notna(c) else "", preferences.cuisines)
    )
    out["match_score"] = out["rating"].astype(float) + 0.15 * out["_cuisine_overlap"]
    out["match_score"] = out["match_score"].round(3)
    return out


def sort_by_match_score(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df.sort_values(
        by=["match_score", "rating"],
        ascending=[False, False],
    ).reset_index(drop=True)


def dataframe_to_llm_records(df: pd.DataFrame, limit: int) -> list[dict[str, Any]]:
    """Narrow columns and types suitable for JSON / LLM prompt context."""
    if df.empty:
        return []

    cap = min(limit, len(df))
    subset = df.head(cap)
    records: list[dict[str, Any]] = []
    for _, row in subset.iterrows():
        rid = row.get("record_id")
        record_id: int | None
        if pd.notna(rid):
            try:
                record_id = int(rid)
            except (TypeError, ValueError):
                record_id = None
        else:
            record_id = None
        records.append(
            {
                "record_id": record_id,
                "restaurant_name": str(row["restaurant_name"]),
                "location": str(row["location"]),
                "cuisines": str(row["cuisines"]),
                "estimated_cost": float(row["estimated_cost"])
                if pd.notna(row.get("estimated_cost"))
                else None,
                "budget_bucket": str(row["budget_bucket"])
                if pd.notna(row.get("budget_bucket"))
                else None,
                "rating": float(row["rating"]),
                "match_score": float(row["match_score"]),
            }
        )
    return records
