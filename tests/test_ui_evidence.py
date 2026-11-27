"""Real UI evidence: PR body images, UI detection, notice, screens checks, page."""

from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

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


def test_preview_link_in_a_comment_becomes_a_real_chrome_shot(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """A preview link in a PR comment yields one real browser screenshot shot."""
    from prc.explainer import evidence

    comment = "Preview ready: https://pr-42-acme.hf.space/app, have a look."
    assert evidence.extract_preview_urls(comment) == ["https://pr-42-acme.hf.space/app"]

    srv, base = _serve()
    try:
        # The host match only accepts preview hosts; point it at the local page so
        # Chrome takes a real screenshot of a real served page.
        found: list[str] = []

        def local_preview(text: str) -> list[str]:
            found.extend(evidence._PREVIEW.findall(text))
            return [f"{base}/page.html"]

        monkeypatch.setattr(evidence, "extract_preview_urls", local_preview)
        ev = evidence.collect(
            {"body": "no images", "comments": [{"body": comment}]},
            _map(["nicegui/elements/stepper.py"]),
            tmp_path,
        )
    finally:
        srv.shutdown()
    assert [u.rstrip(",") for u in found] == ["https://pr-42-acme.hf.space/app"]
    assert [s["source"] for s in ev["shots"]] == ["preview"]
    shot = tmp_path / "evidence" / ev["shots"][0]["path"]
    assert evidence.is_real_image(shot.read_bytes())
    assert ev["notice"] is None


def test_dead_preview_link_leaves_the_notice(tmp_path: Path, monkeypatch: Any) -> None:
    """A preview link that does not answer adds no shot, so the notice stays."""
    from prc.explainer import evidence

    monkeypatch.setattr(evidence, "extract_preview_urls", lambda text: ["http://127.0.0.1:9/none"])
    ev = evidence.collect({"body": "x"}, _map(["nicegui/elements/stepper.py"]), tmp_path)
    assert ev["shots"] == []
    assert ev["notice"] == evidence.NOTICE
    assert not list((tmp_path / "evidence").glob("shot-*"))


def test_notice_set_for_ui_without_media(tmp_path: Path) -> None:
    from prc.explainer.evidence import NOTICE, collect

    ev = collect({"body": "no images here"}, _map(["nicegui/elements/stepper.py"]), tmp_path)
    assert ev["ui_change"] is True
    assert ev["reasons"] == ["nicegui/elements/stepper.py"]
    assert ev["shots"] == []
    assert ev["notice"] == NOTICE


def test_game_screens_and_stylesheets_count_as_ui() -> None:
    """Tuxemon #3610 changed only tuxemon/states/input.py, its player name screen."""
    from prc.explainer.evidence import is_ui_path

    for path in (
        "tuxemon/states/input.py",
        "game/screens/title.py",
        "app/scenes/battle.py",
        "src/menus/pause.py",
        "pkg/ui/panel.py",
        "tool/gui/main_window.py",
        "warehouse/static/sass/blocks/_footer.scss",
        "site/theme.less",
    ):
        assert is_ui_path(path), path
    for path in (
        "src/state.py",
        "pkg/build.py",
        "docs/guide.md",
        "tuxemon/event/actions/rename_player.py",
    ):
        assert not is_ui_path(path), path


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
        # 2026-10-20 v15 videos: the "Source: PR description" line sat on the narration caption.
        # Two caption lines are the worst case, so the screens block must end above that height.
        gap = pg.evaluate(
            """() => {
                const s = document.querySelector('.screens').getBoundingClientRect();
                const c = document.querySelector('.ecap').getBoundingClientRect();
                const line = parseFloat(getComputedStyle(document.querySelector('.ecap')).lineHeight);
                const scale = c.width / 1640;
                return (c.bottom - 2 * line * scale) - s.bottom;
            }"""
        )
        pg.goto((out / "page.html").as_uri())
        pg.locator("#strip button").nth(1).click()
        pg.wait_for_function(f"({probe})().length === 2 && ({probe})().every(Boolean)")
        labels = pg.locator("#scale .slabel").all_text_contents()
        browser.close()
    assert labels == ["Before", "After"]
    assert gap > 0, f"screens block overlaps a two-line caption by {-gap:.0f}px"


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


def _solid_png(w: int, h: int) -> bytes:
    """A real w x h PNG, so the layout sees the true aspect of a screenshot."""
    import struct
    import zlib

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    raw = b"".join(b"\x00" + b"\x30\x60\x90" * w for _ in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


STAGE_BOX = """(sel) => {
    const stage = document.querySelector('#scale') || document.querySelector('.escale');
    const s = stage.getBoundingClientRect(), k = s.width / stage.offsetWidth;
    return [...document.querySelectorAll(sel)].map(el => {
        const r = el.getBoundingClientRect();
        return {x: (r.left - s.left) / k, y: (r.top - s.top) / k, w: r.width / k, h: r.height / k,
                bottom: (r.bottom - s.top) / k, right: (r.right - s.left) / k};
    });
}"""


@pytest.mark.parametrize(
    ("sizes", "look"),
    [([(720, 580)], "labsheet"), ([(1282, 758)], "dark"), ([(1282, 758), (1282, 758)], "labsheet")],
)
def test_a_screenshot_fills_the_frame_without_white_bars(
    tmp_path: Path, sizes: list[tuple[int, int]], look: str
) -> None:
    """2026-10-21 review of textual #6171 and gradio #13767: each shot sat small inside a
    1640 x 600 white box, with wide white bars on both sides."""
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from test_explainer_page import _change

    m, board, _ = _change()
    prepared = tmp_path / "prepared"
    (prepared / "evidence").mkdir(parents=True)
    shots = []
    for i, (w, h) in enumerate(sizes):
        (prepared / "evidence" / f"shot-{i}.png").write_bytes(_solid_png(w, h))
        shots.append(
            {
                "path": f"shot-{i}.png",
                "source": "pr-body",
                "source_url": f"https://example.com/{i}.png",
                "caption": "Shot.",
            }
        )
    evidence = {"ui_change": True, "reasons": ["a.html"], "shots": shots, "notice": None}
    board["scenes"].insert(1, {
        "type": "screens",
        "images": [{"path": s["path"], "label": ("Before", "After")[i] if len(sizes) == 2 else "The screen"} for i, s in enumerate(shots)],
        "caption": "The screen changes after the fix.",
        "source_url": "https://github.com/acme/shop/pull/12",
        "say": ["The screen changes after the fix."],
        "cues": [{"at": [0, 0.0], "do": "show"}],
    })  # fmt: skip
    out = tmp_path / "out"
    facts = verify_board(board, m, evidence)
    render(board, m, facts, out, NoneBackend(), None, keys_only=True, evidence_dir=prepared)
    render_page(
        board,
        m,
        out,
        board["scenes"][-1]["end"],
        has_video=False,
        evidence_dir=prepared,
        look_name=look,
    )
    probe = "() => [...document.querySelectorAll('.screens img')].map(i => i.complete && i.naturalWidth)"
    found = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1600, "height": 1000})
        for name in ("player.html", "page.html"):
            pg.goto((out / name).as_uri())
            if name == "player.html":
                pg.wait_for_function("window.ready === true")
                pg.evaluate("window.seek(window.BOARD.scenes[1].end - 0.3)")
            else:
                pg.locator("#strip button").nth(1).click()
            pg.wait_for_function(
                f"({probe})().length === {len(sizes)} && ({probe})().every(Boolean)"
            )
            pg.wait_for_timeout(1200)
            found[name] = {
                k: pg.evaluate(STAGE_BOX, sel)
                for k, sel in (("img", ".screens img"), ("text", ".screens .scap, .screens .ssrc"))
            }
        browser.close()
    for name, boxes in found.items():
        for (w, h), box in zip(sizes, boxes["img"], strict=True):
            assert abs(box["w"] / box["h"] - w / h) < 0.02, (
                f"{name}: the image box adds bars, {box}"
            )
            if len(sizes) == 1:
                assert box["h"] >= 700 or box["w"] >= 1250, (
                    f"{name}: one shot uses only {box['w']:.0f} x {box['h']:.0f}"
                )
            else:
                assert box["w"] >= 820, (
                    f"{name}: a before/after shot is only {box['w']:.0f} px wide"
                )
            assert box["right"] <= 1890 and box["x"] >= 30, (
                f"{name}: the shot leaves the frame, {box}"
            )
        for box in boxes["img"] + boxes["text"]:
            assert box["bottom"] <= 862, (
                f"{name}: the screens block reaches {box['bottom']:.0f}, captions start at 862"
            )


