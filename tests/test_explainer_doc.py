"""doc.html failure modes: prose fidelity, receipts, offline, not-covered, phone fit.

PLAN Stage 4: a reviewer who reads instead of watching gets the same story.
Every sentence is a board sentence or a fixed template; everything else is
map-verbatim (paths, numbers, titles) or a fixed template.
"""

from __future__ import annotations

import base64
import hashlib
import html as htmlmod
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from prc.explainer import render
from prc.explainer.check import verify_board
from prc.explainer.jointest import run as join_run
from prc.explainer.voice import NoneBackend

DATA = Path(__file__).resolve().parent / "data" / "explainer"
ENGINE_JS = Path(__file__).resolve().parents[1] / "src" / "prc" / "explainer" / "assets"

def need_doc():  # type: ignore[no-untyped-def]
    return pytest.importorskip("prc.explainer.doc")


def filled(board_name: str, map_name: str, tmp_path: Path):  # type: ignore[no-untyped-def]
    board = json.loads((DATA / "boards" / board_name).read_text())
    m = json.loads((DATA / "maps" / map_name).read_text())
    facts = verify_board(board, m)
    render.fill(board, m, facts, None)
    audio = tmp_path / "audio"
    audio.mkdir(exist_ok=True)
    from prc.explainer.timing import fit_sentences

    cursor, _ = fit_sentences(board, NoneBackend(), audio, [])
    for s in board["scenes"]:
        if s["type"] == "graph":
            render.layout(s, m)
    return board, m, cursor


def captions(scene: dict[str, Any]) -> list[str]:
    return [s if isinstance(s, str) else s["show"] for s in scene["say"]]


