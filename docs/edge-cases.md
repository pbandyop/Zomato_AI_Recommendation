# Edge Cases: AI-Powered Restaurant Recommendation System

This document lists detailed edge cases for the Zomato-inspired recommendation project, aligned with:

- `docs/problemstatement.md`
- `docs/phased-architecture.md`

## 1) Data Foundation Layer Edge Cases

### Dataset Availability and Integrity

- Hugging Face dataset URL is temporarily unavailable or rate-limited.
- Dataset schema changes (column names renamed, removed, or newly added).
- Dataset contains corrupted rows or malformed encodings.
- Partial download succeeds but file is incomplete.
- Same restaurant appears with multiple IDs due to source inconsistencies.

### Missing and Inconsistent Values

- `location` is null, misspelled, or represented in mixed formats (e.g., "Bangalore", "Bengaluru", "BLR").
- `rating` values are missing, non-numeric, or include text formats (e.g., "4.2/5", "NEW", "-").
- `cost` values are mixed currencies or inconsistent scales (per person vs per meal).
- `cuisine` is missing, empty, or contains noisy delimiters (comma/slash/pipe).
- Duplicate restaurants have conflicting ratings/costs.

### Standardization and Storage

- Cuisine normalization maps distinct cuisines into the same bucket incorrectly.
- Aggressive deduplication removes legitimate branches in different neighborhoods.
- Storage write fails due to locked SQLite file or DB connectivity loss.
- Incremental data refresh introduces duplicate rows after merge.
- Backward-incompatible migration breaks older cleaned datasets.

## 2) Preference Capture Layer Edge Cases

### Input Validation

- User enters unsupported city or typo ("Delhii", "Banglore").
- User provides rating outside valid range (e.g., 6.0 or negative).
- Budget is missing or uses unknown label ("super cheap", "premium+").
- User enters contradictory values (very low budget + very high minimum rating).
- User submits only optional preferences and skips core filters.

### Ambiguous or Fuzzy Inputs

- User gives vague cuisine ("spicy food", "something light") instead of standard categories.
- User asks for multiple cuisines with AND/OR ambiguity.
- Location is broad ("Delhi") but available records are only locality-level.
- Free-text preference includes subjective terms ("Instagrammable", "peaceful vibe").
- Mixed-language input appears in preferences.

### Session and Interaction Handling

- User updates one preference mid-session; stale old values remain active.
- Multiple rapid submissions create race conditions in state management.
- Session expires before recommendation generation completes.
- Two users share same session identifier due to frontend bug.
- Bot/automated spam sends high-frequency malformed requests.

## 3) Candidate Retrieval Layer Edge Cases

### Filtering Logic

- Hard filters return zero candidates.
- Filters return too many candidates (weak constraints) and exceed LLM context limits.
- Budget boundaries are ambiguous (inclusive vs exclusive thresholds).
- Minimum rating filter excludes restaurants with null ratings that might still be relevant.
- Cuisine filter fails when records store multi-cuisine strings.

### Fallback and Relaxation

- Fallback strategy relaxes critical constraints unexpectedly (e.g., wrong city).
- Multiple fallback steps produce irrelevant recommendations.
- No explicit signal is shown when fallback logic is used.
- Fallback loop does not terminate under repeated no-result scenarios.
- Relaxation order is suboptimal (drops rating before cuisine when user cares more about rating).

### Candidate Quality and Ranking Inputs

- Shortlisted records include duplicate restaurant names from different records.
- Candidate set is biased toward areas with denser data.
- Important features are dropped during preprocessing for LLM context packing.
- Retrieval latency spikes due to unindexed query fields.
- Candidate sorting differs between backend and UI due to inconsistent tie-breakers.

## 4) LLM Reasoning and Ranking Layer Edge Cases

### Prompt Construction

- Prompt exceeds token limits due to large candidate payload.
- Prompt omits key constraints (budget or minimum rating) during templating.
- Candidate attributes are inconsistently formatted, confusing the model.
- Hidden prompt injection appears in restaurant metadata fields.
- Prompt template version mismatch between dev and production.

### Model Output Reliability

