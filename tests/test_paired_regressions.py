from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prc.evaluation import kit, session


@pytest.mark.parametrize("field", ["questions", "snapshots", "assignment"])
def test_seal_rejects_changed_study_content(make_paired: Any, field: str) -> None:
    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    path = fixture.study / "study.json"
    data = json.loads(path.read_text())
    if field == "questions":
        data[field]["1a"][0]["key"] = "incorrect replacement"
    elif field == "snapshots":
        data[field]["1a"]["head_sha"] = "0" * 40
    else:
        data[field]["pairs"][0]["product_first"] = not data[field]["pairs"][0]["product_first"]
    path.write_text(json.dumps(data))
    with pytest.raises(kit.KitError, match="drift"):
        kit.load_study(fixture.study)


def test_session_refuses_tampering_before_any_exposure(make_paired: Any) -> None:
    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    path = fixture.study / "study.json"
    data = json.loads(path.read_text())
    data["questions"]["1a"][0]["key"] = "changed"
    path.write_text(json.dumps(data))
    with pytest.raises(kit.KitError, match="drift"):
        session.serve(fixture.study)


def test_lens_state_cannot_hide_wrong_head_in_other_comment_text(make_paired: Any) -> None:
    fixture = make_paired()
    snap = fixture.data["pairs"][0]["snapshots"][0]
    path = fixture.root / snap["artifacts"]["lens"] / "comment.json"
    comment = json.loads(path.read_text())
    comment["body"] = (
        '<!-- pr-lens:sticky -->\n<!-- pr-lens:state {"headSha":"'
        + "0" * 40
        + '"} -->\n'
        + snap["head_sha"]
    )
    path.write_text(json.dumps(comment))
    with pytest.raises(kit.KitError, match="state"):
        kit.prepare_study(fixture.manifest, fixture.study)
    assert not fixture.study.exists()


def test_assignment_changes_in_session_are_rejected(make_paired: Any) -> None:
    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    path = fixture.study / "session.json"
    data = json.loads(path.read_text())
    first = data["trials"][data["order"][0]]
    first["condition"] = "product" if first["condition"] == "baseline" else "baseline"
    path.write_text(json.dumps(data))
    with pytest.raises(kit.KitError, match="assignment"):
        kit.load_study(fixture.study)


def test_trial_paths_cannot_escape_study(make_paired: Any, tmp_path: Path) -> None:
    fixture = make_paired()
    fixture.data["pairs"][0]["snapshots"][0]["snapshot_id"] = "../../escape"
    fixture.save()
    with pytest.raises(kit.KitError, match="snapshot_id"):
        kit.prepare_study(fixture.manifest, fixture.study)
    assert not (tmp_path / "escape").exists()


def test_old_tab_cannot_save_or_finish_a_new_reading(make_paired: Any) -> None:
    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    owner = session.StudySession(fixture.study)
    try:
        report = {
            "familiarity": {"seen_before": False},
            "cross_tool_exposure": {"saw_other_aid": False},
        }
        old = owner.preview()["trial_id"]
        owner.start({**report, "trial_id": old})
        owner.submit({**report, "trial_id": old})
        new = owner.preview()["trial_id"]
        owner.start({**report, "trial_id": new})
        with pytest.raises(session.SessionError, match="stale"):
            owner.save_answers({"q2": "old-tab answer"}, {}, old)
        with pytest.raises(session.SessionError, match="stale"):
            owner.submit({**report, "trial_id": old})
        assert owner.state["active_trial"] == new
        assert owner.state["trials"][new]["answers"] == {}
    finally:
        owner.close()


