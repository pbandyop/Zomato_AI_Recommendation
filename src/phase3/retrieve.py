from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from src.common.config import load_config
from src.common.logging_config import configure_logging
from src.phase2.preferences import UserPreferences
from src.phase2.session_store import PreferenceSessionStore
from src.phase3.fallback import RetrievalResult, retrieve_candidates

logger = logging.getLogger(__name__)


def load_cleaned_restaurants(csv_path: Path | None = None) -> pd.DataFrame:
    config = load_config()
    path = csv_path or (config.processed_data_dir / "restaurants_cleaned.csv")
    if not path.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {path}. Run Phase 1 first: python -m src.phase1.data_foundation"
        )
    df = pd.read_csv(path)
    logger.info("Loaded %s rows from %s", len(df), path)
    return df


def run_retrieval_for_session(
    session_id: str,
    *,
    max_candidates: int = 30,
    csv_path: Path | None = None,
    restaurant_df: pd.DataFrame | None = None,
) -> RetrievalResult:
    store = PreferenceSessionStore()
    record = store.get(session_id)
    if record is None:
        raise ValueError(f"No saved preferences for session_id={session_id!r}")

    df = restaurant_df if restaurant_df is not None else load_cleaned_restaurants(csv_path)
    return retrieve_candidates(df, record.preferences, max_candidates=max_candidates)


def run_retrieval_for_preferences(
    payload: dict,
    *,
    max_candidates: int = 30,
    csv_path: Path | None = None,
    restaurant_df: pd.DataFrame | None = None,
) -> RetrievalResult:
    preferences = UserPreferences.model_validate(payload)
    df = restaurant_df if restaurant_df is not None else load_cleaned_restaurants(csv_path)
    return retrieve_candidates(df, preferences, max_candidates=max_candidates)


def main() -> None:
    config = load_config()
    configure_logging(config.log_level)

    parser = argparse.ArgumentParser(
        description="Phase 3: retrieve restaurant candidates from cleaned data using preferences."
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Load preferences from Phase 2 session store",
    )
    parser.add_argument(
        "--payload",
        type=str,
        help='JSON preferences, e.g. \'{"location":"bangalore","budget":"medium","cuisines":["north indian"],"minimum_rating":4.0}\'',
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional path to restaurants_cleaned.csv (default: data/processed/restaurants_cleaned.csv)",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=30,
        help="Max rows to include in shortlist for LLM (default: 30)",
    )
    args = parser.parse_args()

    if bool(args.session_id) == bool(args.payload):
        parser.error("Provide exactly one of --session-id or --payload")

    if args.session_id:
        result = run_retrieval_for_session(
            args.session_id,
            max_candidates=args.max_candidates,
            csv_path=args.csv,
        )
    else:
        result = run_retrieval_for_preferences(
            json.loads(args.payload),
            max_candidates=args.max_candidates,
            csv_path=args.csv,
        )

    out = {
        "applied_fallbacks": result.applied_fallbacks,
        "candidate_count_before_cap": result.candidate_count_before_cap,
        "preferences_summary": result.preferences_summary,
        "candidates": result.candidates,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
