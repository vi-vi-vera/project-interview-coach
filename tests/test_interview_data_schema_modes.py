"""Mode-branching schema tests for interview-data.schema.json (M4 Task 1).

These verify that the single schema file enforces different `required` fields
based on the `mode` discriminator using JSON Schema draft-07's `if/then`.
"""

import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "interview-data.schema.json").read_text(encoding="utf-8"))
INTERVIEWER_FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "sample_interviewer_data.json").read_text(encoding="utf-8"))
KNOWLEDGE_FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "sample_knowledge_data.json").read_text(encoding="utf-8"))
CANDIDATE_FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "sample_interview_data.json").read_text(encoding="utf-8"))


# 1. interviewer fixture is valid
def test_interviewer_sample_valid():
    jsonschema.validate(INTERVIEWER_FIXTURE, SCHEMA)


# 2. interviewer mode missing rubrics fails
def test_interviewer_missing_rubrics_fails():
    bad = copy.deepcopy(INTERVIEWER_FIXTURE)
    bad.pop("rubrics")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


# 3. interviewer rubric weight out of [0,1] fails
def test_interviewer_rubric_weight_out_of_range_fails():
    bad = copy.deepcopy(INTERVIEWER_FIXTURE)
    bad["rubrics"][0]["criteria"][0]["weight"] = 1.5
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


# 4. knowledge fixture is valid
def test_knowledge_sample_valid():
    jsonschema.validate(KNOWLEDGE_FIXTURE, SCHEMA)


# 5. knowledge mode missing knowledge_map fails
def test_knowledge_missing_knowledge_map_fails():
    bad = copy.deepcopy(KNOWLEDGE_FIXTURE)
    bad.pop("knowledge_map")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


# 6. knowledge topic level out of enum fails
def test_knowledge_topic_invalid_level_fails():
    bad = copy.deepcopy(KNOWLEDGE_FIXTURE)
    bad["knowledge_map"]["topics"][0]["level"] = "可选"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


# 7. candidate fixture must STILL validate after schema changes (regression)
def test_candidate_fixture_still_valid_after_mode_branching():
    jsonschema.validate(CANDIDATE_FIXTURE, SCHEMA)
