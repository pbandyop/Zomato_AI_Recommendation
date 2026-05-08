from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    data_dir: Path
    raw_data_dir: Path
    processed_data_dir: Path
    logs_dir: Path
    environment: str
    log_level: str
    dataset_id: str
    groq_api_key: str | None
    groq_model: str
    cors_origins: tuple[str, ...]
    cors_origin_regex: str | None
    api_rate_limit_per_minute: int
    feedback_sqlite_path: Path
    prompt_version: str


def load_config() -> AppConfig:
    project_root = Path(__file__).resolve().parent.parent.parent
    data_dir = project_root / "data"

    cors_raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    )
    cors_origins = tuple(o.strip() for o in cors_raw.split(",") if o.strip())

    cors_regex_raw = os.getenv("CORS_ORIGIN_REGEX", "").strip()
    cors_origin_regex = cors_regex_raw or None

    rate_raw = os.getenv("API_RATE_LIMIT_PER_MINUTE", "60")
    try:
        api_rate_limit = max(1, int(rate_raw))
    except ValueError:
        api_rate_limit = 60

    logs_dir = project_root / "logs"
    feedback_db = os.getenv("FEEDBACK_SQLITE_PATH", "").strip()
    feedback_sqlite_path = (
        Path(feedback_db)
        if feedback_db
        else logs_dir / "phase8_feedback.db"
    )

    return AppConfig(
        project_root=project_root,
        data_dir=data_dir,
        raw_data_dir=data_dir / "raw",
        processed_data_dir=data_dir / "processed",
        logs_dir=logs_dir,
        environment=os.getenv("APP_ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        dataset_id=os.getenv(
            "DATASET_ID", "ManikaSaini/zomato-restaurant-recommendation"
        ),
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        cors_origins=cors_origins,
        cors_origin_regex=cors_origin_regex,
        api_rate_limit_per_minute=api_rate_limit,
        feedback_sqlite_path=feedback_sqlite_path,
        prompt_version=os.getenv("PROMPT_VERSION", "v1"),
    )
