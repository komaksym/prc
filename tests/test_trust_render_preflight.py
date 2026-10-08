"""Trust-render regressions: D7 line coverage, D9 join parity, D10 notes, D11 fine, D12 estimate, D13 guide."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent / "data" / "explainer"


def tiny_map() -> dict[str, Any]:
    lines = [
        {"op": " ", "old": 1, "new": 1, "text": "def a():"},
        {"op": "+", "old": None, "new": 2, "text": "    x = 1"},
        {"op": "+", "old": None, "new": 3, "text": "    y = 2"},
        {"op": "+", "old": None, "new": 4, "text": "    return x + y"},
    ]
    return {
        "pr": "o/r#1",
        "title": "t",
        "author": "a",
        "base_sha": "b" * 40,
        "head_sha": "h" * 40,
        "url": None,
        "brief": {
            "files": [{"path": "a.py", "kind": "code", "added": 3, "removed": 0}],
            "checks": [],
        },
        "files": [
            {
                "path": "a.py",
                "kind": "code",
                "added": 3,
                "removed": 0,
                "hunks": [{"old_start": 1, "new_start": 1, "lines": lines}],
            }
        ],
        "symbols": [
            {
                "id": "a",
                "path": "a.py",
                "qualname": "a",
                "status": "added",
                "span": [1, 4],
                "base_span": None,
            }
        ],
        "edges": [],
        "tour": [],
    }


def tiny_board(diff_lines: list[Any], *, fine: str | None = "fine print") -> dict[str, Any]:
    outro: dict[str, Any] = {
        "type": "outro",
        "l1": "Change adds two values.",
        "l2": "Start at a in a.py.",
        "say": ["Change adds two values."],
        "cues": [
            {"at": [0, 0.0], "do": "l1"},
            {"at": [0, 0.5], "do": "l2"},
            {"at": [0, 0.9], "do": "cmd"},
        ],
    }
    if fine is not None:
        outro["fine"] = fine
    return {
        "name": "tiny",
        "scenes": [
            {
                "type": "diff",
                "file": "a.py",
                "label": "change",
                "lines": diff_lines,
                "say": ["The change adds values."],
                "cues": [{"at": [0, 0.1], "do": "step", "n": 1}],
            },
            outro,
        ],
    }


def test_line_coverage_counts_changed_lines_not_files() -> None:
    from prc.explainer.preflight import line_coverage

    m = tiny_map()
    b = tiny_board(["2"])
    cov = line_coverage(b, m)
    assert cov["total"] == 3, cov
    assert cov["shown"] == 1, cov
    assert len(cov["missing"]) == 2, cov


def test_board_coverage_and_doc_agree_on_missing_lines() -> None:
    from prc.explainer import boards
    from prc.explainer.doc import uncovered

    m = tiny_map()
    b = tiny_board(["2"])
    text = boards.coverage(b, m)
    assert "1/3" in text, text
    files, syms = uncovered(b, m)
    assert files == [] and syms == [], (files, syms)
    from prc.explainer.preflight import line_coverage

    cov = line_coverage(b, m)
    assert cov["missing"], "partial board must list missing changed lines"


def test_check_rejects_blank_changed_line_like_render() -> None:
    import pytest

    from prc.explainer.check import verify_board

    m = tiny_map()
    m["files"][0]["hunks"][0]["lines"].insert(2, {"op": "+", "old": None, "new": 5, "text": ""})
    b = tiny_board(["2", "5"])
    with pytest.raises(SystemExit) as err:
        verify_board(b, m)
    assert "blank" in str(err.value).lower() or "cut" in str(err.value).lower(), err.value


def test_check_requires_outro_fine() -> None:
    import pytest

    from prc.explainer.check import verify_board

    m = tiny_map()
    b = tiny_board(["2", "3", "4"], fine=None)
    with pytest.raises(SystemExit) as err:
        verify_board(b, m)
    assert "fine" in str(err.value).lower(), err.value


def test_verify_board_reports_trustworthy_silent_estimate() -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import predict
    from prc.explainer.voice import NoneBackend

    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    b = json.loads((DATA / "boards" / "mdp12.json").read_text())
    facts = verify_board(b, m)
    assert "estimate_none_seconds" in facts, sorted(facts)
    assert facts["estimate_none_seconds"] == predict(b, NoneBackend())


def test_note_overlap_risk_is_flagged_not_silent() -> None:
    from prc.explainer.check import verify_board

    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    b = json.loads((DATA / "boards" / "mdp12.json").read_text())
    facts = verify_board(b, m)
    risks = facts.get("note_risks", [])
    assert risks, "mdp12 scene 3 clamps its note over line 1031; check must flag it"
    assert "1031" in risks[0] and "overlap" in risks[0].lower(), risks


def test_fitting_note_stays_silent() -> None:
    from prc.explainer.check import verify_board

    m = tiny_map()
    b = tiny_board(["2", "3", "4"])
    b["scenes"][0]["cues"] = [
        {"at": [0, 0.1], "do": "step", "n": 1},
        {"at": [0, 0.5], "do": "note", "line": "2", "text": "short"},
    ]
    facts = verify_board(b, m)
    assert facts.get("note_risks") == [], facts.get("note_risks")


def test_guide_names_installed_commands_and_preview() -> None:
    from prc.explainer.boards import guide

    text = guide()
    assert "prc board check" in text, text[:800]
    assert "prc board preview" in text, text[:800]
    assert "python3 show.py" not in text
    assert "Read tool" not in text


def test_board_preview_command_exists() -> None:
    from prc.cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["board", "preview", "b.json", "--map", "m.json"])
    assert ns.board_command == "preview"


def opaque_map() -> dict[str, Any]:
    m = tiny_map()
    m["files"].append(
        {
            "path": "yarn.lock",
            "kind": "opaque",
            "added": 50,
            "removed": 10,
            "hunks": [],
        }
    )
    return m


def test_refless_lines_produce_honest_partial_coverage() -> None:
    from prc.explainer import boards
    from prc.explainer.preflight import line_coverage

    m = opaque_map()
    b = tiny_board(["2"])
    cov = line_coverage(b, m)
    assert cov["total"] == 63, cov
    assert cov["known"] == 3, cov
    assert cov["shown"] == 1, cov
    assert cov["unavailable"] == 60, cov
    assert len(cov["missing"]) == 2, cov
    text = boards.coverage(b, m)
    assert "1/63" in text, text
    assert "60" in text and "refs" in text, text
