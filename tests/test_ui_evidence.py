"""Real UI evidence: PR body images, UI detection, notice, screens checks, page."""

from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

# 1x1 PNG bytes (real image magic).
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/a.png", "/b.png"):
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PNG)))
            self.end_headers()
            self.wfile.write(PNG)
        elif self.path == "/page.html":
            body = b"<html><body>not an image</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: Any) -> None:
        pass


def _serve() -> tuple[HTTPServer, str]:
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv, f"http://127.0.0.1:{port}"


def _map(paths: list[str]) -> dict[str, Any]:
    return {
        "pr": "acme/shop#12",
        "title": "T",
        "author": "a",
        "url": "https://github.com/acme/shop/pull/12",
        "base_sha": "0" * 40,
        "head_sha": "1" * 40,
        "files": [{"path": p, "status": "modified"} for p in paths],
    }


def test_collect_two_images_and_skips_non_image(tmp_path: Path) -> None:
    from prc.explainer.evidence import collect

    srv, base = _serve()
    try:
        body = (
            f"Before ![first]({base}/a.png) after\n"
            f'<img alt="second" src="{base}/b.png">\n'
            f"See [{base}/page.html]({base}/page.html) for notes.\n"
        )
        ev = collect({"body": body}, _map(["x.py"]), tmp_path)
        assert len(ev["shots"]) == 2
        assert all((tmp_path / "evidence" / s["path"]).exists() for s in ev["shots"])
        assert ev["shots"][0]["source"] == "pr-body"
        assert ev["shots"][0]["source_url"] == f"{base}/a.png"
    finally:
        srv.shutdown()


def test_ui_change_false_for_pure_python(tmp_path: Path) -> None:
    from prc.explainer.evidence import collect

    ev = collect({"body": "no images"}, _map(["src/app.py"]), tmp_path)
    # /tmp write is outside the checkout; use tmp_path style cleanup manually.
    assert ev["ui_change"] is False
    assert ev["reasons"] == []
    assert ev["notice"] is None


def test_notice_set_for_ui_without_media(tmp_path: Path) -> None:
    from prc.explainer.evidence import NOTICE, collect

    ev = collect({"body": "no images here"}, _map(["nicegui/elements/stepper.py"]), tmp_path)
    assert ev["ui_change"] is True
    assert ev["reasons"] == ["nicegui/elements/stepper.py"]
    assert ev["shots"] == []
    assert ev["notice"] == NOTICE


def test_check_rejects_unknown_screens_path_and_missing_screens() -> None:
    import pytest

    from prc.explainer.check import verify_board

    m = json.loads(
        (Path(__file__).resolve().parents[1] / "tests/data/explainer/maps/pr12.json").read_text()
    )
    # Minimal board with a screens scene citing an unknown file.
    bad = {
        "scenes": [
            {
                "type": "title",
                "title": "A small change",
                "say": ["A small change lands."],
                "cues": [],
            },
            {
                "type": "screens",
                "images": [{"path": "evidence/nope.png", "label": "From the PR"}],
                "caption": "From the PR.",
                "source_url": "https://github.com/acme/shop/pull/12",
                "say": ["The screen shows the change."],
                "cues": [],
            },
        ]
    }
    evidence = {
        "ui_change": True,
        "reasons": ["a.html"],
        "shots": [
            {
                "path": "shot-0.png",
                "source": "pr-body",
                "source_url": "https://example.com/a.png",
                "caption": "From the PR",
            }
        ],
        "notice": None,
    }
    with pytest.raises(SystemExit) as e:
        verify_board(bad, m, evidence)
    assert "evidence.json" in str(e.value)
    # Board without screens but with shots must fail naming the kind.
    noscreens = {
        "scenes": [
            {
                "type": "title",
                "title": "A small change",
                "say": ["A small change lands."],
                "cues": [],
            }
        ]
    }
    with pytest.raises(SystemExit) as e2:
        verify_board(noscreens, m, evidence)
    assert "screens" in str(e2.value)


def test_before_and_after_shots_load_on_the_page_and_in_the_video_player(tmp_path: Path) -> None:
    """The real pipeline: verify, render (player), render_page; both images load in both."""
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from test_explainer_page import _change

    m, board, _ = _change()
    prepared = tmp_path / "prepared"
    (prepared / "evidence").mkdir(parents=True)
    for name in ("shot-0.png", "shot-1.png"):
        (prepared / "evidence" / name).write_bytes(PNG)
    evidence = {
        "ui_change": True,
        "reasons": ["a.html"],
        "shots": [
            {
                "path": "shot-0.png",
                "source": "pr-body",
                "source_url": "https://example.com/a.png",
                "caption": "Before.",
            },
            {
                "path": "shot-1.png",
                "source": "pr-body",
                "source_url": "https://example.com/b.png",
                "caption": "After.",
            },
        ],
        "notice": None,
    }
    board["scenes"].insert(
        1,
        {
            "type": "screens",
            "images": [
                {"path": "shot-0.png", "label": "Before"},
                {"path": "shot-1.png", "label": "After"},
            ],
            "caption": "The stepper keeps its done marks.",
            "source_url": "https://github.com/acme/shop/pull/12",
            "say": ["The stepper keeps its done marks."],
            "cues": [{"at": [0, 0.0], "do": "show"}],
        },
    )
    out = tmp_path / "out"
    facts = verify_board(board, m, evidence)
    render(board, m, facts, out, NoneBackend(), None, keys_only=True, evidence_dir=prepared)
    render_page(board, m, out, board["scenes"][-1]["end"], has_video=False, evidence_dir=prepared)
    probe = "() => [...document.querySelectorAll('.screens img')].map(i => i.complete && i.naturalWidth)"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1280, "height": 800})
        pg.goto((out / "player.html").as_uri())
        pg.wait_for_function("window.ready === true")
        pg.evaluate("window.seek(window.BOARD.scenes[1].end - 0.3)")
        pg.wait_for_function(f"({probe})().length === 2 && ({probe})().every(Boolean)")
        pg.goto((out / "page.html").as_uri())
        pg.locator("#strip button").nth(1).click()
        pg.wait_for_function(f"({probe})().length === 2 && ({probe})().every(Boolean)")
        labels = pg.locator("#scale .slabel").all_text_contents()
        browser.close()
    assert labels == ["Before", "After"]


def test_board_check_cli_reads_evidence_beside_the_map(tmp_path: Path, capsys: Any) -> None:
    """A board that drops the screens scene passes without evidence and fails with it."""
    from prc.cli import main
    from test_explainer_page import _change

    m, board, _ = _change()
    (tmp_path / "map.json").write_text(json.dumps(m))
    (tmp_path / "board.json").write_text(json.dumps(board))
    args = ["board", "check", str(tmp_path / "board.json"), "--map", str(tmp_path / "map.json")]
    assert main(args) == 0
    shot = {
        "path": "shot-0.png",
        "source": "pr-body",
        "source_url": "https://x/a.png",
        "caption": "c",
    }
    evidence = {"ui_change": True, "reasons": ["a.html"], "shots": [shot], "notice": None}
    (tmp_path / "evidence.json").write_text(json.dumps(evidence))
    assert main(args) == 2
    assert "screens" in capsys.readouterr().err
