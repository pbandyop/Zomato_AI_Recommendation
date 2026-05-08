from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from src.common.config import load_config
from src.common.logging_config import configure_logging
from src.phase2.preferences import UserPreferences
from src.phase2.session_store import PreferenceSessionStore
from src.phase3.retrieve import run_retrieval_for_preferences, run_retrieval_for_session
from src.phase4.rank_engine import run_phase4_recommendation

def _result_to_dict(result, *, include_raw: bool) -> dict:
    payload = {
        "recommendations": [asdict(r) for r in result.recommendations],
        "applied_fallbacks": result.applied_fallbacks,
        "preferences_summary": result.preferences_summary,
        "model": result.model,
        "guardrail_notes": list(result.guardrail_notes),
    }
    if result.availability_message:
        payload["availability_message"] = result.availability_message
    if include_raw:
        payload["raw_llm_content"] = result.raw_llm_content
    return payload


def main() -> None:
    config = load_config()
    configure_logging(config.log_level)

    parser = argparse.ArgumentParser(
        description="Phase 4: Groq LLM ranking and explanations for Phase 3 candidates."
    )
    parser.add_argument("--session-id", type=str, help="Phase 2 session id")
    parser.add_argument(
        "--payload",
        type=str,
        help="Preferences JSON (Phase 2 shape), if not using --session-id",
    )
    parser.add_argument(
        "--payload-file",
        type=Path,
        default=None,
        help="Path to JSON file with preferences (avoids shell quoting issues)",
    )
    parser.add_argument("--csv", type=str, default=None, help="Optional cleaned CSV path")
    parser.add_argument("--max-candidates", type=int, default=30, help="Phase 3 shortlist size")
    parser.add_argument("--top-n", type=int, default=10, help="How many final recommendations to print")
    parser.add_argument(
        "--include-raw-llm",
        action="store_true",
        help="Include raw LLM response in JSON output",
    )
    args = parser.parse_args()

    modes = sum(
        [
            bool(args.session_id),
            bool(args.payload),
            bool(args.payload_file),
        ]
    )
    if modes != 1:
        parser.error(
            "Provide exactly one of --session-id, --payload, or --payload-file"
        )

    csv_path = Path(args.csv) if args.csv else None

    if args.session_id:
        store = PreferenceSessionStore()
        record = store.get(args.session_id)
        if record is None:
            raise SystemExit(f"No session saved for session_id={args.session_id!r}")
        preferences = record.preferences
        retrieval = run_retrieval_for_session(
            args.session_id,
            max_candidates=args.max_candidates,
            csv_path=csv_path,
        )
    else:
        if args.payload_file:
            preferences_dict = json.loads(
                args.payload_file.read_text(encoding="utf-8")
            )
        else:
            preferences_dict = json.loads(args.payload)
        preferences = UserPreferences.model_validate(preferences_dict)
        retrieval = run_retrieval_for_preferences(
            preferences_dict,
            max_candidates=args.max_candidates,
            csv_path=csv_path,
        )

    result = run_phase4_recommendation(
        preferences,
        retrieval,
        config=config,
        top_n=args.top_n,
    )
    print(json.dumps(_result_to_dict(result, include_raw=args.include_raw_llm), indent=2))


if __name__ == "__main__":
    main()
