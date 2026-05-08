/**
 * Normalized Phase 6 API origin from `NEXT_PUBLIC_API_BASE_URL` (no trailing slash).
 * The browser posts to `/api/recommend`; Next.js proxies to `${origin}/api/v1/recommend`.
 * Prefer server-only `API_BACKEND_ORIGIN` on Vercel (see `docs/deployment-render-vercel.md`).
 *
 * Important: Next.js inlines `NEXT_PUBLIC_*` at **build time** for the browser bundle too.
 */
export function getPublicApiBaseUrl(): string {
  const fallback = "http://127.0.0.1:8000";
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!raw) return fallback;
  const normalized = raw.replace(/\/+$/, "");
  return normalized || fallback;
}

/** True when the page is opened on a real deploy host but the API URL still resolves to localhost (misconfigured prod build). */
export function isDeployedSiteUsingLocalApiFallback(): boolean {
  if (typeof window === "undefined") return false;
  const hostname = window.location.hostname;
  if (hostname === "localhost" || hostname === "127.0.0.1") return false;

  try {
    const u = new URL(getPublicApiBaseUrl());
    return u.hostname === "localhost" || u.hostname === "127.0.0.1";
  } catch {
    return false;
  }
}
