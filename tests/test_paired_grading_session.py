from __future__ import annotations

import copy
import json
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from prc.evaluation import kit, session
from test_paired_session import get, post, start, state


@pytest.fixture
def grading_server(make_paired: Any) -> Iterator[tuple[str, Path]]:
    fixture = make_paired(pairs=2)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = session.serve(fixture.study)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield url, fixture.study
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def close_with_answers(url: str) -> None:
    assert start(url)[0] == 200
    assert (
        post(
            url,
            "/api/submit",
            {
                "answers": {"q1": "cache/evict.go", "q2": "trigger and evidence", "q3": ""},
                "confidence": {"q2": 75},
                "cross_tool_exposure": {"saw_other_aid": True, "note": "reported exposure"},
            },
        )[0]
        == 200
    )
    assert post(url, "/api/close", {})[0] == 200


def scores_for(sheet: dict[str, Any]) -> dict[str, Any]:
    scores: dict[str, dict[str, float]] = {}
    for item in sheet["items"]:
        value = 0.0 if item["answer"] in (None, "") else 0.5
        if item["kind"] == "multiple_choice":
            value = float(item["answer"] == item["key"])
        scores.setdefault(item["trial_id"], {})[item["qid"]] = value
    return {"study_digest": sheet["study_digest"], "scores": scores}


def test_grading_and_analysis_refuse_before_close(grading_server: tuple[str, Path]) -> None:
    url, root = grading_server
    for phase in ("pending", "active", "submitted"):
        assert get(url, "/api/grading")[0] == 403, phase
        assert get(url, "/api/analysis")[0] == 403, phase
        assert post(url, "/api/grade", {"scores": {}})[0] == 409, phase
        assert not (root / "grading.json").exists()
        assert "required_elements" not in get(url, "/api/state")[1]
        if phase == "pending":
            start(url)
        elif phase == "active":
            post(url, "/api/submit", {"cross_tool_exposure": {"saw_other_aid": False}})


def test_closed_grading_is_persisted_blinded_and_answers_stay_frozen(
    grading_server: tuple[str, Path],
) -> None:
    url, root = grading_server
    close_with_answers(url)
    frozen = (root / "session.json").read_bytes()
    status, body = get(url, "/api/grading")
    assert status == 200
    sheet = json.loads(body)
    assert sheet == json.loads((root / "grading.json").read_text())
    assert len(sheet["items"]) == 3
    assert sheet["items"][1]["answer"] == "trigger and evidence"
    assert sheet["items"][1]["required_elements"] == ["trigger", "evidence line"]
    assert sheet["items"][1]["key"] == "trigger named with evidence"
    forbidden = {
        "condition",
        "snapshot_id",
        "pair_id",
        "pr_identity",
        "title",
        "evidence",
        "started_at",
        "ended_at",
        "elapsed_seconds",
        "generation_seconds",
    }
    assert all(not forbidden.intersection(item) for item in sheet["items"])
    assert "vendor-" not in body
    assert "github+prc" not in body and "github+lens-ci" not in body
    assert get(url, "/api/analysis")[0] == 403
    assert post(url, "/api/answers", {"answers": {"q2": "changed"}})[0] == 409
    assert (root / "session.json").read_bytes() == frozen
    for path in (
        "/grading.json",
        "/results.json",
        "/analysis.json",
        "/scores.json",
        "/artifact/missing/aid/index.html",
    ):
        assert get(url, path)[0] == 404


@pytest.mark.parametrize(
    "bad",
    [
        "missing_trial",
        "extra_trial",
        "missing_qid",
        "extra_qid",
        "blank",
        "mc",
        "anchor",
        "boolean",
        "string",
        "nan",
        "digest",
        "shape",
    ],
)
def test_bad_grades_do_not_publish_results(
    grading_server: tuple[str, Path],
    bad: str,
) -> None:
    url, root = grading_server
    close_with_answers(url)
    sheet = json.loads(get(url, "/api/grading")[1])
    payload = copy.deepcopy(scores_for(sheet))
    trial = next(iter(payload["scores"]))
    awarded = payload["scores"][trial]
    if bad == "missing_trial":
        payload["scores"].pop(trial)
    elif bad == "extra_trial":
        payload["scores"]["invented"] = awarded.copy()
    elif bad == "missing_qid":
        awarded.pop("q2")
    elif bad == "extra_qid":
        awarded["q4"] = 0
    elif bad == "blank":
        awarded["q3"] = 1
    elif bad == "mc":
        awarded["q1"] = 0
    elif bad == "digest":
        payload["study_digest"] = "wrong"
    elif bad == "shape":
        payload["scores"] = []
    else:
        awarded["q2"] = {"anchor": 0.25, "boolean": True, "string": "1", "nan": float("nan")}[bad]
    status, body = post(url, "/api/grade", payload)
    assert status == 409
    assert "error" in json.loads(body)
    assert not (root / "results.json").exists()
    assert not (root / "analysis.json").exists()
    assert not (root / "scores.json").exists()
    assert get(url, "/api/analysis")[0] == 403


def test_grade_analyzes_missing_pairs_and_preserves_provenance(
    grading_server: tuple[str, Path],
) -> None:
    from dataclasses import asdict

    from prc.evaluation.analysis import analyze
    from prc.evaluation.io import load_pairs_with_protocol

    url, root = grading_server
    close_with_answers(url)
    sheet = json.loads(get(url, "/api/grading")[1])
    payload = scores_for(sheet)
    assert post(url, "/api/grade", payload, origin="http://evil:1")[0] == 403
    assert post(url, "/api/grade", payload)[0] == 200
    report = json.loads(get(url, "/api/analysis")[1])
    assert report == json.loads((root / "analysis.json").read_text())
    assert json.loads((root / "scores.json").read_text()) == payload
    results = json.loads((root / "results.json").read_text())
    assert report["study_digest"] == results["study_digest"] == sheet["study_digest"]
    assert report["deviations"] == results["deviations"]
    assert (
        "pilot" in report["interpretation"]
        and "not evidence of release readiness" in report["interpretation"]
    )
    assert sum(report["missing_by_condition"].values()) == 3
    assert any(
        d["cross_exposure_submit"] and d["cross_exposure_submit"]["saw_other_aid"]
        for d in report["deviations"]
    )
    pairs, protocol = load_pairs_with_protocol(root / "results.json")
    assert protocol is not None
    expected = json.loads(json.dumps(asdict(analyze(pairs, protocol))))
    assert all(report[key] == value for key, value in expected.items())
    assert state(url)["active"] is None
    with pytest.raises(session.SessionError, match="writer"):
        session.StudySession(root)
    assert post(url, "/api/grade", payload)[0] == 200
    assert json.loads(get(url, "/api/analysis")[1]) == report
