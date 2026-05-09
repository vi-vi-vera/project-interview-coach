# project-interview-coach

> A skill that turns the current workspace project into interview-preparation material — bilingual Markdown plus structured JSON for other agents to consume.

**Status:** M1 — skeleton released. LLM-driven generation lands in M2–M4.

## Install

Clone this repo into your skills directory:

```bash
# Claude Code
git clone https://github.com/vi-vi-vera/project-interview-coach.git ~/.claude/skills/project-interview-coach

# CodeBuddy
git clone https://github.com/vi-vi-vera/project-interview-coach.git ~/.codebuddy/skills/project-interview-coach
```

## Usage (preview)

In a skill-compatible agent, ask:

> 帮我用 project-interview-coach 分析当前项目，生成面试准备材料。

Parameters (see `SKILL.md`):

| Name | Default | Notes |
|------|---------|-------|
| `mode` | `candidate` | `candidate` / `interviewer` / `knowledge` |
| `role` | `全栈` | e.g. 后端 / 前端 / 架构师 |
| `level` | `中级` | 初级 / 中级 / 高级 |
| `depth` | `medium` | `light` / `medium` / `deep` |
| `output_dir` | `./interview-prep` | |
| `force` | `false` | re-run all stages, ignoring cache |

## Outputs

```
interview-prep/
├── interview-prep.zh.md
├── interview-prep.en.md
└── interview-data.json   # see schemas/interview-data.schema.json
```

## CLI

A unified `coach` entry wraps the Python-side scripts. LLM-driven stages
(1→2→3) live outside Python and are orchestrated by the calling agent.

```bash
# 1) Scan workspace → emit redacted JSON bundle (input to stage 1)
python -m scripts.cli scan --workspace . --depth medium > bundle.json

# 2) Render a stage-3 interview-data.json → bilingual markdown
python -m scripts.cli render \
  --data interview-data.json \
  --templates ./templates \
  --out ./interview-prep
```

`coach scan` accepts `--depth {light,medium,deep}` and `--projects auto|<csv>`.
`coach render` works for all three modes (candidate / interviewer / knowledge);
the renderer dispatches by `data.mode`. Word-budget lint warnings (candidate
mode only) are printed to stderr.

## Development

```bash
python -m pytest                   # full suite
python -m pytest tests/test_cli.py # CLI subset
```

## License

MIT — see [LICENSE](./LICENSE).
