"""Tests for scripts.cli — the unified `coach` entry point.

CLI scope (intentionally minimal):
- `coach scan`   : delegate to collect_project_meta (writes bundle to stdout or file)
- `coach render` : delegate to render_markdown (writes zh/en markdown to --out)

We do NOT cover `run` (full pipeline) here because stages 1–3 require LLM calls
that live outside this skill's Python boundary.

Tests use `subprocess.run([sys.executable, "-m", "scripts.cli", ...])` rather
than calling main() in-process. Rationale: the CLI is a user-facing surface,
testing it as a real subprocess catches stuff in-process testing misses
(import path, exit codes, stderr separation).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DATA = ROOT / "tests" / "fixtures" / "sample_interview_data.json"
FIXTURE_CANDIDATE_FOR_AGG = (
    ROOT / "tests" / "fixtures" / "sample_candidate_for_aggregation.json"
)
TEMPLATES = ROOT / "templates"


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "scripts.cli", *args],
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
    )


def test_cli_no_args_prints_help_and_exits_nonzero():
    """`coach` with no subcommand should show usage on stderr and exit non-zero.

    Rationale: argparse's default for missing required subparser. We just
    assert the contract holds — exit code != 0 and 'usage' appears.
    """
    r = _run([])
    assert r.returncode != 0
    assert "usage" in (r.stderr + r.stdout).lower()


def test_cli_help_lists_subcommands():
    """`coach --help` must mention all four subcommands."""
    r = _run(["--help"])
    assert r.returncode == 0
    out = r.stdout + r.stderr
    for sub in ("scan", "render", "aggregate", "run"):
        assert sub in out, f"missing subcommand {sub!r} in help output"


def test_cli_unknown_subcommand_exits_nonzero():
    """Unknown subcommand should exit non-zero with an error message on stderr."""
    r = _run(["lunatic"])
    assert r.returncode != 0
    assert "lunatic" in (r.stderr + r.stdout) or "invalid choice" in (r.stderr + r.stdout).lower()


def test_cli_render_missing_required_args_exits_nonzero():
    """`coach render` without --data must fail loudly, not silently."""
    r = _run(["render"])
    assert r.returncode != 0
    # argparse standard message
    assert "required" in (r.stderr + r.stdout).lower() or "data" in (r.stderr + r.stdout).lower()


def test_cli_render_writes_both_locales(tmp_path):
    """End-to-end: `coach render --data X --templates Y --out Z` produces zh/en md."""
    r = _run([
        "render",
        "--data", str(FIXTURE_DATA),
        "--templates", str(TEMPLATES),
        "--out", str(tmp_path),
    ])
    assert r.returncode == 0, f"stderr: {r.stderr}"
    zh = tmp_path / "interview-prep.zh.md"
    en = tmp_path / "interview-prep.en.md"
    assert zh.exists() and zh.stat().st_size > 0
    assert en.exists() and en.stat().st_size > 0


def test_cli_scan_outputs_valid_json(tmp_path):
    """`coach scan --workspace <tmp_path>` must emit valid JSON on stdout.

    We use a minimal tmp workspace (no git, no manifests) — collect_project_meta
    handles that gracefully and returns a bundle with empty sub_projects.
    """
    r = _run(["scan", "--workspace", str(tmp_path)])
    assert r.returncode == 0, f"stderr: {r.stderr}"
    bundle = json.loads(r.stdout)
    assert "workspace_name" in bundle
    assert "sub_projects" in bundle


def test_cli_scan_invalid_depth_exits_nonzero(tmp_path):
    """`--depth lunatic` should fail at argparse level, before any work runs."""
    r = _run(["scan", "--workspace", str(tmp_path), "--depth", "lunatic"])
    assert r.returncode != 0
    assert "lunatic" in (r.stderr + r.stdout) or "invalid choice" in (r.stderr + r.stdout).lower()


# ---------------------------------------------------------------------------
# aggregate + run (knowledge-mode pure-Python pipeline)
# ---------------------------------------------------------------------------

def test_cli_aggregate_writes_knowledge_json(tmp_path):
    """`coach aggregate --data <candidate> --out <kb.json>` emits valid JSON."""
    out_file = tmp_path / "kb.json"
    r = _run([
        "aggregate",
        "--data", str(FIXTURE_CANDIDATE_FOR_AGG),
        "--out", str(out_file),
    ])
    assert r.returncode == 0, f"stderr: {r.stderr}"
    assert out_file.exists()
    kb = json.loads(out_file.read_text(encoding="utf-8"))
    assert kb["mode"] == "knowledge"
    assert "knowledge_map" in kb
    assert len(kb["knowledge_map"]["topics"]) >= 1


def test_cli_aggregate_rejects_non_candidate_input(tmp_path):
    """Passing a knowledge-mode file to aggregate must fail (not silently succeed)."""
    # Quickly fabricate a knowledge-mode file by toggling mode on the fixture
    bad = json.loads(FIXTURE_CANDIDATE_FOR_AGG.read_text(encoding="utf-8"))
    bad["mode"] = "knowledge"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")

    r = _run([
        "aggregate",
        "--data", str(bad_path),
        "--out", str(tmp_path / "kb.json"),
    ])
    assert r.returncode != 0
    assert "candidate" in (r.stderr + r.stdout).lower()


def test_cli_run_knowledge_end_to_end(tmp_path):
    """`coach run --mode knowledge --data <cand> --templates <T> --out <D>`
    produces knowledge-map.{zh,en}.md in one step (aggregate + render)."""
    r = _run([
        "run",
        "--mode", "knowledge",
        "--data", str(FIXTURE_CANDIDATE_FOR_AGG),
        "--templates", str(TEMPLATES),
        "--out", str(tmp_path),
    ])
    assert r.returncode == 0, f"stderr: {r.stderr}"
    assert (tmp_path / "knowledge-map.zh.md").exists()
    assert (tmp_path / "knowledge-map.en.md").exists()
    # Side-effect: intermediate kb JSON also written (useful for inspection).
    assert (tmp_path / "knowledge-data.json").exists()


def test_cli_run_rejects_non_knowledge_mode(tmp_path):
    """run currently only supports --mode knowledge. Other modes require LLM
    and should fail fast with a clear message."""
    r = _run([
        "run",
        "--mode", "candidate",
        "--data", str(FIXTURE_CANDIDATE_FOR_AGG),
        "--templates", str(TEMPLATES),
        "--out", str(tmp_path),
    ])
    assert r.returncode != 0
    assert "knowledge" in (r.stderr + r.stdout).lower() or \
           "invalid choice" in (r.stderr + r.stdout).lower()

