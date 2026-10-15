"""page.html: the clickable version of the video, built from the same filled board.

The stage mounts one scene with the video engine (engine.js and engine.css), so
each frame is a frame of the video. Narration is the video's own audio track,
played over the current scene's time window; at the scene end the next scene
takes over. Code rows, list items and group boxes on the stage open their hunk
in a side panel with an Open on GitHub link to the line in the PR files view.

Below the stage, the reading path goes deeper than the video: when the board has
a reading list, every changed unit (function, method, class, module lines, CI
step, other file) gets its sentences, its GitHub link and its changed code.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from prc.explainer.preflight import line_coverage
from prc.explainer.units import Unit, units

_URL = re.compile(r"https?://[^\s'\"<>`]+[^\s'\"<>`.,;:)\]}]")


def _code_html(text: str, line_url: str) -> str:
    """Escape one code line; a URL in it links to the line on GitHub, since it is a value, not a page."""
    out, end = [], 0
    for found in _URL.finditer(text):
        out += [
            html.escape(text[end : found.start()]),
            f"<a href='{html.escape(line_url)}' target='_blank' rel='noopener'>"
            f"{html.escape(found.group())}</a>",
        ]
        end = found.end()
    return "".join(out) + html.escape(text[end:])


ASSETS = Path(__file__).resolve().parent / "assets"
FILES_LISTED = 6
# One meaning per color, in Okabe-Ito shades, shared by the video, the page and the infographic.
KEY = (
    ("problem", "Problem or removed", "#D55E00"),
    ("change", "Change", "#E69F00"),
    ("part", "Part", "#56B4E9"),
    ("proof", "Proof or added", "#009E73"),
    ("context", "Context", "#8A93A6"),
)
ROLE_TITLES = {
    "code": "Code",
    "ci": "CI workflows",
    "config": "Configuration",
    "test": "Tests",
    "docs": "Docs",
    "data": "Other files",
}
STATUS_TONE = {"added": "proof", "removed": "problem", "deleted": "problem"}


def files_url(
    owner_repo: str, number: str, path: str, line: int | None = None, removed: bool = False
) -> str:
    anchor = hashlib.sha256(path.encode()).hexdigest()
    side = "" if line is None else ("L" if removed else "R") + str(line)
    return f"https://github.com/{owner_repo}/pull/{number}/files#diff-{anchor}{side}"


def _key(op: str, n: int) -> str:
    return ("-" if op == "-" else "+") + str(n)


def _hunk_html(h: dict[str, Any], owner_repo: str, number: str, path: str) -> str:
    rows = []
    for ln in h.get("lines", []):
        op = ln.get("op") or " "
        num = ln.get("old") if op == "-" else ln.get("new")
        cls = {"+": "hk-add", "-": "hk-del"}.get(op, "hk-ctx")
        sign = {"+": "+", "-": "−"}.get(op, "")
        text = _code_html(
            str(ln.get("text", "")), files_url(owner_repo, number, path, num, op == "-")
        )
        rows.append(
            f"<tr class='{cls}' data-k='{_key(op, num)}'><td class='hk-n'>{num}</td>"
            f"<td class='hk-s'>{sign}</td><td class='hk-t'>{text}</td></tr>"
        )
    head = f"@@ −{h.get('old_start', '?')} +{h.get('new_start', '?')} @@"
    return f"<p class='hk-head'>{head}</p><table class='hk'><tbody>{''.join(rows)}</tbody></table>"


def _hunks(m: dict[str, Any]) -> tuple[list[str], dict[tuple[str, str], int]]:
    owner_repo, number = str(m["pr"]).split("#")
    hunks: list[str] = []
    where: dict[tuple[str, str], int] = {}
    for f in m.get("files", []):
        for h in f.get("hunks", []):
            for ln in h.get("lines", []):
                op = ln.get("op") or " "
                where[(f["path"], _key(op, ln.get("old") if op == "-" else ln.get("new")))] = len(
                    hunks
                )
            hunks.append(_hunk_html(h, owner_repo, number, f["path"]))
    return hunks, where


Ref = tuple[str, int, bool, str | None]


def _refs(scene: dict[str, Any]) -> list[Ref]:
    """Code refs of the scene's clickable regions: diff rows and list items in DOM order,
    group boxes by their element id."""
    if scene.get("type") == "diff":
        return [
            (scene["file"], int(row["num"]), row.get("op") == "-", None)
            for row in scene.get("rows", [])
            if not row.get("gap") and "text" in row
        ]
    if scene.get("type") == "groups":
        boxes: list[Ref] = []
        for g in scene.get("groups", []):
            for it in g.get("items", []):
                if "line" in it:
                    path, n = str(it["line"]).rsplit(":", 1)
                    boxes.append((path, abs(int(n)), int(n) < 0, str(it["id"])))
        return boxes
    refs: list[Ref] = []
    for item in scene.get("items", []):
        path, n = str(item["cite"]).rsplit(":", 1)
        refs.append((path, abs(int(n)), int(n) < 0, None))
    return refs


def _targets(
    board: dict[str, Any], m: dict[str, Any], where: dict[tuple[str, str], int]
) -> list[list[dict[str, Any]]]:
    owner_repo, number = str(m["pr"]).split("#")
    out = []
    for scene in board["scenes"]:
        entries = []
        for path, n, removed, box in _refs(scene):
            key = ("-" if removed else "+") + str(n)
            entry = {
                "label": f"{path} line {n}" + (" (removed)" if removed else ""),
                "url": files_url(owner_repo, number, path, n, removed),
                "hunk": where.get((path, key), -1),
                "key": key,
            }
            if box is not None:
                entry["id"] = box
            entries.append(entry)
        out.append(entries)
    return out


def _receipts(board: dict[str, Any], m: dict[str, Any]) -> list[list[dict[str, str]]]:
    """Every cite of each scene as a link; the video footer has room for four, the page shows all."""
    owner_repo, number = str(m["pr"]).split("#")
    out = []
    for scene in board["scenes"]:
        links = []
        for c in scene.get("cite", []):
            path, n = str(c["line"]).rsplit(":", 1)
            links.append(
                {
                    "label": f"{path.rsplit('/', 1)[-1]}:{abs(int(n))}"
                    + (" (old)" if int(n) < 0 else ""),
                    "url": files_url(owner_repo, number, path, abs(int(n)), int(n) < 0),
                }
            )
        out.append(links)
    return out


def _say_html(say: Any) -> str:
    sentences = [say] if isinstance(say, str) else list(say)
    return " ".join(
        re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(str(s))) for s in sentences
    )


def _unit_html(u: Unit, owner_repo: str, number: str) -> str:
    url = files_url(owner_repo, number, u["path"], u["line"], u["removed"])
    tone = STATUS_TONE.get(str(u["status"]), "change")
    name = u["name"] if u["kind"] != "module" else f"{u['path'].rsplit('/', 1)[-1]} module lines"
    where = f"{u['path']}:{u['line']}" if u["line"] else u["path"]
    rows = []
    for ln in u["lines"]:
        op = ln.get("op")
        num = ln.get("old") if op == "-" else ln.get("new")
        line_url = files_url(owner_repo, number, u["path"], num, op == "-")
        rows.append(
            f"<tr class='{'hk-del' if op == '-' else 'hk-add'}'>"
            f"<td class='hk-n'><a href='{html.escape(line_url)}' target='_blank' rel='noopener'>"
            f"{num}</a></td><td class='hk-s'>{'−' if op == '-' else '+'}</td>"
            f"<td class='hk-t'>{_code_html(str(ln.get('text', '')), line_url)}</td></tr>"
        )
    count = len(u["lines"])
    code = (
        f"<details class='rd-code'><summary>{count} changed "
        + ("line" if count == 1 else "lines")
        + f"</summary><table class='hk'><tbody>{''.join(rows)}</tbody></table></details>"
        if rows
        else "<p class='rd-bin'>No text lines (binary or empty file).</p>"
    )
    return (
        f"<li class='rd-u tone-{tone}' data-unit='{html.escape(u['id'])}'>"
        f"<a class='rd-name' href='{html.escape(url)}' target='_blank' rel='noopener'>"
        f"<code>{html.escape(name)}</code></a> <span class='rd-st'>{html.escape(str(u['status']))}"
        f"</span> <span class='rd-p'>{html.escape(where)}</span>{code}</li>"
    )


def reading_html(board: dict[str, Any], m: dict[str, Any]) -> str:
    """The reading path: each role's entries in board order, each unit linked to its line."""
    entries = board.get("reading")
    if not isinstance(entries, list):
        return ""
    owner_repo, number = str(m["pr"]).split("#")
    known = {u["id"]: u for u in units(m)}
    by_role: dict[str, list[str]] = {}
    for e in entries:
        found = [known[x] for x in e.get("units", []) if x in known]
        if not found:
            continue
        items = "".join(_unit_html(u, owner_repo, number) for u in found)
        by_role.setdefault(found[0]["role"], []).append(
            f"<article class='rd'><p class='rd-say'>{_say_html(e.get('say', ''))}</p>"
            f"<ul class='rd-units'>{items}</ul></article>"
        )
    sections = "".join(
        f"<section class='rd-role' id='reading-{role}'><h3>{ROLE_TITLES[role]}</h3>"
        + "".join(by_role[role])
        + "</section>"
        for role in ROLE_TITLES
        if role in by_role
    )
    return (
        "<section id='reading' class='pg-read'><h2>Every change, in reading order</h2>"
        f"<p class='rd-lead'>{len(known)} changed units. Each name opens its line on GitHub; "
        "each fold shows its changed lines.</p>" + sections + "</section>"
    )


def key_html() -> str:
    return (
        "<p class='pg-key' aria-label='Color key'>"
        + "".join(
            f"<span class='pg-key-i'><i style='background:{color}'></i>{label}</span>"
            for _, label, color in KEY
        )
        + "</p>"
    )


def not_covered(board: dict[str, Any], m: dict[str, Any]) -> str:
    """One summary line; opening it lists a count per file, never raw line links."""
    reading = board.get("reading")
    if isinstance(reading, list):
        listed = {x for e in reading if isinstance(e, dict) for x in e.get("units", [])}
        if all(u["id"] in listed for u in units(m)):
            return (
                "<p id='not-covered' class='pg-nc'>Every changed unit has an entry in "
                "<a href='#reading'>the reading path</a>.</p>"
            )
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
        f"<a href='{commit}'><code>{str(m['head_sha'])[:7]}</code></a></p>{key_html()}</div>"
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
    data = {
        "board": board,
        "hunks": hunks,
        "targets": _targets(board, m, where),
        "receipts": _receipts(board, m),
    }
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
        + "<p id='receipts' class='pg-rc'></p>"
        + "<nav id='strip' class='pg-strip' aria-label='Scenes'></nav>"
        + not_covered(board, m)
        + reading_html(board, m)
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
