"""Collect raw project metadata for the LLM to summarise.

Output is a single dict (JSON-serialisable) shaped like::

    {
      "workspace_name": "...",
      "depth": "medium",
      "high_risk_hits": [...],
      "git_summary": { "is_git_repo": bool, "recent_commits": [...] },
      "sub_projects": [
        {
          "name": "...", "path": "...",
          "manifests": {"package.json": "<redacted text>", ...},
          "readme": "<redacted text or null>",
          "tree": ["relative/path", ...],
          "git_active_files": ["relative/path", ...]
        }
      ]
    }

All file contents pass through :func:`scripts.redact_secrets.redact_text`
first.  Nothing is sent to an LLM from this module.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.detect_subprojects import detect_subprojects
from scripts.redact_secrets import redact_text, scan_for_high_risk

DEPTH_LEVELS = {"light": 2, "medium": 4, "deep": 99}
TREE_FILE_LIMIT = {"light": 200, "medium": 800, "deep": 5000}
MANIFEST_FILES = (
    "package.json", "pyproject.toml", "pom.xml",
    "go.mod", "Cargo.toml", "build.gradle", "requirements.txt",
)
README_CANDIDATES = (
    "README.md", "README.MD", "Readme.md", "README", "readme.md",
)
SKIP_DIRS = {
    "node_modules", "dist", "build", ".git", ".cache",
    ".venv", "venv", "__pycache__", ".next", ".nuxt",
    "target", "out", ".pytest_cache",
}


def _read_text_redacted(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return redact_text(text)


def _collect_tree(root: Path, depth: int, file_limit: int) -> List[str]:
    out: List[str] = []

    def walk(d: Path, current_depth: int) -> None:
        if current_depth > depth or len(out) >= file_limit:
            return
        try:
            entries = sorted(d.iterdir())
        except OSError:
            return
        for e in entries:
            if e.name in SKIP_DIRS or e.name.startswith("."):
                continue
            rel = e.relative_to(root).as_posix()
            out.append(rel + ("/" if e.is_dir() else ""))
            if len(out) >= file_limit:
                return
            if e.is_dir():
                walk(e, current_depth + 1)

    walk(root, 1)
    return out


def _git_recent(workspace: Path, n: int = 50) -> Dict[str, Any]:
    try:
        subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "--git-dir"],
            check=True, capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"is_git_repo": False, "recent_commits": [], "active_files": []}

    log = subprocess.run(
        ["git", "-C", str(workspace), "log", f"-n{n}",
         "--pretty=format:%h|%s", "--name-only"],
        capture_output=True, text=True,
    ).stdout

    commits: List[Dict[str, Any]] = []
    active_files: List[str] = []
    current: Optional[Dict[str, Any]] = None
    for line in log.splitlines():
        if not line.strip():
            if current:
                commits.append(current)
                current = None
            continue
        if "|" in line and current is None:
            sha, _, subject = line.partition("|")
            current = {"sha": sha, "subject": subject, "files": []}
        else:
            if current:
                current["files"].append(line)
            active_files.append(line)
    if current:
        commits.append(current)

    # De-dup preserving order.
    seen: set = set()
    uniq_active: List[str] = []
    for f in active_files:
        if f not in seen:
            seen.add(f)
            uniq_active.append(f)

    return {
        "is_git_repo": True,
        "recent_commits": commits,
        "active_files": uniq_active,
    }


def _filter_active_for_subproject(active: List[str], sub_path: Path) -> List[str]:
    if sub_path.parts == ():
        return active[:50]
    prefix = sub_path.as_posix() + "/"
    return [f for f in active if f.startswith(prefix)][:50]


def collect(
    workspace: Path,
    depth: str = "medium",
    explicit_projects: Optional[List[str]] = None,
) -> Dict[str, Any]:
    workspace = Path(workspace).resolve()
    if depth not in DEPTH_LEVELS:
        raise ValueError(f"unknown depth: {depth}")

    sub_projects = detect_subprojects(workspace, explicit_projects)
    git = _git_recent(workspace)

    sp_out: List[Dict[str, Any]] = []
    high_risk_hits: List[str] = []

    for sp in sub_projects:
        sp_root = workspace / sp.path
        manifests: Dict[str, str] = {}
        for m in MANIFEST_FILES:
            text = _read_text_redacted(sp_root / m)
            if text is not None:
                manifests[m] = text
                high_risk_hits.extend(scan_for_high_risk(text))

        readme: Optional[str] = None
        for cand in README_CANDIDATES:
            readme = _read_text_redacted(sp_root / cand)
            if readme is not None:
                high_risk_hits.extend(scan_for_high_risk(readme))
                break

        tree = _collect_tree(
            sp_root, DEPTH_LEVELS[depth], TREE_FILE_LIMIT[depth],
        )

        # ``Path("").as_posix()`` returns ``"."``; we want an empty string
        # to distinguish "workspace root itself" from a real sub-path.
        path_str = "" if sp.path.parts == () else sp.path.as_posix()

        sp_out.append({
            "name": sp.name,
            "path": path_str,
            "manifests": manifests,
            "readme": readme,
            "tree": tree,
            "git_active_files": _filter_active_for_subproject(
                git["active_files"], sp.path,
            ),
        })

    return {
        "workspace_name": workspace.name,
        "depth": depth,
        "high_risk_hits": high_risk_hits,
        "git_summary": {
            "is_git_repo": git["is_git_repo"],
            "recent_commits": git["recent_commits"][:50],
        },
        "sub_projects": sp_out,
    }


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--workspace", default=".", type=Path)
    p.add_argument(
        "--depth", default="medium", choices=list(DEPTH_LEVELS.keys()),
    )
    p.add_argument("--projects", default="auto")
    args = p.parse_args()

    explicit: Optional[List[str]]
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
        sys.exit(2)

    json.dump(bundle, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
