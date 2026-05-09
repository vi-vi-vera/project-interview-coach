from pathlib import Path

from scripts.collect_project_meta import collect

FIX = Path(__file__).parent / "fixtures"


def test_collect_multi_project_smoke():
    bundle = collect(FIX / "multi_project", depth="light", explicit_projects=None)
    names = sorted(p["name"] for p in bundle["sub_projects"])
    assert names == ["backend", "web"]
    # tree should be a list of strings
    for sp in bundle["sub_projects"]:
        assert isinstance(sp["tree"], list)
        assert all(isinstance(x, str) for x in sp["tree"])
    # git_summary is present even if not a repo
    assert "is_git_repo" in bundle["git_summary"]


def test_collect_single_project_smoke():
    bundle = collect(FIX / "single_project", depth="light", explicit_projects=None)
    assert len(bundle["sub_projects"]) == 1
    assert bundle["sub_projects"][0]["path"] == ""
