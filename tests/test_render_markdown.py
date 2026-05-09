"""Tests for scripts.render_markdown."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_interview_data.json"
TEMPLATES = ROOT / "templates"


def test_render_outputs_both_locales(tmp_path):
    """Given a valid interview-data.json, render() writes both zh.md and en.md."""
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=FIXTURE,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )

    assert zh_path.exists() and zh_path.stat().st_size > 0
    assert en_path.exists() and en_path.stat().st_size > 0

    zh = zh_path.read_text(encoding="utf-8")
    en = en_path.read_text(encoding="utf-8")

    # zh markdown must contain key section headings (from template)
    for keyword in [
        "维度覆盖统计",
        "一句话",
        "标准",
        "深挖",
        "补齐方案",
        "Evidence",
    ]:
        assert keyword in zh, f"Chinese markdown missing heading: {keyword}"

    # en markdown must contain the canonical English headings
    for keyword in [
        "Dimension coverage",
        "Elevator",
        "Standard",
        "Deep dive",
        "Learning plan",
    ]:
        assert keyword in en, f"English markdown missing heading: {keyword}"


def test_render_rejects_invalid_schema(tmp_path):
    """When interview-data.json violates the schema, render() raises instead of silently rendering."""
    from scripts.render_markdown import render

    # drop required field `dimension_coverage`
    bad = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bad.pop("dimension_coverage")
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(Exception):
        render(
            interview_data_path=bad_path,
            template_dir=TEMPLATES,
            output_dir=tmp_path,
        )


def test_render_groups_qa_in_canonical_dimension_order(tmp_path):
    """QA groups must appear in the canonical order: architecture → feature → performance → reliability → observability → security → trade-off."""
    from scripts.render_markdown import render

    # build a minimal 2-qa fixture: one performance qa and one architecture qa;
    # architecture must be rendered BEFORE performance regardless of input order.
    base = json.loads(FIXTURE.read_text(encoding="utf-8"))
    perf_qa = base["qa"][0]
    arch_qa = json.loads(json.dumps(perf_qa))  # deep-copy via json
    arch_qa["id"] = "q-arch-01"
    arch_qa["primary_dimension"] = "architecture"
    arch_qa["question"]["zh"] = "系统分层是怎么设计的？"
    arch_qa["question"]["en"] = "How are the system layers designed?"

    # input order: performance first, architecture second
    base["qa"] = [perf_qa, arch_qa]
    base["dimension_coverage"] = {
        "feature": 0,
        "architecture": 1,
        "performance": 1,
        "reliability": 0,
        "observability": 0,
        "trade-off": 0,
        "security": 0,
    }

    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")

    zh_path, _ = render(
        interview_data_path=data_path,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    zh = zh_path.read_text(encoding="utf-8")

    # architecture section must appear before performance section in rendered output
    arch_pos = zh.find("architecture")
    perf_pos = zh.find("performance）")  # inside the section heading, parenthesised
    assert arch_pos != -1, "architecture section not rendered"
    assert perf_pos != -1, "performance section not rendered"
    assert arch_pos < perf_pos, "architecture must render before performance"
