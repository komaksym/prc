"""Checker port: plant.py's 10 mistakes each fail with its message; clean boards pass."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from prc.explainer.check import MAX_SECONDS, behavior_file, verify_board

DATA = Path(__file__).resolve().parent / "data" / "explainer"

# (board file, map file, receipts, covered, changed, tests added) measured in the
# prototype with check.py; the port must agree exactly. v4 added one cite per behavior
# file the prototype boards left off screen: one to mdp14, four to mdp4, one to
# mdp4high and mdp4zoom.
PARITY = [
    ("mdp12", "pr12", 30, 2, 3, 3),
    ("mdp14", "pr14", 21, 4, 7, 0),
    ("mdp17b", "pr17", 64, 1, 4, 7),
    ("mdp4", "pr4", 36, 2, 49, 11),
    ("mdp4high", "pr4", 53, 15, 49, 11),
    ("mdp4zoom", "pr4", 88, 14, 49, 11),
]


def load(board: str, map_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads((DATA / "boards" / f"{board}.json").read_text()),
        json.loads((DATA / "maps" / f"{map_name}.json").read_text()),
    )


@pytest.mark.parametrize(("board", "map_name", "receipts", "covered", "changed", "tests"), PARITY)
def test_clean_boards_match_prototype(
    board: str, map_name: str, receipts: int, covered: int, changed: int, tests: int
) -> None:
    b, m = load(board, map_name)
    facts = verify_board(b, m)

    assert facts["receipts"] == receipts
    assert facts["covered"] == covered
    assert facts["changed"] == changed
    assert facts["tests_added"] == tests


def scene(board: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(s for s in board["scenes"] if s["type"] == kind)


def phrase_cue(board: dict[str, Any]) -> dict[str, Any]:
    return next(c for s in board["scenes"] for c in s.get("cues", []) if isinstance(c["at"], str))


def say_twice(board: dict[str, Any]) -> None:
    s = next(s for s in board["scenes"] if any(isinstance(c["at"], str) for c in s.get("cues", [])))
    s["say"].append(f"Again, {next(c['at'] for c in s['cues'] if isinstance(c['at'], str))}.")


def too_many_rows(board: dict[str, Any], m: dict[str, Any]) -> None:
    s = scene(board, "diff")
    f = next(f for f in m["files"] if f["path"] == s["file"])
    refs = [
        f"-{x['old']}" if x["op"] == "-" else str(x["new"]) for h in f["hunks"] for x in h["lines"]
    ]
    s["lines"] = refs[:15]


PLANTS: dict[str, Callable[[dict[str, Any], dict[str, Any]], None]] = {
    "is not in the narration": lambda b, m: phrase_cue(b).update(at="a phrase nobody says"),
    "times in the narration": lambda b, m: say_twice(b),
    "is not a line of the diff": lambda b, m: scene(b, "diff")["lines"].append("99999"),
    "out of diff order": lambda b, m: scene(b, "diff")["lines"].reverse(),
    "but the screen fits": too_many_rows,
    "no cue says when": lambda b, m: scene(b, "diff").update(
        cues=[c for c in scene(b, "diff")["cues"] if c["do"] != "step"]
    ),
    "unknown cue 'shwo'": lambda b, m: scene(b, "groups")["cues"].append(
        {"at": 0, "do": "shwo", "ids": []}
    ),
    "types a number": lambda b, m: scene(b, "list").update(big="12"),
    "counts only the items this board picked": lambda b, m: scene(b, "list").update(big="{items}"),
    "no such id 'nobody'": lambda b, m: scene(b, "groups")["cues"].append(
        {"at": 0, "do": "fly", "from": "a", "to": "nobody"}
    ),
}


def test_clean_mdp17b_passes() -> None:
    b, m = load("mdp17b", "pr17")
    verify_board(b, m)


@pytest.mark.parametrize("want", sorted(PLANTS))
def test_planted_mistake_fails_with_its_message(want: str) -> None:
    b, m = load("mdp17b", "pr17")
    PLANTS[want](b, m)

    with pytest.raises(SystemExit) as error:
        verify_board(b, m)

    assert want in str(error.value)


@pytest.mark.parametrize("missing", ["card:0", "card:1", "l1", "l2", "cmd"])
def test_final_scene_elements_require_reveal_cues(missing: str) -> None:
    b, m = load("mdp12", "pr12")
    stats: dict[str, Any] = {
        "type": "stats",
        "say": ["Tests guard the change."],
        "cards": [
            {"value": "{tests_added}", "label": "new tests"},
            {"value": "{changed}", "label": "changed functions"},
        ],
        "cues": [
            {"at": [0, 0.0], "do": "card", "i": 0},
            {"at": [0, 0.5], "do": "card", "i": 1},
        ],
    }
    b["scenes"].insert(-1, stats)
    if missing.startswith("card:"):
        index = int(missing.split(":")[1])
        stats["cues"] = [c for c in stats["cues"] if c["i"] != index]
        message = f"card {index} needs a reveal cue"
    else:
        outro = scene(b, "outro")
        outro["cues"] = [c for c in outro["cues"] if c["do"] != missing]
        message = f"outro needs a {missing!r} cue"
    with pytest.raises(SystemExit, match=message):
        verify_board(b, m)


def tiny() -> tuple[dict[str, Any], dict[str, Any]]:
    """A one-file pull request and a groups board that cites both of its added lines."""
    path = "src/oracle.py"
    lines = ["if status == 404:", '    return "not_found"', '    log("404")']
    m: dict[str, Any] = {
        "pr": "o/r#1",
        "title": "Handle a missing reference",
        "author": "ann",
        "files": [
            {
                "path": path,
                "status": "modified",
                "added": len(lines),
                "removed": 0,
                "hunks": [
                    {
                        "lines": [
                            {"op": "+", "new": n + 1, "old": None, "text": text}
                            for n, text in enumerate(lines)
                        ]
                    }
                ],
            }
        ],
        "symbols": [],
        "edges": [],
        "tour": [],
        "brief": {
            "files": [{"path": path, "kind": "code", "added": len(lines), "removed": 0}],
            "checks": [],
            "look_first": [],
            "mismatches": [],
        },
    }
    board: dict[str, Any] = {
        "name": "tiny",
        "scenes": [
            {
                "type": "groups",
                "groups": [
                    {
                        "id": "req",
                        "title": "Request",
                        "col": 0,
                        "items": [{"id": "code", "text": "404"}],
                    },
                    {
                        "id": "res",
                        "title": "Result",
                        "col": 1,
                        "items": [
                            {"id": "name", "text": "not_found"},
                            {"id": "logged", "text": "404"},
                        ],
                    },
                ],
                "cite": [
                    {"line": path + ":1", "match": "404"},
                    {"line": path + ":2", "match": "not_found"},
                    {"line": path + ":3", "match": "404"},
                ],
                "say": ["A missing reference now returns an explicit result."],
                "cues": [],
            }
        ],
    }
    return m, board


def cue(board: dict[str, Any], **fields: Any) -> dict[str, Any]:
    board["scenes"][0]["cues"].append({"at": [0, 0.2], **fields})
    return board


def test_fly_between_different_texts_fails_and_names_the_arrow_cue() -> None:
    m, board = tiny()
    cue(board, do="fly", **{"from": "code", "to": "name"})

    with pytest.raises(SystemExit) as error:
        verify_board(board, m)

    message = str(error.value)
    assert "scene 0: fly from 'code' to 'name'" in message
    assert "'404'" in message and "'not_found'" in message
    assert 'use an "arrow" cue' in message


def test_fly_between_equal_texts_is_a_copy_and_passes() -> None:
    m, board = tiny()
    cue(board, do="fly", **{"from": "code", "to": "logged"})

    verify_board(board, m)


@pytest.mark.parametrize(
    "ends", [("code", "name"), ("req", "res"), ("code", "res")], ids=["items", "groups", "mixed"]
)
def test_arrow_between_different_boxes_passes(ends: tuple[str, str]) -> None:
    m, board = tiny()
    cue(
        board,
        do="arrow",
        label="becomes the name",
        until=[0, 0.9],
        **dict(zip(("from", "to"), ends, strict=True)),
    )

    verify_board(board, m)


@pytest.mark.parametrize(
    ("fields", "want"),
    [
        ({"from": "code"}, "arrow cue needs 'from' and 'to'"),
        ({"from": "code", "to": "nobody"}, "no such id 'nobody'"),
        ({"from": "code", "to": "code"}, "arrow cue joins 'code' to itself"),
        ({"from": "code", "to": "name", "label": "x" * 30}, "arrow label"),
        ({"from": "code", "to": "name", "label": 7}, "arrow label"),
    ],
)
def test_bad_arrow_cue_fails_with_its_message(fields: dict[str, Any], want: str) -> None:
    m, board = tiny()
    cue(board, do="arrow", **fields)

    with pytest.raises(SystemExit) as error:
        verify_board(board, m)

    assert want in str(error.value)


def narrate(*say: Any) -> str:
    """The checker's message for a tiny board that narrates these sentences."""
    m, board = tiny()
    board["scenes"][0]["say"] = list(say)
    with pytest.raises(SystemExit) as error:
        verify_board(board, m)
    return str(error.value)


