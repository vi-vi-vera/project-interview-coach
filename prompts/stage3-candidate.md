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
| `elevator` | ≤ 50 Chinese chars | ≤ 35 English words | One-sentence summary, resume-grade |
| `standard` | 110–300 Chinese chars | 80–180 English words | 30–60 second spoken answer |
| `deep_dive` | 350–800 Chinese chars | 220–450 English words | 2–3 minute deep dive |

Note on zh floors: bilingual technical text in zh inevitably embeds English
identifiers (sandbox-warm-pool, X-Accel-Buffering, ...) which do not count
toward the CJK char total. A content-rich `deep_dive` in matter-of-fact
voice typically lands at 350–500 CJK chars; pushing higher requires either
genuinely more technical content (good) or filler (bad). When in doubt,
prefer fewer characters with more concrete content over more characters
with restated points.

### C.0 Voice baseline (applies to ALL three tiers)

The output is what a candidate says in an interview, not a design doc they hand
over. The target tone is **matter-of-fact spoken** — first-person, neutral
connectives, no theatrics. If a sentence sounds like a TED talk, a podcast
host, or a "let me tell you a story" coach, rewrite it. Plain is better than
performative.

**How to hit word budgets without padding:** when an answer is short, do NOT
reach for filler, dramatization, or rephrasing. Add another layer of concrete
technical content instead. Good ways to extend:
- name a specific config knob, header, or threshold (e.g. `X-Accel-Buffering: no`,
  `15s keepalive`, `200ms debounce`)
- spell out one more decision: what was considered, what was chosen, why
- describe the failure mode of the alternative in one sentence
- mention the adjacent system this touches (nginx, k8s ingress, CodeMirror, vite)
- give the actual number when you have it; if you don't, drop the metric — do
  not pad with "noticeably" repeated

**Hard rules:**

1. **First person, active voice.** Use 我 / 我们 in zh, I / we in en. Avoid passive
   constructions ("X 被实现为…" / "X is implemented as…") — say who did it.
