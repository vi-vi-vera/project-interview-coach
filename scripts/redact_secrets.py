"""Redact common secrets from text.

Used before any project content is sent to an LLM. Detection is
intentionally pattern-based and conservative: false positives are
preferred over leaking real secrets.

Public API:
    redact_text(text: str) -> str
    scan_for_high_risk(text: str) -> list[str]
"""
from __future__ import annotations

import re
from typing import List

REDACTED = "<REDACTED>"

# Order matters: more specific patterns first.
_PATTERNS = [
    # AWS access key id
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), REDACTED),
    # URL-embedded credentials: scheme://user:password@host
    (
        re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*://)(?P<user>[^:\s/]+):(?P<pwd>[^@\s]+)@"),
        lambda m: f"{m.group('scheme')}{m.group('user')}:{REDACTED}@",
    ),
    # KEY=VALUE in .env style. Only redact the value when the key name
    # smells secret-ish.
    (
        re.compile(
            r"(?P<key>[A-Z][A-Z0-9_]*"
            r"(?:PASSWORD|PASSWD|SECRET|TOKEN|KEY|APIKEY|API_KEY|PRIVATE)"
            r"[A-Z0-9_]*)"
            r"\s*=\s*(?P<val>\S+)"
        ),
        lambda m: f"{m.group('key')}={REDACTED}",
    ),
]

_HIGH_RISK_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----"),
    re.compile(r"-----BEGIN CERTIFICATE-----"),
]


def redact_text(text: str) -> str:
    """Return ``text`` with known secret patterns replaced."""
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def scan_for_high_risk(text: str) -> List[str]:
    """Return a list of high-risk markers found in ``text``.

    The caller is expected to halt and ask the user to confirm before
    proceeding when this list is non-empty.
    """
    hits: List[str] = []
    for pattern in _HIGH_RISK_PATTERNS:
        for match in pattern.findall(text):
            hits.append(match)
    return hits
