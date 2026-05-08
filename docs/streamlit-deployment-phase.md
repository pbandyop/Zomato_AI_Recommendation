# Streamlit Deployment Phase

## Purpose

Define how to package and run the recommendation system as an interactive Streamlit app for demos, internal testing, and lightweight production usage.

## Goal

Package and deploy the recommendation system as an interactive Streamlit app for demos, internal testing, and lightweight production usage.

## Components

- **Streamlit app shell:** Single entrypoint (`streamlit run`) with a clean layout for preference input and recommendation output.
- **Backend integration strategy:** Either direct calls to the Phase 6 API or in-process invocation of orchestration services for local deployments.
- **Environment and secrets management:** Configure API base URL, `GROQ_API_KEY`, and model settings using environment variables and `.env` files.
- **Deployment target:** Host on Streamlit Community Cloud, Docker container, or VM with startup command, health checks, and restart policy.
- **Operational readiness:** Basic logging, error messages in UI, and version pinning for reproducible deployments.

## Output

A deployable Streamlit artifact that exposes the end-to-end recommendation flow with minimal setup.

---

## Repository layout & run commands

Artifacts live in-repo:

| Artifact | Purpose |
|----------|---------|
| `streamlit_app.py` | **Default entry** for Streamlit Cloud / `streamlit run`. |
| `streamlit_app/app.py` | Streamlit UI implementation (form + results). |
| `.streamlit/config.toml` | Server bind (`0.0.0.0:8501`), headless defaults. |
| `Dockerfile.streamlit` | Immutable image with app + pinned deps from `requirements.txt`. |
| `docker-compose.streamlit.yml` | Optional **API + Streamlit** stack (UI uses `STREAMLIT_BACKEND=api`). |

### Backend integration

- **`STREAMLIT_BACKEND=local` (default):** Runs `src.phase6.service.recommend_from_preferences` in-process (same stack as FastAPI); needs `data/processed/restaurants_cleaned.csv` and `GROQ_API_KEY`.
- **`STREAMLIT_BACKEND=api`:** Sends `POST {STREAMLIT_API_BASE_URL}/api/v1/recommend` (same contract as Phase 7). Use base URL **`http://api:8000`** when both services run inside `docker-compose.streamlit.yml`.

### Environment & secrets

- Local / Docker: reuse root **`.env`** (`python-dotenv`); see **`.env.example`** for `STREAMLIT_*` knobs.
- [Streamlit Community Cloud](https://streamlit.io/cloud): configure **`GROQ_API_KEY`** (and optional `STREAMLIT_BACKEND` / URL) via app **Secrets**.

### Operational commands

Local (repo root):

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Single container (`local` backend inside the container):

```bash
docker build -f Dockerfile.streamlit -t nextleap-zomato:streamlit .
docker run --rm -p 8501:8501 \
  --env-file .env \
  -v "$(pwd)/data/processed/restaurants_cleaned.csv:/app/data/processed/restaurants_cleaned.csv:ro" \
  nextleap-zomato:streamlit
```

API + Streamlit:

```bash
docker compose -f docker-compose.streamlit.yml --env-file .env up --build
```

Docker **healthchecks** probe `/_stcore/health` (Streamlit) and `/health` (FastAPI compose service).
