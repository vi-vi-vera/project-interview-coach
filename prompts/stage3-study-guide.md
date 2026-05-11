# Stage 3 — Study-guide mode prompt

You are given:
- `<<KNOWLEDGE_JSON>>` — the already-produced knowledge-mode interview-data.json
  (Stage 3 output, `mode = "knowledge"`). Its `knowledge_map.topics[]` contains
  every must-master / bonus knowledge point with reverse index `questions_using`.
- `<<PROJECT_CONTEXT_JSON>>` — output of Stage 1 (used for `platform_name` and
  optional Windows / WSL / package-manager hints from `tooling`).

## Your task

Produce a single JSON object that conforms to `schemas/interview-data.schema.json`
with `mode = "study-guide"`. The reader is a beginner who has seen the
knowledge-map but does NOT know **what to learn first, in what order, and where
to click**. The output must turn the knowledge map into a sequenced, runnable
study path.

---

## A. Top-level rules

1. `schema_version = "1.0"`. `mode = "study-guide"`. `platform_name` copied
   from `PROJECT_CONTEXT_JSON.platform_name`.
2. Do NOT emit `project_pitch`, `highlights`, `qa`, `dimension_coverage`,
   `knowledge_map`. The schema `if/then` branch for study-guide mode requires
   only `study_guide`.
3. `study_guide` must contain four arrays/objects:
   - `clusters[]` — knowledge clusters (the heart of the document)
   - `phases[]` — 3–5 high-level phases each grouping several clusters
   - `global_self_check[]` — one short Q&A item per cluster
   - `tips[]` — 4–6 efficiency tips

---

## B. Cluster construction (the most important step)

A "cluster" is a group of knowledge-map topics that share the same question
origin (a candidate-mode `qa.id`). Topics that come from the same `qa.id` in
`questions_using` are almost always taught together.

Algorithm:

1. **Group topics by qa-id**: for each topic in `KNOWLEDGE_JSON.knowledge_map.topics`,
   for each `qa_id` in `topic.questions_using`, push the topic into a bucket
   keyed by `qa_id`.
2. **One cluster per qa-id**. Inside the cluster, list all topics that pointed
   to this qa-id. Topics that touch multiple qa-ids appear in multiple clusters
   (this is intentional — the reader learns related concepts together at each
   stage).
3. **Order clusters into a learning sequence**: pick an order based on
   dependency intuition. Heuristic priority (low → high):
   1. fundamentals (HTTP, language, build tools)
   2. framework basics (React/Vue/Next/Nuxt routing & rendering)
   3. state & data layer (stores, query layer, ORM)
   4. performance & rendering optimization
   5. observability & security
   6. domain-specific advanced topics (AI agent, editor, sandbox, etc.)
   Within a tier, order alphabetically by qa-id for determinism.
4. **Group clusters into 3–5 phases** (`phases[]`). Each phase contains
   `cluster_ids` of consecutive clusters and a one-line `theme`.

For each cluster object, emit fields exactly as defined in section E below.

---

## C. Per-cluster content rules

For every cluster:

1. `id` = the qa-id that birthed the cluster (e.g. `"q-03"`).
2. `title` ≤ 30 chars Chinese / 50 chars English. Format: `"<核心概念> + <周边补充>"`.
   Example: `"SSE 流式推送 与 fetch-event-source"`.
3. `scenario` — exactly **one sentence** answering "this cluster solves what real
   problem". Avoid academic phrasing.
4. `prerequisites` — 0–2 bullets describing minimum prior knowledge (e.g.
   "知道 fetch / 跑过 npm create vite"). If a prerequisite has its own canonical
   beginner doc, append a URL.
