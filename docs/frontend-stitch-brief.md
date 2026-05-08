# Frontend UI Brief — Next.js (for design / image generation tools)

**Purpose:** Share this document with **Google Stitch** (or similar UI/mockup generators) to produce screens, components, or visual references for a **Next.js** frontend that talks to the **NextLeap Zomato** recommendation backend (Phase 6 API).

**Product:** AI-assisted restaurant recommendations inspired by Zomato — users enter location, budget, cuisines, and minimum rating; the backend returns ranked restaurants with **AI-written explanations** and **confidence** scores.

**Target framework:** **Next.js** (recommended: **App Router**, **TypeScript**, **React Server Components** where helpful; client components for forms and interactive result lists).

---

## Brand & visual direction (suggestions for mockups)

- **Mood:** Warm, appetizing, trustworthy — food discovery app; not generic “admin dashboard.”
- **Palette (suggested):** Deep charcoal or warm brown for text; accent **tomato red** or **saffron** (Zomato-adjacent but original); soft cream/off-white backgrounds; subtle green for success states.
- **Typography:** Clean sans-serif (e.g. system UI stack or **Geist** / **Inter**); clear hierarchy (page title → section → card title → meta).
- **Shape:** Rounded cards (`border-radius` medium); subtle shadows on recommendation cards.
- **Imagery:** Optional placeholder for restaurant thumbnail or abstract food/location illustration per card (not required for MVP wireframes).

---

## Backend integration (high level)

- **Base URL:** Configured via environment variable, e.g. `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` (must match CORS `CORS_ORIGINS` on the API).
- **Primary flow:** User submits preferences → `POST /api/v1/recommend` with JSON body → render returned `recommendations` array.
- **Alternative:** `POST /api/v1/sessions` to save preferences, then `POST /api/v1/recommend` with `{ "session_id": "..." }` (optional two-step UX).

---

## API contracts (for accurate UI fields)

### Request: user preferences (Phase 2 shape)

Use these labels on the form:

| Field | Type / notes |
|--------|----------------|
| `location` | string — city or locality (e.g. “Bellandur”, “Bangalore”) |
| `budget` | enum — **`low`**, **`medium`**, **`high`** (maps to cost tiers in data; not raw rupees in API) |
| `cuisines` | string array — e.g. `["North Indian", "Chinese"]` — allow multi-select or chips |
| `minimum_rating` | number — `0.0`–`5.0` — slider or stepper |
| `additional_preferences` | optional string array — free-text tags or textarea split into tags (e.g. “family-friendly”, “~₹2000 for two”) |

### Request: recommend (inline preferences)

```json
{
  "preferences": {
    "location": "bellandur",
    "budget": "high",
    "cuisines": ["north indian", "chinese"],
    "minimum_rating": 4.0,
    "additional_preferences": ["budget around 2000 for two"]
  },
  "max_candidates": 30,
  "top_n": 10,
  "include_raw_llm": false
}
```

### Response: recommendation payload (Phase 5 / presentation)

Top-level keys the UI should consume:

- `recommendations` — array of ranked items (show in order).
- `applied_fallbacks` — array of strings (e.g. retrieval relaxed filters) — show as **non-blocking info banner**.
- `preferences_summary` — echo of normalized preferences — optional “Your search” recap.
- `model` — LLM model id — optional footer/debug.
- `guardrail_notes` — array — show only in dev or collapsible “Details” (optional).

Each item in `recommendations`:

| Key | UI treatment |
|-----|----------------|
| `rank` | Badge or number (1, 2, 3…) |
| `restaurant_name` | Primary title, bold |
| `location` | Subtitle / meta row with map-pin icon |
| `cuisines` | Chips or comma-separated muted text |
| `estimated_cost` | Label “Approx. for two” + currency (assume ₹) |
| `budget_bucket` | Small tag: low / medium / high |
| `rating` | Stars or numeric (e.g. **4.2**) |
| `match_score` | Optional secondary metric — “Match” tooltip or hide in simple UI |
| `explanation` | **Highlight block** — AI reason; readable paragraph (1–3 sentences) |
| `confidence` | **0–1** — show as percentage, progress bar, or “High / medium / low” bucket |

---

## Pages & screens to generate (Stitch / mockup checklist)

### 1. Home — “Find restaurants”

- **Hero:** Short headline + subtext (“Tell us what you’re in the mood for”).
- **Form sections:** Location (text input), Budget (segmented control or three large buttons), Cuisines (multi-select / chip input), Minimum rating (slider), Additional preferences (optional tags or textarea).
- **Primary CTA:** “Get recommendations” (full width on mobile).
- **Secondary:** Link to “How it works” or collapsible FAQ (optional).

### 2. Loading state

- Full-width or in-place **skeleton** cards (3–5 placeholders) or centered spinner + “Finding places you’ll love…”

### 3. Results — recommendation list

- **Header:** “Top picks for you” + recap line from `preferences_summary` (location, budget, cuisines).
- **Info banner** (if `applied_fallbacks` non-empty): e.g. “We widened your search slightly to show more options” — neutral/informational style.
- **List:** Vertical stack of cards (mobile-first); on desktop optional two-column grid.
- **Card layout:** Rank badge; name; rating + cost on one row; cuisines chips; **explanation** in distinct panel; confidence indicator.
- **Empty state:** Illustration + “No matches” + suggestion to relax rating or budget (copy only; no new API).

### 4. Error state

- Friendly message for network / 4xx / 5xx; **Retry** button; no raw stack traces.

### 5. Optional — Compare (Phase 5)

- Select 2–3 cards → **Compare** drawer or table: columns = Restaurant | Rating | Cost | Cuisines | Explanation (truncated with expand).

### 6. Optional — Footer

- “Powered by AI explanations” disclaimer; link to API docs or GitHub (placeholder).

---

## Next.js implementation notes (for builders, not required for images)

- **`NEXT_PUBLIC_API_BASE_URL`** for browser-side `fetch` to Phase 6.
- Use **Route Handlers** or **Server Actions** if you prefer proxying the API (keeps Groq keys off the client — already true if only public base URL is used).
- Forms: **react-hook-form** or native; validation mirrors backend (budget enum, rating range).
- **Accessibility:** labels tied to inputs, focus visible, announce loading/results to screen readers where practical.

---

## Suggested filenames in a Next.js repo (reference only)

- `app/page.tsx` — home + results on same page (state) *or* `app/results/page.tsx` after submit.
- `components/PreferenceForm.tsx`
- `components/RecommendationCard.tsx`
- `components/InfoBanner.tsx`
- `lib/api.ts` — `recommend()` wrapper.

---

## One-line prompt you can paste into Stitch (optional)

> “Generate a **mobile-first** Next.js-style UI mockup for a **Zomato-inspired restaurant recommender**: warm food-app aesthetic, form with location, budget (low/medium/high), multi-cuisine chips, rating slider, then a vertical list of **ranked recommendation cards** showing name, location, ₹ cost for two, star rating, cuisine tags, and a **prominent AI explanation paragraph** plus a **confidence** indicator; include loading skeletons and a soft info banner when search was relaxed.”

---

## Document metadata

- **Companion backend spec:** `docs/phased-architecture.md` (Phases 6–7).
- **Example API host:** `http://127.0.0.1:8000` (development).
- **OpenAPI:** `GET /docs` on the running API server.
