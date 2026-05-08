/**
 * Browser fetch helpers for recommendation calls (Render cold starts; friendly errors).
 */

/** Long enough for Render free-tier wake + Groq round-trip */
export const PUBLIC_API_FETCH_MS = 120_000;

export function publicApiAbortSignal(ms: number = PUBLIC_API_FETCH_MS): AbortSignal {
  const Ab = AbortSignal as unknown as { timeout?: (n: number) => AbortSignal };
  if (typeof Ab.timeout === "function") {
    return Ab.timeout(ms);
  }
  const c = new AbortController();
  setTimeout(() => c.abort(), ms);
  return c.signal;
}

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

/** `troubleshootApiOrigin` — base URL whose `/health` you can open to wake/debug Render (often `NEXT_PUBLIC_API_BASE_URL`). */
export function explainRecommendFetchFailure(
  troubleshootApiOrigin: string,
  err: unknown,
): string {
  if (isAbortError(err)) {
    const h = troubleshootApiOrigin.replace(/\/+$/, "");
    return (
      `Timed out after ${PUBLIC_API_FETCH_MS / 1000}s. Render's free tier can take 30–60s to wake after sleep — try again. ` +
      `Open ${h}/health in a new tab until you see JSON, then retry.`
    );
  }
  const msg =
    err instanceof Error ? err.message : String(err ?? "").toLowerCase();
  const looksNetwork =
    typeof msg === "string" && /failed to fetch|networkerror|load failed/i.test(msg);
  if (looksNetwork) {
    return (
      `Network error reaching this site’s /api/recommend route (same-origin on Vercel). ` +
      `Check connectivity and retry. If it keeps failing, open Vercel → Deployments → your deployment → Functions ` +
      `and look for errors on POST /api/recommend. ` +
      `Typically the Next.js runtime could not reach Render: set API_BACKEND_ORIGIN (preferred, server-only on Vercel) or ` +
      `NEXT_PUBLIC_API_BASE_URL to your Render HTTPS origin (no trailing slash) for Production, then redeploy ` +
      `so the env is applied.`
    );
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Something went wrong calling the recommendation API.";
}
