"""End to end through the `prc` entry point. Leaves a repeatable artifact in artifacts/e2e/."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "e2e"


def prc(*args: str, expect: int = 0) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )

    assert completed.returncode == expect, completed.stderr

    return json.loads(completed.stdout) if expect == 0 and completed.stdout.strip() else {}


def test_full_review_lifecycle_and_reproducible_artifact(tmp_path: Path) -> None:
    shutil.rmtree(ARTIFACT, ignore_errors=True)
    store, out = str(ARTIFACT / "store"), str(ARTIFACT / "reviews")
    source = "fixture:basic"

    first = prc("review", "--source", source, "--store", store, "--out", out)

    assert first["source"] == "fixture" and first["live_verified"] is False
    assert first["capture_consistency"] == "stable" and first["canonical_publication_won"] is True

    review_dir = Path(str(first["out_dir"]))

    for name in (
        "index.html",
        "infographic.svg",
        "flow.svg",
        "entry.md",
        "semantic.json",
        "snapshot.json",
        "manifest.json",
        "view.json",
    ):
        assert (review_dir / name).is_file(), name

    rerun = prc("review", "--source", source, "--store", store, "--out", out)

    assert rerun["view_id"] == first["view_id"] and rerun["canonical_publication_won"] is True

    status = prc("status", "--source", source, "--store", store)

    assert status["status"] == "match" and status["effective_now"] == "match"
    assert float(str(status["freshness_deadline"])) > float(str(status["last_observed_at"]))

    late = prc("status", "--source", source, "--store", store, "--clock-offset", "100000")

    assert late["status"] == "stale" and "verification" in late["differences"]

    decided = prc(
        "decide", "--source", source, "--store", store,
        "--expect-snapshot", str(first["snapshot_id"]), "--expect-view", str(first["view_id"]),
        "--reviewer", "creator", "--decision", "request_changes", "--confidence", "70",
    )  # fmt: skip

    assert decided["recorded"] == "request_changes"

    mutated = subprocess.run(
        [sys.executable, "-m", "prc.cli", "fixture-mutate", "basic", "edit-title", "--store", store],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )  # fmt: skip
    assert "edit-title" in mutated.stdout

    stale = prc("status", "--source", source, "--store", store)

    assert stale["status"] == "stale" and "metadata" in stale["differences"]

    second = prc("review", "--source", source, "--store", store, "--out", out)

    assert second["snapshot_id"] != first["snapshot_id"]

    prc(
        "decide", "--source", source, "--store", store,
        "--expect-snapshot", str(first["snapshot_id"]), "--expect-view", str(first["view_id"]),
        "--reviewer", "creator", "--decision", "approve", expect=2,
    )  # fmt: skip
    prc(
        "decide", "--source", source, "--store", store,
        "--expect-snapshot", str(second["snapshot_id"]), "--expect-view", str(second["view_id"]),
        "--reviewer", "creator", "--decision", "approve", "--confidence", "85",
    )  # fmt: skip

    fresh = prc(
        "review", "--source", source, "--store", str(tmp_path / "s"), "--out", str(tmp_path / "o")
    )

    assert fresh["view_id"] == first["view_id"]
    assert (Path(str(fresh["out_dir"])) / "index.html").read_bytes() == (
        review_dir / "index.html"
    ).read_bytes()


def test_unknown_consistency_and_hostile_fixtures_publish_with_visible_gaps(tmp_path: Path) -> None:
    hostile = prc(
        "review",
        "--source",
        "fixture:hostile",
        "--store",
        str(tmp_path / "s"),
        "--out",
        str(tmp_path / "o"),
    )
    html = (Path(str(hostile["out_dir"])) / "index.html").read_text()

    assert "&lt;script&gt;" in html and "<script" not in html
    assert int(str(hostile["coverage_gaps"])) >= 1


def test_eval_analyze_runs_on_synthetic_input() -> None:
    report = prc("eval-analyze", str(ROOT / "tests" / "data" / "synthetic_pairs.json"))

    assert report["decision"] in ("success", "inconclusive", "no promising signal")
    assert len(report["pair_rows"]) == 12
