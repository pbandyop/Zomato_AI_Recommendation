from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.common.config import load_config
from src.common.logging_config import configure_logging
from src.phase0.healthcheck import run_healthcheck
from src.phase2.preferences import UserPreferences
from src.phase3.retrieve import load_cleaned_restaurants
from src.phase6.rate_limit import RateLimiter
from src.phase6.schemas import RecommendRequest, SessionCreateResponse
from src.phase6 import service
from src.phase8.schemas import FeedbackEventRequest, FeedbackEventResponse
from src.phase8.store import Phase8Store
from src.phase8.telemetry_log import log_feedback_ingested, log_recommendation_completion

_cfg = load_config()


def _groq_issue_flag(guardrail_notes: list[str]) -> bool:
    return any(
        str(n).startswith("groq_error:") or str(n).startswith("groq_config:")
        for n in guardrail_notes
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = _cfg
    configure_logging(_cfg.log_level)
    app.state.rate_limiter = RateLimiter(_cfg.api_rate_limit_per_minute)
    app.state.restaurant_df = load_cleaned_restaurants()
    app.state.phase8_store = Phase8Store(_cfg.feedback_sqlite_path)
    yield


http_app = FastAPI(
    title="NextLeap Zomato Recommendation API",
    version="1.0.0",
    description=(
        "Phases 6 & 8: recommendation API plus feedback ingestion, "
        "telemetry summaries, and prompt-version tagging."
    ),
    lifespan=lifespan,
)

http_app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_cfg.cors_origins),
    allow_origin_regex=_cfg.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def enforce_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    request.app.state.rate_limiter.hit(client)


@http_app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


@http_app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    cfg = getattr(request.app.state, "config", _cfg)
    if cfg.environment.lower() == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


@http_app.get("/")
def root():
    """Base URL hit in the browser otherwise returns FastAPI's default JSON 404."""
    return {
        "service": http_app.title,
        "hint": "No resource at /. Use GET /health, POST /api/v1/recommend, or /docs.",
        "health": "/health",
        "openapi_docs": "/docs",
    }


@http_app.get("/health")
def health_check(request: Request):
    cfg = request.app.state.config
    checks = run_healthcheck()
    checks["groq_configured"] = str(bool(cfg.groq_api_key))
    checks["restaurant_rows"] = str(len(request.app.state.restaurant_df))
    checks["prompt_version"] = cfg.prompt_version
    checks["feedback_db"] = str(cfg.feedback_sqlite_path)
    checks["cors_origin_regex"] = str(bool(cfg.cors_origin_regex))
    checks["render_hosted"] = str(os.getenv("RENDER", "").lower() == "true")
    return checks


@http_app.post("/api/v1/sessions", response_model=SessionCreateResponse)
def create_preference_session(
    preferences: UserPreferences,
    request: Request,
    _: None = Depends(enforce_rate_limit),
):
    session_id = service.create_session(preferences)
    return SessionCreateResponse(session_id=session_id)


@http_app.post("/api/v1/recommend")
def recommend(
    body: RecommendRequest,
    request: Request,
    _: None = Depends(enforce_rate_limit),
):
    df = request.app.state.restaurant_df
    cfg = request.app.state.config
    phase8_store: Phase8Store = request.app.state.phase8_store
    run_id = str(uuid.uuid4())
    try:
        if body.session_id is not None:
            outcome = service.recommend_from_session(
                body.session_id,
                restaurant_df=df,
                config=cfg,
                max_candidates=body.max_candidates,
                top_n=body.top_n,
                include_raw_llm=body.include_raw_llm,
            )
        else:
            outcome = service.recommend_from_preferences(
                body.preferences,
                restaurant_df=df,
                config=cfg,
                max_candidates=body.max_candidates,
                top_n=body.top_n,
                include_raw_llm=body.include_raw_llm,
            )
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session_id") from None

    notes_list = list(outcome.data.get("guardrail_notes") or [])
    groq_issue = _groq_issue_flag(notes_list)
    n_results = len(outcome.data.get("recommendations") or [])

    phase8_store.record_recommendation_run(
        run_id=run_id,
        retrieval_ms=outcome.retrieval_ms,
        ranking_ms=outcome.ranking_ms,
        num_results=n_results,
        groq_issue=groq_issue,
        guardrail_notes=notes_list,
        prompt_version=cfg.prompt_version,
    )
    log_recommendation_completion(
        recommendation_run_id=run_id,
        retrieval_ms=outcome.retrieval_ms,
        ranking_ms=outcome.ranking_ms,
        num_results=n_results,
        groq_issue=groq_issue,
        prompt_version=cfg.prompt_version,
    )

    response = JSONResponse(content=outcome.data)
    response.headers["X-Recommendation-Run-Id"] = run_id
    response.headers["X-Timing-Retrieval-Ms"] = f"{outcome.retrieval_ms:.3f}"
    response.headers["X-Timing-Ranking-Ms"] = f"{outcome.ranking_ms:.3f}"
    response.headers["X-Prompt-Version"] = cfg.prompt_version
    return response


@http_app.post("/api/v1/feedback", response_model=FeedbackEventResponse)
def ingest_feedback(
    body: FeedbackEventRequest,
    request: Request,
    _: None = Depends(enforce_rate_limit),
):
    store: Phase8Store = request.app.state.phase8_store
    event_id = store.add_feedback(body)
    log_feedback_ingested(
        event_id=event_id,
        recommendation_run_id=body.recommendation_run_id,
        event_type=body.event_type,
        record_id=body.record_id,
    )
    return FeedbackEventResponse(stored=True, event_id=event_id)


@http_app.get("/api/v1/telemetry/summary")
def telemetry_summary(request: Request, hours: float = 24.0):
    store: Phase8Store = request.app.state.phase8_store
    if hours <= 0 or hours > 24 * 90:
        raise HTTPException(status_code=422, detail="hours must be in (0, 2160]")
    return store.summarize(window_hours=hours)
