"""Scene transitions: the next scene's cards never land on the current scene's cards.

2026-10-18: the style prototypes showed two moments at once for about 0.65 s at every
cut, so the new cards slid in on top of the old ones. These tests drive the real engine
and the real page in Chromium and sample every frame around each cut.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from test_explainer_page import _groups_change

VISIBLE = 0.02


def _rendered(tmp_path: Path, look: str = "dark") -> tuple[dict[str, Any], dict[str, Any]]:
    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, board, _ = _groups_change()
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["duration"], has_video=False, look_name=look)
    return m, board


def test_engine_shows_one_scene_at_a_time_even_when_windows_overlap(tmp_path: Path) -> None:
    """Replays the prototype defect: scene 2 starts 0.65 s before scene 1 ends."""
    from playwright.sync_api import sync_playwright

    _, board = _rendered(tmp_path)
    player = tmp_path / "player.html"
    early = json.loads(json.dumps(board))
    cut = float(early["scenes"][1]["start"])
    early["scenes"][1]["start"] = cut - 0.65
    text = player.read_text()
    text = re.sub(
        r"window\.BOARD = .*?;</script>",
        lambda _: "window.BOARD = " + json.dumps(early).replace("</", "<\\/") + ";</script>",
        text,
        count=1,
        flags=re.S,
    )
    player.write_text(text)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(player.as_uri())
        page.wait_for_function("window.ready === true")
        both = []
        for k in range(int((0.65 + 1.0) / 0.05) + 1):
            t = cut - 0.9 + k * 0.05
            shown = page.evaluate(
                f"seek({t}), [...document.querySelectorAll('.scene')]"
                f".map(s => parseFloat(s.style.opacity) || 0).filter(o => o > {VISIBLE}).length"
            )
            if shown > 1:
                both.append(round(t, 2))
        browser.close()
    assert both == [], f"two scenes visible at once at {both}"


def test_render_refuses_a_board_whose_scene_windows_overlap() -> None:
    from prc.explainer.render import overlapping_scenes

    board = {"scenes": [{"i": 0, "start": 0.0, "end": 5.0}, {"i": 1, "start": 4.35, "end": 9.0}]}
    assert overlapping_scenes(board) == ["scene 1 starts at 4.350s, before scene 0 ends at 5.000s"]
    board["scenes"][1]["start"] = 5.0
    assert overlapping_scenes(board) == []


@pytest.mark.parametrize("look", ["dark", "paper"])
def test_page_step_fades_the_old_scene_out_before_the_new_scene_in(
    tmp_path: Path, look: str
) -> None:
    """Next on the page: the old scene fades out, then the new one fades in, never together."""
    from playwright.sync_api import sync_playwright

    _rendered(tmp_path, look)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((tmp_path / "page.html").as_uri())
        page.wait_for_selector("#scale .scene")
        samples = page.evaluate(
            """() => new Promise(done => {
              const out = [], t0 = performance.now();
              document.getElementById('next').click();
              const step = () => {
                const ghost = document.querySelector('#stage .pg-ghost');
                const live = document.getElementById('scale');
                out.push({
                  ms: performance.now() - t0,
                  ghost: ghost ? parseFloat(getComputedStyle(ghost).opacity) : 0,
                  live: parseFloat(getComputedStyle(live).opacity),
                });
                if (performance.now() - t0 < 700) requestAnimationFrame(step); else done(out);
              };
              requestAnimationFrame(step);
            })"""
        )
        counter = page.locator("#counter").inner_text()
        browser.close()
    assert counter == "Scene 2 of 2"
    assert any(s["ghost"] > 0.3 for s in samples), "the old scene vanished with no fade"
    together = [s for s in samples if s["ghost"] > VISIBLE and s["live"] > VISIBLE]
    assert together == [], f"old and new scene visible together: {together[:3]}"
    assert samples[-1]["live"] == 1 and samples[-1]["ghost"] == 0


def test_light_look_key_reads_the_light_ink_on_page_and_stage(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    from prc.tones import LIGHT, TONES

    _rendered(tmp_path, "paper")
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((tmp_path / "page.html").as_uri())
        page.wait_for_selector("#scale .ckey span")
        css = "el => getComputedStyle(el).backgroundColor"
        header = [page.locator(".pg-key-i i").nth(k).evaluate(css) for k in range(len(TONES))]
        stage = [page.locator("#scale .ckey i").nth(k).evaluate(css) for k in range(len(TONES))]
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        browser.close()

    def rgb(hex_: str) -> str:
        return "rgb({}, {}, {})".format(*(int(hex_[i : i + 2], 16) for i in (1, 3, 5)))

    assert header == stage == [rgb(LIGHT[t]) for t in TONES]
    assert bg == rgb("#FBF8F1")


def test_a_wrapped_added_row_shows_its_text_only_at_full_height(tmp_path: Path) -> None:
    """2026-10-18 v12 review, linkedin-mdp #5 at 75.7 s in every look: while an added row
    that wraps to two lines grew open, its text already showed, so the two lines squeezed
    onto each other and onto the rows around it, and the last line was cut in half."""
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from test_explainer_v6 import _diff_board

    m, board, path, ln = _diff_board()
    ln["text"] = ln["text"] + "  # " + " ".join(["the snapshot ended on a short page"] * 4)
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((tmp_path / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        rows = page.evaluate("window.BOARD.scenes[1].rows.filter(r => r.op === '+')")
        assert any(r.get("breaks") for r in rows), "the fixture row must wrap to two lines"
        start, dur = rows[0]["motion"]["reveal"]
        squeezed = []
        for k in range(int((dur + 0.4) * 30) + 1):
            t = start - 0.2 + k / 30
            bad = page.evaluate(
                f"""seek({t}), [...document.querySelectorAll('.diff .drow')].filter(row => {{
                    const tx = row.querySelector('.tx');
                    return tx && parseFloat(row.style.opacity || '1') > {VISIBLE}
                        && row.clientHeight + 1 < tx.offsetHeight;
                }}).length"""
            )
            if bad:
                squeezed.append(round(t, 2))
        browser.close()
    assert squeezed == [], f"row text shows before its row is full height at {squeezed}"


def test_a_note_bar_leaves_the_line_number_readable(tmp_path: Path) -> None:
    """2026-10-19 v12 review, linkedin-mdp #5 in the dark and paper videos: the 6 px note
    bar on a row's left edge sat on the first digit of its line number (36, 146, 173, 15)."""
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from test_explainer_v6 import _diff_board

    m, board, _, ln = _diff_board()
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((tmp_path / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        gaps = page.evaluate(
            """seek(window.BOARD.scenes[1].end - 0.4),
            [...document.querySelectorAll('.diff .drow')].filter(r => r.style.boxShadow).map(row => {
                const ln = row.querySelector('.ln');
                const range = document.createRange();
                range.selectNodeContents(ln);
                return range.getBoundingClientRect().left - row.getBoundingClientRect().left;
            })"""
        )
        browser.close()
    assert gaps, "the fixture needs a row with a note bar"
    assert min(gaps) >= 12, f"line number starts {min(gaps)} px from the row edge; the bar is 6 px"
