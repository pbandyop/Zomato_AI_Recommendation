# NextLeap Zomato Recommendation System

This repository contains a phased implementation of an AI-powered restaurant recommendation system.

## Project Structure

- `src/common/`: shared configuration and logging utilities
- `src/phase0/`: foundation bootstrap and healthcheck
- `src/phase1/`: data foundation pipeline
- `src/phase2/`: preference capture and session persistence
- `src/phase3/`: candidate retrieval (filters, fallback, scoring, shortlist)
- `src/phase4/`: Groq LLM ranking, structured response parsing, guardrails
- `src/phase6/`: FastAPI backend (Phase 6) — API, orchestration, CORS, rate limits
- `frontend/`: Next.js UI — form + recommendation cards calling the API
- `tests/phase0/` … `tests/phase6/`: phase-wise tests

Production deployment (Render backend + Vercel frontend): see **`docs/deployment-render-vercel.md`**.

## Phase 0 (Implemented)

Phase 0 establishes project foundations required before the architecture phases:

- Centralized config loading via environment variables
- Logging setup
- Bootstrap script for directory creation
- Healthcheck script to verify runtime setup
- Basic web UI as the primary source of user preference input (planned in Phase 0 scope)

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment template:

```bash
cp .env.example .env
```

## Run Phase 0

Bootstrap directories:

```bash
python -m src.phase0.bootstrap
```

Run healthcheck:

```bash
python -m src.phase0.healthcheck
```

## Run Phase 1 (Data Foundation Layer)

This phase ingests the Hugging Face dataset, cleans key fields, standardizes schema, and stores outputs.

```bash
python -m src.phase1.data_foundation
```

Generated artifacts:

- `data/raw/restaurants_raw.csv`
- `data/processed/restaurants_cleaned.csv`
- `data/processed/restaurants.db` (table: `restaurants_cleaned`)

## Run Phase 2 (Preference Capture Layer)

This phase validates user inputs (location, budget, cuisines, minimum rating, optional preferences)
and stores per-session preference state for downstream recommendation phases.

Run with demo payload:

```bash
python -m src.phase2.capture --demo
```

Run with custom payload:

```bash
python -m src.phase2.capture --payload "{\"location\":\"Delhi\",\"budget\":\"medium\",\"cuisines\":[\"North Indian\",\"Chinese\"],\"minimum_rating\":4.1}"
```

Generated artifact:

- `data/processed/preference_sessions.json`

## Run Phase 3 (Candidate Retrieval Layer)

Loads `data/processed/restaurants_cleaned.csv`, applies rule-based filters (location, budget, rating, cuisine),
runs a **fallback chain** when there are no matches, then builds a scored shortlist (default **30** rows) for Phase 4 / LLM.

**Using inline preferences (JSON):**

```bash
python -m src.phase3.retrieve --payload "{\"location\":\"bangalore\",\"budget\":\"medium\",\"cuisines\":[\"north indian\"],\"minimum_rating\":4.0}"
```

**Using a Phase 2 session id:**

```bash
python -m src.phase3.retrieve --session-id YOUR_SESSION_UUID
```

Optional: `--csv PATH` to override the cleaned CSV path, `--max-candidates N` to change the shortlist size.

The printed JSON includes `applied_fallbacks`, `candidate_count_before_cap`, `preferences_summary`, and `candidates`.

## Run Phase 4 (LLM Reasoning and Ranking — Groq)

Requires a [Groq](https://console.groq.com/) API key. Set `GROQ_API_KEY` (and optionally `GROQ_MODEL`) in `.env`; see `.env.example`.

Runs Phase 3 internally to build the candidate shortlist, then calls **Groq** `chat.completions` to rank and explain. Only `record_id`s from the shortlist are kept (**guardrails**). If the API or JSON parsing fails, output falls back to deterministic `match_score` ordering.

```bash
python -m src.phase4.recommend --payload "{\"location\":\"bangalore\",\"budget\":\"medium\",\"cuisines\":[\"north indian\"],\"minimum_rating\":4.0}"
```

With a Phase 2 session:

```bash
python -m src.phase4.recommend --session-id YOUR_SESSION_UUID
```

Options: `--csv`, `--max-candidates`, `--top-n`, `--include-raw-llm`. On Windows, prefer `--payload-file` with a JSON file to avoid quoting issues.

Example payload file (Bellandur, ~₹2000, rating ≥ 4.0; `budget` is `high` because Phase 1 maps cost > ₹1200 to high):

```bash
python -m src.phase4.recommend --payload-file examples/phase4_bellandur_payload.json --top-n 5 --max-candidates 50
```

## Run Phase 6 (Backend API)

HTTP API that orchestrates **Phases 2→3→4→5**: validates preferences, loads the Phase 1 dataset (cached in memory at startup), calls Groq for ranking, returns the same JSON shape as the Phase 4 CLI (without printing logs to stdout for normal requests).

**Start the server** (from repo root, after `pip install -r requirements.txt` and Phase 1 data exists):

```bash
uvicorn src.phase6.app:http_app --reload --host 127.0.0.1 --port 8000
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Phase 0-style checks + `groq_configured` + `restaurant_rows` + `render_hosted` / `cors_origin_regex` flags |
| `POST` | `/api/v1/sessions` | Body: Phase 2 preferences JSON → `{ "session_id": "..." }` |
| `POST` | `/api/v1/recommend` | Body: `{ "preferences": {...} }` **or** `{ "session_id": "..." }`, plus optional `max_candidates`, `top_n`, `include_raw_llm` |

**Environment** (see `.env.example`): `CORS_ORIGINS`, optional `CORS_ORIGIN_REGEX` (e.g. Vercel previews), `API_RATE_LIMIT_PER_MINUTE`, `GROQ_API_KEY`, `GROQ_MODEL`, `APP_ENV` (`production` hides internal error details).

**Render:** root **`render.yaml`** defines the Python web service (`uvicorn`, `$PORT`, `/health`). Full checklist: **`docs/deployment-render-vercel.md`**.

**Example (recommend with inline preferences):**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/recommend -H "Content-Type: application/json" -d "{\"preferences\":{\"location\":\"bangalore\",\"budget\":\"medium\",\"cuisines\":[\"north indian\"],\"minimum_rating\":4.0},\"top_n\":5}"
```

OpenAPI docs: `http://127.0.0.1:8000/docs`.

## Run frontend (Next.js)

The app lives in **`frontend/`**. You need **Node.js** installed (`npm` on your PATH).

```bash
cd frontend
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000). See `frontend/README.md` for details.

## Run backend and frontend together

**Terminal 1 — API (from repo root):**

```bash
uvicorn src.phase6.app:http_app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — Next.js:**

```bash
cd frontend
npm install
npm run dev
```

## Run Tests

```bash
pytest -q
```