class Doc(HTMLParser):
    """Sections, prose, links, styles and the one script of a doc.html."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.stack: list[tuple[str, dict[str, str], bool]] = []
        self.shot_depth = 0
        self.prose: list[list[str]] = []
        self.in_prose = False
        self.buf = ""
        self.links: list[tuple[str, str, str]] = []
        self.in_a = False
        self.a_href = ""
        self.a_class = ""
        self.a_buf = ""
        self.scripts: list[str] = []
        self.in_script = False
        self.script_buf = ""
        self.styles: list[str] = []
        self.in_style = False
        self.style_buf = ""
        self.metas: list[dict[str, str]] = []
        self.texts: list[str] = []
        self.shots: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        at = {k: v or "" for k, v in attrs}
        cls = at.get("class", "").split()
        is_shot = tag == "div" and "shot" in cls
        if is_shot:
            self.shot_depth += 1
            self.shots.append(at.get("data-scene", "?"))
        self.stack.append((tag, at, is_shot))
        if self.shot_depth:
            if tag == "script":
                self.in_script = True
                self.script_buf = ""
            return
        if tag == "meta":
            self.metas.append(at)
        if tag == "script":
            assert "src" not in at, "doc.html must inline its only script"
            self.in_script = True
            self.script_buf = ""
        if tag == "style":
            self.in_style = True
            self.style_buf = ""
        if tag == "p" and "prose" in cls:
            self.in_prose = True
            self.buf = ""
        if tag == "a":
            self.in_a = True
            self.a_href, self.a_class, self.a_buf = at.get("href", ""), at.get("class", ""), ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.in_script:
            self.scripts.append(self.script_buf)
            self.in_script = False
        if tag == "style" and self.in_style:
            self.styles.append(self.style_buf)
            self.in_style = False
        if tag == "p" and self.in_prose:
            text = htmlmod.unescape(self.buf.strip())
            if self.prose and len(self.prose[-1]) < 99:
                self.prose[-1].append(text)
            else:
                self.prose.append([text])
            self.in_prose = False
        if tag == "a" and self.in_a:
            self.links.append((self.a_class, self.a_href, htmlmod.unescape(self.a_buf.strip())))
            self.in_a = False
        if self.stack and self.stack[-1][0] == tag:
            _, _, was_shot = self.stack.pop()
            if was_shot:
                self.shot_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.script_buf += data
        elif self.in_style:
            self.style_buf += data
        elif not self.shot_depth:
            if self.in_prose:
                self.buf += data
            if self.in_a:
                self.a_buf += data
            if data.strip():
                self.texts.append(htmlmod.unescape(data.strip()))


def parse(html: str) -> Doc:
    doc = Doc()
    doc.feed(html)
    return doc


def shown_refs(board: dict[str, Any]) -> set[tuple[str, int]]:
    shown: set[tuple[str, int]] = set()
    for s in board["scenes"]:
        for c in s.get("cite", []):
            path, n = c["line"].rsplit(":", 1)
            shown.add((path, int(n)))
        for it in s.get("items", []):
            if "cite" in it:
                path, n = it["cite"].rsplit(":", 1)
                shown.add((path, int(n)))
        if s["type"] == "diff":
            for r in s["lines"]:
                ref = r["ref"] if isinstance(r, dict) else r
                shown.add((s["file"], int(ref)))
    return shown


def uncovered_rule(board: dict[str, Any], m: dict[str, Any]) -> tuple[set[str], set[str]]:
    """The same rule as prc board coverage: a part counts when a line of it is on screen."""
    kinds = {f["path"]: f["kind"] for f in m["files"]}
    shown = shown_refs(board)

    def hit(sym: dict[str, Any]) -> bool:
        for path, n in shown:
            if path != sym["path"]:
                continue
            span = sym["span"] if n > 0 else sym.get("base_span")
            if span and span[0] <= abs(n) <= span[1]:
                return True
        return False

    files = {p for p, _ in shown}
    missed_files = {p for p in kinds if p not in files}
    missed_syms = {
        s["id"]
        for s in m["symbols"]
        if s["status"] in ("added", "modified") and kinds.get(s["path"]) == "code" and not hit(s)
    }
    return missed_files, missed_syms


def test_prose_is_board_sentences(tmp_path: Path) -> None:
    docmod = need_doc()
    board, m, cursor = filled("mdp17b.json", "pr17.json", tmp_path)
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=True)
    doc = parse(html)
    flat = [p for section in doc.prose for p in section]
    want = [line for s in board["scenes"] for line in captions(s)]
    assert flat == want


def test_doc_adds_no_new_claims(tmp_path: Path) -> None:
    """Every doc string is a board sentence, a fixed template, or map-verbatim."""
    board, m, cursor = filled("mdp12.json", "pr12.json", tmp_path)
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=True)
    doc = parse(html)
    sentences = {line for s in board["scenes"] for line in captions(s)}
    # Fixed template strings: the only chrome the doc may add.
    templates = set(docmod.TEMPLATE_STRINGS)
    blob = json.dumps(board) + json.dumps(m)
    joined_prose = "\n".join(p for section in doc.prose for p in section)
    link_labels = {label for _, _, label in doc.links}
    for section in doc.prose:
        for p in section:
            assert p in sentences, p
    for text in doc.texts:
        if text in sentences or text in templates or text in link_labels:
            continue
        if text in joined_prose:
            continue
        if re.fullmatch(r"Scene \d+ of \d+ · \w+", text):
            continue
        assert text in blob, f"doc says {text!r}, which is in neither board, map nor templates"


def test_receipt_links_point_at_the_diff(tmp_path: Path) -> None:
    docmod = need_doc()
    board, m, cursor = filled("mdp17b.json", "pr17.json", tmp_path)
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=True)
    doc = parse(html)
    owner_repo = m["pr"].split("#")[0]
    new_lines = {
        (f["path"], line["new"])
        for f in m["files"]
        for h in f["hunks"]
        for line in h["lines"]
        if line["op"] != "-"
    }
    old_lines = {
        (f["path"], line["old"])
        for f in m["files"]
        for h in f["hunks"]
        for line in h["lines"]
        if line["op"] == "-"
    }
    receipts = [link for link in doc.links if "receipt" in link[0]]
    assert receipts, "scenes with receipts must link them"
    for _, href, _ in receipts:
        hit = re.fullmatch(
            r"https://github\.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)#L(\d+)", href
        )
        assert hit, href
        assert hit.group(1) == owner_repo, href
        sha, path, n = hit.group(2), hit.group(3), int(hit.group(4))
        if (path, n) in new_lines:
            assert sha == m["head_sha"], href
        else:
            assert (path, n) in old_lines, href
            assert sha == m["base_sha"], href


class DomTokens(HTMLParser):
    """Tokens per diff scene from the doc DOM: .mt spans in order, gaps kept."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scenes: list[list[dict[str, Any]]] = []
        self.current: list[dict[str, Any]] | None = None
        self.depth = 0
        self.in_drow = False
        self.gap = False
        self.in_mt = False
        self.mt_buf = ""
        self.tokens: list[str] = []

    VOID = {"br", "img", "hr", "meta", "link", "input"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        at = {k: v or "" for k, v in attrs}
        cls = at.get("class", "").split()
        if self.current is None:
            if tag == "div" and "code" in cls:
                self.current = []
                self.scenes.append(self.current)
                self.depth = 1
            return
        if tag not in self.VOID:
            self.depth += 1
        if tag == "div" and "drow" in cls:
            self.in_drow = True
            self.gap = "gap" in cls
            self.tokens = []
        if self.in_drow and tag == "span" and "mt" in cls:
            self.in_mt = True
            self.mt_buf = ""

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if self.in_mt and tag == "span":
            self.tokens.append(self.mt_buf)
            self.in_mt = False
        if self.in_drow and tag == "div":
            self.current.append({"gap": True} if self.gap else {"tokens": self.tokens})
            self.in_drow = False
        self.depth -= 1
        if self.depth <= 0:
            self.current = None

    def handle_data(self, data: str) -> None:
        if self.in_mt:
            self.mt_buf += data


def test_doc_code_rows_join_to_the_diff(tmp_path: Path) -> None:
    """The join test on the doc DOM: rendered tokens must join to the diff lines."""
    board, m, cursor = filled("mdp12.json", "pr12.json", tmp_path)
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=False)
    dom = DomTokens()
    dom.feed(html)
    diffs = [s for s in board["scenes"] if s["type"] == "diff"]
    assert len(dom.scenes) == len(diffs) and dom.scenes
    for s, rows in zip(diffs, dom.scenes, strict=True):
        code = [r for r in s["rows"] if "text" in r]
        assert len(rows) == len(s["rows"]), "gap rows stay in the DOM in order"
        frames = [
            {"gap": True} if row.get("gap") else {
                "ref": r["ref"],
                "marker": "+" if r["op"] == "+" else "−" if r["op"] == "-" else "",
                "tokens": row["tokens"],
            }
            for row, r in zip(rows, s["rows"], strict=True)
        ]
        errs, rc = join_run(
            {"file": s["file"], "cut": s["cut"], "transform": "build",
             "refs": [r["ref"] for r in code],
             "frames": [{"t": s["end"] - 0.5, "rows": frames}]},
            m,
            [r["ref"] for r in code],
        )
        assert rc == 0, "\n".join(errs)


