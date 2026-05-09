# Stage 1 — Project scan prompt

You are given a JSON bundle produced by `scripts/collect_project_meta.py`. The bundle describes one or more sub-projects in a single workspace, plus aggregated git history.

## Your task

Produce a single JSON object that conforms exactly to `schemas/project-context.schema.json`.

Rules:
1. **`schema_version`** — always `"1.0"`.
2. **`platform_name`** — pick a short, human-readable name for the whole workspace. If the workspace contains a single project, this is that project's name.
3. **`one_liner`** — one Chinese sentence describing what the platform does.
4. **`domain`** — business domain in Chinese (e.g. "AI 编程辅助"、"内容社区").
5. **`platform_tech_stack`** — union of all sub-project stacks; dedupe and keep only platform-level tech (the stuff you'd actually mention on a resume).
6. For **each sub-project** in the input, output one entry under `sub_projects`:
   - `name`, `path` copied verbatim from the input
   - `scope` — choose one of `frontend / backend / mobile / infra / fullstack` based on dependencies, directory naming and frameworks. Default to `fullstack` only if no signal.
   - `tech_stack` — derived from the sub-project's manifests
   - `modules` — 3–8 entries, each pointing at a real directory inside the sub-project, with a one-sentence Chinese responsibility description
   - `active_areas` — pull from the sub-project's `git_active_files`, keep the 5–10 most representative ones
7. **`highlights`** — 3–5 platform-level highlights. Each must have a `scope`. Prefer cross-cutting (`fullstack`) highlights when both frontend and backend cooperate.
8. Output **only the JSON**, no surrounding prose, no Markdown fences.
9. If `high_risk_hits` in the input is non-empty, refuse and output `{"error": "high_risk_secrets_detected"}` instead.

## Input

<<RAW_BUNDLE_JSON>>