LONG_INSTRUCTION = (
    "Start at the date helper in `report.py` and read each branch that turns "
    "a missing value into the plain word unknown."
)
LONG_DESCRIPTION = (
    "The date helper in `report.py` now reads each stored row and turns every "
    "missing value into the word unknown before the report prints it on screen."
)


def test_instruction_over_twenty_words_fails_with_the_rule() -> None:
    message = narrate(LONG_INSTRUCTION)

    assert f"scene 0: {LONG_INSTRUCTION!r} is an instruction of 21 words" in message
    assert "ASD-STE100 allows 20" in message


def test_description_over_twenty_five_words_fails_with_the_rule() -> None:
    message = narrate(LONG_DESCRIPTION)

    assert f"scene 0: {LONG_DESCRIPTION!r} is a description of 26 words" in message
    assert "ASD-STE100 allows 25" in message


@pytest.mark.parametrize(
    ("sentence", "phrase"),
    [
        ("The result is returned by the handler.", "is returned"),
        ("The name is shown in the report.", "is shown"),
        ("The stale row gets dropped at the end.", "gets dropped"),
        ("The old value is not used again.", "is not used"),
        ("Both rows were written by one call.", "were written"),
    ],
)
def test_passive_voice_fails_with_the_phrase(sentence: str, phrase: str) -> None:
    message = narrate(sentence)

    assert f"scene 0: {sentence!r} uses the passive {phrase!r}" in message
    assert "active voice" in message


