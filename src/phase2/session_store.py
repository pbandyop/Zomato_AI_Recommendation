from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.common.config import load_config
from src.phase2.preferences import UserPreferences


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    created_at: str
    updated_at: str
    preferences: UserPreferences


class PreferenceSessionStore:
    def __init__(self, file_path: Path | None = None) -> None:
        config = load_config()
        self.file_path = file_path or (config.processed_data_dir / "preference_sessions.json")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")

    def _read_all(self) -> dict:
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def _write_all(self, payload: dict) -> None:
        self.file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def upsert(self, session_id: str, preferences: UserPreferences) -> SessionRecord:
        data = self._read_all()
        now = datetime.now(UTC).isoformat()

        existing = data.get(session_id, {})
        record = {
            "session_id": session_id,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "preferences": preferences.model_dump(),
        }
        data[session_id] = record
        self._write_all(data)

        return SessionRecord(
            session_id=record["session_id"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            preferences=preferences,
        )

    def get(self, session_id: str) -> SessionRecord | None:
        data = self._read_all()
        record = data.get(session_id)
        if not record:
            return None

        preferences = UserPreferences.model_validate(record["preferences"])
        return SessionRecord(
            session_id=record["session_id"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            preferences=preferences,
        )
