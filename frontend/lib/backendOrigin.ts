/**
 * Server-only: URL of the FastAPI service (Render). Used by `/app/api/*` Route Handlers.
 * Not exposed to the browser.
 */

export function abortAfter(ms: number): AbortSignal {
  const Any = AbortSignal as unknown as { timeout?: (n: number) => AbortSignal };
  if (typeof Any.timeout === "function") return Any.timeout(ms);
  const c = new AbortController();
  setTimeout(() => c.abort(), ms);
  return c.signal;
}

function trimOrigin(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

/** Prefer API_BACKEND_ORIGIN; else NEXT_PUBLIC_API_BASE_URL unless it is localhost in production. */
export function resolvedBackendOrigin(): string {
  const primary = process.env.API_BACKEND_ORIGIN
    ? trimOrigin(process.env.API_BACKEND_ORIGIN)
    : "";
  if (primary) {
    try {
      const u = new URL(primary.startsWith("http") ? primary : `https://${primary}`);
      return u.origin;
    } catch {
      return "";
    }
  }

  const pub = process.env.NEXT_PUBLIC_API_BASE_URL
    ? trimOrigin(process.env.NEXT_PUBLIC_API_BASE_URL)
    : "";
  if (!pub) return "";

  try {
    const u = new URL(pub.startsWith("http") ? pub : `https://${pub}`);
    const loop = u.hostname === "localhost" || u.hostname === "127.0.0.1";
    if (loop && process.env.NODE_ENV === "production") {
      return "";
    }
    return u.origin;
  } catch {
    return "";
  }
}
