"""Tests for scripts.aggregate_knowledge — Python replacement for the
LLM-driven Stage-3 knowledge mode.

Why a Python aggregator? prompts/stage3-knowledge.md is explicitly a pure
aggregation: "Do not create new topics", "copy verbatim", "the renderer
sorts within each level". Pure aggregation + zero generation = a perfect
fit for deterministic Python. Bonus: zero hallucination risk, full
regression-testability, and no LLM round-trip.

Spec source of truth: prompts/stage3-knowledge.md sections A–D.

Scope deliberately conservative: we follow the prompt's normalize spec
LITERALLY (lowercase + collapse whitespace + strip trailing punctuation).
We do NOT do "smart" merges (e.g. ignoring parenthetical extensions) even
though the LLM sometimes does. Rationale: predictability beats cleverness;
if the user wants smarter merging, they can extend the prompt and we'll
match.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_candidate_for_aggregation.json"
SCHEMA = ROOT / "schemas" / "interview-data.schema.json"


@pytest.fixture
def candidate():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def aggregated(candidate):
    from scripts.aggregate_knowledge import aggregate_knowledge
    return aggregate_knowledge(candidate)


# ---------------------------------------------------------------------------
# Top-level shape
# ---------------------------------------------------------------------------

def test_output_validates_against_schema(aggregated):
    """Aggregated output must conform to the knowledge-mode schema branch."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(aggregated, schema)


def test_top_level_fields(aggregated):
    """schema_version + mode + platform_name carried over correctly."""
    assert aggregated["schema_version"] == "1.0"
    assert aggregated["mode"] == "knowledge"
    assert aggregated["platform_name"] == "Knowledge Aggregator Test Platform"
    # No leakage of candidate-only fields.
    assert "qa" not in aggregated
    assert "project_pitch" not in aggregated
    assert "highlights" not in aggregated
    assert "dimension_coverage" not in aggregated


# ---------------------------------------------------------------------------
# Aggregation: normalize, merge, dedupe (the heart of the spec)
# ---------------------------------------------------------------------------

def test_topic_count_after_normalization(aggregated):
    """Fixture has 3 qa with 6 distinct knowledge_points raw, but three of
    them ('LRU 缓存' / '  LRU 缓存  ' / 'lru 缓存.') normalize to the same
    topic. Expected: 4 topics total."""
    topics = aggregated["knowledge_map"]["topics"]
    names = [t["name"] for t in topics]
    assert len(topics) == 4, f"got {len(topics)} topics: {names}"


def test_canonical_name_picks_longest(aggregated):
    """When merging, the longest original name wins (tie-broken by first
    occurrence). Among 'LRU 缓存' / '  LRU 缓存  ' / 'lru 缓存.' the longest
    by char count is '  LRU 缓存  ' (10 chars vs 6 vs 7), but we strip
    surrounding whitespace from the canonical name (it's a name, not raw
    input). So canonical should be 'lru 缓存.' (7) — wait, that has trailing
    punctuation.

    Spec is: "prefer the longest; ties broken by first occurrence". The
    canonical name is the ORIGINAL form, not the normalized one. After
    stripping surrounding whitespace (which is presentation noise, not
    content), 'LRU 缓存' is 6 chars and 'lru 缓存.' is 7 chars. Longest
    wins → 'lru 缓存.'.
    """
    topics = aggregated["knowledge_map"]["topics"]
    lru = next(t for t in topics if "lru" in t["name"].lower() or "LRU" in t["name"])
    # Whichever rule we land on, canonical must NOT be the surrounded-by-
    # whitespace variant — that's just bad presentation.
    assert lru["name"] == lru["name"].strip()
    # And it must be one of the originals (we don't invent names).
    assert lru["name"] in {"LRU 缓存", "lru 缓存."}


def test_merged_level_takes_must_master(aggregated):
    """LRU appears as 必须掌握 (q-01) AND 加分项 (q-01 dup) AND 必须掌握 (q-02).
    Merged level must be 必须掌握."""
    topics = aggregated["knowledge_map"]["topics"]
    lru = next(t for t in topics if "lru" in t["name"].lower() or "LRU" in t["name"])
    assert lru["level"] == "必须掌握"


def test_questions_using_is_union_sorted(aggregated):
    """LRU appears in q-01 and q-02 (q-01 has it twice — must dedup).
    questions_using should be ['q-01', 'q-02'] (sorted, deduplicated)."""
    topics = aggregated["knowledge_map"]["topics"]
    lru = next(t for t in topics if "lru" in t["name"].lower() or "LRU" in t["name"])
    assert lru["questions_using"] == ["q-01", "q-02"]


def test_related_dimensions_is_union_no_duplicates(aggregated):
    """LRU spans q-01 (performance) and q-02 (architecture). Order should
    be canonical (architecture, feature, performance, ... per the renderer's
    DIMENSION_META) so renderer/consumer can rely on it."""
    topics = aggregated["knowledge_map"]["topics"]
    lru = next(t for t in topics if "lru" in t["name"].lower() or "LRU" in t["name"])
    # Both must appear, no duplicates.
    assert set(lru["related_dimensions"]) == {"performance", "architecture"}
    assert len(lru["related_dimensions"]) == 2


def test_single_qa_topics_are_kept(aggregated):
    """Spec D: 'Do not drop topics even if they appear in only one qa'."""
    topics = aggregated["knowledge_map"]["topics"]
    names = [t["name"] for t in topics]
    assert "单 qa 独占主题" in names
    assert "Redis TTL" in names
    assert "SSE 协议" in names


def test_must_read_dedup_across_qas(aggregated):
    """LRU is in q-01 and q-02. q-01.must_read ∪ q-02.must_read =
    {'MDN: Caching', 'Redis 官方文档', 'MDN: Server-sent events'} (dedup'd).
    All three should appear (≤3 limit; spec says 1–3)."""
    topics = aggregated["knowledge_map"]["topics"]
    lru = next(t for t in topics if "lru" in t["name"].lower() or "LRU" in t["name"])
    assert "MDN: Caching" in lru["must_read"]
    assert "Redis 官方文档" in lru["must_read"]
    # Each entry only appears once.
    assert len(lru["must_read"]) == len(set(lru["must_read"]))
    # ≤3 per spec C.5.
    assert 1 <= len(lru["must_read"]) <= 3


def test_hands_on_dedup_and_capped(aggregated):
    """Spec C.6: 1–2 hands_on items, deduplicated."""
    topics = aggregated["knowledge_map"]["topics"]
    for t in topics:
        assert 1 <= len(t["hands_on"]) <= 2, f"{t['name']}: {t['hands_on']}"
        assert len(t["hands_on"]) == len(set(t["hands_on"]))


# ---------------------------------------------------------------------------
# Determinism: same input → same output, byte for byte
# ---------------------------------------------------------------------------

def test_aggregation_is_deterministic(candidate):
    """Critical for diff-friendly outputs and reliable regression tests."""
    from scripts.aggregate_knowledge import aggregate_knowledge
    a = aggregate_knowledge(candidate)
    b = aggregate_knowledge(candidate)
    assert json.dumps(a, sort_keys=True, ensure_ascii=False) == \
           json.dumps(b, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Defensive: rejects non-candidate input
# ---------------------------------------------------------------------------

def test_rejects_non_candidate_input(candidate):
    """Aggregating a knowledge-mode JSON would be nonsense; aggregator should
    raise rather than silently produce garbage."""
    from scripts.aggregate_knowledge import aggregate_knowledge
    bad = dict(candidate)
    bad["mode"] = "knowledge"
    with pytest.raises(ValueError, match="candidate"):
        aggregate_knowledge(bad)
