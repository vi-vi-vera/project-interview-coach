# Stage 2 — Tech-point extraction prompt

You are given:
- `<<PROJECT_CONTEXT_JSON>>` — output of Stage 1
- Parameters: `role = <<ROLE>>`, `level = <<LEVEL>>`

## Your task

Produce a single JSON object that conforms exactly to `schemas/tech-points.schema.json`.

Rules:
1. `schema_version` — `"1.0"`. `role`, `level` copied verbatim.
2. Extract **6–15 tech points** that an interviewer of the given `role` and `level` is likely to drill into.
3. Each point's `scope` MUST equal the scope of the sub-project (or highlight) it is drawn from. Cross-cutting points use `fullstack`.
4. `sub_project` — set when the point is clearly rooted in one sub-project; omit for platform-wide cross-cutting points.
5. `evidence` MUST contain at least one workspace-relative path that exists in the input's `modules` or `active_areas`. When the point comes from a sub-project, the path MUST start with that sub-project's `path`.
6. `interview_value`:
   - `高` for points the candidate clearly designed/implemented (active_areas + module match)
   - `中` for standard framework usage
   - `低` for boilerplate. Drop `低` points unless fewer than 6 remain.
7. Adjust depth by level:
   - `初级` → focus on framework usage & CRUD
   - `中级` → add module boundaries & data flow
   - `高级` → add scalability, observability, trade-off decisions
8. **`primary_dimension` (REQUIRED for every point)** — pick exactly one from this enum:
   - `feature` — what the module does (CRUD, business workflow, integration surface)
   - `architecture` — how modules compose, boundary design, data flow
   - `performance` — caching, batching, debouncing, concurrency dedup, indexing, code-splitting, render optimization, streaming back-pressure
   - `reliability` — retry, timeout, abort propagation, idempotency, rate limiting, graceful degradation
   - `observability` — tracing, metrics, logging, cost / token tracking, alerting
   - `trade-off` — explicit "X over Y" selection rationale, A/B comparison, deprecation rationale
   - `security` — authn/z, sandbox isolation, RBAC, secret handling, supply-chain
   `depth_tags` is still free-form and SHOULD include the primary_dimension as one of its tags (plus any sub-tags).
9. **Dimension coverage (post-condition on the whole point set)**:
   - For `中级` and above, the final set MUST cover **at least 5 distinct `primary_dimension` values**.
   - Whenever the project shows performance evidence (cache, debounce/throttle, batch, index, lazy load, memoization, etc.), AT LEAST ONE point MUST have `primary_dimension = "performance"`.
   - Same rule applies to `reliability` and `security` when corresponding evidence exists (e.g. retry/timeout/abort code, sandbox/RBAC/secret-handling code).
   - `trade-off` is NOT required to be a standalone point — it is typically expressed as a follow-up question on top of another point during Stage 3. Do NOT fabricate a trade-off point without real comparative evidence.
   - If the project genuinely lacks evidence for a dimension, do NOT invent points for it.
10. Output JSON only.

## Input

PROJECT_CONTEXT_JSON:
<<PROJECT_CONTEXT_JSON>>
