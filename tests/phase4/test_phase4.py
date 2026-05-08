from __future__ import annotations

from src.phase2.preferences import UserPreferences
from src.phase3.fallback import RetrievalResult
from src.phase4.guardrails import apply_guardrails
from src.phase4.parser import parse_ranking_response
from src.phase4.prompt_builder import build_ranking_messages
from src.phase4.rank_engine import run_phase4_recommendation


def test_build_ranking_messages_includes_candidates() -> None:
    prefs = UserPreferences.model_validate(
        {
            "location": "bangalore",
            "budget": "medium",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )
    candidates = [{"record_id": 5, "restaurant_name": "Test"}]
    messages = build_ranking_messages(
        prefs, candidates, applied_fallbacks=["strict"]
    )
    assert messages[0]["role"] == "system"
    assert "record_id" in messages[1]["content"]


def test_parse_ranking_response_strips_markdown_fence() -> None:
    text = '```json\n[{"record_id": 1, "rank": 1, "explanation": "x", "confidence": 0.8}]\n```'
    rows = parse_ranking_response(text)
    assert len(rows) == 1
    assert rows[0]["record_id"] == 1


def test_apply_guardrails_drops_unknown_ids() -> None:
    candidates = [
        {
            "record_id": 1,
            "restaurant_name": "A",
            "location": "bangalore",
            "cuisines": "north indian",
            "estimated_cost": 500.0,
            "budget_bucket": "low",
            "rating": 4.2,
            "match_score": 4.3,
        }
    ]
    parsed = [
        {"record_id": 99, "rank": 1, "explanation": "bad", "confidence": 0.9},
        {"record_id": 1, "rank": 2, "explanation": "ok", "confidence": 0.8},
    ]
    merged, notes = apply_guardrails(parsed, candidates)
    assert len(merged) == 1
    assert merged[0].record_id == 1
    assert any("dropped_unknown" in n for n in notes)


def test_run_phase4_recommendation_mock_groq(monkeypatch) -> None:
    from src.phase4 import rank_engine

    def fake_complete(_messages, **kwargs):
        return (
            '[{"record_id": 10, "rank": 1, "explanation": "Fits budget and cuisine.", '
            '"confidence": 0.85}]'
        )

    monkeypatch.setattr(rank_engine, "groq_chat_completion", fake_complete)

    prefs = UserPreferences.model_validate(
        {
            "location": "bangalore",
            "budget": "medium",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
    )
    retrieval = RetrievalResult(
        candidates=[
            {
                "record_id": 10,
                "restaurant_name": "Mock Place",
                "location": "bangalore",
                "cuisines": "north indian",
                "estimated_cost": 600.0,
                "budget_bucket": "medium",
                "rating": 4.3,
                "match_score": 4.4,
            }
        ],
        applied_fallbacks=["strict"],
        candidate_count_before_cap=1,
        preferences_summary={},
    )

    result = run_phase4_recommendation(prefs, retrieval, top_n=5)
    assert len(result.recommendations) == 1
    assert result.recommendations[0].restaurant_name == "Mock Place"
    assert result.recommendations[0].explanation
