---
name: project-interview-coach
version: 1.0.0
description: 扫描当前工作区项目，生成针对面试的复盘材料（中英双语 Markdown + 结构化 JSON）。
parameters:
  mode:
    type: enum
    values: [candidate, interviewer, knowledge]
    default: candidate
  role:
    type: string
    default: 全栈
  level:
    type: enum
    values: [初级, 中级, 高级]
    default: 中级
  depth:
    type: enum
    values: [light, medium, deep]
    default: medium
  output_dir:
    type: path
    default: ./interview-prep
  force:
    type: bool
    default: false
outputs:
  - interview-prep/interview-prep.zh.md
  - interview-prep/interview-prep.en.md
  - interview-prep/interview-data.json
---

# project-interview-coach

This skill turns the current workspace project into interview-preparation material from a job-seeker's perspective. It produces bilingual (Chinese / English) Markdown plus a structured JSON file that can be consumed by other agents.

## When to use this skill

Activate when the user asks any of:
- "帮我准备这个项目的面试问答"
- "summarize this project for an interview"
- "generate interview Q&A from this codebase"

## Execution flow

The skill is a 3-stage pipeline. Run stages **in order**. Each stage caches its output under `.cache/interview-coach/` in the workspace; subsequent runs reuse cached artifacts unless `force=true`.

### Stage 1 — Project scan
1. Run `python scripts/collect_project_meta.py --depth=<depth>` to gather README, dependency manifests, git log, directory tree, with secrets redacted via `scripts/redact_secrets.py`.
2. Feed the resulting raw bundle plus `prompts/stage1-scan.md` to the LLM. The LLM returns JSON conforming to `schemas/project-context.schema.json`.
3. Save to `.cache/interview-coach/project-context.json`.

### Stage 2 — Tech-point extraction
1. Load `project-context.json`.
2. Send it together with `prompts/stage2-extract.md` (parameterised by `role` and `level`) to the LLM.
3. Validate the LLM output against `schemas/tech-points.schema.json` and save to `.cache/interview-coach/tech-points.json`.

### Stage 3 — Interview material generation
1. Pick the prompt by `mode`:
   - `candidate` → `prompts/stage3-candidate.md` (default)
   - `interviewer` → `prompts/stage3-interviewer.md`
   - `knowledge` → `prompts/stage3-knowledge.md`
2. Feed both cached JSON files plus the chosen prompt to the LLM, get JSON conforming to `schemas/interview-data.schema.json`.
3. Save `interview-data.json` to `output_dir`.
4. Run `python scripts/render_markdown.py --input <output_dir>/interview-data.json --output-dir <output_dir>` to produce `interview-prep.zh.md` and `interview-prep.en.md`.

## Safety rules

- Always run `scripts/redact_secrets.py` over any file content before sending it to an LLM.
- If the redactor reports a high-risk hit (`HIGH_RISK_HIT`), **stop** and ask the user to confirm or whitelist before continuing.
- Never include `.env*`, `secrets/`, or `*.key` files in raw form.

## Outputs

After a successful run the workspace contains:

```
interview-prep/
├── interview-prep.zh.md
├── interview-prep.en.md
└── interview-data.json
```

Other agents may consume `interview-data.json` directly; its shape is defined by `schemas/interview-data.schema.json`.

## Status

This is the M1 release (skeleton + redactor). LLM-driven stages will be implemented in M2–M4.
