import { NextResponse, type NextRequest } from "next/server";

import { abortAfter, resolvedBackendOrigin } from "@/lib/backendOrigin";

export const runtime = "nodejs";

const TIMEOUT_MS = 30_000;

export async function POST(req: NextRequest) {
  const base = resolvedBackendOrigin();
  if (!base) {
    return NextResponse.json({ detail: "Backend URL not configured" }, { status: 503 });
  }

  const body = await req.text();

  try {
    const upstream = await fetch(`${base}/api/v1/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": req.headers.get("content-type") || "application/json",
        Accept: "application/json",
      },
      body,
      cache: "no-store",
      signal: abortAfter(TIMEOUT_MS),
    });

    const out = new NextResponse(await upstream.arrayBuffer(), {
      status: upstream.status,
    });
    const ct = upstream.headers.get("content-type");
    if (ct) out.headers.set("Content-Type", ct);
    return out;
  } catch {
    return NextResponse.json({ detail: "Upstream unreachable" }, { status: 502 });
  }
}
