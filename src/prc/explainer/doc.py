"""doc.html: the board as a searchable offline page. Same story as the video.

One offline file with the same CSP style as map.html. Each scene is drawn by
the same engine, frozen at its settled time, under its caption sentences.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from prc.explainer.render import ASSETS, board_json

# Fixed template strings: the only chrome the doc may add. Every other string
# is a board sentence or map-verbatim (titles, paths, numbers, shas).
TEMPLATE_STRINGS = frozenset(
    {
        "Pull request walkthrough",
        "Author",
        "Head",
        "commit",
        "Receipts",
        "Not covered",
        "Files and symbols this board leaves out.",
        "Changed files not shown",
        "Changed symbols not shown",
        "Everything changed is on screen.",
        "Built by prc explain from the checked board.",
    }
)


def captions(scene: dict[str, Any]) -> list[str]:
    """Caption prose: the show text, not the voice spelling."""
    return [s if isinstance(s, str) else s.get("show", s.get("speak", "")) for s in scene["say"]]


def receipt_refs(scene: dict[str, Any]) -> list[tuple[str, int, bool]]:
    """(path, line, removed) in screen order: cites, list items, then diff rows."""
    refs: list[tuple[str, int, bool]] = []
    for c in scene.get("cite", []):
        path, n = c["line"].rsplit(":", 1)
        refs.append((path, abs(int(n)), int(n) < 0))
    for it in scene.get("items", []):
        if "cite" in it:
            path, n = it["cite"].rsplit(":", 1)
            refs.append((path, abs(int(n)), int(n) < 0))
    if scene["type"] == "diff":
        for r in scene.get("rows", []):
            if "text" not in r:
                continue
            refs.append((scene["file"], r["num"], r["op"] == "-"))
    return refs


def receipt_url(owner_repo: str, head_sha: str, base_sha: str, path: str, n: int, removed: bool) -> str:
    sha = base_sha if removed else head_sha
    return f"https://github.com/{owner_repo}/blob/{sha}/{path}#L{n}"


def uncovered(board: dict[str, Any], m: dict[str, Any]) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    """Changed files and symbols the board does not show. Same rule as board coverage."""
    kinds = {f["path"]: f["kind"] for f in m["files"]}
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
                shown.add((s["file"], int(r["ref"] if isinstance(r, dict) else r)))

    def hit(sym: dict[str, Any]) -> bool:
        for path, n in shown:
            if path != sym["path"]:
                continue
            span = sym["span"] if n > 0 else sym.get("base_span")
            if span and span[0] <= abs(n) <= span[1]:
                return True
        return False

    on_screen = {p for p, _ in shown}
    files = sorted((p, kinds[p]) for p in kinds if p not in on_screen)
    syms = sorted(
        (s for s in m["symbols"]
         if s["status"] in ("added", "modified") and kinds.get(s["path"]) == "code" and not hit(s)),
        key=lambda s: (s["path"], s["qualname"]),
    )
    return files, syms


def header_html(m: dict[str, Any]) -> str:
    """PR title, repo#N, author, head sha, GitHub links. Null url shows `pr`."""
    owner_repo, number = m["pr"].split("#")
    pr_link = (
        f'<a class="pr-link" href="{html.escape(m["url"])}">{html.escape(m["pr"])}</a>'
        if m.get("url")
        else "<span>pr</span>"
    )
    commit = f"https://github.com/{owner_repo}/commit/{m['head_sha']}"
    return (
        '<header class="doc-head">\n'
        '<p class="kicker">Pull request walkthrough</p>\n'
        f"<h1>{html.escape(m['title'])}</h1>\n"
        f'<p class="meta">{pr_link}</p>\n'
        '<p class="meta"><span class="lbl">Author</span> '
        f"<span>{html.escape(m['author'])}</span></p>\n"
        '<p class="meta"><span class="lbl">Head</span> '
        f"<code>{m['head_sha']}</code> "
        f'<a href="{commit}">commit</a></p>\n'
        "</header>"
    )