2. **Identifiers can stay bare.** Camel/snake-case names (streamManager,
   resumableStreamService, h5-preview.service) read fine on their own. Add a
   category prefix only when the listener genuinely cannot infer what kind of
   thing it is — and even then, one short noun is enough ("一个服务叫
   streamManager"), not a sentence-long introduction. Do NOT prefix every
   identifier; that's the surest way to sound like a script.
3. **Break long sentences.** A spoken sentence rarely exceeds ~25 zh chars or ~20 en
   words. When you find yourself reaching for a comma to keep going, end the sentence
   and start a new one.
4. **Connective words: sparing and neutral.** Use plain transitions — zh: 所以 /
   后来 / 一开始 / 不过 / 这里; en: so / later / at first / but / here. Avoid
   theatrical fillers (你想 / 说白了 / 这事得有解法 / 老实说; here's the thing /
   the way I'd put it / look). They read as performance, not speech. **No quota.**
   Add a connective only where a real conversational beat needs marking.
5. **Don't translate every term.** If the codebase uses a term (RTT, P95,
   AbortController, vite base, Last-Event-ID), use it directly. Add a one-clause
   gloss only when the term is genuinely obscure to the role being interviewed.
   Over-glossing makes the answer sound like the candidate is reciting a tutorial.
6. **No dramatization.** Avoid intensifiers (巨难 / 骤降 / 几乎全失败 / 肉眼可见 /
   一下就好了; dramatically / catastrophically / nailed it / blew up). Describe
   the change with a plain verb (减少 / 下降 / 变快; reduced, dropped, sped up).
   If a number exists, the number does the work; if it doesn't, understate.
7. **Don't volunteer failure stories.** A `deep_dive` may include a failure lesson
   only when the evidence supports it (§C.1) AND the lesson genuinely shaped the
   design. Otherwise stay on the design itself. Tone-wise: state what happened in
   one sentence, what changed in one sentence; do not editorialize ("那次教训挺
   痛的" / "that one stung"). Stating the fact is enough.
8. **Banned vocabulary (book-language flags).** zh: 旨在, 致力于, 综上所述,
   首先...其次...最后, 不仅...而且. en: aforementioned, in order to (use "to"),
   leverage (use "use"), facilitate (use "make/let"), utilize (use "use"). These
   are written, not spoken.

### Voice contrast examples (memorize the delta)

These show what to fix. The "✅ matter-of-fact" column is the target — neutral,
first-person, no theater.

| ❌ Document voice | ❌ Performative voice | ✅ Matter-of-fact spoken voice |
|---|---|---|
| streamManager 维护 session 流，resumableStreamService 给事件打单调递增 ID。 | 你想，LLM 流可能跑几十秒，网络抖一下就断了，这事得有解法。我们写了两个服务配合干这事…… | LLM 流通常跑几十秒，中间网络抖一下连接就断了，所以需要做断点续传。后端有两个服务：streamManager 按 session 维护活跃流，resumableStreamService 给每条事件分配递增 ID 并缓存最近一段窗口。 |
| 跨 Pod 状态以 Redis 为权威源、DB 兜底。 | 跨 Pod 的状态我们是这么放的：热路径上 Redis 说了算，DB 在后面兜底，Redis 挂了不至于丢数据。 | 跨 Pod 的状态权威源放在 Redis，DB 做兜底。Redis 挂了 DB 还能恢复。 |
| Tail latency on git operations dropped sharply. | Tail latency on git ops came way down — basically went from "felt laggy" to "feels instant". | Tail latency on the git endpoints dropped noticeably. We folded the multi-step flow into one composite command, so each call pays one round-trip instead of several. |
| We exposed SSE backed by the Claude Agent SDK plus MCP. | Here's the thing — on the backend side we exposed SSE, the Agent SDK and MCP sit behind it doing the orchestration. | The backend exposes an SSE endpoint. Behind it the Claude Agent SDK plus MCP handle the orchestration. |

### Content requirements per tier

- **`elevator`**: one sentence, conclusion first, no setup. Resume-grade.
- **`standard`**: structure as `Problem → Approach → Result`. Open with the
  problem in 1 sentence; give the approach in 2–3 short sentences naming
  concrete techniques (e.g. "200ms debounce", "AbortController"); close with
  one sentence of observable outcome. Plain, declarative. Connectives only
  where a real beat needs marking — do not force them in.
- **`deep_dive`**: this is where the candidate explains the design in depth.
  Structure suggestion (not a script):
  1. *Restate the problem* in 1–2 sentences.
  2. *Walk through the design in 2–3 beats* — short paragraphs or "first... then..."
     phrasing. Numbered lists are acceptable when the steps are genuinely
     sequential; otherwise prose is better.
  3. *One self-posed question is fine, not required* ("为什么不用 X？" /
     "Why not X?"). Use it only when the alternative is a genuine reader
     question, not as a rhetorical device.
  4. *End on the trade-off, lesson, or metric* in one sentence. State it; do
     not editorialize.

  `deep_dive` MUST still contain at least one of:
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

Both languages must read like a real person talking, not a translated doc. The
content under `zh` and `en` should be **independently composed** — same facts,
same trade-offs, but written in each language's natural conversational rhythm.
**Never literally translate from one to the other.**

**`zh` — 中文口吻：**
- 第一人称（我 / 我们）开口，主谓清晰。把「X 被实现为 Y」改成「我们把 X 做成了 Y」。
- 技术术语保留英文（SSE / AbortController / Postgres / RTT / P95）。**只有在
  术语对该角色确实陌生时**才补一句白话解释，且最多一句。不要每个术语都翻译。
- 拒绝长定语链。「一个用 Redis 主、DB 兜底的、跨 Pod 共享的状态权威源」改成
  「状态的权威源在 Redis，DB 做兜底，跨 Pod 共享」。
- 连接词中性、克制。可用：所以 / 后来 / 一开始 / 不过 / 这里。**不要使用：
  你想 / 说白了 / 这事得有解法 / 老实说 / 打个比方 / 现在回头看**——这些是
  「装着像在讲道理」的表演式连接词，写在简历级输出里只会油腻。**没有数量
  下限。** 真有转折、对比、补充时再用一个。
- 避免夸张词：巨难 / 骤降 / 几乎全失败 / 肉眼可见 / 一下就好了 / 痛点。
  改用平实动词：减少 / 下降 / 变快 / 问题。
- 不主动卖失败教训。要讲就一句陈述「早期没做 X，导致 Y，后来加上了」即可，
  不要加「那次教训挺痛的 / 巨难 / 差点把生产改坏」这类点评。
- 不要写「旨在 / 致力于 / 综上所述 / 首先...其次...最后」——这些是公文味。
- 句子短，但不刻意。自然分句即可。

**`en` — Spoken English voice:**
- Active voice, first person. Prefer "we wrote X" over "X was written".
- Contractions are fine (we'd, didn't, we've) — they signal speech.
- Connectives stay neutral: so, later, at first, but, here. **Avoid
  performative fillers**: here's the thing, the way I'd put it, look, basically,
  actually (when used as a verbal tic). These read as performance. **No quota.**
- Translate the meaning, not the words. No literal renderings of Chinese
  idioms.
- Avoid intensifiers: dramatically, catastrophically, blew up, came way down,
  feels instant. Use plain verbs: dropped, reduced, sped up, fell.
- Don't volunteer failure stories. When the lesson is genuine, state it in
  one sentence ("Early on we didn't have X, so Y happened; we added X
  afterward"). No editorial ("that one stung", "lesson learned the hard way").
- Banned: aforementioned, leverage (as a verb), facilitate, utilize, in order to.
- Short sentences. If you wrote a 30-word sentence, break it.

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
