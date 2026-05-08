"""Streamlit UI for restaurant recommendations (Streamlit deployment phase)."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv()

import streamlit as st


def _inject_streamlit_secrets() -> None:
    try:
        sec = st.secrets
    except FileNotFoundError:
        return
    for key in ("GROQ_API_KEY", "GROQ_MODEL", "STREAMLIT_API_BASE_URL"):
        if key in sec:
            os.environ.setdefault(key, str(sec[key]))


_inject_streamlit_secrets()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("streamlit_app")

st.set_page_config(
    page_title="NextLeap Zomato Recommendations",
    page_icon="🍽️",
    layout="centered",
)


@st.cache_resource(show_spinner=False)
def _cached_config():
    from src.common.config import load_config

    return load_config()


@st.cache_resource(show_spinner=False)
def _cached_restaurant_df():
    from src.phase3.retrieve import load_cleaned_restaurants

    return load_cleaned_restaurants()


def _default_backend_mode() -> str:
    return os.getenv("STREAMLIT_BACKEND", "local").strip().lower()


def _recommend_via_api(
    prefs: dict, *, max_candidates: int, top_n: int, api_base: str
) -> dict:
    base = api_base.rstrip("/")
    url = f"{base}/api/v1/recommend"
    r = requests.post(
        url,
        json={
            "preferences": prefs,
            "max_candidates": max_candidates,
            "top_n": top_n,
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def _recommend_local(
    prefs: dict, *, max_candidates: int, top_n: int
) -> dict:
    from src.phase2.preferences import UserPreferences
    from src.phase6.service import recommend_from_preferences

    user = UserPreferences.model_validate(prefs)
    cfg = _cached_config()
    df = _cached_restaurant_df()
    outcome = recommend_from_preferences(
        user,
        restaurant_df=df,
        config=cfg,
        max_candidates=max_candidates,
        top_n=top_n,
        include_raw_llm=False,
    )
    return outcome.data


def main() -> None:
    st.title("Find your next meal")
    st.caption(
        "Streamlit deployment — same pipeline as the Phase 6 API (local mode) "
        "or HTTP calls (api mode)."
    )

    default_mode = _default_backend_mode()
    with st.sidebar:
        st.subheader("Backend")
        mode = st.radio(
            "How to run recommendations",
            ["local", "api"],
            index=0 if default_mode == "local" else 1,
            help=(
                "**local**: in-process (Phase 6 service stack). "
                "**api**: `POST /api/v1/recommend` on your FastAPI base URL."
            ),
        )
        api_base = os.getenv(
            "STREAMLIT_API_BASE_URL", "http://127.0.0.1:8000"
        ).rstrip("/")
        if mode == "api":
            api_base = st.text_input(
                "API base URL",
                value=api_base,
            ).rstrip("/")

    cfg = _cached_config()
    st.sidebar.info(
        f"Env: **{cfg.environment}** · Groq key: "
        f"**{'set' if cfg.groq_api_key else 'missing'}** · "
        f"PROMPT_VERSION: **{cfg.prompt_version}**"
    )

    with st.form("prefs"):
        location = st.text_input("Location", value="Bangalore")
        budget = st.selectbox("Budget", ["low", "medium", "high"], index=1)
        cuisines_text = st.text_input(
            "Cuisines (comma-separated)", value="North Indian, Chinese"
        )
        minimum_rating = st.slider(
            "Minimum rating", min_value=0.0, max_value=5.0, value=4.0, step=0.1
        )
        additional = st.text_area(
            "Additional preferences (optional)", height=72, placeholder="e.g. date night"
        )
        max_candidates = st.number_input("Max candidates", 5, 200, 30)
        top_n = st.number_input("Top N", 1, 50, 10)
        submitted = st.form_submit_button("Get recommendations", type="primary")

    if not submitted:
        return

    cuisines = [
        p.strip()
        for p in cuisines_text.replace("|", ",").replace("/", ",").split(",")
        if p.strip()
    ]
    prefs: dict = {
        "location": location.strip(),
        "budget": budget,
        "cuisines": cuisines,
        "minimum_rating": float(minimum_rating),
    }
    if additional.strip():
        prefs["additional_preferences"] = [additional.strip()]

    try:
        with st.spinner("Ranking restaurants…"):
            if mode == "api":
                data = _recommend_via_api(
                    prefs,
                    max_candidates=int(max_candidates),
                    top_n=int(top_n),
                    api_base=api_base,
                )
            else:
                data = _recommend_local(
                    prefs,
                    max_candidates=int(max_candidates),
                    top_n=int(top_n),
                )
    except requests.RequestException as exc:
        logger.exception("Recommendation API error: %s", exc)
        detail = ""
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            detail = exc.response.text or ""
        st.error(f"API request failed ({exc}). {detail[:500]}")
        st.info(
            "Start the backend: "
            "`uvicorn src.phase6.app:http_app --host 127.0.0.1 --port 8000`"
        )
        return
    except Exception as exc:
        logger.exception("Recommendation failed: %s", exc)
        st.error(f"Something went wrong: {exc}")
        st.info(
            "Ensure `GROQ_API_KEY` is set and `data/processed/restaurants_cleaned.csv` exists."
        )
        return

    fallbacks = data.get("applied_fallbacks") or []
    if fallbacks and not (len(fallbacks) == 1 and fallbacks[0] == "strict"):
        st.warning("Search was adjusted: " + ", ".join(str(f) for f in fallbacks))

    recs = data.get("recommendations") or []
    if not recs:
        st.info("No recommendations returned. Try relaxing filters.")
        return

    st.subheader("Top picks")
    for r in recs:
        rank = r.get("rank", 0)
        title = f"#{rank} — {r.get('restaurant_name', 'Restaurant')}"
        expanded = rank == 1
        with st.expander(title, expanded=expanded):
            cost = r.get("estimated_cost")
            cost_s = f"₹{cost}" if cost is not None else "—"
            st.write(
                f"📍 {r.get('location')} · ⭐ {r.get('rating')} · {cost_s} for two · "
                f"{r.get('cuisines', '')}"
            )
            st.write(r.get("explanation", "") or "")
            conf = float(r.get("confidence") or 0)
            st.caption(f"Confidence: {round(conf * 100)}%")

    st.caption(f"Model: **{data.get('model', '?')}**")

    gn = data.get("guardrail_notes") or []
    if gn:
        with st.expander("Technical notes (guardrails / fallbacks)", expanded=False):
            st.code(json.dumps(gn, indent=2))


main()
