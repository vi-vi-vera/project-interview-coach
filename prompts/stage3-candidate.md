# Stage 3 — Candidate-mode interview material prompt

You are given:
- `<<PROJECT_CONTEXT_JSON>>` — output of Stage 1 (workspace + sub-projects + highlights)
- `<<TECH_POINTS_JSON>>` — output of Stage 2 (tech points with `primary_dimension`)
- Parameters: `role = <<ROLE>>`, `level = <<LEVEL>>`

## Your task

Produce a single JSON object that conforms exactly to `schemas/interview-data.schema.json`.

This output is the candidate's interview-prep deliverable. The reader will rely on it
for an upcoming interview, so factual accuracy beats stylistic flourish. Hallucinated
content is worse than a thinner answer.

---

## A. Top-level rules

1. `schema_version = "1.0"`. `mode = "candidate"`. `platform_name` copied from `PROJECT_CONTEXT_JSON.platform_name`.
2. `project_pitch.{elevator, standard, deep_dive}` — three depth tiers describing the
   whole platform. Word budgets and content rules are identical to per-question answers
   below (section C). Base the content on `platform_name`, `one_liner`, `domain`,
   `highlights`, and the sub-project structure. Do **not** invent features absent from
   the inputs.
3. `highlights` — copy 3–5 from `PROJECT_CONTEXT_JSON.highlights`, then for each:
   - keep `title`, `scope`, infer `primary_dimension` (use the same 7-value enum as Stage 2)
   - rewrite `summary` into a `story` field as a STAR-style narrative `{ zh, en }`
     (Situation → Task → Action → Result, 80–150 zh chars / 50–90 en words)
   - extract `tech_keywords` (3–6 short tokens) for quick scanning
4. `qa` — generate questions from `TECH_POINTS_JSON.points`. Selection rule (in order
   of priority; earlier rules override later ones when they conflict):
   - Every point with `interview_value = "高"` MUST yield ≥ 1 qa (hard rule)
   - Every point with `interview_value = "中"` SHOULD yield 1 qa unless redundant
   - Points with `interview_value = "低"` are optional
   - Total qa count: aim for roughly `0.8 × |points|` to `1.5 × |points|`. This is a
     soft target — when it conflicts with the "high-value must yield ≥1" hard rule,
     the hard rule wins (i.e. it is acceptable to exceed 1.5×).
5. `dimension_coverage` — count `qa[].primary_dimension` values into all seven keys:
   `feature`, `architecture`, `performance`, `reliability`, `observability`,
   `trade-off`, `security`. Every key MUST be present even when the count is `0`.
   Numbers MUST match the actual qa array; the renderer will cross-check and reject
   mismatches.

---

## B. Per-`qa` construction rules

For each qa item:

1. `id` — `q-01`, `q-02`, ... in declaration order.
2. `source_tech_point` — the `id` of the tech point this qa is derived from. Required.
3. `primary_dimension`, `scope`, `sub_project`, `evidence` — inherit from the source
   tech point (same enum values, same paths). You MAY add more `evidence` paths if they
   exist in `PROJECT_CONTEXT_JSON.sub_projects[].modules` or `active_areas`, but never
   remove the originals and never invent a path.
4. `depth` — copy from the input parameter `<<LEVEL>>` (`初级` / `中级` / `高级`).
5. `question.{zh, en}` — phrase as an interviewer would actually ask. Avoid "请描述一下"
   openers; prefer "你是怎么…", "为什么选…", "如果…会怎么处理".
6. `answers` — three depth tiers; see section C.
7. `knowledge_points` — see section D.
8. `learning_plan` — see section E.
9. `follow_ups` — see section F.

---

## C. Three-tier `answers` rules

Word budgets (treat as hard limits, not suggestions). For Chinese, "chars" means
**Chinese characters** (CJK code points), not bytes; punctuation does not count
toward the limit. For English, "words" means whitespace-separated tokens.

| Tier | zh budget | en budget | Purpose |
|------|-----------|-----------|---------|
| `elevator` | ≤ 50 Chinese chars | ≤ 30 English words | One-sentence summary, resume-grade |
| `standard` | 150–300 Chinese chars | 80–180 English words | 30–60 second spoken answer |
| `deep_dive` | 500–800 Chinese chars | 250–450 English words | 2–3 minute deep dive |

Content requirements:

- **`elevator`**: state the conclusion in one sentence. No setup, no story.
- **`standard`**: structure as `Problem → Approach → Result`. Mention concrete techniques
  by name (e.g. "200ms debounce", "AbortController"), but do not over-explain.
