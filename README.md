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

## Development

```bash
python -m pytest tests/test_redact.py -v
```

## License

MIT — see [LICENSE](./LICENSE).
