# Next.js frontend (Phase 7)

Requires **Node.js 20+** (includes `npm`). See [nodejs.org](https://nodejs.org/).

## Setup

```bash
cd frontend
copy .env.local.example .env.local
npm install
```

`.env.local` should set `NEXT_PUBLIC_API_BASE_URL` to your Phase 6 API (default `http://127.0.0.1:8000`). The UI calls **`/api/recommend`** on this Next.js app; the server proxies that request to your API, so **`CORS` from browser → Render is avoided** on Vercel. For local tooling that still hits the API directly from the browser, keep `CORS_ORIGINS` on the backend aligned with `.env.example` (`http://localhost:3000`, etc.).

## Dev server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Ensure the Phase 6 API is running:

```bash
# from repository root
uvicorn src.phase6.app:http_app --host 127.0.0.1 --port 8000
```

## Production

```bash
npm run build
npm start
```

For **Vercel** + **Render** API, follow [`docs/deployment-render-vercel.md`](../docs/deployment-render-vercel.md).

### Vercel project settings (monorepo)

| Setting | Value |
|--------|--------|
| **Root Directory** | `frontend` |
| **Framework** | Next.js (or rely on `vercel.json`) |
| **Environment Variables** | `NEXT_PUBLIC_API_BASE_URL` **or** `API_BACKEND_ORIGIN` = `https://your-service.onrender.com` (Production; Preview if needed). Prefer `API_BACKEND_ORIGIN` to keep the Render host out of the client bundle — the proxy resolves it server-side (`lib/backendOrigin.ts`). |

Committed assets: `vercel.json`, `.nvmrc` (Node 20), `app/api/recommend/route.ts` & `app/api/feedback/route.ts` (Render proxy), `lib/publicApi.ts`, `lib/backendOrigin.ts`.
