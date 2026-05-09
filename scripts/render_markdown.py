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
    groups = _group_qa(data.get("qa", []))

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
        autoescape=False,
    )

    context = {
        **data,
        "groups": groups,
        "role": data.get("role", ""),
        "level": data.get("level", ""),
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    zh_tmpl = env.get_template("interview-prep.zh.md.tmpl")
    en_tmpl = env.get_template("interview-prep.en.md.tmpl")

    zh_path = output_dir / "interview-prep.zh.md"
    en_path = output_dir / "interview-prep.en.md"
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
