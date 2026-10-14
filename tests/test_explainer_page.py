"""Page: one storyboard drives the video and the clickable page."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "tests/data/explainer/maps/pr12.json"


def _change() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    m = json.loads(MAP.read_text())
    f = next(f for f in m["files"] if f["hunks"])
    line = next(ln for ln in f["hunks"][0]["lines"] if ln["op"] == "+")
    board = {
        "scenes": [
            {"type": "title", "say": ["A small change lands."], "cues": []},
            {
                "type": "diff",
                "file": f["path"],
                "lines": [str(line["new"])],
                "rows": [
                    {"ref": str(line["new"]), "op": "+", "num": line["new"], "text": line["text"]}
                ],
                "say": ["The diff adds one line."],
                "cues": [{"at": [0, 0.0], "do": "step", "n": 1}],
            },
        ]
    }
    return m, board, line


def _data(page: str) -> dict[str, Any]:
    found = re.search(r"<script>window\.PRC=(.*?);</script>", page)
    assert found
    return json.loads(found.group(1).replace("<\\/", "</"))  # type: ignore[no-any-return]


def test_files_url_points_at_the_line_in_the_pr_files_view() -> None:
    from prc.explainer.page import files_url

    anchor = hashlib.sha256(b"src/a.py").hexdigest()
    base = "https://github.com/acme/shop/pull/12/files#diff-" + anchor
    assert files_url("acme/shop", "12", "src/a.py") == base
    assert files_url("acme/shop", "12", "src/a.py", 42) == base + "R42"
    assert files_url("acme/shop", "12", "src/a.py", 7, removed=True) == base + "L7"


def test_page_carries_the_board_and_one_hunk_target_per_code_row(tmp_path: Path) -> None:
    from prc.explainer.page import files_url, render_page

    m, board, line = _change()
    path = board["scenes"][1]["file"]
    page = render_page(board, m, tmp_path, 12.5, has_video=True, infographic=b"png")
    data = _data(page)
    owner_repo, number = m["pr"].split("#")

    assert data["board"] == board
    assert data["targets"][0] == []
    [target] = data["targets"][1]
    assert target == {
        "label": f"{path} line {line['new']}",
        "url": files_url(owner_repo, number, path, line["new"]),
        "hunk": target["hunk"],
        "key": f"+{line['new']}",
    }
    hunk = data["hunks"][target["hunk"]]
    assert f"data-k='+{line['new']}'" in hunk
    assert (tmp_path / "page.html").read_text() == page
    assert "<audio id='narr' preload='auto' src=video.mp4>" in page
    assert "<img src='infographic.png'" in page
    for gone in ("card.png", "card.html", "no CI", " files · "):
        assert gone not in page


def test_page_without_video_or_infographic_has_no_audio_source_or_dialog(tmp_path: Path) -> None:
    from prc.explainer.page import render_page

    m, board, _ = _change()
    page = render_page(board, m, tmp_path, 0.0, has_video=False, infographic=None)
    assert "<audio id='narr' preload='auto'></audio>" in page
    assert "id='info'" not in page and "id='info-open'" not in page


def test_outro_hands_off_to_github_in_video_and_clickable_page(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, board, _ = _change()
    board["scenes"].append(
        {
            "type": "outro",
            "l1": "The diff adds one line.",
            "l2": "Start with this change.",
            "say": ["Start with this change."],
            "cues": [
                {"at": [0, 0.0], "do": "l1"},
                {"at": [0, 0.5], "do": "l2"},
                {"at": [0, 0.9], "do": "cmd"},
            ],
        }
    )
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["scenes"][-1]["end"], has_video=False)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto((tmp_path / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        page.evaluate("window.seek(window.BOARD.scenes.at(-1).end - 0.5)")
        assert page.locator(".outro .cmd").inner_text().startswith("Review on GitHub ")
        assert "prc map" not in page.locator(".outro").inner_text()
        page.screenshot(path=str(tmp_path / "video-outro.png"))
        page.goto((tmp_path / "page.html").as_uri())
        page.locator("#strip button").last.click()
        assert page.locator(".outro .cmd").inner_text().startswith("Review on GitHub ")
        assert board["scenes"][-1]["url"] in page.locator(".outro .cmd").inner_text()
        page.screenshot(path=str(tmp_path / "page-outro.png"))
        browser.close()
