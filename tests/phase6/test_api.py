from __future__ import annotations

import dataclasses
from contextlib import contextmanager

import pandas as pd
from fastapi.testclient import TestClient

from src.phase4.models import Phase4Result, RankedRecommendation


def _tiny_restaurant_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "record_id": 1,
                "restaurant_name": "Test Cafe",
                "location": "bellandur",
                "cuisines": "north indian",
                "estimated_cost": 500.0,
                "budget_bucket": "low",
                "rating": 4.1,
                "match_score": 4.2,
                "source": "test",
            }
        ]
    )


def _fake_phase4(*args, **kwargs) -> Phase4Result:
    return Phase4Result(
        recommendations=[
            RankedRecommendation(
                rank=1,
                record_id=1,
                restaurant_name="Test Cafe",
                location="bellandur",
                cuisines="north indian",
                estimated_cost=500.0,
                budget_bucket="low",
                rating=4.1,
                match_score=4.2,
                explanation="Good match.",
                confidence=0.9,
            )
        ],
        applied_fallbacks=["strict"],
        preferences_summary={"location": "bellandur"},
        model="test-model",
        guardrail_notes=(),
        raw_llm_content=None,
    )


@contextmanager
def _api_client(monkeypatch):
    import src.phase6.app as app_module

    monkeypatch.setattr(
        app_module,
        "load_cleaned_restaurants",
        lambda *a, **k: _tiny_restaurant_df(),
    )
    monkeypatch.setattr(
        "src.phase6.service.run_phase4_recommendation",
        _fake_phase4,
    )
    with TestClient(app_module.http_app) as client:
        yield client


def test_health_includes_dataset_and_groq_flags(monkeypatch) -> None:
    with _api_client(monkeypatch) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "restaurant_rows" in body
    assert "groq_configured" in body
    assert "prompt_version" in body
    assert "feedback_db" in body
    assert "cors_origin_regex" in body
    assert "render_hosted" in body


def test_recommend_with_preferences(monkeypatch) -> None:
    with _api_client(monkeypatch) as client:
        payload = {
            "preferences": {
                "location": "Bellandur",
                "budget": "low",
                "cuisines": ["north indian"],
                "minimum_rating": 4.0,
            },
            "max_candidates": 10,
            "top_n": 5,
        }
        response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    assert response.headers.get("X-Recommendation-Run-Id")
    assert "X-Timing-Retrieval-Ms" in response.headers
    data = response.json()
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["restaurant_name"] == "Test Cafe"


def test_recommend_unknown_session_returns_404(monkeypatch) -> None:
    with _api_client(monkeypatch) as client:
        payload = {"session_id": "00000000-0000-0000-0000-000000000000", "top_n": 3}
        response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 404


def test_create_session_returns_id(monkeypatch) -> None:
    with _api_client(monkeypatch) as client:
        body = {
            "location": "Delhi",
            "budget": "medium",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        }
        response = client.post("/api/v1/sessions", json=body)
    assert response.status_code == 200
    assert "session_id" in response.json()


def test_feedback_and_telemetry_round_trip(monkeypatch, tmp_path) -> None:
    import src.phase6.app as app_module

    db = tmp_path / "phase8_test.db"
    monkeypatch.setattr(
        app_module,
        "_cfg",
        dataclasses.replace(app_module._cfg, feedback_sqlite_path=db),
    )
    monkeypatch.setattr(
        app_module,
        "load_cleaned_restaurants",
        lambda *a, **k: _tiny_restaurant_df(),
    )
    monkeypatch.setattr(
        "src.phase6.service.run_phase4_recommendation",
        _fake_phase4,
    )
    payload = {
        "preferences": {
            "location": "Bellandur",
            "budget": "low",
            "cuisines": ["north indian"],
            "minimum_rating": 4.0,
        },
        "max_candidates": 10,
        "top_n": 5,
    }
    with TestClient(app_module.http_app) as client:
        rec = client.post("/api/v1/recommend", json=payload)
        run_id = rec.headers["X-Recommendation-Run-Id"]
        fb = client.post(
            "/api/v1/feedback",
            json={
                "recommendation_run_id": run_id,
                "event_type": "like",
                "record_id": 1,
            },
        )
        telemetry = client.get("/api/v1/telemetry/summary?hours=1")
    assert fb.status_code == 200
    assert fb.json()["stored"] is True
    assert telemetry.status_code == 200
    body = telemetry.json()
    assert body["recommendation_runs"] >= 1
    assert body["feedback_events"] >= 1
    assert body["feedback_by_type"].get("like", 0) >= 1
