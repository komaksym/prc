"""End-to-end paired-eval lifecycle through the real CLI entry, artifact saved."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "e2e" / "paired"


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


def http(
    method: str, url: str, payload: dict[str, Any] | None = None, origin: str | None = None
) -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def test_paired_eval_full_lifecycle_through_cli(tmp_path: Path) -> None:
    import shutil

    from paired_builder import build_manifest

    shutil.rmtree(ARTIFACT, ignore_errors=True)
    fixture = build_manifest(ARTIFACT / "fixture", pairs=1)
    study = ARTIFACT / "study"

    summary = prc("eval-prepare", str(fixture.manifest), "--out", str(study))
    assert summary["trials"] == 2 and (study / "study.json").is_file()

    process = subprocess.Popen(
        [sys.executable, "-m", "prc.cli", "eval-session", str(study), "--port", "0"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    url_line = ""
    deadline = time.time() + 15
    while time.time() < deadline:
        url_line = process.stdout.readline().strip()
        if url_line:
            break
    assert url_line.startswith("paired-eval session: http://127.0.0.1:"), url_line
    server_url = url_line.removeprefix("paired-eval session: ")
    _, preview = http("GET", f"{server_url}/api/preview")

    status, body = http(
        "POST",
        f"{server_url}/api/start",
        {
            "trial_id": json.loads(preview)["trial_id"],
            "familiarity": {"seen_before": False, "note": ""},
            "cross_tool_exposure": {"saw_other_aid": False, "note": ""},
        },
        origin=server_url,
    )
    assert status == 200, body

    status, state_body = http("GET", f"{server_url}/api/state")
    active = json.loads(state_body)["active"]
    assert status == 200 and active["aid_kind"] in ("lens", "prc")

    status, _ = http(
        "POST",
        f"{server_url}/api/answers",
        {
            "trial_id": active["trial_id"],
            "answers": {"q1": "cache/evict.go", "q2": "trigger", "q3": "churn"},
            "confidence": {"q1": 80, "q2": 60, "q3": 40},
        },
        origin=server_url,
    )
    assert status == 200

    status, body = http(
        "POST",
        f"{server_url}/api/submit",
        {
            "trial_id": active["trial_id"],
            "cross_tool_exposure": {"saw_other_aid": False, "note": ""},
        },
        origin=server_url,
    )
    assert status == 200, body

    # second trial stays pending; close retains it unknown
    status, _ = http("POST", f"{server_url}/api/close", {}, origin=server_url)
    assert status == 200
    process.terminate()
    process.wait(timeout=10)

    grading_path = ARTIFACT / "grading.json"
    prc("eval-export", str(study), "--out", str(grading_path))
    grading = json.loads(grading_path.read_text())
    answered = {item["trial_id"] for item in grading["items"]}
    assert len(answered) == 1

    scores = {
        "study_digest": grading["study_digest"],
        "scores": {trial_id: {"q1": 1.0, "q2": 0.5, "q3": 0.0} for trial_id in answered},
    }
    scores_path = ARTIFACT / "scores.json"
    scores_path.write_text(json.dumps(scores))
    results_path = ARTIFACT / "results.json"
    prc("eval-grade", str(study), str(scores_path), "--out", str(results_path))

    report = prc("eval-analyze", str(results_path))

    assert len(report["pair_rows"]) == 1
    assert report["pair_rows"][0]["product_state"] in ("scored", "unknown")

    # legacy 12-pair path still intact
    legacy = prc("eval-analyze", "tests/data/synthetic_pairs.json")
    assert len(legacy["pair_rows"]) == 12

    assert (ARTIFACT / "grading.json").is_file() and (ARTIFACT / "results.json").is_file()
