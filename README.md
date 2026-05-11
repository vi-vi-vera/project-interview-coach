# project-interview-coach

> [简体中文](./README.zh-CN.md) · **English**

A skill that turns the current workspace project into interview-preparation material — bilingual Markdown plus structured JSON for downstream agents.

Three output modes:

| Mode | Audience | What you get |
|------|----------|--------------|
| `candidate`   | Job-seeker preparing for an interview | Project pitch (3 tiers) + Q&A with answers, knowledge points, learning plan |
| `interviewer` | Interviewer preparing the panel       | Question bank + scoring rubrics with weighted criteria and three-tier indicators |
| `knowledge`   | Reviewer tracking mastery             | Cross-linked knowledge map (reverse-indexed by question) — pure aggregation, **no LLM call needed** |
| `study-guide` | Beginner who has the knowledge map but does not know where to click | Sequenced learning path: phases → clusters with prerequisites, clickable must-read URLs, hands-on exercises and self-check |

## Status

M4 + post-M4 CLI complete. 83 tests passing. Stages 1–3 (project scan → tech-point extraction → mode-specific generation) require an LLM driver supplied by the calling agent; stage 3 of `knowledge` mode runs fully in Python. `study-guide` consumes a knowledge-mode JSON (run `mode=knowledge` first) and is rendered the same way as the other LLM modes.

## Install

```bash
# CodeBuddy
git clone https://github.com/vi-vi-vera/project-interview-coach.git ~/.codebuddy/skills/project-interview-coach

# Claude Code
git clone https://github.com/vi-vi-vera/project-interview-coach.git ~/.claude/skills/project-interview-coach
```

## Usage from a skill-aware agent

```
帮我用 project-interview-coach 分析当前项目，生成面试准备材料。
```

Parameters (also defined in [`SKILL.md`](./SKILL.md)):

| Name | Default | Notes |
|------|---------|-------|
| `mode` | `candidate` | `candidate` / `interviewer` / `knowledge` / `study-guide` |
| `role` | `全栈` | e.g. 后端 / 前端 / 架构师 |
| `level` | `中级` | `初级` / `中级` / `高级` |
| `depth` | `medium` | `light` / `medium` / `deep` |
| `output_dir` | `./interview-prep` | |
| `force` | `false` | re-run all stages, ignoring cache |
| `include_study_guide` | `false` | only honored when `mode=candidate`. When `true`, after the candidate pass the skill also produces `study-guide.{zh,en}.md` in one shot — see *Study-guide mode* below. |

## Standalone CLI

A unified `coach` entry wraps the Python-side scripts. The LLM-driven stages (candidate / interviewer) are orchestrated by the calling agent; `knowledge` mode is pure aggregation and runs end-to-end in Python.

```bash
# 1) Scan workspace → emit a redacted JSON bundle (input to stage 1)
python -m scripts.cli scan --workspace . --depth medium > bundle.json

# 2) Render an interview-data.json → bilingual markdown
python -m scripts.cli render \
  --data interview-data.json \
  --templates ./templates \
  --out ./interview-prep

# 3) Aggregate a candidate JSON → knowledge JSON (no LLM, deterministic)
python -m scripts.cli aggregate \
  --data candidate-interview-data.json \
  --out knowledge-data.json

# 4) One-shot knowledge pipeline: aggregate + render
python -m scripts.cli run --mode knowledge \
  --data candidate-interview-data.json \
  --templates ./templates \
  --out ./interview-prep
```

Notes:

- `coach scan` accepts `--depth {light,medium,deep}` and `--projects auto|<csv>`. Output goes to stdout by default; use `--out <path>` to write to a file. Scans abort with exit code 2 when the redactor flags `HIGH_RISK_HIT`.
- `coach render` works for all three modes; the renderer dispatches by `data.mode`. Word-budget lint warnings (candidate mode only) are printed to stderr but do not fail rendering.
- `coach aggregate` implements `prompts/stage3-knowledge.md` §§A–D in pure Python — zero hallucination, diff-stable, regression-tested. Conservative by design: follows the prompt's normalization rules literally and does not do "smart" merges (e.g. parenthetical extensions remain distinct topics).
- `coach run --mode knowledge` writes the intermediate `knowledge-data.json` plus `knowledge-map.{zh,en}.md` in one step. `--mode {candidate,interviewer}` are intentionally not supported here because they require LLM stages outside Python.

