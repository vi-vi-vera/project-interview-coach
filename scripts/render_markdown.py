"""Render Stage-3 interview-data.json to bilingual markdown.

Pure renderer: no LLM call. Reads a candidate-mode interview-data.json,
validates it against the schema, groups qa by primary_dimension in a
canonical order, then renders two markdown files (zh & en) via Jinja2.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import jsonschema
from jinja2 import Environment, FileSystemLoader


# Canonical dimension order, emoji and bilingual labels.
# Order rationale: architecture first (big-picture), feature/performance/reliability/
# observability/security for typical depth probing, trade-off last (usually cross-cutting).
DIMENSION_META: list[dict[str, str]] = [
    {"dimension": "architecture",  "emoji": "🏗️", "label_zh": "架构",       "label_en": "Architecture"},
    {"dimension": "feature",       "emoji": "🧩", "label_zh": "功能",       "label_en": "Feature"},
    {"dimension": "performance",   "emoji": "⚡",  "label_zh": "性能",       "label_en": "Performance"},
    {"dimension": "reliability",   "emoji": "🛡️", "label_zh": "可靠性",     "label_en": "Reliability"},
    {"dimension": "observability", "emoji": "📈", "label_zh": "可观测性",   "label_en": "Observability"},
    {"dimension": "security",      "emoji": "🔒", "label_zh": "安全",       "label_en": "Security"},
    {"dimension": "trade-off",     "emoji": "⚖️", "label_zh": "取舍",       "label_en": "Trade-off"},
]

# interview_value weight for intra-group ordering.
_VALUE_WEIGHT = {"高": 0, "中": 1, "低": 2}

# knowledge-map level ordering: 必须掌握 first, 加分项 last.
_LEVEL_META: list[dict[str, str]] = [
    {"level": "必须掌握", "emoji": "🔑", "label_zh": "必须掌握", "label_en": "Must master"},
    {"level": "加分项",   "emoji": "✨", "label_zh": "加分项",   "label_en": "Bonus"},
]

# dimension → emoji lookup for knowledge-map topic badges.
_DIMENSION_EMOJI = {
    "architecture":  "🏗️",
    "feature":       "🧩",
    "performance":   "⚡",
    "reliability":   "🛡️",
    "observability": "📈",
    "security":      "🔒",
    "trade-off":     "⚖️",
}


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "schemas" / "interview-data.schema.json"


def _load_and_validate(interview_data_path: Path) -> dict[str, Any]:
    data = json.loads(interview_data_path.read_text(encoding="utf-8"))
    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)
    return data


def _group_qa(qa_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket qa items by primary_dimension in canonical order.

    Only dimensions with ≥1 qa are emitted, so empty sections are skipped.
    """
    buckets: dict[str, list[dict[str, Any]]] = {m["dimension"]: [] for m in DIMENSION_META}
    for qa in qa_list:
        dim = qa.get("primary_dimension")
        if dim in buckets:
            buckets[dim].append(qa)

    # Intra-group ordering: interview_value (高→中→低) then id.
    # interview_value is not guaranteed on qa items (it lives on tech-points); fall back to id only.
    for dim, items in buckets.items():
        items.sort(key=lambda q: (_VALUE_WEIGHT.get(q.get("interview_value", "中"), 1), q.get("id", "")))

    groups: list[dict[str, Any]] = []
    for meta in DIMENSION_META:
        items = buckets[meta["dimension"]]
        if not items:
            continue
        groups.append({**meta, "qa": items})
    return groups


