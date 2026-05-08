"""Offline evaluation harness: run retrieval + ranking for fixed user profiles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.common.config import load_config
from src.phase2.preferences import UserPreferences
from src.phase6.service import recommend_from_preferences
from src.phase3.retrieve import load_cleaned_restaurants


def _default_profiles_path() -> Path:
    return Path(__file__).resolve().parent / "sample_eval_profiles.json"


def load_profiles(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation profiles file must be a JSON array")
    return data


def run_profiles(
    profiles: list[dict[str, Any]],
    *,
    restaurant_df: Any,
    config: Any,
    max_candidates: int = 30,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in profiles:
        profile_id = row.get("id", "anonymous")
        raw_prefs = row.get("preferences") or {}
        prefs = UserPreferences.model_validate(raw_prefs)
        outcome = recommend_from_preferences(
            prefs,
            restaurant_df=restaurant_df,
            config=config,
            max_candidates=max_candidates,
            top_n=top_n,
            include_raw_llm=False,
        )
        guardrails = outcome.data.get("guardrail_notes") or []
        groq_issue = bool(
            any(
                str(g).startswith("groq_error:") or str(g).startswith("groq_config:")
                for g in guardrails
            )
        )
        results.append(
            {
                "id": profile_id,
                "num_recommendations": len(outcome.data.get("recommendations") or []),
                "retrieval_ms": round(outcome.retrieval_ms, 3),
                "ranking_ms": round(outcome.ranking_ms, 3),
                "groq_issue": groq_issue,
                "applied_fallbacks": outcome.data.get("applied_fallbacks"),
                "top_restaurant": (
                    (outcome.data.get("recommendations") or [{}])[0].get(
                        "restaurant_name"
                    )
                ),
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 8 evaluation harness (sample user profiles)."
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=_default_profiles_path(),
        help="Path to JSON profiles (see sample_eval_profiles.json).",
    )
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args(argv)

    cfg = load_config()
    profiles = load_profiles(args.profiles)
    df = load_cleaned_restaurants()
    rows = run_profiles(
        profiles,
        restaurant_df=df,
        config=cfg,
        max_candidates=args.max_candidates,
        top_n=args.top_n,
    )
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
