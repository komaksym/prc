"""Deterministic grades stay stable across reader answer shapes."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("eval_grade", ROOT / "scripts/eval/grade.py")
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
grade_question = _mod.grade_question


def test_bool_answers_accept_json_booleans() -> None:
    q = {"type": "bool", "key": "false"}
    assert grade_question(q, False) == "correct"
    assert grade_question(q, True) == "wrong"


def test_bool_answers_accept_leading_token_with_justification() -> None:
    q = {"type": "bool", "key": "false"}
    assert grade_question(q, "False. The packet shows a dry run.") == "correct"
    assert grade_question(q, "True, the workflow persists events.") == "wrong"


@pytest.mark.parametrize(
    "answer",
    ["CANNOT TELL", "CANNOT TELL. The card says nothing.", "cannot tell \u2014 packet lacks it"],
)
def test_cannot_tell_with_reason_stays_cannot_tell(answer: str) -> None:
    assert grade_question({"type": "bool", "key": "false"}, answer) == "cannot_tell"
    assert grade_question({"type": "exact", "key": "read_table"}, answer) == "cannot_tell"
    assert grade_question({"type": "location", "key": "a.py :: b"}, answer) == "cannot_tell"


def test_location_same_file_stays_partial() -> None:
    q = {"type": "location", "key": "src/x.py :: _helper"}
    assert grade_question(q, "src/x.py::big_function") == "partial"
    assert grade_question(q, "src/other.py::big_function") == "wrong"


def test_set_none_accepts_empty_list() -> None:
    q = {"type": "set_or_none", "key": "none"}
    assert grade_question(q, []) == "correct"
    assert grade_question(q, "none") == "correct"
    assert grade_question(q, ["external calls"]) == "wrong"


def test_name_or_free_prose_goes_to_human_grading() -> None:
    q = {"type": "name_or_free", "key": "test_pins_dates"}
    assert grade_question(q, "test_pins_dates") == "correct"
    assert grade_question(q, "other_test") == "wrong"
    assert grade_question(q, "Tests pin date display.") == "NEEDS_HUMAN"


def load_round() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "eval_grade_round", ROOT / "scripts/eval/grade_round.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_round_uses_frozen_v1_even_when_unverified_v2_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    module = load_round()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    questions = tmp_path / "eval" / "questions"
    questions.mkdir(parents=True)
    v1 = {"pr": 12, "version": 1, "questions": [{"id": "q2", "type": "exact", "key": "old"}]}
    v2 = {"pr": 12, "version": 2, "questions": [{"id": "q2", "type": "exact", "key": "new"}]}
    (questions / "pr12.json").write_text(json.dumps(v1))
    (questions / "pr12.v2.json").write_text(json.dumps(v2))
    path, selected = module.questions_for(12)
    assert path.name == "pr12.json"
    assert selected["questions"][0]["key"] == "old"


def test_round_rejects_missing_answers_instead_of_improving_score(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    module = load_round()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    questions = tmp_path / "eval" / "questions"
    questions.mkdir(parents=True)
    (questions / "pr12.json").write_text(
        json.dumps(
            {
                "questions": [
                    {"id": "q1", "type": "free", "key": "facts"},
                    {"id": "q2", "type": "exact", "key": "read"},
                ]
            }
        )
    )
    run = tmp_path / "run"
    answers = run / "answers" / "pr12"
    answers.mkdir(parents=True)
    (answers / "c1.json").write_text(json.dumps({"answers": [{"id": "q2", "answer": "read"}]}))
    with pytest.raises(ValueError, match="missing.*q1"):
        module.grade_run(run)


def test_round_rejects_unanswered_packets(tmp_path: Path) -> None:
    packet = tmp_path / "packets" / "pr12" / "c1"
    packet.mkdir(parents=True)
    (packet / "manifest.json").write_text("{}")
    with pytest.raises(ValueError, match="missing answer files.*pr12/c1"):
        load_round().grade_run(tmp_path)


def test_standalone_grader_rejects_duplicate_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import sys

    keys = tmp_path / "questions.json"
    answers = tmp_path / "answers.json"
    keys.write_text(json.dumps({"questions": [{"id": "q2", "type": "exact", "key": "read"}]}))
    answers.write_text(
        json.dumps(
            {
                "answers": [
                    {"id": "q2", "answer": "wrong"},
                    {"id": "q2", "answer": "read"},
                ]
            }
        )
    )
    monkeypatch.setattr(sys, "argv", ["grade.py", str(keys), str(answers)])
    with pytest.raises(ValueError, match="duplicate.*q2"):
        _mod.main()


def test_location_rejects_substring_path_and_symbol() -> None:
    q = {"type": "location", "key": "src/a.py :: foo"}
    assert grade_question(q, "src/a.py :: foo") == "correct"
    assert grade_question(q, "src/a.py.bak :: foobar") == "wrong"
    assert grade_question(q, "see src/a.py :: foo here") == "wrong"
    assert grade_question(q, "src/a.py :: other") == "partial"
    assert grade_question(q, "other.py :: foo") == "partial"


def test_answer_map_rejects_missing_answer_field() -> None:
    with pytest.raises(ValueError, match="missing answer field"):
        _mod.answer_map([{"id": "q2"}], {"answers": [{"id": "q2"}]})


def test_round_rejects_unexpected_answer_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    module = load_round()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    questions = tmp_path / "eval" / "questions"
    questions.mkdir(parents=True)
    (questions / "pr12.json").write_text(
        json.dumps({"questions": [{"id": "q2", "type": "exact", "key": "read"}]})
    )
    run = tmp_path / "run"
    packet = run / "packets" / "pr12" / "c1"
    packet.mkdir(parents=True)
    (packet / "manifest.json").write_text("{}")
    answers = run / "answers" / "pr12"
    answers.mkdir(parents=True)
    body = json.dumps({"answers": [{"id": "q2", "answer": "read"}]})
    (answers / "c1.json").write_text(body)
    (answers / "c2.json").write_text(body)
    with pytest.raises(ValueError, match="unexpected.*pr12/c2"):
        module.grade_run(run)


def test_round_records_question_sha256(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib
    import json

    module = load_round()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    questions = tmp_path / "eval" / "questions"
    questions.mkdir(parents=True)
    qpath = questions / "pr12.json"
    qpath.write_text(
        json.dumps({"questions": [{"id": "q2", "type": "exact", "key": "read"}]}),
        encoding="utf-8",
    )
    run = tmp_path / "run"
    answers = run / "answers" / "pr12"
    answers.mkdir(parents=True)
    (answers / "c1.json").write_text(json.dumps({"answers": [{"id": "q2", "answer": "read"}]}))
    rows = module.grade_run(run)
    want = hashlib.sha256(qpath.read_bytes()).hexdigest()
    assert rows and all(row["key_sha256"] == want for row in rows)


@pytest.mark.parametrize("recorded", [None, "0" * 64])
def test_round_rejects_missing_or_changed_recorded_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded: str | None
) -> None:
    import json

    module = load_round()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    questions = tmp_path / "eval" / "questions"
    questions.mkdir(parents=True)
    (questions / "pr12.json").write_text(
        json.dumps({"questions": [{"id": "q2", "type": "exact", "key": "read"}]})
    )
    run = tmp_path / "run"
    answers = run / "answers" / "pr12"
    answers.mkdir(parents=True)
    (answers / "c1.json").write_text(json.dumps({"answers": [{"id": "q2", "answer": "read"}]}))
    hashes = {} if recorded is None else {"pr12.json": recorded}
    (run / "question-hashes.json").write_text(json.dumps(hashes))
    with pytest.raises(ValueError, match="recorded question key.*pr12.json"):
        module.grade_run(run)


def test_round_comparison_rejects_key_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_round()
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()

    def fake(run: Path) -> list[dict[str, object]]:
        tag = "a" if Path(run).name == "before" else "b"
        return [
            {
                "pr": 12,
                "condition": "c1",
                "question": "q2",
                "key_sha256": tag * 64,
                "verdict": "correct",
            }
        ]

    monkeypatch.setattr(module, "grade_run", fake)
    with pytest.raises(ValueError, match="hash differs"):
        module.main(["grade_round.py", str(before), str(after)])
    monkeypatch.setattr(module, "grade_run", lambda run: fake(before))
    assert module.main(["grade_round.py", str(before), str(after)]) == 0


def test_single_run_reports_coverage_for_pilot_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    module = load_round()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    questions = tmp_path / "eval" / "questions"
    questions.mkdir(parents=True)
    (questions / "pr12.json").write_text(
        json.dumps(
            {
                "questions": [
                    {"id": "q1", "type": "free", "key": "facts"},
                    {"id": "q2", "type": "exact", "key": "read"},
                ]
            }
        )
    )
    run = tmp_path / "run"
    packet = run / "packets" / "pr12" / "c1"
    packet.mkdir(parents=True)
    (packet / "manifest.json").write_text("{}")
    answers = run / "answers" / "pr12"
    answers.mkdir(parents=True)
    (answers / "c1.json").write_text(
        json.dumps({"answers": [{"id": "q1", "answer": "facts"}, {"id": "q2", "answer": "read"}]})
    )
    assert module.main(["grade_round.py", str(run)]) == 0
    out = capsys.readouterr().out
    assert "packets: 1/1" in out
    assert "answers: 1 files" in out
    assert "questions: 2 rows" in out


def test_single_run_reports_coverage_without_manifests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    module = load_round()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    questions = tmp_path / "eval" / "questions"
    questions.mkdir(parents=True)
    (questions / "pr12.json").write_text(
        json.dumps({"questions": [{"id": "q2", "type": "exact", "key": "read"}]})
    )
    run = tmp_path / "run"
    answers = run / "answers" / "pr12"
    answers.mkdir(parents=True)
    (answers / "c1.json").write_text(json.dumps({"answers": [{"id": "q2", "answer": "read"}]}))
    assert module.main(["grade_round.py", str(run)]) == 0
    out = capsys.readouterr().out
    assert "packets: no manifests" in out
    assert "answers: 1 files" in out
    assert "questions: 1 rows" in out
