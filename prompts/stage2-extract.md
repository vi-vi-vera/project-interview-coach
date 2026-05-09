# Stage 2 — Tech-point extraction prompt

You are given:
- `<<PROJECT_CONTEXT_JSON>>` — output of Stage 1
- Parameters: `role = <<ROLE>>`, `level = <<LEVEL>>`

## Your task

Produce a single JSON object that conforms exactly to `schemas/tech-points.schema.json`.

Rules:
1. `schema_version` — `"1.0"`. `role`, `level` copied verbatim.
2. Extract **6–12 tech points** that an interviewer of the given `role` and `level` is likely to drill into.
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
8. Output JSON only.

## Input

PROJECT_CONTEXT_JSON:
<<PROJECT_CONTEXT_JSON>>
