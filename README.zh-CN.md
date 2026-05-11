# project-interview-coach

> **简体中文** · [English](./README.md)

把当前工作区项目转成面试复盘材料的 skill —— 中英双语 Markdown + 结构化 JSON，下游 agent 可直接消费。

三种产出模式：

| 模式 | 适用人群 | 产物形态 |
|------|---------|---------|
| `candidate`   | 求职者准备面试         | 三档 project pitch（电梯/标准/深挖）+ 问答（含答案、知识点、补齐方案） |
| `interviewer` | 面试官准备面试评估       | 题库 + 评分卡，每题 ≥3 个评分维度，三档表现指标（优秀/合格/不合格） |
| `knowledge`   | 复盘者梳理掌握度         | 反向索引的知识图谱（按问题归并）—— 纯聚合，**不需要调用 LLM** |
| `study-guide` | 看完知识图谱但不知道从哪下手的初学者 | 阶段 → 簇的学习路径：每个簇带前置、可点击的必读外链、动手练习与 3 道自检 |

## 当前状态

M4 + 后续 CLI 完成，83 个测试全绿。Stage 1–3（项目扫描 → tech-point 抽取 → 各模式产出）需要调用方提供 LLM 驱动；`knowledge` 模式的 stage 3 在 Python 里完整闭环。`study-guide` 消费 knowledge 模式 JSON（先跑一次 `mode=knowledge`），渲染路径与其他 LLM 模式一致。

## 安装

```bash
# CodeBuddy
git clone https://github.com/vi-vi-vera/project-interview-coach.git ~/.codebuddy/skills/project-interview-coach

# Claude Code
git clone https://github.com/vi-vi-vera/project-interview-coach.git ~/.claude/skills/project-interview-coach
```

## 在支持 skill 的 agent 中使用

```
帮我用 project-interview-coach 分析当前项目，生成面试准备材料。
```

参数（同样定义在 [`SKILL.md`](./SKILL.md)）：

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `mode` | `candidate` | `candidate` / `interviewer` / `knowledge` / `study-guide` |
| `role` | `全栈` | 例：后端 / 前端 / 架构师 |
| `level` | `中级` | `初级` / `中级` / `高级` |
| `depth` | `medium` | `light` / `medium` / `deep` |
| `output_dir` | `./interview-prep` | |
| `force` | `false` | 强制重跑全部 stage，忽略缓存 |
| `include_study_guide` | `false` | 仅在 `mode=candidate` 下生效。设为 `true` 时，candidate 主流程跑完后会顺手产出 `study-guide.{zh,en}.md`，详见下文 *study-guide 模式*。|

## 独立 CLI

`coach` 是 Python 脚本的统一入口。需要 LLM 的阶段（candidate / interviewer）由调用 agent 协调；`knowledge` 模式是纯聚合，可以从头到尾在 Python 里跑完。

```bash
# 1) 扫描工作区 → 输出脱敏后的 JSON bundle（stage 1 的输入）
python -m scripts.cli scan --workspace . --depth medium > bundle.json

# 2) 把 interview-data.json 渲染为中英双语 markdown
python -m scripts.cli render \
  --data interview-data.json \
  --templates ./templates \
  --out ./interview-prep

# 3) 把 candidate JSON 聚合为 knowledge JSON（无 LLM、确定性输出）
python -m scripts.cli aggregate \
  --data candidate-interview-data.json \
  --out knowledge-data.json

# 4) knowledge 模式一键流水线：聚合 + 渲染
python -m scripts.cli run --mode knowledge \
  --data candidate-interview-data.json \
  --templates ./templates \
  --out ./interview-prep
```

说明：

- `coach scan` 接受 `--depth {light,medium,deep}` 和 `--projects auto|<csv>`。默认输出到 stdout，加 `--out <path>` 写文件。脱敏器命中 `HIGH_RISK_HIT` 时退出码为 2，扫描中止。
- `coach render` 支持三种模式，渲染器按 `data.mode` 分发。candidate 模式会做 word-budget lint，越界以 warning 形式打到 stderr，不影响渲染产物。
- `coach aggregate` 把 `prompts/stage3-knowledge.md` §§A–D 的规则原样翻译成 Python：零幻觉、diff 稳定、可回归测试。设计上保守优先——严格遵循 prompt 明文的归一化规则，不做「智能」合并（例如带括号扩展的同名 topic 仍保留为两条）。
- `coach run --mode knowledge` 一步产出中间 `knowledge-data.json` 加 `knowledge-map.{zh,en}.md`。`--mode candidate/interviewer` 故意不提供——它们必须经过 LLM stage，不在 Python 边界内。

