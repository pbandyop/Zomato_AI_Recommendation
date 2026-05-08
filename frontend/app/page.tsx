"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  explainRecommendFetchFailure,
  publicApiAbortSignal,
} from "@/lib/apiFetch";
import {
  getPublicApiBaseUrl,
  isDeployedSiteUsingLocalApiFallback,
} from "@/lib/publicApi";

const TROUBLESHOOT_API_ORIGIN = getPublicApiBaseUrl();

type Rec = {
  rank: number;
  record_id: number | null;
  restaurant_name: string;
  location: string;
  cuisines: string;
  estimated_cost: number | null;
  budget_bucket: string | null;
  rating: number;
  match_score: number;
  explanation: string;
  confidence: number;
};

type ApiResponse = {
  recommendations: Rec[];
  preferences_summary: Record<string, unknown>;
  model: string;
  guardrail_notes?: string[];
};

export default function Home() {
  const [prodApiMisconfigured, setProdApiMisconfigured] = useState(false);
  const [location, setLocation] = useState("Bangalore");
  const [budget, setBudget] = useState("medium");
  const [cuisinesInput, setCuisinesInput] = useState("North Indian, Chinese");
  const [minimumRating, setMinimumRating] = useState(4);
  const [additional, setAdditional] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [recommendationRunId, setRecommendationRunId] = useState<string | null>(
    null
  );

  function sendFeedback(payload: {
    event_type: "impression" | "click" | "like" | "dislike" | "select";
    record_id?: number | null;
    client_meta?: Record<string, unknown>;
  }) {
    const body = {
      recommendation_run_id: recommendationRunId,
      session_id: null as string | null,
      record_id:
        payload.record_id !== undefined ? payload.record_id : undefined,
      event_type: payload.event_type,
      client_meta: payload.client_meta ?? {},
    };
    void fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  useEffect(() => {
    setProdApiMisconfigured(isDeployedSiteUsingLocalApiFallback());
  }, []);

  useEffect(() => {
    if (!data || !recommendationRunId) return;
    sendFeedback({
      event_type: "impression",
      client_meta: { result_count: data.recommendations.length },
    });
  }, [data, recommendationRunId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setData(null);
    setRecommendationRunId(null);

    const cuisines = cuisinesInput
      .split(/[,/|]/)
      .map((s) => s.trim())
      .filter(Boolean);

    const preferences: Record<string, unknown> = {
      location,
      budget,
      cuisines,
      minimum_rating: minimumRating,
    };
    const extras = additional.trim()
      ? [additional.trim()]
      : ([] as string[]);
    if (extras.length) preferences.additional_preferences = extras;

    try {
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          preferences,
          max_candidates: 30,
          top_n: 10,
        }),
        signal: publicApiAbortSignal(),
      });

      if (!res.ok) {
        const text = await res.text();
        let message = text.slice(0, 400);
        try {
          const j = JSON.parse(text) as { detail?: unknown };
          if (typeof j.detail === "string") message = j.detail;
        } catch {
          /* use raw slice */
        }
        throw new Error(
          res.status === 422
            ? `Invalid input: ${message}`
            : `Request failed (${res.status}): ${message}`
        );
      }

      const json = (await res.json()) as ApiResponse;
      setData(json);
      const runHeader = res.headers.get("X-Recommendation-Run-Id");
      if (runHeader) setRecommendationRunId(runHeader);
    } catch (err) {
      setError(explainRecommendFetchFailure(TROUBLESHOOT_API_ORIGIN, err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Find your next meal</h1>
      <p className="lead">
        Tell us where you are and what you like — we’ll suggest restaurants with
        short AI explanations.
      </p>

      {prodApiMisconfigured && (
        <div className="banner" role="status">
          <strong>Production backend URL looks wrong for Vercel.</strong> The
          browser calls same-origin <code>/api/recommend</code>; the Next.js
          server proxies to Render using <code>API_BACKEND_ORIGIN</code>{" "}
          (preferred, not sent to the browser) or{" "}
          <code>NEXT_PUBLIC_API_BASE_URL</code>. Your env currently resolves to{" "}
          <code>{TROUBLESHOOT_API_ORIGIN}</code>, which only works on your
          laptop. In Vercel → Settings → Environment Variables set one of those
          keys to your Render HTTPS origin (no trailing slash) for Production
          (and Preview if you use it), then redeploy.{" "}
          <code>NEXT_PUBLIC_*</code> is inlined at build time; server-only{" "}
          <code>API_BACKEND_ORIGIN</code> takes effect after redeploy without
          relying on the public prefix.
        </div>
      )}

      <div className="card">
        <form onSubmit={onSubmit}>
          <label htmlFor="location">Location</label>
          <input
            id="location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Bellandur, Delhi"
            required
            minLength={2}
          />

          <div className="row">
            <div>
              <label htmlFor="budget">Budget</label>
              <select
                id="budget"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label htmlFor="rating">Minimum rating (0–5)</label>
              <input
                id="rating"
                type="number"
                step="0.1"
                min={0}
                max={5}
                value={minimumRating}
                onChange={(e) =>
                  setMinimumRating(parseFloat(e.target.value) || 0)
                }
              />
            </div>
          </div>

          <label htmlFor="cuisines">Cuisines (comma-separated)</label>
          <input
            id="cuisines"
            value={cuisinesInput}
            onChange={(e) => setCuisinesInput(e.target.value)}
            placeholder="North Indian, Italian"
            required
          />

          <label htmlFor="additional">Additional preferences (optional)</label>
          <textarea
            id="additional"
            rows={2}
            value={additional}
            onChange={(e) => setAdditional(e.target.value)}
            placeholder="e.g. family-friendly, ~₹2000 for two"
          />

          <button type="submit" className="primary" disabled={loading}>
            {loading ? "Searching…" : "Get recommendations"}
          </button>
        </form>
      </div>

      {loading && (
        <div className="skeleton-stack" aria-busy="true" aria-label="Loading">
          <div className="skel" />
          <div className="skel" />
          <div className="skel" />
        </div>
      )}

      {error && (
        <div className="banner error" role="alert">
          {error}
          <div style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
            Route: <code>/api/recommend</code> (Vercel → Render, server-side).
            <br />
            Wake or check API:{" "}
            <code>{TROUBLESHOOT_API_ORIGIN.replace(/\/+$/, "")}/health</code>
            <br />
            Local backend:{" "}
            <code>uvicorn src.phase6.app:http_app --reload --port 8000</code>
            <br />
            Vercel env: <code>API_BACKEND_ORIGIN</code> or{" "}
            <code>NEXT_PUBLIC_API_BASE_URL</code> = Render URL (no trailing
            slash), then redeploy.
          </div>
        </div>
      )}

      {data && !loading && (
        <section className="results">
          <h2>Top picks for you</h2>
          {data.recommendations.length === 0 ? (
            <p>No recommendations returned. Try relaxing filters.</p>
          ) : (
            data.recommendations.map((r) => (
              <article
                key={`${r.record_id ?? "x"}-${r.rank}`}
                className="rec-card"
              >
                <header>
                  <h3>{r.restaurant_name}</h3>
                  <span className="rank">#{r.rank}</span>
                </header>
                <div className="meta">
                  📍 {r.location}
                  {" · "}
                  ⭐ {r.rating.toFixed(1)}
                  {r.estimated_cost != null && (
                    <>
                      {" · "}
                      ₹{r.estimated_cost} for two
                    </>
                  )}
                  {r.budget_bucket && <span> · {r.budget_bucket}</span>}
                </div>
                <div className="cuisines">{r.cuisines}</div>
                <p className="explanation">{r.explanation}</p>
                <div className="confidence">
                  Confidence: {Math.round(r.confidence * 100)}%
                </div>
                <div className="rec-feedback">
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      sendFeedback({
                        event_type: "click",
                        record_id: r.record_id,
                      })
                    }
                  >
                    Viewed
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      sendFeedback({
                        event_type: "like",
                        record_id: r.record_id,
                      })
                    }
                  >
                    Like
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      sendFeedback({
                        event_type: "dislike",
                        record_id: r.record_id,
                      })
                    }
                  >
                    Dislike
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() =>
                      sendFeedback({
                        event_type: "select",
                        record_id: r.record_id,
                        client_meta: { choice: "primary" },
                      })
                    }
                  >
                    Pick this
                  </button>
                </div>
              </article>
            ))
          )}

          <p
            style={{ fontSize: "0.8rem", color: "#8a7d72", marginTop: "2rem" }}
          >
            Model: {data.model}
          </p>
        </section>
      )}
    </main>
  );
}
