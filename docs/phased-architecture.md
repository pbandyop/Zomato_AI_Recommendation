# Phase-Wise Architecture

### Phase 0: Foundation and Input Channel Setup

**Goal:** Establish baseline project setup and define the primary user input channel as a basic web UI.

**Components:**

- **Project Bootstrap:** Config, logging, and directory initialization
- **Environment Setup:** Runtime variables and health checks
- **Basic Web UI (Input Source):** A simple form-based interface to capture user preferences
- **Input Contract:** Standardized payload shape from UI to backend (location, budget, cuisine, minimum rating, optional preferences)

**Output:**

- Stable project foundation with a basic web UI as the default source of user input

### Phase 1: Data Foundation Layer

**Goal:** Build a clean, reliable dataset for downstream recommendation logic.

**Components:**

- **Data Source Connector:** Pull dataset from Hugging Face
- **Data Cleaning Pipeline:** Handle nulls, duplicates, and inconsistent formats
- **Feature Standardization:** Normalize cuisine labels, cost ranges, and rating scales
- **Data Storage:** Store cleaned dataset in CSV/SQLite/PostgreSQL for fast querying

**Output:**

- A validated restaurant dataset ready for filtering and ranking

### Phase 2: Preference Capture Layer

**Goal:** Collect and validate user requirements before recommendation generation.

**Components:**

- **Input Interface:** CLI, web form, or chat-style UI
- **Preference Schema:** Location, budget, cuisine, minimum rating, optional constraints
- **Validation Rules:** Ensure valid city names, rating ranges, and budget categories
- **Session Context:** Persist current user choices during interaction

**Output:**

- A structured user preference object

### Phase 3: Candidate Retrieval Layer

**Goal:** Narrow the full dataset to relevant restaurant candidates.

**Components:**

- **Rule-Based Filter Engine:** Apply hard constraints (location, budget, rating)
- **Fallback Logic:** Relax non-critical filters when no results are found
- **Scoring Preprocessor:** Create comparable candidate records for LLM reasoning

**Output:**

- A shortlist of candidate restaurants matching user intent

### Phase 4: LLM Reasoning and Ranking Layer

**Goal:** Rank shortlisted restaurants and generate explainable recommendations.

**Components:**

- **Prompt Builder:** Convert user preferences + candidate data into structured prompt context
- **LLM Inference Module:** Generate ranking and recommendation narratives
- **Response Parser:** Convert model output into structured fields (rank, explanation, confidence)
- **Safety Guardrails:** Prevent hallucinated restaurants and enforce factual grounding in candidate data

**Output:**

- Ranked recommendations with personalized explanations

### Phase 5: Response Presentation Layer

**Goal:** Deliver actionable recommendations in a clear user-facing format.

**Components:**

- **Recommendation View:** Show top N restaurants with key attributes
- **Explanation Panel:** Display why each option was recommended
- **Comparison Support:** Enable side-by-side decision-making for top choices

**Output:**

- User-friendly recommendation response with reasoning (API DTO or UI model consumed by Phase 7)

### Phase 6: Backend Service & API Layer

**Goal:** Expose a proper HTTP API that orchestrates domain phases (2→3→4→5), keeps secrets server-side, and becomes the single integration point for the frontend.

**Components:**

- **Application server:** e.g. FastAPI or Flask — process lifecycle, routing, middleware (logging, request IDs, error handling).
- **Orchestration service:** One or more modules that call **Preference capture** (Phase 2), **Candidate retrieval** (Phase 3), **Groq LLM ranking** (Phase 4), and map results into a stable **recommendation response schema** (Phase 5 shape).
- **Data access:** Load cleaned restaurants from SQLite/CSV (Phase 1 artifacts); optional connection pooling or in-process cache after startup.
- **Session & state:** Replace or complement file-based `preference_sessions.json` with API-managed session identifiers (opaque tokens), or stateless requests if each call sends full preferences.
- **Configuration:** `GROQ_API_KEY`, model id, paths to data — loaded only on the server; never sent to the browser.
- **Security:** Input validation (Pydantic), rate limiting on recommendation endpoints, CORS restricted to the frontend origin(s), no stack traces to clients in production.
- **Observability:** Structured logs, timing for retrieval vs LLM, health/readiness routes (`/health`) aligned with Phase 0 healthcheck concepts.