def test_labsheet_group_titles_outrank_their_subtitles_and_fit_their_group(tmp_path: Path) -> None:
    """2026-10-21 review of nicegui #6380: TABS, PANEL TWO and CLIENT sat in small grey
    letters above a larger dark subtitle, so the titles looked out of place."""
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from test_explainer_page import _groups_change

    m, board, _ = _groups_change()
    board["scenes"][1]["groups"][0]["title"] = "Panel two with a long group title"
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["duration"], has_video=False, look_name="labsheet")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((tmp_path / "page.html").as_uri())
        pg.locator("#strip button").nth(1).click()
        pg.wait_for_timeout(1500)
        groups = pg.evaluate(
            """() => [...document.querySelectorAll('#scale .grp')].map(g => {
                const t = g.querySelector('.gt'), s = g.querySelector('.gs');
                const ts = getComputedStyle(t), ss = getComputedStyle(s);
                const lum = c => { const [r, gg, b] = c.match(/\\d+/g).map(Number); return (0.2126 * r + 0.7152 * gg + 0.0722 * b) / 255; };
                const range = document.createRange(); range.selectNodeContents(t);
                const gr = g.getBoundingClientRect(), tr = range.getBoundingClientRect(), sr = s.getBoundingClientRect();
                const first = [...document.querySelectorAll('#scale .pill')].map(p => p.getBoundingClientRect())
                    .filter(p => p.left >= gr.left - 1 && p.right <= gr.right + 1 && p.top >= gr.top).sort((a, b) => a.top - b.top)[0];
                const k = gr.width / g.offsetWidth;
                return {title: t.textContent, tsize: parseFloat(ts.fontSize), ssize: parseFloat(ss.fontSize),
                        tlum: lum(ts.color), spill: (tr.right - gr.right) / k, gap: first ? (first.top - sr.bottom) / k : null};
            })"""
        )
        pg.screenshot(path=str(tmp_path / "groups.png"))
        browser.close()
    assert len(groups) == 2
    for g in groups:
        assert g["tsize"] >= 28, f"{g['title']}: title is {g['tsize']} px"
        assert g["tsize"] >= g["ssize"], (
            f"{g['title']}: subtitle {g['ssize']} px outranks title {g['tsize']} px"
        )
        assert g["tlum"] < 0.25, f"{g['title']}: title ink is too light ({g['tlum']:.2f})"
        assert g["spill"] <= 0, f"{g['title']}: title runs {g['spill']:.0f} px past its group"
        assert g["gap"] is not None and g["gap"] >= 8, (
            f"{g['title']}: subtitle sits {g['gap']} px from the first box"
        )


