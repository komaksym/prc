from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from prc.presentation.infographic import infobrief


def case() -> tuple[dict[str, Any], dict[str, Any]]:
    path = "tests/oracle.py"
    mapping = {
        "pr": "o/r#1",
        "title": "Handle a missing reference",
        "author": "ann",
        "files": [
            {
                "path": path,
                "status": "modified",
                "added": 2,
                "removed": 0,
                "hunks": [
                    {
                        "lines": [
                            {"op": "+", "new": 1, "old": None, "text": "if status == 404:"},
                            {"op": "+", "new": 2, "old": None, "text": '    return "not_found"'},
                        ]
                    }
                ],
            }
        ],
        "symbols": [],
        "edges": [],
        "tour": [],
        "brief": {
            "files": [{"path": path, "kind": "test", "added": 2, "removed": 0}],
            "checks": [],
            "look_first": [],
            "mismatches": [],
        },
    }
    board = {
        "name": "oracle",
        "infographic": {"scene": 0, "mode": "storyboard-flow"},
        "scenes": [
            {
                "type": "groups",
                "groups": [
                    {
                        "id": "request",
                        "title": "Missing reference",
                        "col": 0,
                        "items": [{"id": "input", "text": "404", "ground": "404"}],
                    },
                    {
                        "id": "result",
                        "title": "Explicit not-found result",
                        "col": 1,
                        "items": [{"id": "output", "text": "not_found", "ground": "not_found"}],
                    },
                ],
                "cite": [
                    {"line": path + ":1", "match": "404"},
                    {"line": path + ":2", "match": "not_found"},
                ],
                "say": ["A missing reference returns an explicit result."],
                "cues": [{"at": [0, 0], "do": "fly", "from": "input", "to": "output"}],
            }
        ],
    }
    return mapping, board


def test_test_only_pr_has_a_cited_high_level_story_flow() -> None:
    mapping, board = case()
    original = deepcopy(board)
    brief = infobrief(mapping, mapping["brief"], board)
    assert [(r.source, r.target, r.kind) for r in brief.relations] == [
        ("Missing reference", "Explicit not-found result", "flow")
    ]
    assert [line.text for line in brief.lines if line.role == "node"] == [
        "Missing reference",
        "Explicit not-found result",
    ]
    assert "Arrows show the cited storyboard flow" in [line.text for line in brief.lines]
    assert not any(line.role == "row" for line in brief.lines)
    assert board == original


@pytest.mark.parametrize("fault", ["uncited", "endpoint", "same_group", "no_flow", "scene", "mode"])
def test_invalid_story_flow_fails_before_drawing(fault: str) -> None:
    mapping, board = case()
    scene = board["scenes"][0]
    if fault == "uncited":
        scene["cite"][0]["match"] = "invented"
    elif fault == "endpoint":
        scene["cues"][0]["to"] = "invented"
    elif fault == "same_group":
        scene["cues"][0]["to"] = "input"
    elif fault == "no_flow":
        scene["cues"] = []
    elif fault == "scene":
        board["infographic"]["scene"] = 5
    else:
        board["infographic"]["mode"] = "invented"
    with pytest.raises((ValueError, SystemExit)):
        infobrief(mapping, mapping["brief"], board)


def test_duplicate_item_id_cannot_change_a_flow_endpoint() -> None:
    mapping, board = case()
    board["scenes"][0]["groups"].append(
        {
            "id": "third",
            "title": "Another branch",
            "col": 2,
            "items": [{"id": "input", "text": "404", "ground": "404"}],
        }
    )
    with pytest.raises(ValueError, match="unique item IDs"):
        infobrief(mapping, mapping["brief"], board)


def test_headline_collision_cannot_silently_erase_selected_flow() -> None:
    mapping, board = case()
    mapping["title"] = "Missing reference"
    with pytest.raises(ValueError, match="headline"):
        infobrief(mapping, mapping["brief"], board)


@pytest.mark.parametrize("title", ["Missing reference", "MISSING reference."])
def test_duplicate_group_titles_cannot_merge_distinct_endpoints(title: str) -> None:
    mapping, board = case()
    scene = board["scenes"][0]
    scene["groups"].append(
        {
            "id": "third",
            "title": title,
            "col": 2,
            "items": [{"id": "third_input", "text": "404", "ground": "404"}],
        }
    )
    scene["cues"].append({"at": [0, 0.5], "do": "fly", "from": "third_input", "to": "output"})
    with pytest.raises(ValueError, match="unique group titles"):
        infobrief(mapping, mapping["brief"], board)


@pytest.mark.parametrize("title", ["Missing reference.", "MISSING reference"])
def test_headline_collision_uses_the_gate_text_normalization(title: str) -> None:
    mapping, board = case()
    mapping["title"] = title
    with pytest.raises(ValueError, match="headline"):
        infobrief(mapping, mapping["brief"], board)


def test_truncated_headline_cannot_become_a_group_title() -> None:
    mapping, board = case()
    title = "Reference " + "response " * 9
    mapping["title"] = title + "tail words past the line limit"
    board["scenes"][0]["groups"][0]["title"] = title.strip()
    with pytest.raises(ValueError, match="headline"):
        infobrief(mapping, mapping["brief"], board)
