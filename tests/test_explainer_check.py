"""Checker port: plant.py's 10 mistakes each fail with its message; clean boards pass."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prc.explainer.check import verify_board

DATA = Path(__file__).resolve().parent / "data" / "explainer"

# (board file, map file, receipts, covered, changed, tests added) measured in the
# prototype with check.py; the port must agree exactly.
PARITY = [
    ("mdp12", "pr12", 30, 2, 3, 3),
    ("mdp14", "pr14", 20, 4, 7, 0),
    ("mdp17b", "pr17", 64, 1, 4, 7),
    ("mdp4", "pr4", 32, 2, 49, 11),
    ("mdp4high", "pr4", 52, 15, 49, 11),
    ("mdp4zoom", "pr4", 87, 14, 49, 11),
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


PLANTS = {
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
