from __future__ import annotations

import json
import os

from src.phase2.preferences import UserPreferences


SYSTEM_PROMPT = """You are a restaurant recommendation assistant for an app similar to Zomato.
You receive a JSON object with user preferences and a list of candidate restaurants (only these may be recommended).
Rules:
- Rank only restaurants from the candidates list by how well they fit the user.
- Use each candidate's record_id exactly as given. Do not invent restaurants or IDs.
- Return ONLY valid JSON (no markdown, no extra prose): an array of objects with keys:
  record_id (integer), rank (integer starting at 1), explanation (string, 1-3 sentences),
  confidence (number from 0 to 1).
- Order the array by ascending rank.
- Cover as many top matches as useful, at most the number of candidates."""


def effective_system_prompt() -> str:
    """Base system prompt plus optional `PROMPT_APPEND` for safe A/B and iteration loops."""
    extra = os.getenv("PROMPT_APPEND", "").strip()
    if not extra:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\n\nAdditional instructions:\n{extra}"


def build_ranking_messages(
    preferences: UserPreferences,
    candidates: list[dict],
    *,
    applied_fallbacks: list[str],
) -> list[dict[str, str]]:
    user_blob = {
        "preferences": {
            "location": preferences.location,
            "budget": preferences.budget,
            "cuisines": preferences.cuisines,
            "minimum_rating": preferences.minimum_rating,
            "additional_preferences": preferences.additional_preferences,
        },
        "retrieval_notes": {
            "applied_fallbacks": applied_fallbacks,
        },
        "candidates": candidates,
    }
    user_content = (
        "Rank and explain recommendations for this user. Respond with JSON array only.\n\n"
        + json.dumps(user_blob, ensure_ascii=False, indent=2)
    )
    return [
        {"role": "system", "content": effective_system_prompt()},
        {"role": "user", "content": user_content},
    ]
