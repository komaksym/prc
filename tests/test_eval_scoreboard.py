"""Exercise the scoreboard CLI with final grades and damaged copies."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eval/scoreboard.py"
FULL = ROOT / "eval/runs/2026-10-06-full"


@pytest.fixture
def run(tmp_path: Path) -> Path:
    for name in ("grades", "audit", "boards"):
        shutil.copytree(FULL / name, tmp_path / name)
    shutil.copyfile(FULL / "results.json", tmp_path / "results.json")
    for path in (FULL / "outputs").glob("*/run.json"):
        target = tmp_path / path.relative_to(FULL)
        target.parent.mkdir(parents=True)
        shutil.copyfile(path, target)
    return tmp_path


def generate(run: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(run), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_reports_final_grades_targets_and_preserves_results(run: Path) -> None:
    results = (run / "results.json").read_bytes()
    outcome = generate(run)
    assert outcome.returncode == 0, outcome.stderr
    report = (run / "scoreboard.md").read_text()
    for condition, correct in ((1, 20), (2, 24), (3, 45), (4, 67), (5, 17)):
        assert f"| C{condition} | correct {correct / 96 * 100:.1f}% ({correct}/96)" in report
    assert "480/480" in report
    assert "misleading answers (wrong from C1-C5): 44" in report
    assert "32.3% (31/96)" in report
    assert "62.3%" in report
    for target in ("35.0%", "60.0%", "70.0%", "85.0%"):
        assert target in report
    assert "C1 absolute target failed" in report
    assert "C4 absolute target failed" in report
    assert "C4 +30pt target passed" in report
    assert "C5 +30pt target failed" in report
    assert "None." not in report
    assert (run / "results.json").read_bytes() == results


@pytest.mark.parametrize("damage", ["duplicate", "missing", "unknown", "verdict", "reviewer"])
def test_invalid_final_grades_cannot_replace_report(run: Path, damage: str) -> None:
    path = run / "grades/reviewer-a.json"
    data = json.loads(path.read_text())
    if damage == "duplicate":
        data["grades"].append(data["grades"][0])
    elif damage == "missing":
        data["grades"].pop()
    elif damage == "unknown":
        data["grades"][0]["question"] = "q99"
    elif damage == "verdict":
        data["grades"][0]["verdict"] = "NEEDS_HUMAN"
    else:
        path.unlink()
    if damage != "reviewer":
        path.write_text(json.dumps(data))
    report = run / "scoreboard.md"
    report.write_text("previous report\n")
    outcome = generate(run)
    assert outcome.returncode != 0
    assert damage in outcome.stderr.lower() or "missing" in outcome.stderr.lower()
    assert report.read_text() == "previous report\n"


def test_missing_grades_do_not_claim_zero_wrong_answers(run: Path) -> None:
    shutil.rmtree(run / "grades")
    assert generate(run).returncode == 0
    report = (run / "scoreboard.md").read_text()
    assert "misleading answers (wrong from C1-C5): not scored" in report
    assert "missing final grades" in report


def test_evidence_gaps_are_separate_from_passing_gates(run: Path) -> None:
    assert generate(run).returncode == 0
    report = (run / "scoreboard.md").read_text()
    assert "96/96" in report
    for text in ("stale audit", "missing judge", "missing OCR", "missing arrow", "missing human"):
        assert text in report
    assert "audit/pr5.json" in report
    assert "Historical" in report


def test_previous_run_uses_final_grades_too(run: Path) -> None:
    assert generate(run, "--prev", str(FULL)).returncode == 0
    report = (run / "scoreboard.md").read_text()
    assert "C4 prev: correct 69.8% (67/96)" in report


def test_frozen_baseline_previous_run_shows_actual_c0(run: Path) -> None:
    baseline = ROOT / "eval/runs/2026-10-06-baseline"
    assert generate(run, "--prev", str(baseline)).returncode == 0
    assert "C0 prev: correct 32.3% (31/96)" in (run / "scoreboard.md").read_text()


def test_stored_aggregate_cannot_override_final_grades(run: Path) -> None:
    path = run / "results.json"
    results = json.loads(path.read_text())
    results["grades"] = {"c4": {"correct": 96, "wrong": 0}}
    path.write_text(json.dumps(results))
    assert generate(run).returncode == 0
    report = (run / "scoreboard.md").read_text()
    assert "| C4 | correct 69.8% (67/96)" in report
    assert "misleading answers (wrong from C1-C5): 44" in report


def test_no_outputs_or_grades_still_produces_incomplete_report(tmp_path: Path) -> None:
    assert generate(tmp_path).returncode == 0
    report = (tmp_path / "scoreboard.md").read_text()
    assert "gates: not scored" in report
    assert "missing final grades" in report
