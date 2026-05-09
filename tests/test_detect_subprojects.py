from pathlib import Path

import pytest

from scripts.detect_subprojects import detect_subprojects, SubProject

FIX = Path(__file__).parent / "fixtures"


def test_detect_two_subprojects():
    result = detect_subprojects(FIX / "multi_project", explicit=None)
    names = sorted(p.name for p in result)
    assert names == ["backend", "web"]
    assert all(isinstance(p, SubProject) for p in result)


def test_skip_dirs_without_manifests():
    result = detect_subprojects(FIX / "multi_project", explicit=None)
    assert "docs" not in [p.name for p in result]


def test_root_itself_is_a_project_when_no_subdirs():
    result = detect_subprojects(FIX / "single_project", explicit=None)
    assert len(result) == 1
    assert result[0].name == "single_project"
    assert result[0].path == Path("")  # relative to root, root itself


def test_explicit_overrides_autodetect():
    result = detect_subprojects(
        FIX / "multi_project", explicit=["backend"]
    )
    names = [p.name for p in result]
    assert names == ["backend"]


def test_explicit_unknown_path_raises():
    with pytest.raises(ValueError, match="not found"):
        detect_subprojects(FIX / "multi_project", explicit=["nonexistent"])
