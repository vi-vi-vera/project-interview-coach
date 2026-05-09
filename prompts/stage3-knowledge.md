# Stage 3 — Knowledge-mode knowledge-map prompt

You are given:
- `<<CANDIDATE_JSON>>` — the already-produced candidate-mode interview-data.json
  (Stage 3 output, `mode = "candidate"`)
- `<<PROJECT_CONTEXT_JSON>>` — output of Stage 1 (for `platform_name` and evidence)

## Your task

Produce a single JSON object that conforms exactly to `schemas/interview-data.schema.json`
with `mode = "knowledge"`. The reader is a candidate who has seen the candidate-mode
output and now wants a **knowledge-centric view** — "if I close my eyes and list the
topics I must master, what are they, and which questions pushed on each?"

---

## A. Top-level rules

1. `schema_version = "1.0"`. `mode = "knowledge"`. `platform_name` copied from
   `PROJECT_CONTEXT_JSON.platform_name`.
2. Do NOT emit `project_pitch`, `highlights`, `qa`, `dimension_coverage`. The schema
   `if/then` branch for knowledge mode requires only `knowledge_map`.
3. `knowledge_map.topics` — de-duplicated, cross-linked aggregation of all
   `CANDIDATE_JSON.qa[].knowledge_points`. See sections B–D.

---

## B. Aggregation and de-duplication

Walk every `qa[i].knowledge_points[j]` in the candidate output:

1. **Normalize the name for matching only**: lowercase, collapse internal whitespace,
   strip trailing punctuation. Two knowledge points are "the same topic" if their
   normalized names are equal.
2. Retain the **most informative original name** as the canonical `topic.name`
   (prefer the longest; ties broken by first occurrence).
3. When merging:
   - `level`: if any occurrence is `"必须掌握"`, the merged level is `"必须掌握"`.
     Otherwise `"加分项"`. (Rationale: interviewers treating the same topic as
     must-master at least once means the candidate cannot skip it.)
   - `questions_using`: union of the source qa ids that contained this knowledge
     point (e.g. `["q-01", "q-04"]`). This is the REVERSE INDEX — the whole point
     of the knowledge-map view.
   - `related_dimensions`: union of `primary_dimension` values from those source qa.

---

## C. Per-topic construction rules

For each de-duplicated topic:

1. `name` — canonical name from B.2. Keep ≤ 20 chars. Do not invent translations;
   keep the original term (e.g. "SSE 协议规范", "Postgres WAL").
2. `level` — `"必须掌握"` or `"加分项"` per B.3.
3. `related_dimensions` — **array** from the 7-value dimension enum.
   Must be non-empty. Do not include `"trade-off"` unless the topic is genuinely
   about weighing alternatives.
4. `questions_using` — non-empty array of qa ids (format `q-01`, `q-02`, …).
   This field is what makes the knowledge map useful; never omit it.
5. `must_read` — 1–3 entries. Reuse / consolidate from the source qa's
   `learning_plan.must_read` where possible; de-duplicate exact matches. Prefer
   official docs over marketing pages. No Medium fluff.
6. `hands_on` — 1–2 entries. Reuse / consolidate from the source qa's
   `learning_plan.hands_on`. Each MUST be completable in ≤ 2 hours and produce a
   concrete artifact.

---

## D. Anti-noise rules

- **Do not create new topics** that were not in any `qa.knowledge_points`. This
  prompt aggregates, it does not generate.
- **Do not drop topics** even if they appear in only one qa. Single-occurrence
  topics are still part of the knowledge surface.
- **Do not rewrite** `must_read` / `hands_on` items into new content — copy them
  verbatim (or pick the better of two near-duplicates). The candidate has already
  seen these in the candidate output; consistency builds trust.
- Ordering: the renderer groups by `level` (必须掌握 first, 加分项 last) and sorts
  by `name` within each level, so the producer does NOT need to emit topics in
  any particular order.

---

## E. Output

Output **only the JSON**, no surrounding prose, no Markdown fences. The JSON must
validate against `schemas/interview-data.schema.json` in knowledge-mode branch.

---

## F. Inputs

CANDIDATE_JSON:
<<CANDIDATE_JSON>>

PROJECT_CONTEXT_JSON:
<<PROJECT_CONTEXT_JSON>>