def test_two_sentences_in_one_say_string_fail() -> None:
    two = "The handler returns a name. The log keeps the number."
    message = narrate(two)

    assert f"scene 0: {two!r} holds 2 sentences" in message
    assert "one statement per sentence" in message


def test_short_active_sentences_pass() -> None:
    m, board = tiny()
    board["scenes"][0]["say"] = [
        "A missing reference now returns the name `not_found` from `oracle.py`.",
        {"show": "The log keeps the number 404 for that request.", "speak": "The log keeps 404."},
        "The date helper reads each stored row and turns a missing value into unknown text.",
        "Start at the status check in the handler.",
    ]

    verify_board(board, m)


@pytest.mark.parametrize(
    ("path", "behavior"),
    [
        ("src/app/handler.py", True),
        ("web/src/page.tsx", True),
        ("scripts/release.sh", True),
        ("db/migrations/001_init.sql", True),
        (".github/workflows/ci.yml", True),
        (".gitlab-ci.yml", True),
        ("pyproject.toml", True),
        ("config/settings.yaml", True),
        ("setup.cfg", True),
        ("tox.ini", True),
        (".env.example", True),
        ("Dockerfile", True),
        ("Makefile", True),
        ("package.json", True),
        ("tsconfig.json", True),
        ("tests/test_handler.py", False),
        ("src/app/test_handler.py", False),
        ("pkg/handler_test.go", False),
        ("web/src/page.test.tsx", False),
        ("uv.lock", False),
        ("poetry.lock", False),
        ("package-lock.json", False),
        ("pnpm-lock.yaml", False),
        ("yarn.lock", False),
        ("docs/assets/diagram.png", False),
        ("report.pdf", False),
        ("static/app.min.js", False),
        ("dist/bundle.js", False),
        ("build/lib/app.py", False),
        ("artifacts/run/result.json", False),
        ("reports/coverage.yml", False),
        ("data/evidence.json", False),
        ("README.md", False),
        ("docs/guide.txt", False),
    ],
)
def test_behavior_file_is_code_ci_or_config(path: str, behavior: bool) -> None:
    assert behavior_file(path) is behavior