- **`deep_dive`**: MUST contain at least one of:
  (a) **concrete numerical data** (latency, throughput, hit rate, code size, etc.)
  (b) **explicit trade-off** ("we chose X over Y because ..., the cost is ...")
  (c) **failure lesson** (a real incident the candidate experienced)

  When the source tech point lacks evidence for (a) or (c) — which is common — prefer
  (b). Trade-offs can usually be reconstructed from what the code *does* use versus
  plausible alternatives the candidate chose not to use. (a) and (c) carry higher
  bars (see §C.1) and should only be used when evidence genuinely supports them.

### C.1 Anti-hallucination rules (HARD)

- **Failure lessons MUST be evidence-backed.** A failure lesson is allowed only if the
  source tech point's evidence (or git history visible in `PROJECT_CONTEXT_JSON`) shows
  defensive code, comments, commit messages, or issue links pointing to that specific
  failure. If no such trace exists, do NOT write a failure lesson — choose path (a) or
  (b) instead.
- **Numerical metrics MUST be traceable.** If you write "10x improvement" or "80% hit
  rate", the source tech point or its evidence path must contain comments / code /
  benchmark hints justifying that number. Otherwise drop the metric and describe the
  improvement qualitatively ("noticeably reduced", "dramatically faster").
- **Never fabricate technologies the project does not use.** Only mention libraries,
  protocols, infra components present in `tech_stack` or `evidence` files.
- When in doubt, write a thinner but truthful answer. Empty calories are worse than
  brevity.

### C.2 Bilingual style

- `zh`: 简体中文，技术术语保留英文（如 SSE / AbortController / Postgres），不用机翻味
  长句。
- `en`: natural professional spoken English. Translate the meaning, not the words. Avoid
  literal renderings of Chinese idioms ("一举两得" → not "kill two birds with one
  stone", instead just say "got both wins"). Use active voice.

---

## D. `knowledge_points` rules

- Provide **2–4** entries.
- At least 1 entry with `level = "必须掌握"` AND at least 1 with `level = "加分项"`.
- `name`: the topic / concept the candidate must know to answer the question well
  (e.g. "SSE 协议规范", "Postgres WAL", "Promise 串行化"). Keep ≤ 20 chars.
- `why`: one sentence (≤ 40 chars) on **why an interviewer would push on this knowledge
  point**, not what the topic is.

Example:
```json
{ "name": "Postgres WAL 与事务粒度", "level": "加分项",
  "why": "讲清为什么高频写会抖动可以让面试官刮目相看" }
```

---

## E. `learning_plan` rules

All five fields are required.

| Field | Constraint |
|---|---|
| `must_read` | 1–3 entries. Prioritize official docs / RFCs / canonical books / well-known engineering blogs. No marketing pages, no Medium fluff. |
| `hands_on` | 1–2 entries. Each MUST be completable in ≤ 2 hours and produce a concrete artifact ("write a 30-line Express SSE demo", "patch existing controller to add AbortController"). |
| `common_pitfalls` | 1–3 entries. Real, specific gotchas — not generic advice. Bad: "注意性能". Good: "nginx 默认开启 buffer 导致流不动 → X-Accel-Buffering: no". |
| `mock_questions` | 2–4 entries. **Question text only, no answers.** Should force the candidate to close the doc and self-test. |
| `time_estimate` | One short Chinese phrase. Calibrate by depth: surface concept ≈ `"半天"`, framework + practice ≈ `"1–2 天"`, fundamentals (e.g. database internals) ≈ `"1 周"`. |

---

## F. `follow_ups` rules

- Generate `follow_ups` for **at least 30%** of all qa items (round up).
- Prefer high-`interview_value` qa as the carriers of follow-ups.
- Each follow-up:
  - `question.{zh, en}` — phrased as a deeper drill-down or a "why not X" probe
  - `primary_dimension` — typically `"trade-off"` for "为什么不用 X" probes; otherwise
    pick the dimension that genuinely matches the question's focus
  - `expected_answer.{zh, en}` — 60–120 zh chars / 30–60 en words. NOT a full deep_dive,
    just the key point an interviewer expects to hear.

Avoid asking the same trade-off question across multiple qa items (e.g. don't ask "why
not WebSocket" three times). Each follow-up should expose a different facet.

---

## G. Output

Output **only the JSON**, no surrounding prose, no Markdown fences. The JSON must
validate against `schemas/interview-data.schema.json`. If you cannot satisfy a hard
constraint (e.g. word budget or anti-hallucination rule), prefer omitting optional
fields over violating the constraint.

---

## H. Inputs

PROJECT_CONTEXT_JSON:
<<PROJECT_CONTEXT_JSON>>

TECH_POINTS_JSON:
<<TECH_POINTS_JSON>>

ROLE: <<ROLE>>
LEVEL: <<LEVEL>>