def test_prepare_refuses_missing_lens_review_page(make_paired: Any) -> None:
    fixture = make_paired()
    for snap in fixture.data["pairs"][0]["snapshots"]:
        (fixture.root / snap["artifacts"]["lens"] / "index.html").unlink(missing_ok=True)
    with pytest.raises(kit.KitError, match="lens index"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_prepare_refuses_lens_page_that_differs_from_its_pin(make_paired: Any) -> None:
    fixture = make_paired()
    snap = fixture.data["pairs"][0]["snapshots"][0]
    (fixture.root / snap["artifacts"]["lens"] / "index.html").write_text("<h1>Fabricated</h1>")
    with pytest.raises(kit.KitError, match="lens page_sha256"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_prepare_refuses_lens_page_without_a_pin(make_paired: Any) -> None:
    fixture = make_paired()
    del fixture.data["pairs"][0]["snapshots"][0]["lens"]["page_sha256"]
    fixture.save()
    with pytest.raises(kit.KitError, match="lens page_sha256"):
        kit.prepare_study(fixture.manifest, fixture.study)


@pytest.mark.parametrize("form", ["identity", "url", "head"])
def test_prepare_refuses_tree_that_names_another_reading(make_paired: Any, form: str) -> None:
    fixture = make_paired(pairs=2)
    snaps = [snap for entry in fixture.data["pairs"] for snap in entry["snapshots"]]
    leaked = snaps[2]
    owner_repo, number = leaked["pr_identity"].split("#")
    text = {
        "identity": leaked["pr_identity"],
        "url": f"https://github.com/{owner_repo}/pull/{number}/files",
        "head": leaked["head_sha"],
    }[form]
    nested = fixture.root / snaps[0]["artifacts"]["prc"] / "nested"
    nested.mkdir()
    (nested / "notes.json").write_text(json.dumps({"note": text}))
    with pytest.raises(kit.KitError, match="names another reading"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_longer_pr_number_is_not_a_cross_reading_leak(make_paired: Any) -> None:
    fixture = make_paired(pairs=2)
    snaps = [snap for entry in fixture.data["pairs"] for snap in entry["snapshots"]]
    owner_repo, number = snaps[2]["pr_identity"].split("#")
    page = fixture.root / snaps[0]["artifacts"]["github"] / "index.html"
    page.write_text(page.read_text() + f"<a href='/{owner_repo}/pull/{number}0'>x</a>")
    kit.prepare_study(fixture.manifest, fixture.study)


def test_wrong_multiple_choice_cannot_receive_full_credit(make_paired: Any) -> None:
    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    owner = session.StudySession(fixture.study)
    tid = owner.preview()["trial_id"]
    report = {
        "trial_id": tid,
        "familiarity": {"seen_before": False},
        "cross_tool_exposure": {"saw_other_aid": False},
    }
    try:
        owner.start(report)
        owner.submit({**report, "answers": {"q1": "docs/notes.md", "q2": "trigger", "q3": "churn"}})
        owner.close_study()
    finally:
        owner.close()
    scores = fixture.root / "bad-scores.json"
    scores.write_text(
        json.dumps(
            {
                "study_digest": kit.study_digest(fixture.study),
                "scores": {tid: {"q1": 1, "q2": 0.5, "q3": 0}},
            }
        )
    )
    with pytest.raises(kit.KitError, match="multiple.choice"):
        kit.apply_scores(fixture.study, scores, fixture.root / "results.json")


def test_lens_svg_name_must_match_its_bytes(make_paired: Any) -> None:
    fixture = make_paired()
    snap = fixture.data["pairs"][0]["snapshots"][0]
    entry = snap["lens"]["svg_files"][0]
    root = fixture.root / snap["artifacts"]["lens"]
    (root / entry["path"]).rename(root / ("0" * 32 + ".svg"))
    entry["path"] = "0" * 32 + ".svg"
    fixture.save()
    with pytest.raises(kit.KitError, match="content.address"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_familiar_pr_never_enters_scored_reading(make_paired: Any) -> None:
    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    owner = session.StudySession(fixture.study)
    try:
        tid = owner.preview()["trial_id"]
        with pytest.raises(session.SessionError, match="familiar"):
            owner.start(
                {
                    "trial_id": tid,
                    "familiarity": {"seen_before": True},
                    "cross_tool_exposure": {"saw_other_aid": False},
                }
            )
        assert owner.public_state()["active"] is None
        assert owner.state["trials"][tid]["started_at"] is None
        assert owner.state["trials"][tid]["state"] == "pending"
        assert owner.preview()["trial_id"] != tid
    finally:
        owner.close()


def test_familiarity_and_exposure_survive_grading_and_analysis(
    make_paired: Any, capsys: Any
) -> None:
    from prc.cli import main

    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    owner = session.StudySession(fixture.study)
    tid = owner.preview()["trial_id"]
    try:
        with pytest.raises(session.SessionError, match="familiar"):
            owner.start(
                {
                    "trial_id": tid,
                    "familiarity": {"seen_before": True, "note": "already read"},
                    "cross_tool_exposure": {"saw_other_aid": False},
                }
            )
        owner.close_study()
    finally:
        owner.close()
    scores = fixture.root / "scores.json"
    scores.write_text(json.dumps({"study_digest": kit.study_digest(fixture.study), "scores": {}}))
    results = fixture.root / "results.json"
    document = kit.apply_scores(fixture.study, scores, results)
    assert document["study_digest"] == kit.study_digest(fixture.study)
    deviation = next(d for d in document["deviations"] if d["trial_id"] == tid)
    assert deviation["familiarity"]["note"] == "already read"
    assert deviation["ineligible"] == "prior familiarity or prior explanation exposure"
    assert all(
        p[condition]["state"] == "unknown"
        for p in document["pairs"]
        for condition in ("baseline", "product")
    )
    assert main(["eval-analyze", str(results)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["study_digest"] == document["study_digest"]
    assert report["deviations"] == document["deviations"]
    assert report["interpretation"] == "exploratory pilot; not evidence of release readiness"


def test_actual_prc_map_must_match_snapshot(make_paired: Any) -> None:
    fixture = make_paired()
    snap = fixture.data["pairs"][0]["snapshots"][0]
    path = fixture.root / snap["artifacts"]["prc"] / "map.json"
    path.write_text(json.dumps({"base_sha": snap["base_sha"], "head_sha": "0" * 40}))
    with pytest.raises(kit.KitError, match="prc map.*head"):
        kit.prepare_study(fixture.manifest, fixture.study)
    assert not fixture.study.exists()


def test_prc_map_cannot_be_missing(make_paired: Any) -> None:
    fixture = make_paired()
    for snap in fixture.data["pairs"][0]["snapshots"]:
        (fixture.root / snap["artifacts"]["prc"] / "map.json").unlink(missing_ok=True)
    with pytest.raises(kit.KitError, match="prc map.*missing"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_unknown_generation_time_is_explicit_not_invented(make_paired: Any) -> None:
    fixture = make_paired()
    for snap in fixture.data["pairs"][0]["snapshots"]:
        snap["generation_seconds"]["lens"] = None
        snap["generation_notes"] = {
            "lens": "Hosted CI was already complete; total preparation time was not measured."
        }
    fixture.save()
    kit.prepare_study(fixture.manifest, fixture.study)
    study = kit.load_study(fixture.study)
    assert all(
        s["generation_seconds"]["lens"] is None
        for s in study.sealed.payload["study_data"]["snapshots"].values()
    )


@pytest.mark.parametrize("kind", ["outside", "symlink"])
def test_artifact_tree_must_stay_inside_manifest_root(make_paired: Any, kind: str) -> None:
    import shutil

    fixture = make_paired()
    snap = fixture.data["pairs"][0]["snapshots"][0]
    original = fixture.root / snap["artifacts"]["prc"]
    outside = fixture.root.parent / "external"
    shutil.copytree(original, outside)
    if kind == "outside":
        snap["artifacts"]["prc"] = "../external"
    else:
        original.rename(original.with_name("prc-original"))
        original.symlink_to(outside, target_is_directory=True)
    fixture.save()
    with pytest.raises(kit.KitError, match="artifact.*(root|symlink)"):
        kit.prepare_study(fixture.manifest, fixture.study)
    assert not fixture.study.exists()


def test_lens_comment_path_cannot_escape_its_tree(make_paired: Any) -> None:
    fixture = make_paired()
    snap = fixture.data["pairs"][0]["snapshots"][0]
    lens = fixture.root / snap["artifacts"]["lens"]
    outside = lens.parent / "external-comment.json"
    outside.write_bytes((lens / "comment.json").read_bytes())
    snap["lens"]["comment_path"] = "../external-comment.json"
    fixture.save()
    with pytest.raises(kit.KitError, match="artifact path escapes"):
        kit.prepare_study(fixture.manifest, fixture.study)


def test_blinded_grading_preserves_descriptive_rubric(make_paired: Any) -> None:
    fixture = make_paired()
    anchors = {
        "0": "No correct elements.",
        "0.5": "Exactly one required element.",
        "1": "Both required elements.",
    }
    for snap in fixture.data["pairs"][0]["snapshots"]:
        snap["questions"][1]["rubric_anchors"] = anchors
    fixture.save()
    kit.prepare_study(fixture.manifest, fixture.study)
    owner = session.StudySession(fixture.study)
    try:
        tid = owner.preview()["trial_id"]
        owner.start(
            {
                "trial_id": tid,
                "familiarity": {"seen_before": False},
                "cross_tool_exposure": {"saw_other_aid": False},
            }
        )
        owner.submit({"trial_id": tid, "cross_tool_exposure": {"saw_other_aid": False}})
        owner.close_study()
    finally:
        owner.close()
    sheet = kit.export_blinded(fixture.study, fixture.root / "grading.json")
    assert next(item for item in sheet["items"] if item["qid"] == "q2")["rubric_anchors"] == anchors


def test_short_key_must_be_readable_frozen_text(make_paired: Any) -> None:
    fixture = make_paired()
    fixture.data["pairs"][0]["snapshots"][0]["questions"][1]["key"] = {
        "requiredElements": ["one", "two"]
    }
    fixture.save()
    with pytest.raises(kit.KitError, match="key.*text"):
        kit.prepare_study(fixture.manifest, fixture.study)