def test_not_covered_matches_map(tmp_path: Path) -> None:
    docmod = need_doc()
    board, m, cursor = filled("mdp12.json", "pr12.json", tmp_path)
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=False)
    missed_files, missed_syms = uncovered_rule(board, m)
    assert missed_files, "mdp12 must leave files out for this test to mean anything"
    assert missed_syms, "mdp12 must leave symbols out for this test to mean anything"
    syms = {s["id"]: s for s in m["symbols"]}
    for path in missed_files:
        assert path in html, path
    for sid in missed_syms:
        assert syms[sid]["qualname"] in html, sid
    shown_files = {p for p, _ in shown_refs(board)}
    for path in shown_files:
        assert f"<code>{path}</code>" not in html.split("Not covered", 1)[1], path


def test_csp_matches_map_style(tmp_path: Path) -> None:
    docmod = need_doc()
    board, m, cursor = filled("mdp12.json", "pr12.json", tmp_path)
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=False)
    doc = parse(html)
    assert len(doc.scripts) == 1, "one inline script, allowed by a CSP hash"
    digest = base64.b64encode(hashlib.sha256(doc.scripts[0].encode()).digest()).decode()
    csp = next(v["content"] for v in doc.metas if v.get("http-equiv") == "Content-Security-Policy")
    assert f"script-src 'sha256-{digest}'" in csp
    assert "style-src 'unsafe-inline'" in csp and "default-src 'none'" in csp


def test_header_and_video_link(tmp_path: Path) -> None:
    docmod = need_doc()
    board, m, cursor = filled("mdp12.json", "pr12.json", tmp_path)
    with_video = docmod.render_doc(board, m, tmp_path, cursor, has_video=True)
    assert m["title"] in with_video and m["author"] in with_video and m["head_sha"] in with_video
    assert f'href="{m["url"]}"' in with_video
    assert re.search(r"Watch the \d+ s video", with_video), "video link names its length"
    assert 'href="video.mp4"' in with_video
    without = docmod.render_doc(board, m, tmp_path, cursor, has_video=False)
    assert "video.mp4" not in without


