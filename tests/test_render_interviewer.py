"""Tests for interviewer-mode rendering in scripts.render_markdown."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_interviewer_data.json"
TEMPLATES = ROOT / "templates"


def test_interviewer_render_outputs_both_locales(tmp_path):
    """Given a valid interviewer-mode payload, render() writes interviewer-pack.{zh,en}.md."""
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=FIXTURE,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )

    assert zh_path.name == "interviewer-pack.zh.md"
    assert en_path.name == "interviewer-pack.en.md"
    assert zh_path.exists() and zh_path.stat().st_size > 0
    assert en_path.exists() and en_path.stat().st_size > 0


def test_interviewer_render_contains_rubric_and_no_learning_plan(tmp_path):
    """Rendered markdown must contain rubric headings AND must NOT leak candidate-mode content.

    This is the anti-cross-contamination test: if render accidentally falls back to
    the candidate template, Chinese 『补齐方案』 or English 『Learning plan』 would appear.
    """
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=FIXTURE,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    zh = zh_path.read_text(encoding="utf-8")
    en = en_path.read_text(encoding="utf-8")

    # must contain interviewer-specific sections
    for keyword in ["面试官出题包", "评分卡", "压力追问", "iq-01", "技术正确性"]:
        assert keyword in zh, f"Chinese interviewer pack missing: {keyword}"
    for keyword in ["Interviewer Question Pack", "Rubric", "Stress probes", "iq-01"]:
        assert keyword in en, f"English interviewer pack missing: {keyword}"

    # must NOT contain candidate-mode section headings
    for forbidden in ["补齐方案", "自测题"]:
        assert forbidden not in zh, f"Chinese interviewer pack leaked candidate content: {forbidden}"
    for forbidden in ["Learning plan", "Self-check questions"]:
        assert forbidden not in en, f"English interviewer pack leaked candidate content: {forbidden}"


def test_interviewer_render_groups_questions_by_dimension(tmp_path):
    """Questions must be grouped in canonical dimension order: architecture → ... → trade-off."""
    from scripts.render_markdown import render

    base = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # add a second question in architecture dimension, then feed in performance-first order
    perf_q = base["question_bank"][0]
    arch_q = json.loads(json.dumps(perf_q))
    arch_q["id"] = "iq-arch-01"
    arch_q["primary_dimension"] = "architecture"
    arch_q["question"]["zh"] = "系统分层是怎么设计的？"
    arch_q["question"]["en"] = "How are the system layers designed?"

    # input order: performance first, architecture second
    base["question_bank"] = [perf_q, arch_q]

    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")

    zh_path, _ = render(
        interview_data_path=data_path,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    zh = zh_path.read_text(encoding="utf-8")

    arch_pos = zh.find("architecture）")  # inside the dimension section heading
    perf_pos = zh.find("performance）")
    assert arch_pos != -1 and perf_pos != -1
    assert arch_pos < perf_pos, "architecture must render before performance"


def test_render_rejects_unknown_mode(tmp_path):
    """An interview-data.json with an unsupported mode value must raise.

    The schema's enum currently covers candidate/interviewer/knowledge, so schema
    validation rejects unknown modes up-front. This protects render() from silently
    degrading to the default path.
    """
    from scripts.render_markdown import render

    bad = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bad["mode"] = "lunatic"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(Exception):
        render(
            interview_data_path=bad_path,
            template_dir=TEMPLATES,
            output_dir=tmp_path,
        )
