"""Trust-render regressions: D7 line coverage, D9 join parity, D10 notes, D11 fine, D12 estimate, D13 guide."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

DATA = Path(__file__).resolve().parent / "data" / "explainer"
ACCEPT = (
    Path(__file__).resolve().parent.parent
    / "artifacts"
    / "trustworthiness"
    / "2026-10-09"
    / "acceptance"
)
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    "/Users/koval/dev/prc/artifacts/release/browser-cache",
)


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


def test_check_outro_fine_defaults_empty() -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.render import fill

    m = tiny_map()
    b = tiny_board(["2", "3", "4"], fine=None)
    facts = verify_board(b, m)
    assert b["scenes"][-1]["fine"] == "", b["scenes"][-1]
    fill(b, m, facts)
    assert b["scenes"][-1]["fine"] == "", b["scenes"][-1]


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


def test_highlight_hunk_fallback_survives_trailing_blank_lines() -> None:
    from prc.explainer.highlight import attach_tokens

    hunks = [
        {
            "old_start": 18,
            "new_start": 18,
            "lines": [
                {"op": " ", "old": 18, "new": 18, "text": "    released: list[int],"},
                {"op": "+", "old": None, "new": 21, "text": "    ordered = list(released)"},
                {"op": "+", "old": None, "new": 22, "text": ""},
                {"op": " ", "old": 19, "new": 23, "text": ""},
                {"op": " ", "old": 20, "new": 24, "text": ""},
            ],
        }
    ]
    rows = [
        {"ref": "18", "op": " ", "num": 18},
        {"ref": "21", "op": "+", "num": 21},
        {"ref": "22", "op": "+", "num": 22},
        {"ref": "23", "op": " ", "num": 23},
        {"ref": "24", "op": " ", "num": 24},
    ]
    attach_tokens(rows, "a.py", 4, None, "h" * 40, "b" * 40, hunks)
    by_ref = {r["ref"]: r for r in rows}
    assert by_ref["22"]["tokens"] == [], by_ref["22"]
    assert by_ref["23"]["tokens"] == [], by_ref["23"]
    assert "".join(t["text"] for t in by_ref["21"]["tokens"]) == ("ordered = list(released)"), (
        by_ref["21"]
    )


def test_keys_only_check_tools_skip_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    from prc.explainer import render as explain_render

    real_which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda name: None if name in ("ffmpeg", "ffprobe") else real_which(name)
    )
    explain_render.check_tools(need_video=False)
    with pytest.raises(explain_render.RenderError, match="ffmpeg"):
        explain_render.check_tools(need_video=True)


def test_preview_keys_only_writes_stills_without_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    real_which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda name: None if name in ("ffmpeg", "ffprobe") else real_which(name)
    )
    m = tiny_map()
    b = tiny_board(["2", "3", "4"])
    facts = verify_board(b, m)
    rendered = render(b, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    assert rendered.frames > 0
    assert sorted(p.name for p in (tmp_path / "keys").glob("*.png")) == [
        "00a.png",
        "00b.png",
        "01a.png",
        "01b.png",
    ]
    assert not (tmp_path / "video.mp4").exists()
    assert not (tmp_path / "narration.wav").exists()


def test_preview_em5756_note_is_not_flagged_as_overlap(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m = json.loads((ACCEPT / "em-5756" / "map.json").read_text())
    b = json.loads((ACCEPT / "em-5756" / "board.json").read_text())
    facts = verify_board(b, m)
    rendered = render(b, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    assert not [w for w in rendered.layout_warnings if "overlaps code" in w], (
        rendered.layout_warnings
    )


def long_map() -> dict[str, Any]:
    lines = [{"op": " ", "old": 1, "new": 1, "text": "def f():"}]
    for n in range(2, 8):
        lines.append({"op": "+", "old": None, "new": n, "text": "    v = (" + "q" * 56 + ")"})
    m = tiny_map()
    m["files"][0]["hunks"] = [{"old_start": 1, "new_start": 1, "lines": lines}]
    m["brief"]["files"][0]["added"] = 6
    return m


def stacked_notes_board() -> dict[str, Any]:
    cues: list[dict[str, Any]] = [{"at": [0, 0.1], "do": "step", "n": 1}]
    for k in range(4):
        cues.append(
            {
                "at": [0, 0.2 + 0.1 * k],
                "do": "note",
                "line": "2",
                "text": "note number " + str(k) + " explains the value here",
            }
        )
    return {
        "name": "stacked",
        "scenes": [
            {
                "type": "diff",
                "file": "a.py",
                "label": "change",
                "lines": ["2", "3", "4", "5", "6", "7"],
                "say": ["The change adds six values."],
                "cues": cues,
            },
            {
                "type": "outro",
                "l1": "Change adds six values.",
                "l2": "Start at f in a.py.",
                "fine": "small print",
                "say": ["Change adds six values."],
                "cues": [
                    {"at": [0, 0.0], "do": "l1"},
                    {"at": [0, 0.5], "do": "l2"},
                    {"at": [0, 0.9], "do": "cmd"},
                ],
            },
        ],
    }


def test_stacked_clamped_notes_still_flag_overlap(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m = long_map()
    b = stacked_notes_board()
    facts = verify_board(b, m)
    assert facts.get("note_risks"), "four long notes on one row must warn in check"
    rendered = render(b, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    assert any("overlaps code" in w for w in rendered.layout_warnings), rendered.layout_warnings


def test_late_numeric_cue_rejected_in_check() -> None:
    from prc.explainer.check import verify_board

    m = tiny_map()
    b = tiny_board(["2", {"ref": "3", "step": 1}, "4"])
    b["scenes"][0]["cues"] = [{"at": 999, "do": "step", "n": 1}]
    with pytest.raises(SystemExit) as err:
        verify_board(b, m)
    assert "999" in str(err.value) and "end" in str(err.value).lower(), err.value


def test_stamped_cues_validated_after_fit(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import check_stamped_cues, fit_sentences
    from prc.explainer.voice import NoneBackend

    m = tiny_map()
    b = tiny_board(["2", "3", "4"])
    verify_board(b, m)
    fit_sentences(b, NoneBackend(), tmp_path, [])
    assert check_stamped_cues(b) == []
    b["scenes"][0]["cues"][0]["t"] = b["scenes"][0]["end"] + 10.0
    problems = check_stamped_cues(b)
    assert problems and "never show" in problems[0], problems


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
    assert "60 without diff references" in text, text
    assert "opaque or oversize" not in text, text
