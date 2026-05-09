"""Detect sub-projects inside a workspace.

A sub-project is any directory containing one of:
- package.json, pyproject.toml, pom.xml, go.mod, Cargo.toml, build.gradle

Detection rules:
1. If ``explicit`` is given (list of relative paths), use those exactly,
   raising ValueError when a path does not exist.
2. Otherwise, scan first-level subdirectories. Any whose root contains
   a manifest is a sub-project.
3. If no first-level matches, treat the workspace root itself as a
   single-project (path == Path(""), name == workspace dir name).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

MANIFESTS: Tuple[str, ...] = (
    "package.json", "pyproject.toml", "pom.xml",
    "go.mod", "Cargo.toml", "build.gradle",
)


@dataclass(frozen=True)
class SubProject:
    name: str
    path: Path  # relative to workspace root; Path("") when root itself
    manifests: Tuple[str, ...] = field(default_factory=tuple)


def _has_manifest(dir_: Path) -> Tuple[str, ...]:
    return tuple(m for m in MANIFESTS if (dir_ / m).is_file())


def detect_subprojects(
    workspace: Path,
    explicit: Optional[List[str]] = None,
) -> List[SubProject]:
    workspace = workspace.resolve()
    if explicit:
        out: List[SubProject] = []
        for rel in explicit:
            full = workspace / rel
            if not full.is_dir():
                raise ValueError(f"path not found: {rel}")
            out.append(SubProject(
                name=full.name,
                path=Path(rel),
                manifests=_has_manifest(full),
            ))
        return out

    matches: List[SubProject] = []
    for child in sorted(workspace.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        mans = _has_manifest(child)
        if mans:
            matches.append(SubProject(
                name=child.name,
                path=Path(child.name),
                manifests=mans,
            ))
    if matches:
        return matches

    # Fallback: workspace root itself as single project.
    return [SubProject(
        name=workspace.name,
        path=Path(""),
        manifests=_has_manifest(workspace),
    )]