**Output:**

- Deployable **backend** artifact (e.g. `uvicorn` service) and documented REST/JSON contract for the web client.

### Phase 7: Frontend Web Application

**Goal:** Deliver Phase 0’s “basic web UI” and Phase 5’s presentation as a dedicated client that talks only to the backend API.

**Components:**

- **UI shell & routing:** Single-page app (e.g. React + Vite) or lightweight multi-page app — home, recommendation results, optional “compare” view.
- **Preference form:** Fields aligned with Phase 2 (`location`, `budget`, `cuisines`, `minimum_rating`, `additional_preferences`); client-side hints/validation; loading and error states.
- **API client:** Typed fetch/axios calls to backend (`POST /api/v1/recommend` or split `POST /api/v1/preferences` + `POST /api/v1/recommendations`); handles session id if the API returns one.
- **Results presentation:** Cards or table for top N restaurants — name, location, cuisines, rating, estimated cost, **explanation** and **confidence** from Phase 4; optional side-by-side comparison (Phase 5).
- **UX polish:** Empty states (no candidates), messaging when retrieval used **fallback** strategies (`applied_fallbacks`), accessibility basics (focus order, contrast).

**Output:**

- Static or CDN-hosted **frontend** build plus environment config (e.g. `VITE_API_BASE_URL`) pointing at the backend.

### Phase 8: Feedback and Continuous Improvement Layer

**Goal:** Improve recommendation quality over time.

**Components:**

- **Feedback Capture:** Track likes/dislikes, clicks, and selected restaurant (frontend → backend events, stored in DB or analytics pipeline).
- **Telemetry and Monitoring:** Measure latency, recommendation quality, and failure rates across API and Groq calls.
- **Prompt Iteration Loop:** Refine prompts based on user outcomes.
- **Evaluation Harness:** Test relevance and consistency across sample user profiles.

**Output:**

- Iteratively improving recommendation performance and user satisfaction

## Full-stack view (how Phases map to code)

| Layer | Typical repo layout (suggested) | Phases covered |
|--------|--------------------------------|----------------|
| **Frontend** | `frontend/` — SPA, components, API client | 0 (UI), 5 (display), 7 |
| **Backend** | `src/phase6/app.py` — FastAPI routes, orchestration | **Phase 6** (API); orchestrates **Phases 2–5** |
| **Feedback / telemetry** | `src/phase8/` — SQLite store, `/api/v1/feedback`, `/api/v1/telemetry/summary`, eval harness (`python -m src.phase8.evaluation`) | **Phase 8** |
| **Data / jobs** | `src/phase1/`, `data/processed/` — ETL scripts | 1 |
| **Domain logic** | `src/phase2/` … `src/phase4/` — reusable from backend | 2–4 |

Secrets (e.g. `GROQ_API_KEY`) live **only** in backend environment — the frontend never embeds them.

## End-to-End Request Flow

1. User opens the **frontend** (Phase 7) and enters preferences.
2. Frontend sends JSON to the **backend API** (Phase 6).
3. Backend validates and structures input (**Phase 2**).
4. Backend runs **Phase 3** retrieval on stored restaurant data (**Phase 1** artifacts).
5. Backend calls **Phase 4** (Groq) and applies guardrails.
6. Backend returns a **Phase 5**-shaped JSON payload (ranked list + explanations + metadata such as `applied_fallbacks`, `guardrail_notes`).
7. Frontend renders recommendations, explanations, and optional comparison UI.
8. Optional: user actions are sent back for **Phase 8** feedback and monitoring.
