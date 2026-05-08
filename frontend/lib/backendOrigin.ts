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

/** Rejects common mistaken values like pasting `API_BACKEND_ORIGIN` or `api_backend_origin` instead of an URL. */
function looksLikeLiteralEnvKeyOrPlaceholder(raw: string, hostname: string): boolean {
  const s = raw.toLowerCase().replace(/^https?:\/\//, "");
  if (hostname === "api_backend_origin") return true;
  if (/^api_backend_origin\/?$/i.test(s)) return true;
  return /^NEXT_PUBLIC_API_BASE_URL$/i.test(hostname) || /^API_BACKEND_ORIGIN$/i.test(hostname);
}

function originFromFlexibleBase(rawBase: string): string | "" {
  const base = trimOrigin(rawBase);
  if (!base) return "";
  try {
    const u = new URL(base.startsWith("http") ? base : `https://${base}`);
    if (looksLikeLiteralEnvKeyOrPlaceholder(base, u.hostname)) {
      console.warn(
        "[backendOrigin] Ignoring malformed API/backend URL (looks like a placeholder, not Render):",
        u.hostname,
      );
      return "";
    }
    return u.origin;
  } catch {
    return "";
  }
}

/** Prefer API_BACKEND_ORIGIN; else NEXT_PUBLIC_API_BASE_URL unless it is localhost in production. */
export function resolvedBackendOrigin(): string {
  const primary = process.env.API_BACKEND_ORIGIN
    ? originFromFlexibleBase(process.env.API_BACKEND_ORIGIN)
    : "";
  if (primary) return primary;

  const fallback = process.env.NEXT_PUBLIC_API_BASE_URL
    ? originFromFlexibleBase(process.env.NEXT_PUBLIC_API_BASE_URL)
    : "";
  if (!fallback) return "";

  try {
    const u = new URL(fallback);
    const loop = u.hostname === "localhost" || u.hostname === "127.0.0.1";
    if (loop && process.env.NODE_ENV === "production") return "";
    return fallback;
  } catch {
    return "";
  }
}
