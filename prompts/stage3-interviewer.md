# Stage 3 — Interviewer-mode question-pack prompt

You are given:
- `<<PROJECT_CONTEXT_JSON>>` — output of Stage 1 (workspace + sub-projects + highlights)
- `<<TECH_POINTS_JSON>>` — output of Stage 2 (tech points with `primary_dimension`)
- Parameters: `role = <<ROLE>>`, `level = <<LEVEL>>`

## Your task

Produce a single JSON object that conforms exactly to `schemas/interview-data.schema.json`
with `mode = "interviewer"`. The reader is the **interviewer**: they will use this pack
during a session to pick questions and score the candidate. The contract is opposite
to candidate-mode: **no model answers** — scoring relies entirely on the rubric attached
to each question.

---

## A. Top-level rules

1. `schema_version = "1.0"`. `mode = "interviewer"`. `platform_name` copied from
   `PROJECT_CONTEXT_JSON.platform_name`.
2. Do NOT emit `project_pitch`, `qa`, `dimension_coverage`, `highlights`. The schema
   `if/then` branch for interviewer mode requires only `question_bank` and `rubrics`.
3. `question_bank` and `rubrics` are 1:1 by `id ↔ qa_id`. Every question MUST have
   a matching rubric, and vice versa.

---

## B. `question_bank` construction rules

For each tech point in `TECH_POINTS_JSON`:

1. `id` — `iq-01`, `iq-02`, … in declaration order. Use the `iq-` prefix to
   distinguish from candidate-mode `q-` ids; the rubric's `qa_id` MUST match.
2. `source_tech_point` — the source tech point's `id`. Required.
3. `primary_dimension`, `scope`, `sub_project`, `evidence` — inherit from the source
   tech point (same enum values, same paths). You MAY add more `evidence` paths if
   they exist in `PROJECT_CONTEXT_JSON.sub_projects[].modules` or `active_areas`,
   but never invent a path.
4. `depth` — copy from the input parameter `<<LEVEL>>`.
5. `question.{zh, en}` — phrase as an interviewer would actually ask. Avoid
   "请描述一下" openers; prefer "你是怎么…", "为什么选…", "如果…会怎么处理".
6. `stress_probes` — 1–2 items. These are what the interviewer asks **when the
   candidate answers too smoothly** (sounds rehearsed, no hesitation, gives the
   textbook answer). Each probe should poke at a concrete failure mode, edge case,
   or trade-off the candidate would only know from real experience.
   - `question.{zh, en}` — phrased as a deeper drill-down or "what if X breaks"
   - `primary_dimension` — typically `reliability` or `trade-off`

### B.1 Question selection

- Every tech point with `interview_value = "高"` MUST yield ≥ 1 question (hard rule).
- Every tech point with `interview_value = "中"` SHOULD yield 1 question unless redundant.
- Tech points with `interview_value = "低"` are optional.
- Total: aim for `0.8 × |points|` to `1.5 × |points|`. The hard rule above wins on conflict.

---

## C. `rubrics` construction rules

For each question, produce one rubric entry.

1. `qa_id` — matches the question's `id`.
2. `criteria` — at least **3** entries. Default scaffold:
   - `技术正确性`（weight 0.4）— did they get the mechanism right?
   - `取舍意识`（weight 0.3）— do they understand the trade-offs vs alternatives?
   - `失败教训复盘能力`（weight 0.3）— can they recall a concrete pitfall and recovery?
3. **Weights MUST sum to 1.0 ± 0.05** across the criteria of one question. The
   renderer prints the sum and flags deviation; producers should not rely on the
   renderer to fix bad weights.
4. Each criterion's `indicators` MUST cover all three levels:
   `优秀` / `合格` / `不合格`, each as bilingual `{ zh, en }`.

### C.1 Indicator anti-patterns (HARD)

- **No subjective filler.** Replace "回答得很好" / "thoughtful answer" with
  observable behaviors: "explicitly names X mechanism and Y constraint",
  "recalls a specific incident with date / commit / metric".
- **No fabricated evidence requirements.** Do not require the candidate to know
  facts that the codebase doesn't actually expose. If the source tech point's
  evidence doesn't show, e.g., specific perf numbers, don't ask the candidate
  to recite them.
- **`不合格` should be a real failure mode**, not a tautology. Bad: "没有回答好".
  Good: "只说『加缓存』『加队列』之类泛泛回答" / "Vague answers like 'add caching'
  or 'use a queue' without specifics".
- **Asymmetric difficulty.** `优秀` should require the candidate to volunteer
  information the interviewer didn't prompt for; `合格` should require correct
  answers to direct questions; `不合格` is when probing reveals confusion.

### C.2 Bilingual style

- `zh`: 简体中文，技术术语保留英文。Avoid 机翻味长句。
- `en`: natural professional English. Translate intent, not words. Use active voice.

---

## D. Anti-hallucination rules (HARD, same as candidate mode)

- Only mention libraries / protocols / infra components present in `tech_stack`
  or `evidence` files.
- Do not put numerical metrics in indicators unless the source tech point or its
  evidence path can justify them. Prefer qualitative bands ("noticeably faster",
  "an order of magnitude").
- When in doubt, write a thinner but truthful indicator. Empty calories are worse
  than brevity.

---

## E. Output

Output **only the JSON**, no surrounding prose, no Markdown fences. The JSON must
validate against `schemas/interview-data.schema.json` in the interviewer-mode branch.

---

## F. Inputs

PROJECT_CONTEXT_JSON:
<<PROJECT_CONTEXT_JSON>>

TECH_POINTS_JSON:
<<TECH_POINTS_JSON>>

ROLE: <<ROLE>>
LEVEL: <<LEVEL>>