def _scene_section(board: dict[str, Any], i: int, s: dict[str, Any], m: dict[str, Any]) -> str:
    owner_repo = m["pr"].split("#")[0]
    prose = "\n".join(f'<p class="prose">{html.escape(line)}</p>' for line in captions(s))
    receipts = ""
    links = [
        (receipt_url(owner_repo, m["head_sha"], m["base_sha"], path, n, removed), path, n)
        for path, n, removed in receipt_refs(s)
    ]
    seen: set[str] = set()
    items = []
    for href, path, n in links:
        if href in seen:
            continue
        seen.add(href)
        items.append(
            f'<li><a class="receipt" href="{html.escape(href)}">'
            f"{html.escape(path)}#L{n}</a></li>"
        )
    if items:
        receipts = "<h3>Receipts</h3>\n" + '<ul class="receipts">\n' + "\n".join(items) + "\n</ul>"
    return (
        f'<section class="scene" id="scene-{i}">\n'
        f"<h2>Scene {i + 1} of {len(board['scenes'])} · {s['type']}</h2>\n"
        f"{prose}\n"
        f'<div class="shot emount" data-scene="{i}">'
        f'<div class="escale" id="mount-{i}"></div></div>\n'
        f"{receipts}\n"
        "</section>"
    )


def _not_covered(board: dict[str, Any], m: dict[str, Any]) -> str:
    files, syms = uncovered(board, m)
    if not files and not syms:
        body = "<p>Everything changed is on screen.</p>"
    else:
        parts = ["<p>Files and symbols this board leaves out.</p>"]
        if files:
            rows = "\n".join(
                f"<li><code>{html.escape(p)}</code> <span>{html.escape(k)}</span></li>"
                for p, k in files
            )
            parts.append(f"<h3>Changed files not shown</h3>\n<ul>\n{rows}\n</ul>")
        if syms:
            rows = "\n".join(
                f"<li><code>{html.escape(s['qualname'])}</code> "
                f"<span>{html.escape(s['path'])}</span></li>"
                for s in syms
            )
            parts.append(f"<h3>Changed symbols not shown</h3>\n<ul>\n{rows}\n</ul>")
        body = "\n".join(parts)
    return f'<section class="not-covered" id="not-covered">\n<h2>Not covered</h2>\n{body}\n</section>'


def render_doc(board: dict[str, Any], m: dict[str, Any], out_dir: Path, duration: float, has_video: bool) -> str:
    """Write doc.html beside video.mp4. `board` must be filled and timed (as render leaves it)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    video = (
        f'<p class="video"><a href="video.mp4">Watch the {round(duration)} s video</a></p>\n'
        if has_video
        else ""
    )
    sections = "\n".join(
        _scene_section(board, i, s, m) for i, s in enumerate(board["scenes"])
    )
    script = (
        f"window.DOC = {board_json(board)};\n"
        + (ASSETS / "engine.js").read_text()
        + """
(function () {
  var board = window.DOC;
  document.querySelectorAll('.shot').forEach(function (shot) {
    var i = +shot.dataset.scene;
    window.prcMount(shot.querySelector('.escale'), board, i)(board.scenes[i].end - 0.5);
  });
  function fit() {
    document.querySelectorAll('.shot').forEach(function (shot) {
      var k = shot.clientWidth / 1920;
      shot.style.setProperty('--k', k);
      shot.style.height = (1080 * k) + 'px';
    });
  }
  window.addEventListener('resize', fit);
  fit();
  window.docReady = true;
})();
"""
    )
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    csp = (
        f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; "
        "img-src data:; base-uri 'none'; form-action 'none'"
    )
    css = (ASSETS / "engine.css").read_text() + (ASSETS / "doc.css").read_text()
    page = (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="dark light">'
        '<meta name="referrer" content="no-referrer">'
        '<link rel="icon" href="data:,">'
        f"<title>{html.escape(m['title'])}</title><style>{css}</style></head>\n"
        '<body class="doc">\n'
        f"{header_html(m)}\n{video}"
        f"{sections}\n{_not_covered(board, m)}\n"
        "<footer><p>Built by prc explain from the checked board.</p>"
        f"<p><code>{m['head_sha']}</code></p></footer>\n"
        f"<script>{script}</script></body></html>\n"
    )
    (out_dir / "doc.html").write_text(page)
    return page
