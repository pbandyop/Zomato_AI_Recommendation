import { NextResponse, type NextRequest } from "next/server";

import { abortAfter, resolvedBackendOrigin } from "@/lib/backendOrigin";

export const runtime = "nodejs";

const TIMEOUT_MS = 120_000;

/** Remove retrieval fallback tags so stale client bundles cannot show the old fallback banner. */
function stripAppliedFallbacksFromJsonBody(raw: ArrayBuffer): BodyInit {
  try {
    const text = new TextDecoder().decode(raw);
    const parsed = JSON.parse(text) as Record<string, unknown>;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return raw;
    if (!("applied_fallbacks" in parsed)) return raw;
    delete parsed.applied_fallbacks;
    return JSON.stringify(parsed);
  } catch {
    return raw;
  }
}

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

  const requestPayload = await req.text();

  let upstream: Response;
  try {
    upstream = await fetch(`${base}/api/v1/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": req.headers.get("content-type") || "application/json",
        Accept: "application/json",
      },
      body: requestPayload,
      cache: "no-store",
      signal: abortAfter(TIMEOUT_MS),
    });
  } catch {
    return NextResponse.json(
      { detail: `Upstream unreachable: ${base}` },
      { status: 502 },
    );
  }

  const raw = await upstream.arrayBuffer();
  const ct = upstream.headers.get("content-type") ?? "";

  let responseBody: BodyInit = raw;
  if (upstream.ok && ct.includes("application/json")) {
    const stripped = stripAppliedFallbacksFromJsonBody(raw);
    if (typeof stripped === "string") responseBody = stripped;
  }

  const out = new NextResponse(responseBody, {
    status: upstream.status,
  });

  if (typeof responseBody === "string") {
    out.headers.set("Content-Type", "application/json; charset=utf-8");
  } else if (ct) out.headers.set("Content-Type", ct);

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
