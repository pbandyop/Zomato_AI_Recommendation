from __future__ import annotations

import json
from dataclasses import asdict

from src.common.config import load_config


def run_healthcheck() -> dict[str, str]:
    config = load_config()
    checks = {
        "environment": config.environment,
        "dataset_id": config.dataset_id,
        "project_root_exists": str(config.project_root.exists()),
        "data_dir_exists": str(config.data_dir.exists()),
        "raw_data_dir_exists": str(config.raw_data_dir.exists()),
        "processed_data_dir_exists": str(config.processed_data_dir.exists()),
        "logs_dir_exists": str(config.logs_dir.exists()),
    }
    return checks


if __name__ == "__main__":
    config = load_config()
    config_dict = {k: str(v) for k, v in asdict(config).items()}
    if config_dict.get("groq_api_key") and config_dict["groq_api_key"] not in ("None", ""):
        config_dict["groq_api_key"] = "***redacted***"
    payload = {
        "config": config_dict,
        "checks": run_healthcheck(),
    }
    print(json.dumps(payload, indent=2))
