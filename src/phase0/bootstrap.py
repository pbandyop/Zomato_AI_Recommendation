from __future__ import annotations

import logging
from pathlib import Path

from src.common.config import load_config
from src.common.logging_config import configure_logging

logger = logging.getLogger(__name__)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    logger.info("Ensured directory exists: %s", path)


def bootstrap_project() -> None:
    config = load_config()
    configure_logging(config.log_level)

    logger.info("Starting Phase 0 bootstrap for env=%s", config.environment)

    ensure_directory(config.data_dir)
    ensure_directory(config.raw_data_dir)
    ensure_directory(config.processed_data_dir)
    ensure_directory(config.logs_dir)

    logger.info("Phase 0 bootstrap complete.")


if __name__ == "__main__":
    bootstrap_project()