def test_an_archived_before_shot_names_its_own_source(tmp_path: Path) -> None:
    """2026-10-21 pypi/warehouse #20329: the PR shows only the new look, so the before shot is an
    archive.org copy of pypi.org. The source line must name the archive, never only "PR description"."""
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from test_explainer_page import _change

    m, board, _ = _change()
    prepared = tmp_path / "prepared"
    (prepared / "evidence").mkdir(parents=True)
    archive = "https://web.archive.org/web/20260819110918/https://pypi.org/project/requests/"
    shots = [
        {"path": "shot-0.png", "source": "archive", "source_url": archive, "caption": "Before."},
        {
            "path": "shot-1.png",
            "source": "pr-body",
            "source_url": "https://example.com/b.png",
            "caption": "After.",
        },
    ]
    for s in shots:
        (prepared / "evidence" / s["path"]).write_bytes(_solid_png(1090, 512))
    evidence = {"ui_change": True, "reasons": ["a.html"], "shots": shots, "notice": None}
    (prepared / "evidence.json").write_text(json.dumps(evidence))
    pr = "https://github.com/acme/shop/pull/12"
    board["scenes"].insert(1, {
        "type": "screens",
        "images": [{"path": "shot-0.png", "label": "Before"}, {"path": "shot-1.png", "label": "After"}],
        "caption": "Each card now carries a state header.",
        "source_url": pr,
        "say": ["Each card now carries a state header."],
        "cues": [{"at": [0, 0.0], "do": "show"}],
    })  # fmt: skip
    out = tmp_path / "out"
    facts = verify_board(board, m, evidence)
    render(board, m, facts, out, NoneBackend(), None, keys_only=True, evidence_dir=prepared)
    render_page(board, m, out, board["scenes"][-1]["end"], has_video=False, evidence_dir=prepared)
    links = (
        "() => [...document.querySelectorAll('.screens .ssrc a')].map(a => [a.textContent, a.href])"
    )
    found = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        pg = browser.new_page(viewport={"width": 1600, "height": 1000})
        for name in ("player.html", "page.html"):
            pg.goto((out / name).as_uri())
            if name == "player.html":
                pg.wait_for_function("window.ready === true")
                pg.evaluate("window.seek(window.BOARD.scenes[1].end - 0.3)")
            else:
                pg.locator("#strip button").nth(1).click()
            pg.wait_for_selector(".screens .ssrc a")
            found[name] = pg.evaluate(links)
        browser.close()
    for name, got in found.items():
        assert got == [["PR description", pr], ["Web archive copy, 19 Aug 2026", archive]], (
            f"{name}: {got}"
        )