def _group_topics_by_level(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket knowledge_map.topics by level in canonical order (必须掌握 → 加分项).

    Within each level, topics are sorted by name for stable output.
    Empty levels are skipped.
    """
    buckets: dict[str, list[dict[str, Any]]] = {m["level"]: [] for m in _LEVEL_META}
    for topic in topics:
        lvl = topic.get("level")
        if lvl in buckets:
            buckets[lvl].append(topic)

    for items in buckets.values():
        items.sort(key=lambda t: t.get("name", ""))

    groups: list[dict[str, Any]] = []
    for meta in _LEVEL_META:
        items = buckets[meta["level"]]
        if not items:
            continue
        groups.append({**meta, "topics": items})
    return groups


def _group_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bucket interviewer-mode question_bank items by primary_dimension in canonical order.

    Mirrors `_group_qa` but emits the field name `questions` (matching the template),
    and sorts only by id (interviewer questions have no interview_value field).
    """
    buckets: dict[str, list[dict[str, Any]]] = {m["dimension"]: [] for m in DIMENSION_META}
    for q in questions:
        dim = q.get("primary_dimension")
        if dim in buckets:
            buckets[dim].append(q)

    for items in buckets.values():
        items.sort(key=lambda q: q.get("id", ""))

    groups: list[dict[str, Any]] = []
    for meta in DIMENSION_META:
        items = buckets[meta["dimension"]]
        if not items:
            continue
        groups.append({**meta, "questions": items})
    return groups


def _index_rubrics_by_qa(rubrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index rubrics by qa_id and pre-compute weight_sum for template display.

    Returns: { qa_id: { ...rubric, "weight_sum": float } }.
    Done in Python (not Jinja2) because Jinja's sum filter on nested attributes is awkward.
    """
    indexed: dict[str, dict[str, Any]] = {}
    for r in rubrics:
        weight_sum = sum(c.get("weight", 0) for c in r.get("criteria", []))
        indexed[r["qa_id"]] = {**r, "weight_sum": weight_sum}
    return indexed


def render(
    interview_data_path: Path,
    template_dir: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Render bilingual markdown from interview-data.json.

    Args:
        interview_data_path: path to interview-data.json (will be schema-validated).
        template_dir: directory containing interview-prep.zh.md.tmpl and .en.md.tmpl.
        output_dir: directory to write interview-prep.zh.md and .en.md (created if missing).

    Returns:
        (zh_path, en_path) — paths to the two rendered files.

    Raises:
        jsonschema.ValidationError: if interview_data_path fails schema validation.
    """
    data = _load_and_validate(interview_data_path)
    mode = data.get("mode", "candidate")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
        autoescape=False,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    if mode == "knowledge":
        return _render_knowledge(data, env, output_dir)
    if mode == "interviewer":
        return _render_interviewer(data, env, output_dir)
    # default: candidate mode
    return _render_candidate(data, env, output_dir)


def _render_candidate(
    data: dict[str, Any],
    env: Environment,
    output_dir: Path,
) -> tuple[Path, Path]:
    groups = _group_qa(data.get("qa", []))
    context = {
        **data,
        "groups": groups,
        "role": data.get("role", ""),
        "level": data.get("level", ""),
    }

    zh_tmpl = env.get_template("interview-prep.zh.md.tmpl")
    en_tmpl = env.get_template("interview-prep.en.md.tmpl")

    zh_path = output_dir / "interview-prep.zh.md"
    en_path = output_dir / "interview-prep.en.md"
    zh_path.write_text(zh_tmpl.render(**context), encoding="utf-8")
    en_path.write_text(en_tmpl.render(**context), encoding="utf-8")
    return zh_path, en_path


def _render_interviewer(
    data: dict[str, Any],
    env: Environment,
    output_dir: Path,
) -> tuple[Path, Path]:
    groups = _group_questions(data.get("question_bank", []))
    rubrics_by_qa = _index_rubrics_by_qa(data.get("rubrics", []))
    context = {
        **data,
        "groups": groups,
        "rubrics_by_qa": rubrics_by_qa,
        "role": data.get("role", ""),
        "level": data.get("level", ""),
    }

    zh_tmpl = env.get_template("interviewer-pack.zh.md.tmpl")
    en_tmpl = env.get_template("interviewer-pack.en.md.tmpl")

    zh_path = output_dir / "interviewer-pack.zh.md"
    en_path = output_dir / "interviewer-pack.en.md"
    zh_path.write_text(zh_tmpl.render(**context), encoding="utf-8")
    en_path.write_text(en_tmpl.render(**context), encoding="utf-8")
    return zh_path, en_path


def _render_knowledge(
    data: dict[str, Any],
    env: Environment,
    output_dir: Path,
) -> tuple[Path, Path]:
    topics = data.get("knowledge_map", {}).get("topics", [])
    level_groups = _group_topics_by_level(topics)
    context = {
        **data,
        "level_groups": level_groups,
        "dimension_emoji": _DIMENSION_EMOJI,
    }

    zh_tmpl = env.get_template("knowledge-map.zh.md.tmpl")
    en_tmpl = env.get_template("knowledge-map.en.md.tmpl")

    zh_path = output_dir / "knowledge-map.zh.md"
    en_path = output_dir / "knowledge-map.en.md"
    zh_path.write_text(zh_tmpl.render(**context), encoding="utf-8")
    en_path.write_text(en_tmpl.render(**context), encoding="utf-8")
    return zh_path, en_path


def _main() -> None:
    parser = argparse.ArgumentParser(description="Render interview-data.json to bilingual markdown.")
    parser.add_argument("--data", required=True, type=Path, help="path to interview-data.json")
    parser.add_argument("--templates", required=True, type=Path, help="directory containing Jinja2 templates")
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    args = parser.parse_args()

    zh, en = render(args.data, args.templates, args.out)
    print(f"Wrote: {zh}")
    print(f"Wrote: {en}")


if __name__ == "__main__":
    _main()
