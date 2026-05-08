# Next.js frontend (Phase 7)

Requires **Node.js 20+** (includes `npm`). See [nodejs.org](https://nodejs.org/).

## Setup

```bash
cd frontend
copy .env.local.example .env.local
npm install
```

`.env.local` should set `NEXT_PUBLIC_API_BASE_URL` to your API (default `http://127.0.0.1:8000`). The backend must allow this origin via `CORS_ORIGINS` (see repo root `.env.example` — `http://localhost:3000` is included).

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
