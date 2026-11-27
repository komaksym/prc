"""v6 regressions: every box explained, callouts off the code, drawer, tip, speech."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

DATA = Path(__file__).resolve().parent / "data" / "explainer"


def _tiny() -> tuple[dict[str, Any], dict[str, Any]]:
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
                "added": 3,
                "removed": 0,
                "hunks": [
                    {
                        "lines": [
                            {"op": "+", "new": n + 1, "old": None, "text": t}
                            for n, t in enumerate(lines)
                        ]
                    }
                ],
            }
        ],
        "symbols": [],
        "edges": [],
        "tour": [],
        "brief": {
            "files": [{"path": path, "kind": "code", "added": 3, "removed": 0}],
            "checks": [],
            "look_first": [],
            "mismatches": [],
        },
    }
    s = {
        "type": "groups",
        "groups": [
            {
                "id": "g0",
                "title": "Source",
                "sub": "before the run",
                "col": 0,
                "row": True,
                "items": [{"id": "a0", "text": "404"}],
            },
            {
                "id": "g1",
                "title": "Target",
                "sub": "before the run",
                "col": 1,
                "row": True,
                "items": [{"id": "a1", "text": "not_found"}],
            },
        ],
        "cite": [
            {"line": path + ":1", "match": "404"},
            {"line": path + ":2", "match": "not_found"},
        ],
        "say": ["A missing code now returns a named result."],
        "cues": [],
    }
    board: dict[str, Any] = {
        "scenes": [{"type": "title", "say": ["A change lands."], "cues": []}, s]
    }
    return m, board


def test_group_without_caption_fails() -> None:
    from prc.explainer.check import verify_board

    m, board = _tiny()
    del board["scenes"][1]["groups"][0]["sub"]
    with pytest.raises(SystemExit) as e:
        verify_board(board, m)
    assert "needs a caption" in str(e.value)


def test_slot_without_fill_label_fails() -> None:
    from prc.explainer.check import verify_board

    m, board = _tiny()
    board["scenes"][1]["groups"][1]["items"][0] = {
        "id": "a1",
        "text": "not_found",
        "kind": "slot",
        "label": "",
    }
    del board["scenes"][1]["groups"][1]["items"][0]["label"]
    with pytest.raises(SystemExit) as e:
        verify_board(board, m)
    assert "needs a label" in str(e.value)


def test_count_label_must_match_drawn() -> None:
    from prc.explainer.check import verify_board

    m, board = _tiny()
    s = board["scenes"][1]
    s["groups"][0]["items"] = [{"id": "c1", "text": "Fetched rows: 4"}]
    s["cite"] = [
        {"line": "src/oracle.py:1", "match": "Fetched rows: 4"},
        {"line": "src/oracle.py:2", "match": "not_found"},
    ]
    # ground the count text on the cited line by extending the match text
    m["files"][0]["hunks"][0]["lines"][0]["text"] = "Fetched rows: 4 and 404"
    s["cues"] = [{"at": [0, 0.2], "do": "arrow", "from": "c1", "to": "g1", "label": "six counts"}]
    with pytest.raises(SystemExit) as e:
        verify_board(board, m)
    assert "draw all 6 or drop the number" in str(e.value)
    s["cues"][0]["label"] = "counts"
    verify_board(board, m)


def test_identifier_speaks_as_one_unit_without_pause() -> None:
    from prc.explainer.speech import say_token

    assert say_token("match_names") == "match names"
    assert say_token("trace_first_dm") == "trace first dm"
    assert say_token("google_doc_report") == "google doc report"
    assert "," not in say_token("match_names")
    assert say_token("ErrNotExist") == "error, not exist"


def test_identifier_gap_check_uses_word_timestamps() -> None:
    from prc.explainer.listen import IDENT_GAP_MAX, check_identifier_gaps

    assert abs(IDENT_GAP_MAX - 0.15) < 1e-9
    board = {"scenes": [{"say": ["Check match_names now"]}]}
    tight = [
        {"word": "check", "start": 0.0, "end": 0.2},
        {"word": "match", "start": 0.3, "end": 0.4},
        {"word": "names", "start": 0.45, "end": 0.6},
        {"word": "now", "start": 0.7, "end": 0.8},
    ]
    assert check_identifier_gaps(board, tight) == []
    wide = [
        {"word": "check", "start": 0.0, "end": 0.2},
        {"word": "match", "start": 0.3, "end": 0.4},
        {"word": "names", "start": 0.7, "end": 0.9},
        {"word": "now", "start": 1.0, "end": 1.1},
    ]
    bad = check_identifier_gaps(board, wide)
    assert len(bad) == 1 and bad[0]["token"] == "match_names" and bad[0]["gap"] > IDENT_GAP_MAX


def _diff_board(
    map_path: str = "pr12.json",
) -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Any]]:
    m = cast(dict[str, Any], json.loads((DATA / "maps" / map_path).read_text()))
    f = next(f for f in m["files"] if f["hunks"] and f["path"].startswith("src/"))
    long_lines = [
        ln
        for h in f["hunks"]
        for ln in h["lines"]
        if ln["op"] == "+" and len(ln.get("text", "")) >= 60
    ]
    ln = cast(
        dict[str, Any],
        (
            sorted(long_lines, key=lambda x: len(x["text"]), reverse=True)
            or [next(ln for h in f["hunks"] for ln in h["lines"] if ln["op"] == "+")]
        )[0],
    )
    board: dict[str, Any] = {
        "scenes": [
            {"type": "title", "say": ["A small change lands."], "cues": []},
            {
                "type": "diff",
                "file": f["path"],
                "lines": [str(ln["new"])],
                "say": ["The diff adds one long line."],
                "cues": [
                    {"at": [0, 0.0], "do": "step", "n": 1},
                    {
                        "at": [0, 0.5],
                        "do": "note",
                        "line": str(ln["new"]),
                        "text": "Google checks run first",
                    },
                ],
            },
        ]
    }
    return m, board, f["path"], ln


def test_callout_leaves_code_uncovered_v5a_v5b(tmp_path: Path) -> None:
    import shutil

    pw = pytest.importorskip("playwright.sync_api")
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, board, _, ln = _diff_board()
    assert len(ln["text"]) >= 40, "need a long line to replay v5-a line 36 / v5-b line 84"
    facts = verify_board(board, m)
    out = tmp_path / "callout"
    render(board, m, facts, out, NoneBackend(), None, keys_only=True)
    with pw.sync_playwright() as d:
        b = d.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto((out / "player.html").as_uri())
        pg.wait_for_function("window.ready === true")
        pg.evaluate("window.seek(window.BOARD.scenes[1].end - 0.4)")
        hit = pg.evaluate("""() => {
          const note = document.querySelector('.dnote');
          if (!note) return {ok: false, why: 'no note'};
          const r = note.getBoundingClientRect();
          const codes = [...document.querySelectorAll('.diff .code .ct')].flatMap(ct => [...ct.getClientRects()]);
          const bad = codes.some(c => Math.min(r.right, c.right) - Math.max(r.left, c.left) > 12 && Math.min(r.bottom, c.bottom) - Math.max(r.top, c.top) > 12);
          const placed = !!document.querySelector('.dleader') || !!document.querySelector('.dnote[data-moved]');
          return {ok: !bad, placed, note: [r.left, r.top, r.width, r.height]};
        }""")
        b.close()
    assert hit["ok"], "callout covers code glyphs; v5-a line 36 and v5-b line 84 regressed"
    # New placement draws a leader from the code end to the margin note.
    # The old inline placement has no leader, so this fails on the base commit.
    assert hit["placed"], (
        "callout needs a margin leader line (or a below-code move); v5-a line 36 regressed"
    )


def test_outro_review_tip_card(tmp_path: Path) -> None:
    pw = pytest.importorskip("playwright.sync_api")
    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    f = next(f for f in m["files"] if f["hunks"] and f["path"].startswith("src/"))
    ln = next(ln for h in f["hunks"] for ln in h["lines"] if ln["op"] == "+")
    board = {
        "scenes": [
            {"type": "title", "say": ["A small change lands."], "cues": []},
            {
                "type": "diff",
                "file": f["path"],
                "lines": [str(ln["new"])],
                "say": ["The diff adds one line."],
                "cues": [{"at": [0, 0.0], "do": "step", "n": 1}],
            },
            {
                "type": "outro",
                "l1": "The diff adds one line for every caller.",
                "l2": "Start with this change.",
                "say": ["Start with this change."],
                "cues": [
                    {"at": [0, 0.0], "do": "l1"},
                    {"at": [0, 0.5], "do": "l2"},
                    {"at": [0, 0.9], "do": "cmd"},
                ],
            },
        ]
    }
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, 12.5, has_video=False)
    with pw.sync_playwright() as d:
        b = d.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto((tmp_path / "player.html").as_uri())
        pg.wait_for_function("window.ready === true")
        pg.evaluate("window.seek(window.BOARD.scenes.at(-1).end - 0.5)")
        label = pg.locator(".outro .tip .tlabel").inner_text()
        body = pg.locator(".outro .tip .tbody").inner_text()
        assert label.strip().lower() == "review tip"
        assert "Start with this change" in body
        box = pg.locator(".outro .tip").bounding_box()
        summ = pg.locator(".outro .l1").bounding_box()
        assert box and summ and box["y"] > summ["y"] + summ["height"] + 20, (
            "tip needs a gap below the summary"
        )
        lh = float(
            pg.evaluate(
                "getComputedStyle(document.querySelector('.outro .tip')).lineHeight.replace('px','')"
            )
        )
        fs = float(
            pg.evaluate(
                "getComputedStyle(document.querySelector('.outro .tip')).fontSize.replace('px','')"
            )
        )
        assert lh / fs >= 1.3, "outro wall of text: raise line height"
        pg.goto((tmp_path / "page.html").as_uri())
        pg.locator("#strip button").last.click()
        assert pg.locator(".outro .tip .tlabel").inner_text().strip().lower() == "review tip"
        b.close()


def test_hunk_drawer_overlays_and_returns_focus(tmp_path: Path) -> None:
    pw = pytest.importorskip("playwright.sync_api")
    from prc.explainer.page import render_page

    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    f = next(f for f in m["files"] if f["hunks"] and f["path"].startswith("src/"))
    ln = next(ln for h in f["hunks"] for ln in h["lines"] if ln["op"] == "+")
    board = {
        "scenes": [
            {"type": "title", "say": ["A small change lands."], "cues": []},
            {
                "type": "diff",
                "file": f["path"],
                "lines": [str(ln["new"])],
                "rows": [{"ref": str(ln["new"]), "op": "+", "num": ln["new"], "text": ln["text"]}],
                "say": ["The diff adds one line."],
                "cues": [{"at": [0, 0.0], "do": "step", "n": 1}],
            },
        ]
    }
    from prc.explainer.check import verify_board
    from prc.explainer.render import render as _render
    from prc.explainer.voice import NoneBackend

    facts = verify_board(board, m)
    _render(board, m, facts, tmp_path / "r", NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, 12.5, has_video=False)
    with pw.sync_playwright() as d:
        b = d.chromium.launch()
        for width in (800, 1440):
            pg = b.new_page(viewport={"width": width, "height": 800})
            pg.goto((tmp_path / "page.html").as_uri())
            pg.locator("#strip button").nth(1).click()
            box = pg.locator(".pg-hit").first
            box.click()
            pg.wait_for_selector("#panel:not([hidden])")
            over = pg.evaluate("""() => {
              const st = document.querySelector('#stage').getBoundingClientRect();
              const pn = document.querySelector('#panel').getBoundingClientRect();
              const ix = Math.min(st.right, pn.right) - Math.max(st.left, pn.left);
              const iy = Math.min(st.bottom, pn.bottom) - Math.max(st.top, pn.top);
              const stvis = st.top >= 0 && st.bottom <= innerHeight + 1;
              return {ix, iy, stvis};
            }""")
            assert over["ix"] > 50 and over["iy"] > 50, (
                "hunk panel must overlay the stage at every width"
            )
            assert over["stvis"], "opening a box must not scroll the scene away"
            pg.keyboard.press("Escape")
            pg.wait_for_selector("#panel", state="hidden")
            focused = pg.evaluate("document.activeElement && document.activeElement.className")
            assert "pg-hit" in focused, "Esc must return focus to the same box"
            box.click()
            pg.wait_for_selector("#panel:not([hidden])")
            pg.locator("#panel-close").click()
            pg.wait_for_selector("#panel", state="hidden")
            focused2 = pg.evaluate("document.activeElement && document.activeElement.className")
            assert "pg-hit" in focused2, "Close must return focus to the same box"
            pg.close()
        b.close()