EXTRA = {
    ".github/workflows/ci.yml": ("run: uv run pytest -q", "modified"),
    "pyproject.toml": ('requires-python = ">=3.12"', "modified"),
    "uv.lock": ('version = "1.2.3"', "modified"),
    "tests/test_oracle.py": ("def test_missing():", "added"),
    "docs/oracle.md": ("Missing references return not_found.", "added"),
    "artifacts/run.json": ('{"ok": true}', "added"),
    "src/old.py": ("def gone():", "deleted"),
}


def wide() -> tuple[dict[str, Any], dict[str, Any]]:
    """The tiny pull request plus CI, config, lock, test, doc, evidence and deleted files."""
    m, board = tiny()
    for path, (text, status) in EXTRA.items():
        op, new, old = ("-", None, 1) if status == "deleted" else ("+", 1, None)
        m["files"].append(
            {
                "path": path,
                "status": status,
                "added": 0 if status == "deleted" else 1,
                "removed": 1 if status == "deleted" else 0,
                "hunks": [{"lines": [{"op": op, "new": new, "old": old, "text": text}]}],
            }
        )
        kind = "test" if path.startswith("tests/") else "code"
        m["brief"]["files"].append({"path": path, "kind": kind, "added": 1, "removed": 0})
    return m, board


def test_behavior_files_on_no_scene_fail_and_are_listed() -> None:
    m, board = wide()

    with pytest.raises(SystemExit) as error:
        verify_board(board, m)

    message = str(error.value)
    assert "behavior files on no scene: .github/workflows/ci.yml, pyproject.toml" in message
    for skipped in ("uv.lock", "tests/test_oracle.py", "docs/oracle.md", "artifacts/run.json"):
        assert skipped not in message
    assert "src/old.py" not in message


def show_by(board: dict[str, Any], how: str, path: str) -> None:
    ref, text = path + ":1", EXTRA[path][0]
    says = {"say": ["The pull request also changes this file."]}
    if how == "cite":
        board["scenes"][0]["cite"].append({"line": ref, "match": text})
    elif how == "diff":
        board["scenes"].append(
            {"type": "diff", "file": path, "lines": [{"ref": "1", "step": 0}], **says, "cues": []}
        )
    elif how == "list":
        items = [{"text": text, "cite": ref}]
        cues = [{"at": [0, 0.1], "do": "items"}]
        board["scenes"].append(
            {"type": "list", "label": "Lines", "items": items, **says, "cues": cues}
        )
    else:
        rows = [{"line": ref, "text": text}]
        cues = [{"at": [0, 0.1], "do": "rows"}]
        board["scenes"].append({"type": "receipt", "rows": rows, **says, "cues": cues})


@pytest.mark.parametrize("how", ["cite", "diff", "list", "receipt"])
def test_each_scene_kind_can_show_a_behavior_file(how: str) -> None:
    m, board = wide()
    show_by(board, how, ".github/workflows/ci.yml")
    show_by(board, "cite", "pyproject.toml")

    verify_board(board, m)


def test_board_over_the_time_limit_fails() -> None:
    m, board = tiny()
    board["scenes"][0]["hold"] = MAX_SECONDS

    with pytest.raises(SystemExit) as error:
        verify_board(board, m)

    assert f"over the {MAX_SECONDS} s limit" in str(error.value)
    board["scenes"][0]["hold"] = MAX_SECONDS - 10
    verify_board(board, m)
