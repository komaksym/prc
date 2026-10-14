"""page.html: the clickable version of the video, built from the same filled board.

The stage mounts one scene with the video engine (engine.js and engine.css), so
each frame is a frame of the video. Narration is the video's own audio track,
played over the current scene's time window; at the scene end the next scene
takes over. Code regions on the stage open their hunk in a side panel with an
Open on GitHub link to the line in the PR files view.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from prc.explainer.preflight import line_coverage

ASSETS = Path(__file__).resolve().parent / "assets"
FILES_LISTED = 6


def files_url(
    owner_repo: str, number: str, path: str, line: int | None = None, removed: bool = False
) -> str:
    anchor = hashlib.sha256(path.encode()).hexdigest()
    side = "" if line is None else ("L" if removed else "R") + str(line)
    return f"https://github.com/{owner_repo}/pull/{number}/files#diff-{anchor}{side}"


def _key(op: str, n: int) -> str:
    return ("-" if op == "-" else "+") + str(n)


def _hunk_html(h: dict[str, Any]) -> str:
    rows = []
    for ln in h.get("lines", []):
        op = ln.get("op") or " "
        num = ln.get("old") if op == "-" else ln.get("new")
        cls = {"+": "hk-add", "-": "hk-del"}.get(op, "hk-ctx")
        sign = {"+": "+", "-": "−"}.get(op, "")
        rows.append(
            f"<tr class='{cls}' data-k='{_key(op, num)}'><td class='hk-n'>{num}</td>"
            f"<td class='hk-s'>{sign}</td><td class='hk-t'>{html.escape(str(ln.get('text', '')))}</td></tr>"
        )
    head = f"@@ −{h.get('old_start', '?')} +{h.get('new_start', '?')} @@"
    return f"<p class='hk-head'>{head}</p><table class='hk'><tbody>{''.join(rows)}</tbody></table>"


def _hunks(m: dict[str, Any]) -> tuple[list[str], dict[tuple[str, str], int]]:
    hunks: list[str] = []
    where: dict[tuple[str, str], int] = {}
    for f in m.get("files", []):
        for h in f.get("hunks", []):
            for ln in h.get("lines", []):
                op = ln.get("op") or " "
                where[(f["path"], _key(op, ln.get("old") if op == "-" else ln.get("new")))] = len(
                    hunks
                )
            hunks.append(_hunk_html(h))
    return hunks, where


def _refs(scene: dict[str, Any]) -> list[tuple[str, int, bool]]:
    """Code refs in the DOM order of the scene's clickable regions."""
    if scene.get("type") == "diff":
        return [
            (scene["file"], int(row["num"]), row.get("op") == "-")
            for row in scene.get("rows", [])
            if not row.get("gap") and "text" in row
        ]
    refs = []
    for item in scene.get("items", []):
        path, n = str(item["cite"]).rsplit(":", 1)
        refs.append((path, abs(int(n)), int(n) < 0))
    return refs


def _targets(
    board: dict[str, Any], m: dict[str, Any], where: dict[tuple[str, str], int]
) -> list[list[dict[str, Any]]]:
    owner_repo, number = str(m["pr"]).split("#")
    out = []
    for scene in board["scenes"]:
        entries = []
        for path, n, removed in _refs(scene):
            key = ("-" if removed else "+") + str(n)
            entries.append(
                {
                    "label": f"{path} line {n}" + (" (removed)" if removed else ""),
                    "url": files_url(owner_repo, number, path, n, removed),
                    "hunk": where.get((path, key), -1),
                    "key": key,
                }
            )
        out.append(entries)
    return out


