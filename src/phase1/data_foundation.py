from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from datasets import load_dataset

from src.common.config import load_config
from src.common.logging_config import configure_logging

logger = logging.getLogger(__name__)


LOCATION_ALIASES = {
    "bengaluru": "bangalore",
    "blr": "bangalore",
    "new delhi": "delhi",
    "ncr": "delhi",
    "bombay": "mumbai",
    "calcutta": "kolkata",
}


BUDGET_BUCKETS = {
    "low": (0, 500),
    "medium": (501, 1200),
    "high": (1201, None),
}


@dataclass(frozen=True)
class Phase1Artifacts:
    raw_csv_path: Path
    cleaned_csv_path: Path
    sqlite_path: Path


def _choose_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    for candidate in candidates:
        for col in df.columns:
            if candidate.lower() in col.lower():
                return col
    return None


def _parse_rating(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if not text or text in {"new", "-", "nan", "none"}:
        return None
    match = re.search(r"\d+(\.\d+)?", text)
    if not match:
        return None
    rating = float(match.group())
    if rating > 5:
        rating = rating / 2
    if rating < 0 or rating > 5:
        return None
    return round(rating, 2)


def _parse_cost(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    digits = re.findall(r"\d+", text.replace(",", ""))
    if not digits:
        return None
    cost = float(digits[0])
    if cost <= 0:
        return None
    return cost


def _normalize_location(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None
    return LOCATION_ALIASES.get(text, text)


def _normalize_cuisines(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    parts = re.split(r"[,/|]", text)
    cleaned = sorted({part.strip() for part in parts if part.strip()})
    if not cleaned:
        return None
    return ", ".join(cleaned)


def _budget_from_cost(cost: float | None) -> str | None:
    if cost is None:
        return None
    for label, (minimum, maximum) in BUDGET_BUCKETS.items():
        if maximum is None and cost >= minimum:
            return label
        if maximum is not None and minimum <= cost <= maximum:
            return label
    return None


def _load_source_dataframe(dataset_id: str) -> pd.DataFrame:
    dataset = load_dataset(dataset_id)
    split_name = "train" if "train" in dataset else next(iter(dataset.keys()))
    logger.info("Loaded dataset '%s' split '%s'", dataset_id, split_name)
    return dataset[split_name].to_pandas()


def _standardize_schema(df: pd.DataFrame) -> pd.DataFrame:
    name_col = _choose_column(df, ["restaurant_name", "name", "res_name"])
    location_col = _choose_column(df, ["location", "city", "locality"])
    cuisines_col = _choose_column(df, ["cuisines", "cuisine"])
    cost_col = _choose_column(
        df,
        [
            "average_cost_for_two",
            "approx_cost(for two people)",
            "cost",
            "price",
            "avg_cost",
        ],
    )
    rating_col = _choose_column(df, ["aggregate_rating", "rating", "rate", "votes_rating"])

    standardized = pd.DataFrame(
        {
            "restaurant_name": df[name_col] if name_col else None,
            "location": df[location_col] if location_col else None,
            "cuisines": df[cuisines_col] if cuisines_col else None,
            "estimated_cost": df[cost_col] if cost_col else None,
            "rating": df[rating_col] if rating_col else None,
        }
    )

    standardized["restaurant_name"] = standardized["restaurant_name"].map(
        lambda v: str(v).strip() if pd.notna(v) and str(v).strip() else None
    )
    standardized["location"] = standardized["location"].map(_normalize_location)
    standardized["cuisines"] = standardized["cuisines"].map(_normalize_cuisines)
    standardized["rating"] = standardized["rating"].map(_parse_rating)
    standardized["estimated_cost"] = standardized["estimated_cost"].map(_parse_cost)
    standardized["budget_bucket"] = standardized["estimated_cost"].map(_budget_from_cost)

    standardized["record_id"] = range(1, len(standardized) + 1)
    standardized["source"] = "huggingface"

    # Drop rows that cannot be used in downstream retrieval.
    standardized = standardized.dropna(
        subset=["restaurant_name", "location", "cuisines", "estimated_cost", "rating"]
    )

    standardized = standardized.drop_duplicates(
        subset=["restaurant_name", "location", "cuisines", "estimated_cost", "rating"]
    ).reset_index(drop=True)

    return standardized[
        [
            "record_id",
            "restaurant_name",
            "location",
            "cuisines",
            "estimated_cost",
            "budget_bucket",
            "rating",
            "source",
        ]
    ]


def _write_sqlite(df: pd.DataFrame, sqlite_path: Path) -> None:
    with sqlite3.connect(sqlite_path) as conn:
        df.to_sql("restaurants_cleaned", conn, if_exists="replace", index=False)
    logger.info("Saved SQLite table at %s", sqlite_path)


def run_phase1() -> Phase1Artifacts:
    config = load_config()
    configure_logging(config.log_level)

    config.raw_data_dir.mkdir(parents=True, exist_ok=True)
    config.processed_data_dir.mkdir(parents=True, exist_ok=True)

    raw_csv_path = config.raw_data_dir / "restaurants_raw.csv"
    cleaned_csv_path = config.processed_data_dir / "restaurants_cleaned.csv"
    sqlite_path = config.processed_data_dir / "restaurants.db"

    raw_df = _load_source_dataframe(config.dataset_id)
    raw_df.to_csv(raw_csv_path, index=False)
    logger.info("Saved raw dataset to %s (rows=%s)", raw_csv_path, len(raw_df))

    cleaned_df = _standardize_schema(raw_df)
    cleaned_df.to_csv(cleaned_csv_path, index=False)
    logger.info("Saved cleaned dataset to %s (rows=%s)", cleaned_csv_path, len(cleaned_df))

    _write_sqlite(cleaned_df, sqlite_path)

    return Phase1Artifacts(
        raw_csv_path=raw_csv_path,
        cleaned_csv_path=cleaned_csv_path,
        sqlite_path=sqlite_path,
    )


if __name__ == "__main__":
    artifacts = run_phase1()
    logger.info("Phase 1 completed: %s", artifacts)