def test_null_url_header_shows_pr() -> None:
    docmod = need_doc()
    m: dict[str, Any] = {
        "pr": "o/r#12",
        "title": "A title",
        "author": "someone",
        "head_sha": "a" * 40,
        "base_sha": "b" * 40,
        "url": None,
    }
    header = docmod.header_html(m)
    assert ">pr<" in header and "github.com" not in header


def test_hostile_text_cannot_break_doc(tmp_path: Path) -> None:
    board: dict[str, Any] = {
        "name": "hostile",
        "scenes": [
            {"type": "title", "kicker": "Open pull request",
             "say": ['A title with a quote " and </script> inside.']},
            {"type": "outro", "l1": "First line with </script> in it.", "l2": "Second line.",
             "say": ["Closing out."],
             "cues": [{"at": [0, 0.0], "do": "l1"}, {"at": [0, 0.5], "do": "l2"},
                      {"at": [0, 0.9], "do": "cmd"}]},
        ],
    }
    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    docmod = need_doc()
    facts = verify_board(board, m)
    render.fill(board, m, facts, None)
    audio = tmp_path / "audio"
    audio.mkdir(exist_ok=True)
    from prc.explainer.timing import fit_sentences

    cursor, _ = fit_sentences(board, NoneBackend(), audio, [])
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=False)
    assert html.count("</script>") == 1, "only the one real script tag may close"


def test_engine_exposes_mount() -> None:
    js = (ENGINE_JS / "engine.js").read_text()
    assert "prcMount" in js and "mount(root, board, sceneIndex)" in js
    assert "window.BOARD" not in js, "mount takes the board as an argument now"


needs_browser = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH"
)


@pytest.fixture(scope="module")
def doc_page_url(tmp_path_factory):
    docmod = need_doc()
    pytest.importorskip("playwright.sync_api")
    tmp_path = tmp_path_factory.mktemp("doc")
    board = json.loads((DATA / "boards" / "mdp17b.json").read_text())
    m = json.loads((DATA / "maps" / "pr17.json").read_text())
    facts = verify_board(board, m)
    render.fill(board, m, facts, None)
    audio = tmp_path / "audio"
    audio.mkdir(exist_ok=True)
    from prc.explainer.timing import fit_sentences

    cursor, _ = fit_sentences(board, NoneBackend(), audio, [])
    html = docmod.render_doc(board, m, tmp_path, cursor, has_video=True)
    (tmp_path / "video.mp4").write_bytes(b"")  # presence flag only; never fetched
    assert 'href="video.mp4"' in html
    return (tmp_path / "doc.html").as_uri()


@needs_browser
def test_doc_loads_offline(doc_page_url: str) -> None:
    from playwright.sync_api import sync_playwright

    http_hits: list[str] = []
    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium cannot launch here: {str(error).splitlines()[0]}")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route(re.compile(r"^https?://"), lambda route: route.abort())
        page.on("request", lambda req: http_hits.append(req.url) if req.url.startswith("http") else None)
        failed: list[str] = []
        page.on("requestfailed", lambda req: failed.append(req.url))
        page.goto(doc_page_url)
        page.wait_for_function("window.docReady === true", timeout=15000)
        assert page.evaluate("document.querySelectorAll('.shot').length") == 8
        browser.close()
    assert http_hits == [], http_hits
    assert failed == [], failed


@needs_browser
def test_doc_fits_a_phone(doc_page_url: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            pytest.skip(f"Chromium cannot launch here: {str(error).splitlines()[0]}")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(doc_page_url)
        page.wait_for_function("window.docReady === true", timeout=15000)
        page.screenshot(path=str(Path(doc_page_url[7:]).parent / "doc-390.png"))
        wide = page.evaluate(
            """[...document.querySelectorAll('body *')].filter(
                 el => el.tagName !== 'PRE' && !el.closest('pre') &&
                       el.getBoundingClientRect().right > 391).map(el => el.className)"""
        )
        assert wide == [], wide
        browser.close()
