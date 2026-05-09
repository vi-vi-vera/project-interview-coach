"""Schema tests for interview-data.schema.json (Stage 3 candidate output contract)."""
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"
SCHEMA_PATH = ROOT / "schemas" / "interview-data.schema.json"
SAMPLE_PATH = FIX / "sample_interview_data.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text())


def _sample():
    return json.loads(SAMPLE_PATH.read_text())


def test_sample_interview_data_valid():
    jsonschema.validate(_sample(), _schema())


def test_missing_answers_deep_dive_fails():
    bad = _sample()
    del bad["qa"][0]["answers"]["deep_dive"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())


def test_invalid_primary_dimension_fails():
    bad = _sample()
    bad["qa"][0]["primary_dimension"] = "made-up"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())


def test_missing_mock_questions_fails():
    bad = _sample()
    del bad["qa"][0]["learning_plan"]["mock_questions"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())


def test_invalid_knowledge_point_level_fails():
    bad = _sample()
    bad["qa"][0]["knowledge_points"][0]["level"] = "随便看看"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())


def test_answer_missing_bilingual_pair_fails():
    bad = _sample()
    # Drop English translation of the standard answer.
    del bad["qa"][0]["answers"]["standard"]["en"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())


def test_empty_highlights_fails():
    bad = _sample()
    bad["highlights"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, _schema())
