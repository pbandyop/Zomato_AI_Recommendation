from __future__ import annotations

from src.phase2.preferences import UserPreferences
from src.phase4.models import RankedRecommendation


def _coerce_int(value: object, *, fallback: int) -> int:
    try:
        if value is None:
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_float_01(value: object, *, default: float = 0.7) -> float:
    try:
        if value is None:
            return default
        x = float(value)
        return max(0.0, min(1.0, x))
    except (TypeError, ValueError):
        return default


def apply_guardrails(
    parsed_rows: list[dict],
    candidates: list[dict],
) -> tuple[list[RankedRecommendation], list[str]]:
    """Keep only record_ids present in candidates; stable order by model rank."""
    by_id: dict[int, dict] = {}
    for c in candidates:
        rid = c.get("record_id")
        if rid is None:
            continue
        try:
            by_id[int(rid)] = c
        except (TypeError, ValueError):
            continue

    notes: list[str] = []
    sorted_rows = sorted(
        parsed_rows,
        key=lambda r: _coerce_int(r.get("rank"), fallback=10**6),
    )

    merged: list[RankedRecommendation] = []
    seen: set[int] = set()

    for raw in sorted_rows:
        rid = raw.get("record_id")
        if rid is None:
            notes.append("skipped_missing_record_id")
            continue
        try:
            rid_int = int(rid)
        except (TypeError, ValueError):
            notes.append("skipped_invalid_record_id")
            continue
        if rid_int not in by_id:
            notes.append(f"dropped_unknown_record_id:{rid_int}")
            continue
        if rid_int in seen:
            notes.append(f"deduped_record_id:{rid_int}")
            continue
        seen.add(rid_int)

        base = by_id[rid_int]
        explanation = str(raw.get("explanation", "")).strip()
        if not explanation:
            explanation = "Fits the stated preferences among the candidate list."

        merged.append(
            RankedRecommendation(
                rank=len(merged) + 1,
                record_id=rid_int,
                restaurant_name=str(base.get("restaurant_name", "")),
                location=str(base.get("location", "")),
                cuisines=str(base.get("cuisines", "")),
                estimated_cost=base.get("estimated_cost"),
                budget_bucket=str(base["budget_bucket"]) if base.get("budget_bucket") is not None else None,
                rating=float(base["rating"]),
                match_score=float(base.get("match_score", 0.0)),
                explanation=explanation,
                confidence=_coerce_float_01(raw.get("confidence"), default=0.75),
            )
        )

    return merged, notes


def _user_facing_fallback_explanation(
    base: dict,
    preferences: UserPreferences | None,
) -> str:
    """Short copy when we rank from retrieval scores instead of model prose."""
    name = str(base.get("restaurant_name", "")).strip() or "This restaurant"
    loc = str(base.get("location", "")).strip()
    cuis_raw = str(base.get("cuisines", "")).strip()
    budget = str(base.get("budget_bucket", "")).strip()
    try:
        rating = float(base.get("rating", 0.0))
    except (TypeError, ValueError):
        rating = 0.0

    cuisine_lead = ""
    if cuis_raw:
        cuisine_lead = next((t.strip() for t in cuis_raw.split(",") if t.strip()), "")

    parts: list[str] = []
    if loc:
        parts.append(f"in {loc}")
    if cuisine_lead:
        parts.append(cuisine_lead)
    if budget:
        parts.append(f"{budget} budget")
    if rating > 0:
        parts.append(f"rated {rating:.1f}/5")

    tail = "; ".join(parts) if parts else "among the strongest matches for your filters"
    if preferences is not None:
        want = ", ".join(preferences.cuisines) if preferences.cuisines else ""
        area = preferences.location.strip()
        if want and area:
            return f"{name} fits your search around {area} for {want} — {tail}."
        if area:
            return f"{name} fits your search around {area} — {tail}."
    return f"{name} — {tail}."


def fallback_rankings(
    candidates: list[dict],
    *,
    limit: int = 10,
    preferences: UserPreferences | None = None,
) -> list[RankedRecommendation]:
    """Deterministic ranking when LLM fails or guardrails remove everything."""
    sorted_c = sorted(
        candidates,
        key=lambda c: (-float(c.get("match_score", 0.0)), -float(c.get("rating", 0.0))),
    )
    out: list[RankedRecommendation] = []
    for i, base in enumerate(sorted_c[:limit], start=1):
        out.append(
            RankedRecommendation(
                rank=i,
                record_id=int(base["record_id"]) if base.get("record_id") is not None else None,
                restaurant_name=str(base.get("restaurant_name", "")),
                location=str(base.get("location", "")),
                cuisines=str(base.get("cuisines", "")),
                estimated_cost=base.get("estimated_cost"),
                budget_bucket=str(base["budget_bucket"]) if base.get("budget_bucket") is not None else None,
                rating=float(base.get("rating", 0.0)),
                match_score=float(base.get("match_score", 0.0)),
                explanation=_user_facing_fallback_explanation(base, preferences),
                confidence=0.55,
            )
        )
    return out
