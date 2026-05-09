"""Tests for knowledge-mode rendering in scripts.render_markdown."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_knowledge_data.json"
TEMPLATES = ROOT / "templates"


def test_knowledge_render_outputs_both_locales(tmp_path):
    """Given a valid knowledge-mode interview-data.json, render() writes knowledge-map.{zh,en}.md."""
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=FIXTURE,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )

    # Knowledge mode must produce knowledge-map.* (not interview-prep.*)
    assert zh_path.name == "knowledge-map.zh.md"
    assert en_path.name == "knowledge-map.en.md"
    assert zh_path.exists() and zh_path.stat().st_size > 0
    assert en_path.exists() and en_path.stat().st_size > 0


def test_knowledge_render_contains_required_headings(tmp_path):
    """Rendered markdown must contain canonical section headings and topic content."""
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=FIXTURE,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    zh = zh_path.read_text(encoding="utf-8")
    en = en_path.read_text(encoding="utf-8")

    # zh required content
    for keyword in ["知识图谱", "必读材料", "动手练习", "SSE 协议规范", "Promise 多消费者语义", "q-01", "q-03"]:
        assert keyword in zh, f"Chinese knowledge map missing: {keyword}"

    # en required content
    for keyword in ["Knowledge Map", "Must-read", "Hands-on", "SSE 协议规范", "q-01", "q-03"]:
        assert keyword in en, f"English knowledge map missing: {keyword}"


def test_knowledge_render_groups_topics_by_level(tmp_path):
    """必须掌握 (must-master) topics must appear before 加分项 (bonus) topics."""
    from scripts.render_markdown import render

    zh_path, _ = render(
        interview_data_path=FIXTURE,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    zh = zh_path.read_text(encoding="utf-8")

    # SSE 协议规范 is 必须掌握; Promise 多消费者语义 is 加分项 — sse must come first
    sse_pos = zh.find("SSE 协议规范")
    promise_pos = zh.find("Promise 多消费者语义")
    assert sse_pos != -1 and promise_pos != -1
    assert sse_pos < promise_pos, "必须掌握 topics must render before 加分项 topics"


def test_knowledge_render_rejects_invalid_schema(tmp_path):
    """A knowledge-mode payload missing required `knowledge_map` must raise."""
    from scripts.render_markdown import render

    bad = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bad.pop("knowledge_map")
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(Exception):
        render(
            interview_data_path=bad_path,
            template_dir=TEMPLATES,
            output_dir=tmp_path,
        )
