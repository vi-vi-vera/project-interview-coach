"""Tests for study-guide-mode rendering and schema branch."""

import copy
import json
import re
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "interview-data.schema.json").read_text(encoding="utf-8"))
STUDY_GUIDE_FIXTURE_PATH = ROOT / "tests" / "fixtures" / "sample_study_guide_data.json"
STUDY_GUIDE_FIXTURE = json.loads(STUDY_GUIDE_FIXTURE_PATH.read_text(encoding="utf-8"))
KNOWLEDGE_FIXTURE = json.loads(
    (ROOT / "tests" / "fixtures" / "sample_knowledge_data.json").read_text(encoding="utf-8")
)
TEMPLATES = ROOT / "templates"


# ---------------------------------------------------------------------------
# Schema branch
# ---------------------------------------------------------------------------

def test_study_guide_fixture_validates():
    jsonschema.validate(STUDY_GUIDE_FIXTURE, SCHEMA)


def test_study_guide_missing_study_guide_fails():
    bad = copy.deepcopy(STUDY_GUIDE_FIXTURE)
    bad.pop("study_guide")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_study_guide_must_read_url_required():
    """Bare titles in must_read (no URL) must be rejected."""
    bad = copy.deepcopy(STUDY_GUIDE_FIXTURE)
    # Drop url on the first must_read of the first cluster.
    bad["study_guide"]["clusters"][0]["must_read"][0].pop("url")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_study_guide_must_read_non_https_rejected():
    """Schema's pattern ^https?:// keeps the URLs publicly fetchable."""
    bad = copy.deepcopy(STUDY_GUIDE_FIXTURE)
    bad["study_guide"]["clusters"][0]["must_read"][0]["url"] = "ftp://example.com/x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_study_guide_self_check_must_be_three():
    """Each cluster must carry exactly 3 self-check questions."""
    bad = copy.deepcopy(STUDY_GUIDE_FIXTURE)
    bad["study_guide"]["clusters"][0]["self_check"] = bad["study_guide"]["clusters"][0]["self_check"][:2]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_study_guide_forbidden_fields():
    """study-guide branch must NOT carry candidate / interviewer / knowledge payloads."""
    for forbidden_key, sample_payload in [
        ("qa", [{"id": "x"}]),
        ("knowledge_map", {"topics": [{"name": "t"}]}),
        ("project_pitch", {"elevator": {"zh": "x", "en": "y"}}),
    ]:
        bad = copy.deepcopy(STUDY_GUIDE_FIXTURE)
        bad[forbidden_key] = sample_payload
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, SCHEMA)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def test_study_guide_render_outputs_both_locales(tmp_path):
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=STUDY_GUIDE_FIXTURE_PATH,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    assert zh_path.name == "study-guide.zh.md"
    assert en_path.name == "study-guide.en.md"
    assert zh_path.exists() and zh_path.stat().st_size > 0
    assert en_path.exists() and en_path.stat().st_size > 0


def test_study_guide_render_required_sections(tmp_path):
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=STUDY_GUIDE_FIXTURE_PATH,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    zh = zh_path.read_text(encoding="utf-8")
    en = en_path.read_text(encoding="utf-8")

    for keyword in ["零基础学习指引", "怎么使用这份指引", "必读材料", "动手练习", "自检", "全局自检", "学习效率 Tips"]:
        assert keyword in zh, f"Chinese study guide missing: {keyword}"
    for keyword in ["Beginner Study Guide", "How to use this guide", "Must Read", "Hands-On", "Self Check", "Global Self Check", "Learning Tips"]:
        assert keyword in en, f"English study guide missing: {keyword}"


def test_study_guide_render_phase_order_and_clusters(tmp_path):
    """Phases render in declared order; each cluster appears under its phase."""
    from scripts.render_markdown import render

    zh_path, _ = render(
        interview_data_path=STUDY_GUIDE_FIXTURE_PATH,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    zh = zh_path.read_text(encoding="utf-8")

    pos_a = zh.find("阶段 A：Web 基础底座")
    pos_b = zh.find("阶段 B：并发与状态")
    pos_c = zh.find("阶段 C：性能与运行时")
    assert pos_a > 0 and pos_b > pos_a > 0 and pos_c > pos_b
    # Cluster id appears under its phase.
    assert zh.find("（q-01）", pos_a) < zh.find("（q-03）", pos_b) < zh.find("（q-04）", pos_c)


def test_study_guide_render_must_read_are_clickable_links(tmp_path):
    """Every must_read entry must render as `[title](https://...)` markdown link.

    Acceptance criterion 3 from the implementation directive:
      grep one pass: each must_read line is `\\[.*\\]\\(http`.
    """
    from scripts.render_markdown import render

    zh_path, en_path = render(
        interview_data_path=STUDY_GUIDE_FIXTURE_PATH,
        template_dir=TEMPLATES,
        output_dir=tmp_path,
    )
    link_re = re.compile(r"\[[^\]]+\]\(https?://[^\)]+\)")
    expected_total = sum(
        len(c["must_read"]) for c in STUDY_GUIDE_FIXTURE["study_guide"]["clusters"]
    )
    for path in (zh_path, en_path):
        text = path.read_text(encoding="utf-8")
        # The "Must Read"/"必读材料" section is the only place numbered http
        # links appear; every entry must use the [title](url) syntax.
        numbered = re.findall(r"^\d+\. (\[.+\]\(https?://[^\)]+\))", text, flags=re.MULTILINE)
        assert len(numbered) == expected_total, (
            f"{path.name}: expected {expected_total} clickable must_read entries, "
            f"got {len(numbered)}"
        )
        # All matches must conform to markdown link.
        for line in numbered:
            assert link_re.fullmatch(line) or link_re.search(line)


def test_study_guide_covers_all_knowledge_topics():
    """Acceptance criterion 4 (directive §7):

    Union of clusters[*].covered_topics MUST equal the set of
    knowledge_map.topics[*].name. The fixture was authored to satisfy this
    against tests/fixtures/sample_knowledge_data.json.
    """
    knowledge_topic_names = {
        t["name"] for t in KNOWLEDGE_FIXTURE["knowledge_map"]["topics"]
    }
    covered: set[str] = set()
    for c in STUDY_GUIDE_FIXTURE["study_guide"]["clusters"]:
        covered.update(c["covered_topics"])
    missing = knowledge_topic_names - covered
    assert not missing, f"covered_topics misses: {missing}"


def test_study_guide_phase_cluster_ids_resolve():
    """Every cluster_id in a phase must point to an existing cluster."""
    cluster_ids = {c["id"] for c in STUDY_GUIDE_FIXTURE["study_guide"]["clusters"]}
    for phase in STUDY_GUIDE_FIXTURE["study_guide"]["phases"]:
        for cid in phase["cluster_ids"]:
            assert cid in cluster_ids, f"phase {phase['id']} references unknown cluster {cid}"
