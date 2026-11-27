"""Unit tests for the Study v3 candidate selector (Phase B1)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def selector() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts/select_v3_candidates.py"
    spec = importlib.util.spec_from_file_location("v3_selection", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_code_paths_count_py_but_skip_docs_artifacts_and_workflows() -> None:
    sel = selector()
    assert sel.is_code_path("scripts/fetch_supabase_snapshot.py") is True
    assert sel.is_code_path("scripts/report_state.js") is True
    assert sel.is_code_path("README.md") is False
    assert sel.is_code_path("reports/2026-10-09/index.html") is False
    assert sel.is_code_path("artifacts/inbox-e2e-evidence.json") is False
    assert sel.is_code_path(".github/workflows/render-daily-report.yml") is False
    assert sel.is_code_path(".gitignore") is False
    assert sel.is_code_path("infographic/x/infographic.png") is False


def test_compute_stats_splits_python_web_and_excluded_lines() -> None:
    sel = selector()
    stats = sel.compute_stats(
        [
            {"filename": "scripts/a.py", "additions": 100, "deletions": 10},
            {"filename": "scripts/b.js", "additions": 20, "deletions": 0},
            {"filename": "docs/notes.md", "additions": 50, "deletions": 50},
            {"filename": ".github/workflows/ci.yml", "additions": 30, "deletions": 0},
        ]
    )
    assert stats["code_lines"] == 130
    assert stats["python_lines"] == 110
    assert stats["web_lines"] == 20
    assert stats["code_files"] == 2
    assert stats["total_lines"] == 260


def test_python_majority_needs_strict_half_and_beats_web() -> None:
    sel = selector()
    assert sel.is_python_majority({"code_lines": 200, "python_lines": 150, "web_lines": 0}) is True
    assert sel.is_python_majority({"code_lines": 132, "python_lines": 66, "web_lines": 0}) is False
    assert (
        sel.is_python_majority({"code_lines": 300, "python_lines": 160, "web_lines": 140}) is True
    )
    assert (
        sel.is_python_majority({"code_lines": 300, "python_lines": 140, "web_lines": 140}) is False
    )
    assert sel.is_python_majority({"code_lines": 0, "python_lines": 0, "web_lines": 0}) is False


def test_parse_lens_head_pins_only_sticky_state_bodies() -> None:
    sel = selector()
    head = "d" * 40
    body = (
        "<!-- pr-lens:sticky -->\nreviewed \n"
        '<!-- pr-lens:state {"v":1,"headSha":"' + head + '","outdated":false} -->'
    )
    assert sel.parse_lens_head(body) == head
    assert sel.parse_lens_head("no markers here") is None
    assert sel.parse_lens_head("<!-- pr-lens:sticky --> without state") is None
    other = "0" * 40
    assert sel.lens_matches_head([body], head) is True
    assert sel.lens_matches_head([body], other) is False
    assert sel.lens_matches_head([], head) is False


def test_can_pair_enforces_ratio_and_file_counts() -> None:
    sel = selector()
    assert sel.can_pair(61, 66, 2, 2) is True
    assert sel.can_pair(211, 218, 2, 2) is True
    assert sel.can_pair(40, 60, 2, 2) is True
    assert sel.can_pair(40, 61, 2, 2) is False
    assert sel.can_pair(100, 120, 2, 4) is False
    assert sel.can_pair(0, 50, 1, 1) is False


def test_collect_excluded_ignores_current_study_outputs(tmp_path: Path) -> None:
    sel = selector()
    current = tmp_path / "artifacts" / "paired-study" / "private" / "v3-candidates"
    current.mkdir(parents=True)
    (current / "pool.json").write_text('{"rows": [{"pr_identity": "owner/repo#1"}]}')
    prior = tmp_path / "artifacts" / "paired-study"
    (prior / "old-packet.json").write_text('{"rows": [{"pr_identity": "owner/repo#2"}]}')
    excluded = sel.collect_excluded([tmp_path])
    assert "owner/repo#2" in excluded
    assert "owner/repo#1" not in excluded


def test_extract_lens_bodies_keeps_one_entry_per_lens_comment() -> None:
    sel = selector()
    stale = "e" * 40
    current = "f" * 40
    payload = [
        {
            "user": {"login": "coldtea-pr-lens[bot]"},
            "body": (
                "<!-- pr-lens:sticky -->\nstale \n"
                '<!-- pr-lens:state {"v":1,"headSha":"' + stale + '"} -->'
            ),
        },
        {
            "user": {"login": "someone-else"},
            "body": "not a lens review",
        },
        {
            "user": {"login": "github-actions[bot]"},
            "body": (
                "<!-- pr-lens:sticky -->\ncurrent \n"
                '<!-- pr-lens:state {"v":1,"headSha":"' + current + '"} -->'
            ),
        },
    ]
    bodies = sel.extract_lens_bodies(payload)
    assert len(bodies) == 2
    assert sel.lens_matches_head(bodies, current) is True
    assert sel.lens_matches_head(bodies, "0" * 40) is False
