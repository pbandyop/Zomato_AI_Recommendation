from pathlib import Path

from src.phase2.preferences import UserPreferences
from src.phase2.session_store import PreferenceSessionStore


def test_session_store_upsert_and_get(tmp_path: Path) -> None:
    store = PreferenceSessionStore(file_path=tmp_path / "sessions.json")
    preferences = UserPreferences.model_validate(
        {
            "location": "Delhi",
            "budget": "low",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )

    saved = store.upsert("session-1", preferences)
    loaded = store.get("session-1")

    assert saved.session_id == "session-1"
    assert loaded is not None
    assert loaded.preferences.location == "delhi"