def not_covered(board: dict[str, Any], m: dict[str, Any]) -> str:
    """One summary line; opening it lists a count per file, never raw line links."""
    cov = line_coverage(board, m)
    total = int(cov["total"])
    hidden = max(0, total - int(cov["shown"]))
    if hidden == 0:
        return "<p id='not-covered' class='pg-nc'>Everything changed is on screen.</p>"
    owner_repo, number = str(m["pr"]).split("#")
    per_file = Counter(ref.rsplit(":", 1)[0] for ref in cov["missing"])
    rows = [
        f"<li><a href='{html.escape(files_url(owner_repo, number, path))}' target='_blank' "
        f"rel='noopener'><code>{html.escape(path)}</code></a> {count} "
        + ("line" if count == 1 else "lines")
        + "</li>"
        for path, count in per_file.most_common(FILES_LISTED)
    ]
    more = len(per_file) - FILES_LISTED
    if more > 0:
        rows.append(
            f"<li class='pg-more'>{more} more " + ("file" if more == 1 else "files") + "</li>"
        )
    if cov["unavailable"]:
        rows.append(
            f"<li class='pg-more'>{cov['unavailable']} lines have no line numbers in the diff</li>"
        )
    return (
        "<details id='not-covered' class='pg-nc'>"
        f"<summary>Not covered: {hidden} of {total} changed lines</summary>"
        f"<ul>{''.join(rows)}</ul></details>"
    )


def _header(m: dict[str, Any], has_video: bool, has_info: bool) -> str:
    owner_repo = str(m["pr"]).split("#")[0]
    pr = html.escape(str(m["pr"]))
    pr_link = f"<a href='{html.escape(m['url'])}'>{pr}</a>" if m.get("url") else pr
    commit = f"https://github.com/{owner_repo}/commit/{m['head_sha']}"
    actions = ""
    if has_info:
        actions += "<button id='info-open' type='button'>Infographic</button>"
    if has_video:
        actions += "<a class='pg-btn' href='video.mp4'>Video file</a>"
    return (
        "<header class='pg-head'><div class='pg-id'>"
        f"<h1>{html.escape(str(m['title']))}</h1>"
        f"<p class='pg-meta'>{pr_link} · {html.escape(str(m['author']))} · head "
        f"<a href='{commit}'><code>{str(m['head_sha'])[:7]}</code></a></p></div>"
        f"<div class='pg-actions'>{actions}</div></header>"
    )


def _json(value: Any) -> str:
    return json.dumps(value).replace("</", "<\\/")


def render_page(
    board: dict[str, Any],
    m: dict[str, Any],
    out_dir: Path,
    duration: float,
    has_video: bool,
    infographic: bytes | None = None,
) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    hunks, where = _hunks(m)
    data = {"board": board, "hunks": hunks, "targets": _targets(board, m, where)}
    has_info = infographic is not None
    info = (
        "<dialog id='info' class='pg-info'><form method='dialog'>"
        "<button id='info-close'>Close</button></form>"
        "<img src='infographic.png' alt='Infographic of this pull request'></dialog>"
        if has_info
        else ""
    )
    body = (
        _header(m, has_video, has_info)
        + "<main id='main' class='pg-main'><section class='pg-col'>"
        + "<div id='stage' class='emount pg-stage'><div id='scale' class='escale'></div></div>"
        + "<div class='pg-controls'><button id='prev' type='button'>Previous</button>"
        + "<button id='play' type='button' class='pg-play'>Play</button>"
        + "<button id='next' type='button'>Next</button>"
        + "<span id='counter' class='pg-counter'></span><span id='hint' class='pg-hint'></span></div>"
        + "<nav id='strip' class='pg-strip' aria-label='Scenes'></nav>"
        + not_covered(board, m)
        + "</section><aside id='panel' class='pg-panel' hidden>"
        + "<div class='pg-panel-head'><h2 id='panel-title'></h2>"
        + "<button id='panel-close' type='button' aria-label='Close hunk'>Close</button></div>"
        + "<div id='panel-diff' class='pg-panel-diff'></div>"
        + "<a id='panel-gh' class='pg-btn pg-gh' href='#' target='_blank' rel='noopener'>"
        + "Open on GitHub</a></aside></main>"
        + info
        + f"<audio id='narr' preload='auto'{' src=video.mp4' if has_video else ''}></audio>"
    )
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='color-scheme' content='dark'><meta name='referrer' content='no-referrer'>"
        "<link rel='icon' href='data:,'>"
        f"<title>{html.escape(str(m['title']))}</title><style>"
        + (ASSETS / "engine.css").read_text()
        + (ASSETS / "page.css").read_text()
        + "</style></head><body class='pg'>"
        + body
        + f"<script>window.PRC={_json(data)};</script><script>"
        + (ASSETS / "engine.js").read_text()
        + "</script><script>"
        + (ASSETS / "page.js").read_text()
        + "</script></body></html>"
    )
    (out_dir / "page.html").write_text(page)
    return page
