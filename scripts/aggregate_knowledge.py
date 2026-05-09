"""Aggregate a candidate-mode interview-data.json into a knowledge-mode one.

This is a pure-Python replacement for prompts/stage3-knowledge.md. The
prompt is explicitly "aggregate, do not generate", which maps cleanly onto
deterministic set operations over the candidate output.

Spec: prompts/stage3-knowledge.md §§A–D (source of truth).

Key design decisions (see also tests/test_aggregate_knowledge.py):

- **Normalization is conservative.** lowercase + collapse whitespace + strip
  trailing ASCII/CJK punctuation. We do NOT do "smart" merges such as
  ignoring parenthetical extensions. Predictability > cleverness. If a user
  wants smarter merging, they extend the prompt spec and we match it here.
- **Canonical name = longest original (with surrounding whitespace stripped),
  ties broken by first occurrence.** Surrounding whitespace is presentation
  noise, not content — stripping it does not violate "do not invent names".
- **must_read / hands_on inherit the WHOLE learning_plan of every qa the
  topic appears in**, then dedupe. This matches LLM behavior under the same
  prompt (the prompt's "source qa's learning_plan" is qa-level, not
  knowledge_point-level). Capped to spec limits (must_read ≤3, hands_on ≤2)
  by preferred-order selection.
- **Topic ordering.** The renderer groups by level + sorts by name itself,
  so the aggregator emits topics in deterministic insertion order (first
  occurrence of canonical name across qa walk).
- **related_dimensions ordering.** Canonical dimension order from the
  renderer (architecture, feature, performance, reliability, observability,
  security, trade-off) — so diffs stay stable even if the qa order changes.
"""
from __future__ import annotations

import re
from typing import Any

# Canonical dimension order (must stay in sync with render_markdown.DIMENSION_META).
_DIMENSION_ORDER = [
    "architecture", "feature", "performance",
    "reliability", "observability", "security", "trade-off",
]

# Trailing punctuation to strip during normalization. Covers ASCII + common
# CJK full-width variants. Intentionally narrow: NOT a general sanitizer.
_TRAILING_PUNCT_RE = re.compile(r"[.。,，!！?？:：;；\s]+$")

# Spec limits from prompts/stage3-knowledge.md §C.
_MUST_READ_MAX = 3
_HANDS_ON_MAX = 2


def _normalize(name: str) -> str:
    """Normalize a knowledge_point name for matching only.

    Per spec: lowercase + collapse internal whitespace + strip trailing
    punctuation. Returns the match key; the original string is retained
    elsewhere for canonical display.
    """
    s = name.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = _TRAILING_PUNCT_RE.sub("", s)
    return s


def _pick_canonical(names: list[str]) -> str:
    """Pick the canonical display name from a list of original variants.

    Rule: longest (by char count, after stripping surrounding whitespace),
    ties broken by first occurrence. Surrounding whitespace is stripped
    because it's never meaningful in a topic name.
    """
    stripped = [n.strip() for n in names]
    # Stable sort by (-length, original index) → first-occurrence tie-break.
    best_idx = max(
        range(len(stripped)),
        key=lambda i: (len(stripped[i]), -i),
    )
    return stripped[best_idx]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _sort_dimensions(dims: set[str]) -> list[str]:
    """Sort dimensions by canonical order; unknown ones appended alphabetically."""
    known = [d for d in _DIMENSION_ORDER if d in dims]
    unknown = sorted(d for d in dims if d not in _DIMENSION_ORDER)
    return known + unknown


def aggregate_knowledge(candidate: dict[str, Any]) -> dict[str, Any]:
    """Build a knowledge-mode interview-data dict from a candidate-mode one.

    Raises:
        ValueError: if ``candidate["mode"]`` is not ``"candidate"``.
    """
    mode = candidate.get("mode")
    if mode != "candidate":
        raise ValueError(
            f"aggregate_knowledge requires a candidate-mode input, got mode={mode!r}"
        )

    # ---- Walk qa and collect per-topic bundles --------------------------
    # Keyed by normalized name. Value: accumulator dict.
    buckets: dict[str, dict[str, Any]] = {}
    # Preserve first-occurrence order for deterministic output.
    order: list[str] = []

    for qa in candidate.get("qa", []):
        qa_id = qa["id"]
        qa_dim = qa["primary_dimension"]
        plan = qa.get("learning_plan", {})
        qa_must_read: list[str] = list(plan.get("must_read", []))
        qa_hands_on: list[str] = list(plan.get("hands_on", []))

        for kp in qa.get("knowledge_points", []):
            name = kp["name"]
            level = kp["level"]
            key = _normalize(name)
            if not key:
                # Defensive: a name that normalizes to empty is malformed;
                # skip rather than crash. (Schema should prevent this.)
                continue

            b = buckets.get(key)
            if b is None:
                b = {
                    "original_names": [],
                    "any_must_master": False,
                    "questions_using": [],
                    "related_dimensions": set(),
                    "must_read_pool": [],
                    "hands_on_pool": [],
                }
                buckets[key] = b
                order.append(key)

            b["original_names"].append(name)
            if level == "必须掌握":
                b["any_must_master"] = True
            if qa_id not in b["questions_using"]:
                b["questions_using"].append(qa_id)
            b["related_dimensions"].add(qa_dim)
            b["must_read_pool"].extend(qa_must_read)
            b["hands_on_pool"].extend(qa_hands_on)

    # ---- Materialize topics ---------------------------------------------
    topics: list[dict[str, Any]] = []
    for key in order:
        b = buckets[key]
        must_read = _dedupe_preserve_order(b["must_read_pool"])[:_MUST_READ_MAX]
        hands_on = _dedupe_preserve_order(b["hands_on_pool"])[:_HANDS_ON_MAX]
        # Schema demands ≥1 entry for each; if the source qa had none, we
        # cannot synthesize — surface as an error rather than produce
        # invalid output.
        if not must_read or not hands_on:
            raise ValueError(
                f"topic {_pick_canonical(b['original_names'])!r} ended up with "
                f"empty must_read or hands_on; source qa's learning_plan is "
                f"incomplete."
            )

        topics.append({
            "name": _pick_canonical(b["original_names"]),
            "level": "必须掌握" if b["any_must_master"] else "加分项",
            "related_dimensions": _sort_dimensions(b["related_dimensions"]),
            "questions_using": sorted(b["questions_using"]),
            "must_read": must_read,
            "hands_on": hands_on,
        })

    # ---- Top-level envelope ---------------------------------------------
    out: dict[str, Any] = {
        "schema_version": candidate.get("schema_version", "1.0"),
        "mode": "knowledge",
        "platform_name": candidate["platform_name"],
        "knowledge_map": {"topics": topics},
    }
    # Optional passthrough fields permitted by schema.
    for opt in ("role", "level"):
        if opt in candidate:
            out[opt] = candidate[opt]
    return out
