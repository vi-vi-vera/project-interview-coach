"""Tests for the secrets redactor.

Only deterministic logic is tested — LLM outputs are not.
"""
from pathlib import Path

from scripts.redact_secrets import redact_text, scan_for_high_risk

FIXTURES = Path(__file__).parent / "fixtures"


def test_env_password_value_is_redacted():
    raw = (FIXTURES / "sample.env").read_text()
    out = redact_text(raw)
    assert "supersecret123" not in out
    assert "abcd1234efgh5678" not in out
    # Key names should remain so the structure is still readable.
    assert "DB_PASSWORD" in out
    assert "API_TOKEN" in out
    # Non-secret value should remain.
    assert "example.com" in out


def test_connection_string_password_is_redacted():
    raw = (FIXTURES / "sample.txt").read_text()
    out = redact_text(raw)
    assert "p@ssw0rd" not in out
    assert "postgres://" in out  # scheme preserved


def test_aws_access_key_is_redacted():
    raw = (FIXTURES / "sample.txt").read_text()
    out = redact_text(raw)
    assert "AKIAIOSFODNN7EXAMPLE" not in out


def test_private_key_block_triggers_high_risk():
    raw = (FIXTURES / "sample.txt").read_text()
    hits = scan_for_high_risk(raw)
    assert any("PRIVATE KEY" in h for h in hits)


def test_clean_text_passes_through():
    raw = "Just a normal sentence with no secrets."
    assert redact_text(raw) == raw
    assert scan_for_high_risk(raw) == []
