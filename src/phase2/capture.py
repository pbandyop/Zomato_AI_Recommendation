from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from uuid import uuid4

from pydantic import ValidationError

from src.common.config import load_config
from src.common.logging_config import configure_logging
from src.phase2.preferences import UserPreferences
from src.phase2.session_store import PreferenceSessionStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaptureResult:
    session_id: str
    preferences: UserPreferences
    message: str


def capture_preferences(payload: dict, session_id: str | None = None) -> CaptureResult:
    preferences = UserPreferences.model_validate(payload)
    resolved_session_id = session_id or str(uuid4())

    store = PreferenceSessionStore()
    store.upsert(resolved_session_id, preferences)

    return CaptureResult(
        session_id=resolved_session_id,
        preferences=preferences,
        message="Preferences captured and session persisted.",
    )


def _demo_payload() -> dict:
    return {
        "location": "Bengaluru",
        "budget": "medium",
        "cuisines": ["North Indian", "Chinese"],
        "minimum_rating": 4.0,
        "additional_preferences": ["family-friendly", "quick service"],
    }


def main() -> None:
    config = load_config()
    configure_logging(config.log_level)

    parser = argparse.ArgumentParser(
        description="Phase 2 preference capture layer (web UI contract backend)."
    )
    parser.add_argument(
        "--payload",
        type=str,
        help='JSON string payload, e.g. \'{"location":"Delhi","budget":"low","cuisines":["north indian"],"minimum_rating":4.0}\'',
    )
    parser.add_argument("--session-id", type=str, help="Optional session identifier")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with a built-in sample payload",
    )
    args = parser.parse_args()

    if args.demo:
        payload = _demo_payload()
    elif args.payload:
        payload = json.loads(args.payload)
    else:
        raise ValueError("Provide --payload JSON or use --demo")

    try:
        result = capture_preferences(payload=payload, session_id=args.session_id)
    except ValidationError as exc:
        logger.error("Preference validation failed: %s", exc)
        raise

    print(
        json.dumps(
            {
                "session_id": result.session_id,
                "message": result.message,
                "preferences": result.preferences.model_dump(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
