"""Tests for word-budget lint in candidate-mode render pipeline.

Budget rules come from prompts/stage3-candidate.md §C:
| Tier      | zh (CJK chars) | en (words) |
|-----------|----------------|------------|
| elevator  | ≤ 50           | ≤ 35       |
| standard  | 110–300        | 80–180     |
| deep_dive | 350–800        | 220–450    |

Applies to `project_pitch.*` AND every `qa[].answers.*`.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_interview_data.json"


def test_lint_word_budget_reports_fixture_underruns():
    """The canonical sample_interview_data.json is an intentionally thin fixture;
    its project_pitch.standard.zh / deep_dive.zh sit well below the budget floor.

    This test locks in that behavior: lint MUST emit warnings on it, and the
    warnings MUST include the path identifying the out-of-budget field. This
    serves two purposes:
      1. Fails if the lint silently drops underruns.
      2. Documents that tests deliberately use a thin fixture — don't "fix" the
         fixture to make this pass; fix the test if the fixture ever grows real.
    """
    from scripts.render_markdown import lint_word_budget

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    warnings = lint_word_budget(data)
    assert len(warnings) > 0, "sample fixture should trip lint (thin content)"
    # at least one warning must name project_pitch.standard (zh ~53 chars, floor 150)
    assert any("project_pitch.standard" in w for w in warnings), (
        f"expected project_pitch.standard to be flagged, got: {warnings}"
    )


def test_lint_detects_elevator_zh_overrun():
    """zh elevator > 50 CJK chars triggers a warning that names the path and the counts."""
    from scripts.render_markdown import lint_word_budget

    data = {
        "mode": "candidate",
        "project_pitch": {
            "elevator":  {"zh": "字" * 80,  "en": "word " * 20},  # zh over (80 > 50)
            "standard":  {"zh": "字" * 200, "en": "word " * 100},
            "deep_dive": {"zh": "字" * 600, "en": "word " * 300},
        },
        "qa": [],
    }
    warnings = lint_word_budget(data)
    assert len(warnings) == 1
    w = warnings[0]
    assert "project_pitch.elevator.zh" in w
    assert "80" in w  # actual count
    assert "50" in w  # limit


def test_lint_detects_qa_standard_en_underrun():
    """en standard < 80 words triggers a warning; underruns are reported just like overruns."""
    from scripts.render_markdown import lint_word_budget

    data = {
        "mode": "candidate",
        "project_pitch": {
            "elevator":  {"zh": "字" * 30,  "en": "word " * 20},
            "standard":  {"zh": "字" * 200, "en": "word " * 100},
            "deep_dive": {"zh": "字" * 600, "en": "word " * 300},
        },
        "qa": [
            {
                "id": "q-01",
                "answers": {
                    "elevator":  {"zh": "字" * 30,  "en": "word " * 20},
                    "standard":  {"zh": "字" * 200, "en": "word " * 40},   # en under (40 < 80)
                    "deep_dive": {"zh": "字" * 600, "en": "word " * 300},
                },
            }
        ],
    }
    warnings = lint_word_budget(data)
    assert len(warnings) == 1
    w = warnings[0]
    assert "qa[0].answers.standard.en" in w
    assert "40" in w
    assert "80" in w  # lower bound mentioned


def test_lint_ignores_non_candidate_modes():
    """interviewer and knowledge modes have no word budget — lint returns []."""
    from scripts.render_markdown import lint_word_budget

    interviewer = {
        "mode": "interviewer",
        "question_bank": [],
        "rubrics": [],
    }
    knowledge = {
        "mode": "knowledge",
        "knowledge_map": {"topics": []},
    }
    assert lint_word_budget(interviewer) == []
    assert lint_word_budget(knowledge) == []


def test_lint_counts_cjk_chars_not_bytes_and_ignores_punctuation():
    """zh counting: CJK code points only; punctuation / ASCII / whitespace don't count.

    Rule from stage3-candidate.md §C: "For Chinese, 'chars' means Chinese characters
    (CJK code points), not bytes; punctuation does not count toward the limit."
    """
    from scripts.render_markdown import lint_word_budget

    # 51 CJK chars with tons of punctuation / whitespace mixed in — should still count as 51,
    # which is over the 50 elevator limit.
    zh_51 = "字" * 51 + "，。；：！？" + " " * 20 + "hello world"
    data = {
        "mode": "candidate",
        "project_pitch": {
            "elevator":  {"zh": zh_51,       "en": "word " * 20},
            "standard":  {"zh": "字" * 200,  "en": "word " * 100},
            "deep_dive": {"zh": "字" * 600,  "en": "word " * 300},
        },
        "qa": [],
    }
    warnings = lint_word_budget(data)
    assert len(warnings) == 1
    assert "project_pitch.elevator.zh" in warnings[0]
    assert "51" in warnings[0]