5. `must_read` — 2–6 entries, each `{ title, url }`. **`url` MUST be a public
   https URL**. Prefer in this priority order:
   - Official docs in the user's language (中文优先 if `platform_name` is
     Chinese-context). If no Chinese version, use English official.
   - W3C / WHATWG / RFC primary specs.
   - MDN.
   - High-signal authored articles (Martin Fowler, Dan Abramov, Kent C. Dodds,
     Julia Evans).
   - Tool README on GitHub when no separate doc site exists.
   You MAY merge with topics' original `must_read` entries, but if the original
   lacks a URL, you MUST upgrade it to a URL form.
6. `hands_on` — 2–4 entries, each ≤ 2 hours, producing a concrete artifact.
   Each entry must start with a verb (写 / 实现 / 配置 / 对比 / 部署 …).
   Reuse existing `hands_on` from the topics where possible.
7. `self_check` — exactly **3 short questions** the learner can answer in 30s
   each to declare the cluster done. Phrase them as questions, not statements.
8. `covered_topics` — array of topic names from the knowledge map that this
   cluster covers (de-dup within cluster, copy verbatim).

---

## D. Anti-noise rules

- **Never invent a cluster** without a corresponding `qa.id`. Aggregation only.
- **Never drop a topic**: every topic in `knowledge_map.topics` must appear in
  at least one cluster's `covered_topics`. After computing all clusters, run a
  set-diff check; if any topic is missing, add a synthetic cluster
  `id = "extras"` to capture them (rare; usually a sign of bad input).
- **Never use bare titles in `must_read`**. If you cannot find a URL, drop the
  entry.
- **Avoid emoji** in titles or scenarios. Markdown renderer adds visual cues.
- **Tone**: write in second person, friendly, action-oriented Chinese
  (or English in the en variant). Do NOT use marketing language.

---

## E. JSON shape (must match schema)

```json
{
  "schema_version": "1.0",
  "mode": "study-guide",
  "platform_name": "<copied>",
  "study_guide": {
    "phases": [
      { "id": "A", "theme": "Web 基础底座", "cluster_ids": ["q-01", "q-12", "q-06"] }
    ],
    "clusters": [
      {
        "id": "q-01",
        "title": "SSE 流式推送 与 fetch-event-source",
        "scenario": "ChatGPT 那种逐字蹦字的效果背后，就是 SSE。",
        "prerequisites": [
          { "text": "知道 HTTP 请求/响应；用过 fetch", "url": "https://developer.mozilla.org/zh-CN/docs/Web/API/Fetch_API/Using_Fetch" }
        ],
        "must_read": [
          { "title": "MDN: Using server-sent events", "url": "https://developer.mozilla.org/zh-CN/docs/Web/API/Server-sent_events/Using_server-sent_events" }
        ],
        "hands_on": [
          "用 Express 写 30 行 SSE demo，支持 Last-Event-ID 续接",
          "把 demo 接到本地 nginx 反代后面，验证 X-Accel-Buffering 关闭后流式首字节"
        ],
        "self_check": [
          "为什么 SSE 报文必须以 \\n\\n 结尾？",
          "为什么 SSE 在 nginx 后默认会卡住不流？",
          "选 SSE 不选 WebSocket 的 3 个理由是什么？"
        ],
        "covered_topics": ["SSE 协议规范", "fetch-event-source", "WebSocket vs SSE"]
      }
    ],
    "global_self_check": [
      { "cluster_id": "q-01", "question": "SSE 报文为什么必须 \\n\\n 结尾？" }
    ],
    "tips": [
      "先做 demo 再读规范：每个簇都从最小可运行开始",
      "Windows 同学：sandbox / nginx / shell 部分强烈建议在 WSL2 里做",
      "每周写一篇 200 字小结：是最便宜的检索机制"
    ]
  }
}
```

---

## F. Output

Output **only the JSON**, no surrounding prose, no Markdown fences. Validate
against `schemas/interview-data.schema.json` study-guide branch.

---

## G. Inputs

KNOWLEDGE_JSON:
<<KNOWLEDGE_JSON>>

PROJECT_CONTEXT_JSON:
<<PROJECT_CONTEXT_JSON>>

<!-- impl version: v1.0 -->
