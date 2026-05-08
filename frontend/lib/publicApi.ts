/**
 * Public (browser) origin for the Phase 6 API.
 * Must match `NEXT_PUBLIC_API_BASE_URL` on Vercel — no trailing slash (see docs/deployment-render-vercel.md).
 */
export function getPublicApiBaseUrl(): string {
  const fallback = "http://127.0.0.1:8000";
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!raw) return fallback;
  const normalized = raw.replace(/\/+$/, "");
  return normalized || fallback;
}
