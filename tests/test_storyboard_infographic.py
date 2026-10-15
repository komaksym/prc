from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from prc.presentation.infographic import (
    DISCLOSURE,
    MAX_WORDS,
    PANELS_MAX_WORDS,
    allowed_words,
    brief_dict,
    infobrief,
    tokenize,
)


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
                "cues": [{"at": [0, 0], "do": "arrow", "from": "input", "to": "output"}],
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


def test_arrow_to_a_group_and_a_same_text_fly_both_map_to_story_flows() -> None:
    mapping, board = case()
    scene = board["scenes"][0]
    scene["groups"].append(
        {
            "id": "log",
            "title": "Log entry",
            "col": 2,
            "items": [{"id": "logged", "text": "404", "ground": "404"}],
        }
    )
    scene["cues"] = [
        {"at": [0, 0], "do": "arrow", "from": "request", "to": "result", "label": "returns"},
        {"at": [0, 0.5], "do": "fly", "from": "input", "to": "logged"},
    ]
    brief = infobrief(mapping, mapping["brief"], board)
    assert [(r.source, r.target, r.kind) for r in brief.relations] == [
        ("Missing reference", "Explicit not-found result", "flow"),
        ("Missing reference", "Log entry", "flow"),
    ]


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
    scene["cues"].append({"at": [0, 0.5], "do": "arrow", "from": "third_input", "to": "output"})
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


PANELS: dict[str, Any] = {
    "mode": "panels",
    "headline": "Missing references get an explicit result",
    "subtitle": "One status check in the handler",
    "panels": [
        {"title": "BEFORE", "lines": ["404 had no name", "Callers guessed the meaning"]},
        {"title": "SWITCH", "lines": ["Handler checks the status", "Returns not_found"]},
        {"title": "PROOF", "lines": ["One test covers 404"]},
    ],
    "footer": ["tests/oracle.py", "Start at the status check"],
}


def panels_board(**change: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping, board = case()
    board["infographic"] = deepcopy(PANELS) | change
    return mapping, board


def test_panels_brief_permits_exactly_the_authored_lines() -> None:
    mapping, board = panels_board()
    brief = infobrief(mapping, mapping["brief"], board)

    assert brief.mode == "panels"
    assert brief.title == PANELS["headline"]
    assert [(line.role, line.text) for line in brief.lines] == [
        ("headline", "Missing references get an explicit result"),
        ("subtitle", "One status check in the handler"),
        ("panel", "1. BEFORE"),
        ("item", "404 had no name"),
        ("item", "Callers guessed the meaning"),
        ("panel", "2. SWITCH"),
        ("item", "Handler checks the status"),
        ("item", "Returns not_found"),
        ("panel", "3. PROOF"),
        ("item", "One test covers 404"),
        ("footer", "tests/oracle.py"),
        ("footer", "Start at the status check"),
        ("legend", "Problem"),
        ("legend", "Change"),
        ("legend", "Proof"),
        ("note", DISCLOSURE),
    ]
    assert brief.tones == ("problem", "change", "proof")
    assert [(r.source, r.target) for r in brief.relations] == [
        ("1. BEFORE", "2. SWITCH"),
        ("2. SWITCH", "3. PROOF"),
    ]
    assert "explicit" in allowed_words(brief) and "handle" not in allowed_words(brief)


def test_panels_carry_one_meaning_color_each_and_a_key() -> None:
    """The v4-a review: two colors made a dull picture. Each panel takes its meaning color."""
    mapping, board = panels_board()
    board["infographic"]["panels"][1]["tone"] = "part"
    payload = brief_dict(infobrief(mapping, mapping["brief"], board))
    prompt = payload["prompt"]

    assert payload["tones"] == ["problem", "part", "proof"]
    assert '"1. BEFORE" (color: vermillion #D55E00' in prompt
    assert '"2. SWITCH" (color: sky blue #56B4E9' in prompt
    assert '"3. PROOF" (color: bluish green #009E73' in prompt
    assert 'Key: "Part" beside the sky blue #56B4E9 swatch' in prompt
    assert "Change" not in [ln["text"] for ln in payload["lines"]]
    board["infographic"]["panels"][1]["tone"] = "purple"
    with pytest.raises(ValueError, match="tone 'purple' is not one of"):
        infobrief(mapping, mapping["brief"], board)


def test_panels_prompt_asks_for_a_baoyu_blueprint_with_only_the_lines() -> None:
    mapping, board = panels_board()
    payload = brief_dict(infobrief(mapping, mapping["brief"], board))
    prompt = payload["prompt"]

    for want in (
        "baoyu-infographic",
        "technical-schematic",
        "blueprint",
        "structural-breakdown",
        "landscape 16:9",
        "numbered header",
        "icon",
        "footer bar",
        "arrow from each panel to the next",
    ):
        assert want in prompt, want
    for line in payload["lines"]:
        assert f'"{line["text"]}"' in prompt
    assert '"1. BEFORE" to "2. SWITCH"' in prompt and '"2. SWITCH" to "3. PROOF"' in prompt
    assert mapping["title"] not in prompt
    assert payload["mode"] == "panels"


def test_storyboard_flow_brief_keeps_its_mode_and_gets_a_prompt() -> None:
    mapping, board = case()
    payload = brief_dict(infobrief(mapping, mapping["brief"], board))

    assert payload["mode"] == "storyboard-flow"
    assert '"Missing reference"' in payload["prompt"]


def test_panels_words_fit_the_raised_cap() -> None:
    lines = ["one two three four five six"] * 3
    panels = [{"title": f"Step {k}", "lines": lines} for k in range(3)]
    mapping, board = panels_board(panels=panels, footer=["one two three"])
    brief = infobrief(mapping, mapping["brief"], board)

    words = sum(len(tokenize(line.text)) for line in brief.lines)
    assert MAX_WORDS < words <= PANELS_MAX_WORDS
    assert [line.text for line in brief.lines].count("one two three four five six") == 9


@pytest.mark.parametrize(
    ("change", "want"),
    [
        ({"panels": PANELS["panels"][:1]}, "2 to 4 panels"),
        ({"panels": PANELS["panels"] * 2}, "2 to 4 panels"),
        ({"panels": [{"title": "A", "lines": []}, PANELS["panels"][1]]}, "1 to 4 lines"),
        ({"panels": [{"title": "A", "lines": ["x"] * 5}, PANELS["panels"][1]]}, "1 to 4 lines"),
        (
            {"panels": [{"title": "A", "lines": ["one two three four five six seven"]}] * 2},
            "at most 6 words",
        ),
        ({"footer": ["a", "b", "c", "d"]}, "0 to 3 footer"),
        ({"headline": ""}, "headline"),
        ({"panels": [PANELS["panels"][0], PANELS["panels"][0]]}, "unique panel titles"),
        (
            {
                "panels": [
                    {"title": f"Step {k}", "lines": ["one two three four five six"] * 4}
                    for k in range(4)
                ]
            },
            f"at most {PANELS_MAX_WORDS} words",
        ),
    ],
)
def test_bad_panels_fail_before_drawing(change: dict[str, Any], want: str) -> None:
    mapping, board = panels_board(**change)

    with pytest.raises(ValueError, match=want):
        infobrief(mapping, mapping["brief"], board)