## Study-guide mode (beginner-friendly path)

`study-guide` turns a knowledge-mode JSON into a sequenced learning path with clickable must-read URLs and hands-on exercises.

### Easiest: piggyback on `mode=candidate`

If you already plan to run `mode=candidate`, just pass `include_study_guide=true` and the skill will produce both deliverables in one go:

```
invoke project-interview-coach with mode=candidate, include_study_guide=true
```

What happens internally (see [`SKILL.md`](./SKILL.md) Stage 3.5):

1. Standard candidate pipeline runs to completion → `interview-data.json` + `interview-prep.{zh,en}.md`.
2. `coach aggregate` derives a knowledge-mode JSON from the candidate output (pure Python, no LLM).
3. `prompts/stage3-study-guide.md` runs once against that knowledge JSON → `study-guide-data.json`.
4. `coach render` writes `study-guide.{zh,en}.md`.

The candidate `interview-data.json` is **not** modified. `include_study_guide=true` outside `mode=candidate` is a no-op.

### Manual: standalone study-guide run

If you only want the study guide (e.g. on top of an existing knowledge JSON):

```bash
# 0) Pre-requisite: produce a knowledge-mode JSON first.
python -m scripts.cli run --mode knowledge \
  --data candidate-interview-data.json \
  --templates ./templates \
  --out ./interview-prep

# 1) Drive prompts/stage3-study-guide.md with the knowledge JSON
#    (and optionally the stage-1 project context); the LLM returns a
#    study-guide-mode interview-data.json. Save it as study-guide-data.json.

# 2) Render the bilingual markdown.
python -m scripts.cli render \
  --data study-guide-data.json \
  --templates ./templates \
  --out ./interview-prep
# → interview-prep/study-guide.zh.md + study-guide.en.md
```

From a skill-aware agent:

```
invoke project-interview-coach with mode=study-guide
```

The schema branch is enforced: `must_read[].url` MUST be `https://...`, every cluster carries exactly 3 self-check questions, and candidate / interviewer / knowledge payloads are forbidden in a study-guide JSON.

## Outputs

A successful run leaves the chosen `output_dir` looking like:

```
interview-prep/
├── interview-data.json        # always: structured JSON, see schemas/
├── interview-prep.zh.md       # candidate mode
├── interview-prep.en.md       # candidate mode
├── interviewer-pack.zh.md     # interviewer mode
├── interviewer-pack.en.md     # interviewer mode
├── knowledge-map.zh.md        # knowledge mode
├── knowledge-map.en.md        # knowledge mode
├── study-guide.zh.md          # study-guide mode
└── study-guide.en.md          # study-guide mode
```

Other agents may consume `interview-data.json` directly; its shape is defined by `schemas/interview-data.schema.json` (single schema, three `if/then` branches by `mode`).

## Project layout

```
project-interview-coach/
├── prompts/        # stage 1/2/3-{candidate,interviewer,knowledge,study-guide} prompts
├── schemas/        # JSON Schemas (draft-07): project-context, tech-points, interview-data
├── scripts/        # Python: CLI, scan, redact, render, aggregate
├── templates/      # Jinja2 templates for the 4 modes × 2 locales
├── tests/          # pytest suite
├── SKILL.md
└── README.md / README.zh-CN.md
```

## Development

```bash
python -m pytest                          # full suite (83 tests)
python -m pytest tests/test_cli.py        # CLI subset
python -m pytest tests/test_aggregate_knowledge.py  # knowledge aggregator
python -m pytest tests/test_render_study_guide.py   # study-guide mode
```

Dependencies: `jsonschema`, `jinja2`, `pytest`.

## Design principles

- **Aggregate, do not generate.** Stage 3 prompts forbid the LLM from inventing topics not grounded in earlier stages; knowledge mode goes further and runs entirely in Python.
- **Schema is the contract.** Three modes share one schema with `if/then/required` branches by `mode`; the renderer and the aggregator both validate against it.
- **Conservative over clever.** When prompt and LLM disagree on edge cases, the Python implementation follows the prompt's literal text — predictable diffs beat occasional cleverness.

## License

MIT — see [LICENSE](./LICENSE).
