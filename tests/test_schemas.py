import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"


def _validate(schema_name: str, sample_name: str) -> None:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text())
    sample = json.loads((FIX / sample_name).read_text())
    jsonschema.validate(sample, schema)


def test_project_context_sample_valid():
    _validate("project-context.schema.json", "sample_project_context.json")


def test_tech_points_sample_valid():
    _validate("tech-points.schema.json", "sample_tech_points.json")


def test_project_context_missing_required_fails():
    schema = json.loads(
        (ROOT / "schemas" / "project-context.schema.json").read_text()
    )
    bad = {"schema_version": "1.0", "sub_projects": []}  # missing platform_name; empty list
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_tech_points_evidence_required():
    schema = json.loads(
        (ROOT / "schemas" / "tech-points.schema.json").read_text()
    )
    bad = {
        "schema_version": "1.0",
        "role": "后端",
        "level": "中级",
        "points": [
            {
                "id": "x", "topic": "t", "scope": "backend",
                "evidence": [], "interview_value": "高",
            }
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
