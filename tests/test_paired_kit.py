"""Paired-eval kit: manifest validation, sealing, export, and grading."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from prc.evaluation import kit
from prc.evaluation.scoring import DECISION_ANCHORS


def _submit_all(study: Path) -> None:
    session_state = json.loads((study / "session.json").read_text())
    for trial in session_state["trials"].values():
        trial["state"] = "submitted"
        trial["started_at"] = 1.0
        trial["ended_at"] = 60.0
        trial["answers"] = {"q1": "cache/evict.go", "q2": "trigger", "q3": ""}
        trial["confidence"] = {"q1": 80, "q2": 60, "q3": None}
    session_state["active_trial"] = None
    (study / "session.json").write_text(json.dumps(session_state))


def _decision_item(fixture: Any, **fields: Any) -> None:
    q3 = fixture.data["pairs"][0]["snapshots"][0]["questions"][2]
    q3["slot"] = "review_decision"
    q3["rubric_anchors"] = dict(DECISION_ANCHORS)
    q3.update(fields)
    fixture.save()


def test_decision_item_needs_accepted_verdicts(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    _decision_item(fixture)
    with pytest.raises(kit.KitError, match="accepted_verdicts"):
        kit.load_manifest(fixture.manifest)


def test_decision_item_rejects_unknown_verdict(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    _decision_item(fixture, accepted_verdicts=["merge", "approve"])
    with pytest.raises(kit.KitError, match="accepted_verdicts"):
        kit.load_manifest(fixture.manifest)


def test_decision_item_rejects_its_own_anchors(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    _decision_item(
        fixture,
        accepted_verdicts=["merge"],
        rubric_anchors={"0": "Request changes earns no credit.", "0.5": "One.", "1": "Both."},
    )
    with pytest.raises(kit.KitError, match="decision anchors"):
        kit.load_manifest(fixture.manifest)


def test_grading_sheet_carries_both_accepted_verdicts(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    _decision_item(fixture, accepted_verdicts=["merge", "request_changes"])
    kit.prepare_study(fixture.manifest, fixture.study)
    _submit_all(fixture.study)
    kit.close_study(fixture.study)
    grading = fixture.root / "grading.json"
    kit.export_blinded(fixture.study, grading)
    items = json.loads(grading.read_text())["items"]
    decision = [item for item in items if item["qid"] == "q3" and item["accepted_verdicts"]]
    assert [item["accepted_verdicts"] for item in decision] == [["merge", "request_changes"]]
    assert decision[0]["rubric_anchors"] == {
        "0": "No accepted verdict is stated, neither element is present, "
        "or the stated reason contradicts the diff.",
        "0.5": "An accepted verdict with exactly one of the two required elements.",
        "1": "An accepted verdict with both required elements: "
        "a named risk the diff supports and a runnable probe.",
    }


def test_paired_protocol_v2_is_bounded_and_uncapped(make_paired: Any) -> None:
    assert kit.PAIRED_PROTOCOL_V2.pair_count == 3
    assert kit.PAIRED_PROTOCOL_V2.generation_cap_seconds == 0.0
    assert kit.PAIRED_PROTOCOL_V2.deadline_seconds == 1200.0
    assert kit.PAIRED_PROTOCOL_V2.session_days == (1,)

    loaded = kit.load_manifest(make_paired().manifest)
    assert loaded.protocol.pair_count == 1
    assert [pair.pair_id for pair in loaded.pairs] == [1]


def test_duplicate_pr_identity_fails_even_at_different_head(make_paired: Any) -> None:
    fixture = make_paired(pairs=2)
    clone = copy.deepcopy(fixture.data["pairs"][0]["snapshots"][0])
    fixture.data["pairs"][1]["snapshots"][1]["pr_identity"] = clone["pr_identity"]
    fixture.data["pairs"][1]["snapshots"][1]["head_sha"] = "a" * 40  # different commit, same PR
    fixture.data["pairs"][1]["snapshots"][1]["lens"]["reviewed_sha"] = "a" * 40
    fixture.data["pairs"][1]["snapshots"][1]["lens"]["headSha"] = "a" * 40
    fixture.data["pairs"][1]["snapshots"][1]["lens"]["graphKey"] = "a" * 40
    fixture.data["pairs"][1]["snapshots"][1]["lens"]["check_head_sha"] = "a" * 40
    fixture.data["pairs"][1]["snapshots"][1]["prc"]["base_sha"] = "b" * 40
    fixture.data["pairs"][1]["snapshots"][1]["prc"]["head_sha"] = "a" * 40
    fixture.save()

    with pytest.raises(kit.KitError, match="duplicate"):
        kit.load_manifest(fixture.manifest)


@pytest.mark.parametrize(
    "identity",
    [
        "willtho89/librarySync#98",
        "cybersemics/em#5756",
        "swarm-deploy/swarm-deploy#116",
        "some-familiar/repo#7",
    ],
)
def test_exposed_or_familiar_pr_rejected(make_paired: Any, identity: str) -> None:
    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["snapshots"][1]["pr_identity"] = identity
    fixture.save()

    with pytest.raises(kit.KitError, match="exposed|familiar"):
        kit.load_manifest(fixture.manifest)


def test_mismatched_change_kind_or_missing_rationale_fails(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["snapshots"][1]["change_kind"] = "feat-cache"
    fixture.save()
    with pytest.raises(kit.KitError, match="change_kind"):
        kit.load_manifest(fixture.manifest)

    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["matching_rationale"] = ""
    fixture.save()
    with pytest.raises(kit.KitError, match="rationale"):
        kit.load_manifest(fixture.manifest)


def test_incompatible_question_kinds_fail(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["snapshots"][1]["questions"] = fixture.data["pairs"][0]["snapshots"][
        1
    ]["questions"][::-1]
    fixture.save()
    with pytest.raises(kit.KitError, match="question"):
        kit.load_manifest(fixture.manifest)


def test_missing_tool_artifact_fails_preparation(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    import shutil

    shutil.rmtree(fixture.root / fixture.data["pairs"][0]["snapshots"][1]["artifacts"]["lens"])
    fixture.save()
    with pytest.raises(kit.KitError, match="lens"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_stale_tool_source_fails_preparation(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["snapshots"][1]["prc"]["head_sha"] = "f" * 40
    fixture.save()
    with pytest.raises(kit.KitError, match="head"):
        kit.prepare_study(fixture.manifest, fixture.study)

    fixture = make_paired(pairs=1)
    snap = fixture.data["pairs"][0]["snapshots"][1]
    snap["lens"]["svg_files"][0]["sha256"] = "0" * 64
    fixture.save()
    with pytest.raises(kit.KitError, match="svg"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_lens_provider_validated_via_check_and_comment_state(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(
        fixture.manifest, fixture.study
    )  # valid passes: app slug + bot author + head state

    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["snapshots"][0]["lens"]["check_head_sha"] = "a" * 40
    fixture.save()
    with pytest.raises(kit.KitError, match="check"):
        kit.prepare_study(fixture.manifest, fixture.study)

    fixture = make_paired(pairs=1)
    lens_dir = fixture.root / fixture.data["pairs"][0]["snapshots"][0]["artifacts"]["lens"]
    record = json.loads((lens_dir / "check_run.json").read_text())
    record["conclusion"] = "failure"
    (lens_dir / "check_run.json").write_text(json.dumps(record))
    fixture.save()
    with pytest.raises(kit.KitError, match="check"):
        kit.prepare_study(fixture.manifest, fixture.study)

    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["snapshots"][0]["lens"]["check_app_slug"] = "totally-other-app"
    fixture.save()
    with pytest.raises(kit.KitError, match="captured app record|app slug"):
        kit.prepare_study(fixture.manifest, fixture.study)

    fixture = make_paired(pairs=1)
    fixture.data["pairs"][0]["snapshots"][0]["lens"]["comment_author"] = "vendor-bot"
    fixture.save()
    with pytest.raises(kit.KitError, match="comment author"):
        kit.prepare_study(fixture.manifest, fixture.study)

    fixture = make_paired(pairs=1)
    lens_dir = fixture.root / fixture.data["pairs"][0]["snapshots"][0]["artifacts"]["lens"]
    comment = json.loads((lens_dir / "comment.json").read_text())
    comment["body"] = comment["body"].replace(kit.LENS_STATE_MARKER_PREFIX, "fake-state ")
    (lens_dir / "comment.json").write_text(json.dumps(comment))
    fixture.save()
    with pytest.raises(kit.KitError, match="state marker"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_hosted_app_version_accepted_and_prc_artifact_must_not_claim_lens(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    snap = fixture.data["pairs"][0]["snapshots"][0]
    snap["lens"]["version"] = "hosted-app captured 2026-10-11T09:30:00Z"
    fixture.save()
    kit.prepare_study(fixture.manifest, fixture.study)

    fixture = make_paired(pairs=1)
    prc_dir = fixture.root / fixture.data["pairs"][0]["snapshots"][0]["artifacts"]["prc"]
    (prc_dir / "index.html").write_text(kit.LENS_STICKY_MARKER)
    fixture.save()
    with pytest.raises(kit.KitError, match="sticky|lens marker"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_prepare_seals_and_assigns_without_overwrite(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    summary = kit.prepare_study(fixture.manifest, fixture.study)
    assert summary["trials"] == 2

    study = kit.load_study(fixture.study)
    assert kit.verify_digest(study.sealed)
    conditions = sorted(trial.condition for trial in study.trials.values())
    assert conditions == ["baseline", "product"]
    assert {trial.state for trial in study.trials.values()} == {"pending"}

    with pytest.raises(kit.KitError, match="exists"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_load_study_drift_check_fails_on_tampered_artifact(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    sid = fixture.data["pairs"][0]["snapshots"][0]["snapshot_id"]
    target = fixture.study / "snapshots" / sid
    svg = next(target.rglob("*.svg"))
    svg.write_text(svg.read_text() + "<!-- tampered -->")

    with pytest.raises(kit.KitError, match="drift"):
        kit.load_study(fixture.study)


def test_export_requires_closed_and_blinds_condition_but_keeps_keys(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    session_state = json.loads((fixture.study / "session.json").read_text())
    for trial in session_state["trials"].values():
        trial["state"] = "submitted"
        trial["started_at"] = 1.0
        trial["ended_at"] = 60.0
        trial["answers"] = {"q1": "cache/evict.go", "q2": "trigger", "q3": "churn"}
        trial["confidence"] = {"q1": 80, "q2": 60, "q3": 40}
    session_state["active_trial"] = None
    (fixture.study / "session.json").write_text(json.dumps(session_state))
    grading = fixture.root / "grading.json"

    with pytest.raises(kit.KitError, match="closed"):
        kit.export_blinded(fixture.study, grading)

    kit.close_study(fixture.study)
    kit.export_blinded(fixture.study, grading)
    raw = grading.read_text()
    data = json.loads(raw)
    assert data["study_digest"] == kit.study_digest(fixture.study)
    assert "condition-blinded" in data["blinding_label"]
    assert data["rubric_evidence_caveat"]

    assert "github+" not in raw and "lens-ci" not in raw
    assert fixture.data["pairs"][0]["snapshots"][0]["pr_identity"] not in raw
    first = data["items"][0]
    assert first["key"] and first["required_elements"] is not None
    assert first["rubric"]["multiple_choice"] == [0.0, 1.0]
    assert all("sha" not in item and "url" not in json.dumps(item) for item in data["items"])


def test_grade_rejects_unknown_ids_bad_anchors_and_blank_awards(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    _submit_all(fixture.study)
    kit.close_study(fixture.study)
    grading = fixture.root / "grading.json"
    kit.export_blinded(fixture.study, grading)
    items = json.loads(grading.read_text())["items"]
    trial_id = items[0]["trial_id"]

    def write_scores(scores: dict[str, Any], digest: str | None = None) -> Path:
        path = Path(fixture.root) / "scores.json"
        path.write_text(
            json.dumps(
                {"study_digest": digest or kit.study_digest(fixture.study), "scores": scores}
            )
        )
        return path

    with pytest.raises(kit.KitError, match="trial"):
        kit.apply_scores(fixture.study, write_scores({}), fixture.root / "r1.json")
    with pytest.raises(kit.KitError, match="digest"):
        kit.apply_scores(
            fixture.study, write_scores({}, digest="deadbeef"), fixture.root / "r2.json"
        )
    with pytest.raises(kit.KitError, match="terminal trials|qid"):
        kit.apply_scores(
            fixture.study, write_scores({trial_id: {"qX": 1.0}}), fixture.root / "r3.json"
        )
    with pytest.raises(kit.KitError, match="qid"):
        all_trials = {item["trial_id"] for item in items}
        kit.apply_scores(
            fixture.study,
            write_scores({trial: {"qX": 1.0, "qY": 0.5, "qZ": 1.0} for trial in all_trials}),
            fixture.root / "r3b.json",
        )
    with pytest.raises(kit.KitError, match="anchor"):
        all_trials = {item["trial_id"] for item in items}
        kit.apply_scores(
            fixture.study,
            write_scores({trial: {item["qid"]: 0.25 for item in items} for trial in all_trials}),
            fixture.root / "r4.json",
        )


def test_grade_builds_results_with_protocol_and_unknowns(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    # answer only the first trial in reading order; the second stays pending (unknown)
    session_state = json.loads((fixture.study / "session.json").read_text())
    first = session_state["trials"][session_state["order"][0]]
    first["state"] = "submitted"
    first["started_at"] = 1.0
    first["ended_at"] = 90.0
    first["answers"] = {"q1": "cache/evict.go", "q2": "trigger", "q3": ""}
    first["confidence"] = {"q1": 80, "q2": 60, "q3": None}
    session_state["active_trial"] = None
    (fixture.study / "session.json").write_text(json.dumps(session_state))
    kit.close_study(fixture.study)
    grading = fixture.root / "grading.json"
    kit.export_blinded(fixture.study, grading)
    items = json.loads(grading.read_text())["items"]
    trial_ids = [item["trial_id"] for item in items]
    scores = {trial_id: {"q1": 1.0, "q2": 0.5, "q3": 0.0} for trial_id in trial_ids[:1]}
    scores_path = fixture.root / "scores.json"
    scores_path.write_text(
        json.dumps({"study_digest": kit.study_digest(fixture.study), "scores": scores})
    )

    results = kit.apply_scores(fixture.study, scores_path, fixture.root / "results.json")
    assert results["protocol"]["pair_count"] == 1
    assert len(results["pairs"]) == 1
    pair = results["pairs"][0]
    states = [pair["product"]["state"], pair["baseline"]["state"]]
    assert sorted(states) == ["scored", "unknown"]
    scored = pair["product"] if pair["product"]["state"] == "scored" else pair["baseline"]
    assert scored["item_scores"] == [1.0, 0.5, 0.0]

    from prc.evaluation.io import load_pairs_with_protocol

    pairs, protocol = load_pairs_with_protocol(fixture.root / "results.json")
    assert protocol is not None and protocol.pair_count == 1
    assert len(pairs) == 1
