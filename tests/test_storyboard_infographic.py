from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from prc.presentation.infographic import (
    DISCLOSURE,
    LAYOUT_REGISTRY,
    MAX_WORDS,
    PANELS_MAX_WORDS,
    allowed_words,
    brief_dict,
    content_shape,
    infobrief,
    tokenize,
)
from prc.presentation.infographic import (
    prompt as infographic_prompt,
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
                        "sub": "HTTP 404 reply",
                        "col": 0,
                        "items": [{"id": "input", "text": "404", "ground": "404"}],
                    },
                    {
                        "id": "result",
                        "title": "Explicit not-found result",
                        "sub": "handler return value",
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
            "sub": "written after the reply",
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
            "sub": "second 404 reply",
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
            "sub": "second 404 reply",
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

    layout = payload["profile"]["layout"]
    assert layout in (
        "binary-comparison",
        "linear-progression",
        "hub-spoke",
        "structural-breakdown",
    )
    for want in (
        "baoyu-infographic",
        "technical-schematic",
        "blueprint",
        layout,
        "landscape 16:9",
        "numbered header",
        "icon",
        "footer bar",
    ):
        assert want in prompt, want
    arrow_cues = {
        "binary-comparison": "Across the divider",
        "linear-progression": "Along the path",
        "hub-spoke": "Spokes:",
        "structural-breakdown": "arrow from each panel to the next",
    }
    assert arrow_cues[layout] in prompt, layout
    for line in payload["lines"]:
        assert f'"{line["text"]}"' in prompt
    if layout == "binary-comparison":
        # One arrow crosses the divider; the proof strip takes none.
        assert '"1. BEFORE" to "2. SWITCH"' in prompt
        assert '"2. SWITCH" to "3. PROOF"' not in prompt
    else:
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
        # 2026-10-19 sklearn #34386: the board footer "Start at `_get_counts`" was drawn
        # with its backticks, because a raster image cannot show a code span.
        ({"footer": ["Start at `_get_counts`"]}, "backtick"),
        ({"headline": "Faster `Counter` pass"}, "backtick"),
        (
            {"panels": [{"title": "A", "lines": ["Calls `_unique` once"]}, PANELS["panels"][1]]},
            "backtick",
        ),
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


V5_ROOT = Path("/Users/koval/dev/prc/.claude/worktrees/v3-study/artifacts/output-v5")
V5_LAYOUTS = {
    "v5-a": "linear-progression",
    "v5-b": "binary-comparison",
    "v5-c": "hub-spoke",
}


def _load_v5(sid: str) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping = json.loads((V5_ROOT / "prepared" / sid / "map.json").read_text())
    board = json.loads((V5_ROOT / "boards" / sid / "board.json").read_text())
    return mapping, board


@pytest.mark.parametrize("sid,layout", sorted(V5_LAYOUTS.items()))
def test_v5_maps_select_layouts_matching_their_shape(sid: str, layout: str) -> None:
    if not (V5_ROOT / "prepared" / sid / "map.json").is_file():
        pytest.skip("v5 fixtures absent in this checkout")
    mapping, board = _load_v5(sid)
    brief = infobrief(mapping, mapping["brief"], board)
    assert brief.mode == "panels"
    assert brief.layout == layout, content_shape(mapping, board)
    assert len(set(brief.tones)) >= 3
    payload = brief_dict(brief)
    assert payload["profile"]["layout"] == layout
    assert layout in payload["prompt"]


def test_v5_layouts_are_not_all_one() -> None:
    present = [sid for sid in V5_LAYOUTS if (V5_ROOT / "prepared" / sid / "map.json").is_file()]
    if len(present) < 2:
        pytest.skip("v5 fixtures absent in this checkout")
    seen = set()
    for sid in present:
        mapping, board = _load_v5(sid)
        seen.add(infobrief(mapping, mapping["brief"], board).layout)
    assert len(seen) > 1


def _layout_section(prompt_text: str) -> str:
    start = prompt_text.index("Layout:")
    end = prompt_text.index("Text:", start)
    return prompt_text[start:end]


LAYOUT_GEOMETRY_CUES = {
    "binary-comparison": ("divider", "strip"),
    "hub-spoke": ("hub", "spoke"),
    "linear-progression": ("path", "node"),
    "structural-breakdown": ("one row",),
}


def test_panels_layout_section_describes_registry_geometry() -> None:
    mapping, board = panels_board()
    base = infobrief(mapping, mapping["brief"], board)
    layouts = {entry["layout"] for entry in LAYOUT_REGISTRY.values()}
    assert set(LAYOUT_GEOMETRY_CUES) == layouts
    for layout, cues in LAYOUT_GEOMETRY_CUES.items():
        forced = replace(base, layout=layout)
        section = _layout_section(infographic_prompt(forced)).lower()
        for cue in cues:
            assert cue in section, layout


def test_panels_arrow_rules_match_layout_geometry() -> None:
    mapping, board = panels_board()
    base = infobrief(mapping, mapping["brief"], board)
    sections = {}
    for layout in LAYOUT_GEOMETRY_CUES:
        forced = replace(base, layout=layout)
        text = infographic_prompt(forced)
        rules = text[text.index("Rules:") :]
        sections[layout] = rules.lower()
    assert "spoke" in sections["hub-spoke"]
    assert "divider" in sections["binary-comparison"] or "strip" in sections["binary-comparison"]
    assert "path" in sections["linear-progression"]


def test_v5_prompts_have_different_layout_sections() -> None:
    missing = [sid for sid in V5_LAYOUTS if not (V5_ROOT / "prepared" / sid / "map.json").is_file()]
    if missing:
        pytest.skip("v5 fixtures absent in this checkout")
    sections = set()
    for sid in V5_LAYOUTS:
        mapping, board = _load_v5(sid)
        text = infographic_prompt(infobrief(mapping, mapping["brief"], board))
        sections.add(_layout_section(text))
    assert len(sections) == len(V5_LAYOUTS)


FOUR_PANELS: dict[str, Any] = {
    "mode": "panels",
    "headline": "Name lookup ranks prospects by similarity",
    "subtitle": "In trace_first_dm.py",
    "panels": [
        {"title": "BEFORE", "lines": ["Substring match on names"]},
        {"title": "CHANGE", "lines": ["Keep rows scoring high"]},
        {"title": "PARTS", "lines": ["Tiers name each band"]},
        {"title": "PROOF", "lines": ["Four new unit tests"]},
    ],
    "footer": ["Start at match_names"],
}


def four_panel_board() -> tuple[dict[str, Any], dict[str, Any]]:
    mapping, board = case()
    board["infographic"] = deepcopy(FOUR_PANELS)
    return mapping, board


def _arrows_line(prompt_text: str) -> str:
    for line in prompt_text.splitlines():
        if line.startswith(
            (
                "- Across the divider:",
                "- Along the path:",
                "- Spokes:",
                "- Between panels:",
            )
        ):
            return line
    raise AssertionError("prompt names no arrows line")


def sized_mapping(n_files: int, n_edges: int) -> dict[str, Any]:
    mapping, _ = case()
    mapping = deepcopy(mapping)
    mapping["brief"] = {
        "files": [
            {"path": f"src/part{k}.py", "kind": "src", "added": 1, "removed": 0}
            for k in range(n_files)
        ],
        "checks": [],
        "look_first": [],
        "mismatches": [],
    }
    mapping["edges"] = [
        {"source": f"src/part{k}.py:run", "target": f"src/part{k + 1}.py:run"}
        for k in range(n_edges)
    ]
    return mapping


@pytest.mark.parametrize(
    ("n_files", "n_edges", "layout"),
    [
        (1, 0, "binary-comparison"),
        (2, 15, "hub-spoke"),
        (5, 0, "linear-progression"),
        (4, 0, "structural-breakdown"),
    ],
)
def test_prompt_arrows_are_allowed_by_their_own_layout_geometry(
    n_files: int, n_edges: int, layout: str
) -> None:
    """Every arrow the prompt names must be drawn by that layout's geometry.

    Regression for the v5-b binary-comparison line: it named one bold arrow
    from BEFORE to CHANGE and then listed three pairs in parentheses, including
    PARTS to PROOF, on the same line that bans arrows into the proof strip.
    Each layout is reached through the real content-shape path, so the brief
    relations are the ones the fixed source builds for that geometry.
    """
    mapping = sized_mapping(n_files, n_edges)
    _, board = four_panel_board()
    brief = infobrief(mapping, mapping["brief"], board)
    assert brief.layout == layout
    assert brief.tones == ("problem", "change", "part", "proof")
    named = re.findall(r'"([^"]+)" to "([^"]+)"', _arrows_line(infographic_prompt(brief)))
    headers = [line.text for line in brief.lines if line.role == "panel"]
    assert named, layout
    if layout == "binary-comparison":
        # One arrow crosses the divider to the first right-hand panel. The
        # stacked right-hand panels and the proof strip take none.
        assert named == [(headers[0], headers[1])]
        assert all("PROOF" not in endpoint for pair in named for endpoint in pair)
    elif layout == "hub-spoke":
        hub = headers[brief.tones.index("part")]
        assert len(named) == len(headers) - 1
        assert all(hub in pair for pair in named)
    else:
        assert named == list(zip(headers, headers[1:], strict=False))
    # The prompt agrees with the brief relations the gate counts.
    assert named == [(relation.source, relation.target) for relation in brief.relations]
