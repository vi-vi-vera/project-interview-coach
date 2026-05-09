"""Unified CLI entry for project-interview-coach.

Subcommands (intentionally minimal):
- ``scan``   : run :mod:`scripts.collect_project_meta` and emit a JSON bundle
- ``render`` : run :mod:`scripts.render_markdown` and write bilingual markdown

LLM-driven stages (1→2→3) live outside Python and are orchestrated by the
calling agent. We do not provide a ``run`` subcommand for that reason.

Why a thin dispatcher? Each existing module already has its own ``main`` and
its own well-shaped argparse. The CLI's job is *only* to give them one
consistent entry point so users (and downstream tooling) don't need to
remember two module paths. Heavy logic stays in the modules.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.aggregate_knowledge import aggregate_knowledge
from scripts.collect_project_meta import DEPTH_LEVELS, collect
from scripts.render_markdown import render


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="coach",
        description="project-interview-coach unified CLI.",
    )
    sub = p.add_subparsers(dest="cmd", metavar="<command>", required=True)

    # ----- scan ---------------------------------------------------------
    s = sub.add_parser(
        "scan",
        help="Scan workspace, emit a redacted JSON bundle for stage 1.",
    )
    s.add_argument("--workspace", default=".", type=Path)
    s.add_argument(
        "--depth", default="medium", choices=list(DEPTH_LEVELS.keys()),
    )
    s.add_argument(
        "--projects", default="auto",
        help="comma-separated paths or 'auto'",
    )
    s.add_argument(
        "--out", default=None, type=Path,
        help="output file path; default stdout",
    )

    # ----- render -------------------------------------------------------
    r = sub.add_parser(
        "render",
        help="Render interview-data.json to bilingual markdown.",
    )
    r.add_argument("--data", required=True, type=Path,
                   help="path to interview-data.json")
    r.add_argument("--templates", required=True, type=Path,
                   help="directory containing Jinja2 templates")
    r.add_argument("--out", required=True, type=Path,
                   help="output directory for the rendered markdown")

    # ----- aggregate (Python replacement for stage3-knowledge LLM call) --
    a = sub.add_parser(
        "aggregate",
        help="Aggregate a candidate-mode JSON into a knowledge-mode JSON "
             "(pure Python, no LLM).",
    )
    a.add_argument("--data", required=True, type=Path,
                   help="path to candidate-mode interview-data.json")
    a.add_argument("--out", required=True, type=Path,
                   help="output path for the knowledge-mode JSON")

    # ----- run (one-shot aggregate + render for knowledge mode) ---------
    run_p = sub.add_parser(
        "run",
        help="End-to-end pipeline. Currently only --mode knowledge is "
             "supported (candidate/interviewer need LLM stages outside "
             "Python).",
    )
    run_p.add_argument("--mode", required=True, choices=["knowledge"],
                       help="pipeline mode; knowledge is the only fully "
                            "Python-implementable mode today")
    run_p.add_argument("--data", required=True, type=Path,
                       help="path to candidate-mode interview-data.json")
    run_p.add_argument("--templates", required=True, type=Path,
                       help="directory containing Jinja2 templates")
    run_p.add_argument("--out", required=True, type=Path,
                       help="output directory (will receive both the "
                            "intermediate JSON and the rendered markdown)")

    return p


def _cmd_scan(args: argparse.Namespace) -> int:
    explicit: list[str] | None
    if args.projects == "auto":
        explicit = None
    else:
        explicit = [s.strip() for s in args.projects.split(",") if s.strip()]

    bundle = collect(args.workspace, args.depth, explicit)

    if bundle["high_risk_hits"]:
        print(
            "HIGH_RISK_HIT: " + ", ".join(bundle["high_risk_hits"])
            + "\nAborting; please whitelist or remove these files.",
            file=sys.stderr,
        )
        return 2

    text = json.dumps(bundle, ensure_ascii=False, indent=2)
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote: {args.out}", file=sys.stderr)
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    zh, en = render(
        interview_data_path=args.data,
        template_dir=args.templates,
        output_dir=args.out,
    )
    print(f"Wrote: {zh}")
    print(f"Wrote: {en}")
    return 0


def _cmd_aggregate(args: argparse.Namespace) -> int:
    candidate = json.loads(args.data.read_text(encoding="utf-8"))
    try:
        kb = aggregate_knowledge(candidate)
    except ValueError as e:
        print(f"aggregate failed: {e}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(kb, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote: {args.out}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    # argparse restricts --mode to {"knowledge"} today; leaving this explicit
    # so the error message is readable if we ever loosen the choice list.
    if args.mode != "knowledge":
        print(
            f"run --mode={args.mode!r} not supported: only 'knowledge' "
            "can run without an LLM.",
            file=sys.stderr,
        )
        return 2

    candidate = json.loads(args.data.read_text(encoding="utf-8"))
    try:
        kb = aggregate_knowledge(candidate)
    except ValueError as e:
        print(f"aggregate failed: {e}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    kb_path = args.out / "knowledge-data.json"
    kb_path.write_text(
        json.dumps(kb, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    zh, en = render(
        interview_data_path=kb_path,
        template_dir=args.templates,
        output_dir=args.out,
    )
    print(f"Wrote: {kb_path}")
    print(f"Wrote: {zh}")
    print(f"Wrote: {en}")
    return 0


_DISPATCH = {
    "scan": _cmd_scan,
    "render": _cmd_render,
    "aggregate": _cmd_aggregate,
    "run": _cmd_run,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _DISPATCH[args.cmd]  # KeyError impossible: subparsers require=True
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
