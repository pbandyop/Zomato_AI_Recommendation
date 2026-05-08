import { NextResponse, type NextRequest } from "next/server";

import { abortAfter, resolvedBackendOrigin } from "@/lib/backendOrigin";

export const runtime = "nodejs";

const TIMEOUT_MS = 120_000;

function backendNotConfiguredResponse() {
  return NextResponse.json(
    {
      detail:
        "Missing backend URL. Set API_BACKEND_ORIGIN (preferred) or NEXT_PUBLIC_API_BASE_URL to your Render HTTPS origin on Vercel, then redeploy.",
    },
    { status: 503 },
  );
}

export async function POST(req: NextRequest) {
  const base = resolvedBackendOrigin();
  if (!base) {
    return backendNotConfiguredResponse();
  }

  const body = await req.text();

  let upstream: Response;
  try {
    upstream = await fetch(`${base}/api/v1/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": req.headers.get("content-type") || "application/json",
        Accept: "application/json",
      },
      body,
      cache: "no-store",
      signal: abortAfter(TIMEOUT_MS),
    });
  } catch {
    return NextResponse.json(
      { detail: `Upstream unreachable: ${base}` },
      { status: 502 },
    );
  }

  const out = new NextResponse(await upstream.arrayBuffer(), {
    status: upstream.status,
  });

  const ct = upstream.headers.get("content-type");
  if (ct) out.headers.set("Content-Type", ct);

  for (const h of [
    "X-Recommendation-Run-Id",
    "X-Timing-Retrieval-Ms",
    "X-Timing-Ranking-Ms",
    "X-Prompt-Version",
    "X-Request-ID",
  ] as const) {
    const v = upstream.headers.get(h);
    if (v) out.headers.set(h, v);
  }

  return out;
}
