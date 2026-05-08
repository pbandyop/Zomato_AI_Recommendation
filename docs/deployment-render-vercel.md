# Deployment plan: Render (backend) + Vercel (frontend)

Split production into two deployments: **FastAPI** on [Render](https://render.com/docs) (Python web service) and **Next.js** on [Vercel](https://vercel.com/docs) (frontend). The browser only talks to Vercel. The **`POST /api/recommend`** and **`POST /api/feedback`** [Route Handlers](https://nextjs.org/docs/app/building-your-application/routing/route-handlers) run on Vercel and **server-fetch** Render (`…/api/v1/recommend` and `…/api/v1/feedback`), which **removes browser CORS** issues for those calls. Configure the Render origin with **`API_BACKEND_ORIGIN`** (recommended, server-only) or **`NEXT_PUBLIC_API_BASE_URL`** (also used as a fallback resolver in `frontend/lib/backendOrigin.ts`).

---

## Prerequisites

| Item | Notes |
|------|------|
| Git repo | Connected to GitHub (e.g. [pbandyop/Zomato_AI_Recommendation](https://github.com/pbandyop/Zomato_AI_Recommendation)). |
| Groq API key | Set on Render as a secret (`GROQ_API_KEY`). |
| Dataset in repo | `data/processed/restaurants_cleaned.csv` must ship with deploys (tracked in Git). Raw CSV stays out of Git (Phase 1 pipeline). |

**Deploy order:** create the **Render** service first → copy the public HTTPS API URL → set **`API_BACKEND_ORIGIN`** (or `NEXT_PUBLIC_API_BASE_URL`) on **Vercel** → redeploy the frontend. **CORS** on Render remains useful for tools that hit the API directly from the browser; it is **not required** for the default Vercel UI path, which proxies server-side.

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
| `API_BACKEND_ORIGIN` | Production (and Preview if you use previews) | `https://<your-render-host>.onrender.com` (**no trailing slash**). **Preferred:** server-side only — not inlined into client JS; used by `frontend/app/api/recommend/route.ts` and `frontend/app/api/feedback/route.ts`. |
| `NEXT_PUBLIC_API_BASE_URL` | Same scopes *(optional when `API_BACKEND_ORIGIN` is set)* | Same Render URL **or** `http://127.0.0.1:8000` locally. If set, proxies fall back to it when `API_BACKEND_ORIGIN` is absent (`frontend/lib/backendOrigin.ts`). In **production**, a value pointing at **`localhost` / `127.0.0.1` is ignored** so the bundle never wedges the server proxy to your laptop. Also used for **`/health` troubleshooting** hints in `frontend/lib/publicApi.ts` (stripped slash, localhost default when unset). |

After changing env vars, **redeploy Vercel** so Route Handlers pick up **`API_BACKEND_ORIGIN`**; **`NEXT_PUBLIC_*`** still requires a **rebuild** to refresh values baked into client code.

### Build

Recommended flow (also set in `frontend/vercel.json`):

- Install: `npm install` (from `frontend/`)
- Build: `npm run build`

### Frontend files tied to Vercel

| File | Role |
|------|------|
| `frontend/vercel.json` | Framework + explicit install/build commands for the `frontend/` root. |
| `frontend/.nvmrc` | Node **20** (local tools; Vercel can use **[Project Settings → Node.js Version](https://vercel.com/docs/functions/runtimes/node-js)** to match). |
| `frontend/lib/backendOrigin.ts` | Server-only resolver: **`API_BACKEND_ORIGIN`** → else **`NEXT_PUBLIC_API_BASE_URL`**, prod localhost guardrails. |
| `frontend/app/api/recommend/route.ts` | Proxies **`POST`** to Render **`…/api/v1/recommend`**, forwards key response headers (`X-Recommendation-Run-Id`, timings, etc.). |
| `frontend/app/api/feedback/route.ts` | Proxies **`POST`** to **`…/api/v1/feedback`**. |
| `frontend/lib/publicApi.ts` | Normalizes **`NEXT_PUBLIC_API_BASE_URL`** for troubleshooting copy + client-side defaults. |
| `frontend/.env.local.example` | Template for local + notes for dashboard env vars. |

---

## Verification checklist

1. **`GET https://<render>/health`** → 200 JSON with `groq_configured`, `restaurant_rows`.
2. From the deployed Vercel site, submit the form → DevTools **Network** shows **`POST`** to **`/api/recommend`** on your Vercel host with **200**. The Route Handler then server-fetches **`POST https://<render>/api/v1/recommend`**, so missing Render **CORS** entries do **not** break this browser flow.
3. **Secrets:** `GROQ_API_KEY` stays on Render only; **`API_BACKEND_ORIGIN`** is backend URL metadata (not Groq secrets) and is preferable to widening `NEXT_PUBLIC_*` if you want the Render hostname out of shipped client JS.

---

## Troubleshooting: “No Next.js version detected” / Could not identify Next.js version

**Cause:** Vercel is building from the **repository root**. This monorepo’s root has **no `package.json` with `next`** — Next.js lives under **`frontend/package.json`** only.

**Fix (recommended):**

1. Open **[Vercel Dashboard](https://vercel.com/dashboard)** → your project → **Settings** → **General**.
2. Find **Root Directory** (sometimes under **Build & Development Settings**).
3. Change it from **`./`** (empty/root) to **`frontend`** exactly (lowercase, no slashes).
4. Save, then trigger a **new deployment** (**Deployments → Redeploy** or push a commit).

**Verify:**

- After saving, **Build Logs** should run `npm install` / `next build` in `frontend/` and detect **Next.js 15**.
- **`GROQ_API_KEY` is not required on Vercel** for this app (Groq is used only on **Render**). Keeping it on Vercel does not fix Next detection; only **Root Directory** does. Avoid **`NEXT_PUBLIC_`** prefixes for any secret keys.

**If Root Directory already says `frontend`:** confirm the Git integration branch is correct and that **`frontend/package.json`** exists on that branch (paths are case-sensitive on Linux builders).

---

## Troubleshooting: “Failed to fetch” / help text shows `http://127.0.0.1:8000`

**Cause:** The **Vercel server proxy** (`/api/recommend`) could not resolve a **non-loopback Render URL**. Often **`NEXT_PUBLIC_API_BASE_URL` was absent at build**, so troubleshooting copy falls back to localhost; **`API_BACKEND_ORIGIN`** was also unset.

**Fix:**

1. Vercel → **Settings → Environment Variables** → set **`API_BACKEND_ORIGIN`** (preferred) = `https://<your-render-service>.onrender.com` (no **`/`** at the end). **Alternatively** set **`NEXT_PUBLIC_API_BASE_URL`** to the same value — the resolver in `frontend/lib/backendOrigin.ts` uses either.
2. Scope to **Production** (and **Preview** if you need branch hosts).
3. **Redeploy** Vercel. **`NEXT_PUBLIC_*`**, if used for hints in the bundle, updates only after **`next build`**; **`API_BACKEND_ORIGIN`** applies to Route Handlers on the **next deploy** without being embedded in browser JS.

---

## Troubleshooting: “Failed to fetch” **with** **`POST /api/recommend`** (same-origin on Vercel)

The browser talks only to **`/api/recommend`**; Vercel’s server calls Render. Typical causes:

1. **503 “Missing backend URL”** → set **`API_BACKEND_ORIGIN`** or **`NEXT_PUBLIC_API_BASE_URL`** on Vercel and redeploy.
2. **502 “Upstream unreachable”** → **`GET https://<render>/health`** should return JSON; check **Render logs** and cold-start delays.
3. **Timeout (~120s)** → free-tier sleeps; open **`/health`** in a tab, wait for JSON, retry.

Historical note: **browser `fetch`** straight to **`https://<render>/api/v1/recommend`** can fail with opaque “Failed to fetch” when **CORS** blocks the response. This repo avoids that path; if you call Render from the browser elsewhere, configure **`CORS_ORIGINS`** / **`CORS_ORIGIN_REGEX`** on Render.

---

## Troubleshooting (reference): browser-direct Render calls → **CORS** still applies

If any **browser** JavaScript hits Render **cross-origin**, FastAPI still needs **`Origin`** allowance via **`CORS_ORIGINS`** or **`CORS_ORIGIN_REGEX`** (see Part **A**, **Minimal CORS examples**).

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