## study-guide 模式（零基础学习路径）

`study-guide` 把 knowledge 模式 JSON 转成有序的学习路径，必读材料都是可点击的外链。

### 最省事的用法：跟 `mode=candidate` 一起跑

如果你本来就要跑 `mode=candidate`，直接加 `include_study_guide=true`，candidate 跑完顺手把学习指引一起出了：

```
invoke project-interview-coach with mode=candidate, include_study_guide=true
```

内部流程（详见 [`SKILL.md`](./SKILL.md) Stage 3.5）：

1. candidate 主流程正常跑完 → `interview-data.json` + `interview-prep.{zh,en}.md`。
2. `coach aggregate` 从 candidate JSON 派生出一份 knowledge JSON（纯 Python，无 LLM）。
3. `prompts/stage3-study-guide.md` 用这份 knowledge JSON 跑一次 LLM → `study-guide-data.json`。
4. `coach render` 写出 `study-guide.{zh,en}.md`。

candidate 的 `interview-data.json` **不会被改动**。`include_study_guide=true` 在非 candidate 模式下是 no-op。

### 手动用法：单独跑 study-guide

如果你只想要学习指引（比如基于已有的 knowledge JSON）：

```bash
# 0) 前置：先跑一次 knowledge 模式产出 knowledge JSON。
python -m scripts.cli run --mode knowledge \
  --data candidate-interview-data.json \
  --templates ./templates \
  --out ./interview-prep

# 1) 用 prompts/stage3-study-guide.md 驱动 LLM，输入 knowledge JSON
#    （可选附带 stage-1 的 project-context），让 LLM 输出
#    study-guide 模式的 interview-data.json，存为 study-guide-data.json。

# 2) 渲染中英文 markdown。
python -m scripts.cli render \
  --data study-guide-data.json \
  --templates ./templates \
  --out ./interview-prep
# → interview-prep/study-guide.zh.md + study-guide.en.md
```

在支持 skill 的 agent 里：

```
invoke project-interview-coach with mode=study-guide
```

schema 分支强制：`must_read[].url` 必须是 `https://...`，每个 cluster 恰好 3 道自检，study-guide JSON 不允许夹带 candidate / interviewer / knowledge 的字段。

## 产物

一次完整运行后，`output_dir` 大致是：

```
interview-prep/
├── interview-data.json        # 始终产出：结构化 JSON，参见 schemas/
├── interview-prep.zh.md       # candidate 模式
├── interview-prep.en.md       # candidate 模式
├── interviewer-pack.zh.md     # interviewer 模式
├── interviewer-pack.en.md     # interviewer 模式
├── knowledge-map.zh.md        # knowledge 模式
├── knowledge-map.en.md        # knowledge 模式
├── study-guide.zh.md          # study-guide 模式
└── study-guide.en.md          # study-guide 模式
```

其他 agent 可以直接读 `interview-data.json`，它的形状由 `schemas/interview-data.schema.json` 定义（单 schema，按 `mode` 分三个 `if/then` 分支）。

## 目录结构

```
project-interview-coach/
├── prompts/        # stage 1/2/3-{candidate,interviewer,knowledge,study-guide} 的 prompt
├── schemas/        # JSON Schema（draft-07）：project-context / tech-points / interview-data
├── scripts/        # Python：CLI、扫描、脱敏、渲染、聚合
├── templates/      # 4 模式 × 2 语言的 Jinja2 模板
├── tests/          # pytest 测试集
├── SKILL.md
└── README.md / README.zh-CN.md
```

## 开发

```bash
python -m pytest                                     # 全量（83 个测试）
python -m pytest tests/test_cli.py                   # CLI 子集
python -m pytest tests/test_aggregate_knowledge.py   # knowledge 聚合器
python -m pytest tests/test_render_study_guide.py    # study-guide 模式
```

依赖：`jsonschema`、`jinja2`、`pytest`。

## 设计原则

- **聚合而非生成**。Stage 3 prompt 明确禁止 LLM 自己造前面阶段没有的 topic；knowledge 模式更进一步，整个 stage 3 都在 Python 里跑。
- **Schema 即契约**。三个模式共用一份 schema，按 `mode` 触发不同 `if/then/required` 分支；渲染器和聚合器都按 schema 校验输出。
- **保守优于取巧**。Prompt 与 LLM 在边界场景上不一致时，Python 实现按 prompt 明文行事 —— diff 稳定胜过偶尔的「聪明合并」。

## 许可

MIT —— 详见 [LICENSE](./LICENSE)。
