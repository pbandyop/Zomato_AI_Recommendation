# Deployment plan: Render (backend) + Vercel (frontend)

Split production into two deployments: **FastAPI** on [Render](https://render.com/docs) (Python web service) and **Next.js** on [Vercel](https://vercel.com/docs) (frontend). The browser only talks to Vercel; the Next.js app calls your Render API using `NEXT_PUBLIC_API_BASE_URL`.

---

## Prerequisites

| Item | Notes |
|------|------|
| Git repo | Connected to GitHub (e.g. [pbandyop/Zomato_AI_Recommendation](https://github.com/pbandyop/Zomato_AI_Recommendation)). |
| Groq API key | Set on Render as a secret (`GROQ_API_KEY`). |
| Dataset in repo | `data/processed/restaurants_cleaned.csv` must ship with deploys (tracked in Git). Raw CSV stays out of Git (Phase 1 pipeline). |

**Deploy order:** create the **Render** service first → copy the public HTTPS API URL → configure **Vercel** env → tighten **CORS** on Render to match your frontend URL(s).

---

## Part A — Backend on Render

### Service type

- **Web Service** → **Python 3**
- Repository: this monorepo; **root directory** `.` (default)

### Build command

```bash
pip install -r requirements.txt
```

### Start command

Render injects **`PORT`**; uvicorn must listen on **`0.0.0.0`**:

```bash
uvicorn src.phase6.app:http_app --host 0.0.0.0 --port $PORT
```

On Render’s dashboard, **`$PORT`** is expanded correctly for the selected shell/runtime.

### Health check

- **Health check path:** `/health`
- Method: GET (Render default HTTP check)

### Environment variables

| Variable | Example / notes |
|---------|-------------------|
| `PYTHON_VERSION` | `3.12.8` (or set via Render “Python version” UI) |
| `APP_ENV` | `production` — avoids leaking tracebacks to clients (`src/phase6/app.py`). |
| `GROQ_API_KEY` | **Secret.** From [Groq console](https://console.groq.com/keys). |
| `GROQ_MODEL` | e.g. `llama-3.3-70b-versatile` (must match `.env.example`). |
| `CORS_ORIGINS` | Comma-separated **exact** frontend origins allowed to call the API from the browser via `fetch`. Include production and local dev if needed. |
| `CORS_ORIGIN_REGEX` | *(Optional)* Regex for additional origins (matches `Origin` header). Example for all Vercel previews: `https://.*\.vercel\.app` — keep patterns as tight as practical. |

**Minimal CORS examples**

- Production only:  
  `https://your-app.vercel.app`
- Production + local Next:  
  `https://your-app.vercel.app,http://localhost:3000,http://127.0.0.1:3000`

Render API URL typically looks like `https://<service-name>.onrender.com`.

**Vercel preview deployments** (`*.vercel.app` per branch) each get a distinct origin. Besides appending specific URLs to `CORS_ORIGINS`, the backend supports **`CORS_ORIGIN_REGEX`** (e.g. `https://.*\.vercel\.app`) so previews work without editing the list each time. Prefer a **tight** regex; see `.env.example`.

**Infrastructure as code:** a root **`render.yaml`** is committed for this repo; you can create the service from a [Render Blueprint](https://render.com/docs/infrastructure-as-code) and then supply `GROQ_API_KEY` / `CORS_ORIGINS` via the dashboard prompts.

Optional Phase 8 / ops (see `.env.example`):

- `FEEDBACK_SQLITE_PATH`, `API_RATE_LIMIT_PER_MINUTE`, `PROMPT_VERSION`, etc.

### Ephemeral filesystem (Phase 8 SQLite)

Feedback/telemetry SQLite defaults under `logs/`. Render’s filesystem is **ephemeral** unless you attach a [**persistent disk**](https://render.com/docs/disks); expect metrics to reset on redeploy unless you configure a persistent path or migrate to Postgres later.

---

## Part B — Frontend on Vercel

### Project setup

1. Import the Git repository in Vercel.
2. **Root Directory:** `frontend`
3. **Framework preset:** Next.js (explicit in `frontend/vercel.json`; `package.json` declares `engines.node` ≥ 20).

### Environment variables

| Variable | Scope | Value |
|---------|-------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | Production | `https://<your-render-host>.onrender.com` (**no trailing slash**) |

Mirror the same variable for **Preview** / **Development** if you use branch previews (point previews at a staging API or the same Render URL—your choice).

The UI resolves the API base in `frontend/lib/publicApi.ts`: it reads `NEXT_PUBLIC_API_BASE_URL`, **strips trailing slashes**, and defaults to `http://127.0.0.1:8000` when unset.

### Build

Recommended flow (also set in `frontend/vercel.json`):

- Install: `npm install` (from `frontend/`)
- Build: `npm run build`

### Frontend files tied to Vercel

| File | Role |
|------|------|
| `frontend/vercel.json` | Framework + explicit install/build commands for the `frontend/` root. |
| `frontend/.nvmrc` | Node **20** (local tools; Vercel can use **[Project Settings → Node.js Version](https://vercel.com/docs/functions/runtimes/node-js)** to match). |
| `frontend/lib/publicApi.ts` | Normalizes `NEXT_PUBLIC_API_BASE_URL` for `fetch()` calls. |
| `frontend/.env.local.example` | Template for local + notes for dashboard env vars. |

---

## Verification checklist

1. **`GET https://<render>/health`** → 200 JSON with `groq_configured`, `restaurant_rows`.
2. **CORS:** From the deployed Vercel site, submit the form → network tab shows `POST https://<render>/api/v1/recommend` with **200** (no CORS errors).
3. **Secrets:** `GROQ_API_KEY` never appears in frontend env (only server-side Render).

---

## `render.yaml` (in this repo)

The repository root includes **`render.yaml`** for a [Render Blueprint](https://render.com/docs/infrastructure-as-code): Python web service, `pip install`, `uvicorn` on `$PORT`, `/health`. Adjust **`region`** / **`plan`** / **`name`** as needed.

When you apply the blueprint, complete the prompted secrets **`GROQ_API_KEY`** and **`CORS_ORIGINS`**. Optionally add **`CORS_ORIGIN_REGEX`** in the Render dashboard for Vercel preview hosts.

---

## Rollback / iteration

- **Backend:** Render “Manual Deploy” → previous successful deploy.
- **Frontend:** Vercel **Deployments** → promote a prior deployment.

---

## Related repo docs

- API contract: [`README.md`](../README.md) (Phase 6).
- Local frontend: [`frontend/README.md`](../frontend/README.md).
- Secrets template: `.env.example`.