- LLM hallucinates restaurants not present in candidate list.
- LLM recommends restaurants outside user city despite strict filters.
- LLM contradicts itself (rank #1 has lower fit explanation than rank #3).
- Explanations are generic and not personalized to user constraints.
- LLM output format breaks parser expectations (missing rank/explanation fields).

### Safety and Guardrails

- Guardrails over-filter outputs and remove all recommendations.
- Hallucination detection fails for near-matching restaurant names.
- Toxic or biased phrasing appears in generated explanations.
- Model includes prohibited content from prompt history unintentionally.
- Retry strategy on model errors causes duplicate request billing.

## 5) Response Presentation Layer Edge Cases

### UI/UX and Data Display

- Cost or rating displays as `null`, `NaN`, or placeholder text.
- Restaurant names exceed UI width and break layout.
- Sorting shown in UI does not match backend ranking order.
- Same restaurant appears multiple times in top results.
- Explanation text is too long and crowds out essential attributes.

### Communication and Transparency

- UI does not indicate when fallback/relaxed filtering was applied.
- Users cannot tell why a recommendation was included despite low rating.
- No message appears for zero-result cases with actionable next steps.
- Confidence/uncertainty is not communicated for weak matches.
- Different surfaces (CLI/web/chat) show inconsistent recommendation details.

### Accessibility and Localization

- Color-only ranking indicators are not accessible.
- Currency format does not match user locale.
- Unicode cuisine names render incorrectly in some clients.
- Screen reader order does not align with visual ranking.
- Mobile view truncates explanation before key rationale appears.

## 6) Feedback and Continuous Improvement Layer Edge Cases

### Feedback Capture

- Click events are captured but recommendation IDs are missing.
- Implicit feedback (clicks) conflicts with explicit feedback (dislike).
- Duplicate feedback events inflate performance metrics.
- Users provide feedback after content refresh, mapping to stale recommendations.
- Anonymous sessions make longitudinal quality measurement difficult.

### Monitoring and Metrics

- Latency metrics exclude LLM response time due to instrumentation gap.
- Error logs miss upstream data pipeline failures.
- Monitoring dashboard aggregates all cities, hiding regional quality drops.
- Success metric optimized for clicks degrades true user satisfaction.
- Silent failures occur when telemetry queue is down.

### Evaluation and Iteration

- Offline eval set is not representative of real user distribution.
- Prompt updates improve one cuisine category but regress others.
- A/B tests have uneven traffic allocation across user segments.
- No regression alerts when recommendation relevance drops over time.
- Model version updates change behavior without baseline comparison.

## 7) End-to-End and System-Level Edge Cases

### Reliability and Performance

- Concurrent peak-time traffic causes retrieval or LLM request bottlenecks.
- Timeout mismatch: backend waits longer than frontend, causing user-visible failures.
- Circuit breaker opens frequently due to intermittent model provider errors.
- Cache returns stale recommendations after user changes preferences.
- Retries across layers amplify load (retry storm).

### Security and Abuse

- Prompt injection via user free-text ("ignore previous constraints").
- Malicious strings in dataset fields are passed into prompt unsanitized.
- API key leakage through logs or client-side exposure.
- Abuse via scripted requests drives up LLM usage cost.
- Personally identifying user data is inadvertently logged in plain text.

### Business Logic and Trust

- Sponsored/featured restaurants (if introduced later) bias ranking transparency.
- Popularity-heavy logic suppresses niche but high-fit restaurants.
- New restaurants with sparse data never surface ("cold start").
- System repeatedly recommends same restaurants, reducing discovery.
- User trust drops if explanations do not match visible attributes.

## 8) Recommended Mitigation Checklist

- Enforce strict schemas and contract tests for ingestion and parsing.
- Add canonicalization maps for city/cuisine/cost/rating formats.
- Implement deterministic fallback policy with user-visible messaging.
- Use constrained output formats (JSON schema) for LLM responses.
- Add hallucination checks against candidate IDs before display.
- Log end-to-end trace IDs across ingestion, retrieval, LLM, and UI.
- Monitor relevance, latency, failure rates, and recommendation diversity.
- Build regression test suites with curated user personas and edge inputs.
