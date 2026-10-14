"""page.html: the storyboard as a clickable page. Same story as the video.

One static file with no scripts. Each scene shows the same caption sentences
the video narrates, the narration audio for that scene where the voice
backend produced it, and links to the exact file and hunk: a GitHub PR
files URL with a diff anchor plus a blob URL for the exact line, and a
local diff view quoted from the stored map. The video and this page never
disagree: both read the same filled board dict and the same map dict.
"""

from __future__ import annotations

import hashlib
import html
from pathlib import Path
from typing import Any

from prc.captions import shown, shown_html
from prc.explainer.preflight import cited_refs
from prc.presentation.infographic import DISCLOSURE

TEMPLATE_STRINGS = frozenset(
    {
        "Pull request review",
        "Author",
        "Head",
        "commit",
        "Scenes",
        "Captions",
        "Narration",
        "No narration audio",
        "Files and hunks",
        "Open on GitHub",
        "blob",
        "Local diff",
        "Not covered",
        "Files and symbols this board leaves out.",
        "Changed files not shown",
        "Changed symbols not shown",
        "Changed lines not shown",
        "Some changed lines have no line refs and cannot be quoted.",
        "Everything changed is on screen.",
        "Built by prc explain from the checked board.",
        "Watch the video",
        "View the infographic",
        DISCLOSURE,
    }
)


def captions(scene: dict[str, Any]) -> list[str]:
    return [shown(s) for s in scene["say"]]


def receipt_refs(scene: dict[str, Any]) -> list[tuple[str, int, bool]]:
    refs: list[tuple[str, int, bool]] = []
    for c in scene.get("cite", []):
        path, n = c["line"].rsplit(":", 1)
        refs.append((path, abs(int(n)), int(n) < 0))
    for it in scene.get("items", []):
        if "cite" in it:
            path, n = it["cite"].rsplit(":", 1)
            refs.append((path, abs(int(n)), int(n) < 0))
    if scene["type"] == "diff":
        for row in scene.get("rows", []):
            if "text" not in row:
                continue
            refs.append((scene["file"], row["num"], row["op"] == "-"))
    return refs


def blob_url(
    owner_repo: str, head_sha: str, base_sha: str, path: str, n: int, removed: bool
) -> str:
    sha = base_sha if removed else head_sha
    return f"https://github.com/{owner_repo}/blob/{sha}/{path}#L{n}"


def files_url(owner_repo: str, number: str, path: str) -> str:
    anchor = hashlib.md5(path.encode()).hexdigest()
    return f"https://github.com/{owner_repo}/pull/{number}/files#diff-{anchor}"


def _hunk_for(m: dict[str, Any], path: str, n: int, removed: bool) -> dict[str, Any] | None:
    for f in m.get("files", []):
        if f.get("path") != path:
            continue
        for h in f.get("hunks", []):
            for ln in h.get("lines", []):
                if removed and ln.get("op") == "-" and ln.get("old") == n:
                    return h  # type: ignore[no-any-return]
                if not removed and ln.get("op") != "-" and ln.get("new") == n:
                    return h  # type: ignore[no-any-return]
        return None
    return None


def _hunk_html(h: dict[str, Any]) -> str:
    rows = []
    for ln in h.get("lines", []):
        op = ln.get("op") or " "
        num = ln.get("old") if op == "-" else ln.get("new")
        cls = "add" if op == "+" else ("del" if op == "-" else "ctx")
        rows.append(
            f"<tr class='{cls}'><td class='op'>{html.escape(str(op))}</td><td class='ln'>{html.escape(str(num))}</td><td class='tx'>{html.escape(str(ln.get('text', '')))}</td></tr>"
        )
    return "<table class='diff'><tbody>" + "".join(rows) + "</tbody></table>"


def _scene_audio(board_i: int, scene: dict[str, Any], out_dir: Path) -> list[str]:
    files: list[str] = []
    for j in range(len(scene.get("say", []))):
        cand = out_dir / "audio" / f"{board_i:02d}_{j}.wav"
        if cand.is_file():
            files.append(f"audio/{board_i:02d}_{j}.wav")
    return files


def header_html(m: dict[str, Any], duration: float, has_video: bool, has_info: bool) -> str:
    owner_repo, number = m["pr"].split("#")
    pr_link = (
        f"<a href='{html.escape(m['url'])}'>{html.escape(m['pr'])}</a>"
        if m.get("url")
        else "<span>pr</span>"
    )
    commit = f"https://github.com/{owner_repo}/commit/{m['head_sha']}"
    media = ""
    if has_video:
        media += f"<p class='media'><a href='video.mp4'>Watch the {round(duration)} s video</a></p>"
    if has_info:
        media += "<p class='media'><a href='infographic.png'>View the infographic</a></p>"
    return (
        "<header class='doc-head'>"
        + "<p class='kicker'>Pull request review</p>"
        + f"<h1>{html.escape(m['title'])}</h1>"
        + f"<p class='meta'>{pr_link}</p>"
        + "<p class='meta'><span class='lbl'>Author</span> "
        + f"<span>{html.escape(m['author'])}</span></p>"
        + "<p class='meta'><span class='lbl'>Head</span> "
        + f"<code>{m['head_sha']}</code> <a href='{commit}'>commit</a></p>"
        + media
        + "</header>"
    )


def _scene_section(
    board: dict[str, Any], i: int, s: dict[str, Any], m: dict[str, Any], out_dir: Path
) -> str:
    owner_repo, number = m["pr"].split("#")
    prose = "".join(f"<p class='prose'>{shown_html(line)}</p>" for line in s["say"])
    clips = _scene_audio(i, s, out_dir)
    if clips:
        audio = "<h3>Narration</h3>" + "".join(
            f"<p><audio controls preload='none' src='{html.escape(c)}'></audio></p>" for c in clips
        )
    else:
        audio = "<p class='muted'>No narration audio in this build.</p>"
    seen: set[str] = set()
    items: list[str] = []
    hunks: list[str] = []
    for path, n, removed in receipt_refs(s):
        b = blob_url(owner_repo, m["head_sha"], m["base_sha"], path, n, removed)
        f = files_url(owner_repo, number, path)
        label = f"{path}#L{n} (removed)" if removed else f"{path}#L{n}"
        key = b
        if key not in seen:
            seen.add(key)
            items.append(
                f"<li><code>{html.escape(label)}</code> <a href='{html.escape(f)}'>Open on GitHub</a> <a href='{html.escape(b)}'>blob</a></li>"
            )
        h = _hunk_for(m, path, n, removed)
        if h is not None:
            hk = f"{path}:{h.get('old_start')}:{h.get('new_start')}"
            if hk not in seen:
                seen.add(hk)
                hunks.append(f"<h4>{html.escape(path)}</h4>" + _hunk_html(h))
    if s["type"] == "diff" and not hunks:
        rows = []
        for row in s.get("rows", []):
            if "text" not in row:
                rows.append("<tr class='gap'><td></td><td></td><td>...</td></tr>")
                continue
            op = row.get("op") or " "
            cls = "add" if op == "+" else ("del" if op == "-" else "ctx")
            rows.append(
                f"<tr class='{cls}'><td class='op'>{html.escape(str(op))}</td><td class='ln'>{html.escape(str(row.get('num')))}</td><td class='tx'>{html.escape(str(row.get('text')))}</td></tr>"
            )
        hunks.append(
            "<h4>Local diff</h4><table class='diff'><tbody>" + "".join(rows) + "</tbody></table>"
        )
    receipts = (
        ("<h3>Files and hunks</h3><ul class='receipts'>" + "".join(items) + "</ul>")
        if items
        else ""
    )
    local = ("<h3>Local diff</h3>" + "".join(hunks)) if hunks else ""
    nav = ""
    if i > 0:
        nav += f"<a href='#scene-{i - 1}'>Previous</a> "
    if i + 1 < len(board["scenes"]):
        nav += f"<a href='#scene-{i + 1}'>Next</a>"
    return (
        f"<section class='scene' id='scene-{i}'>"
        + f"<h2>Scene {i + 1} of {len(board['scenes'])} - {html.escape(str(s['type']))}</h2>"
        + f"<div class='nav'>{nav}</div>"
        + "<h3>Captions</h3>"
        + prose
        + audio
        + receipts
        + local
        + "</section>"
    )


def _uncovered(
    board: dict[str, Any], m: dict[str, Any]
) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    kinds = {f["path"]: f["kind"] for f in m["files"]}
    shown = cited_refs(board)

    def hit(sym: dict[str, Any]) -> bool:
        for path, n in shown:
            if path != sym["path"]:
                continue
            span = sym["span"] if n > 0 else sym.get("base_span")
            if span and span[0] <= abs(n) <= span[1]:
                return True
        return False

    on_screen = {q for q, _ in shown}
    files = sorted((q, kinds[q]) for q in kinds if q not in on_screen)
    syms = sorted(
        (
            s
            for s in m["symbols"]
            if s["status"] in ("added", "modified")
            and kinds.get(s["path"]) == "code"
            and not hit(s)
        ),
        key=lambda s: (s["path"], s["qualname"]),
    )
    return files, syms


def _not_covered(board: dict[str, Any], m: dict[str, Any]) -> str:
    files, syms = _uncovered(board, m)
    from prc.explainer.preflight import line_coverage

    cov = line_coverage(board, m)
    missing = cov["missing"]
    unavail = cov["unavailable"]
    count = f"<p>{cov['shown']} of {cov['total']} changed lines are on screen.</p>"
    if not missing and not files and not syms and not unavail:
        body = f"{count}<p>Everything changed is on screen.</p>"
    else:
        parts = [count, "<p>Files and symbols this board leaves out.</p>"]
        if unavail:
            parts.append("<p>Some changed lines have no line refs and cannot be quoted.</p>")
        if missing:
            owner_repo = m["pr"].split("#")[0]
            items = []
            for ref in missing:
                path, n = ref.rsplit(":", 1)
                removed = n.startswith("-")
                num = abs(int(n))
                href = blob_url(owner_repo, m["head_sha"], m["base_sha"], path, num, removed)
                label = f"{path}#L{num} (removed)" if removed else f"{path}#L{num}"
                items.append(
                    f'<li><a class="leftout" href="{html.escape(href)}">{html.escape(label)}</a></li>'
                )
            parts.append(
                "<h3>Changed lines not shown</h3><ul class='receipts'>" + "".join(items) + "</ul>"
            )
        if files:
            parts.append(
                "<h3>Changed files not shown</h3><ul>"
                + "".join(
                    f"<li><code>{html.escape(p)}</code> <span>{html.escape(k)}</span></li>"
                    for p, k in files
                )
                + "</ul>"
            )
        if syms:
            parts.append(
                "<h3>Changed symbols not shown</h3><ul>"
                + "".join(
                    f"<li><code>{html.escape(s['qualname'])}</code> <span>{html.escape(s['path'])}</span></li>"
                    for s in syms
                )
                + "</ul>"
            )
        body = "".join(parts)
    return f"<section class='not-covered' id='not-covered'><h2>Not covered</h2>{body}</section>"


CSS = (
    "body{font-family:system-ui,sans-serif;margin:0 auto;max-width:960px;padding:16px;line-height:1.55;color:#e6edf3;background:#0d1117}"
    "a{color:#9ecbff}.muted{color:#9aa7b4}.scene{border:1px solid #30363d;border-radius:12px;padding:16px;margin:16px 0}.nav a{margin-right:12px}table.diff{border-collapse:collapse;width:100%;font-family:ui-monospace,monospace;font-size:13px}table.diff td{border-bottom:1px solid #21262d;padding:4px 8px;vertical-align:top}tr.add{background:#12261a}tr.del{background:#2d1416}td.op{width:24px}td.ln{width:64px;color:#9aa7b4}td.tx{white-space:pre-wrap;overflow-wrap:anywhere}audio{width:100%}.kicker{color:#9aa7b4;text-transform:uppercase;letter-spacing:.08em}.meta{color:#9aa7b4}"
)
CSP = "default-src 'none'; style-src 'unsafe-inline'; media-src 'self'; img-src data:; base-uri 'none'; form-action 'none'"


def render_page(
    board: dict[str, Any],
    m: dict[str, Any],
    out_dir: Path,
    duration: float,
    has_video: bool,
    infographic: bytes | None = None,
) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    nav = (
        "<nav><h2>Scenes</h2><ol>"
        + "".join(
            f"<li><a href='#scene-{i}'>Scene {i + 1} - {html.escape(str(s['type']))}</a></li>"
            for i, s in enumerate(board["scenes"])
        )
        + "</ol></nav>"
    )
    sections = "".join(
        _scene_section(board, i, s, m, out_dir) for i, s in enumerate(board["scenes"])
    )
    figure = ""
    if infographic is not None:
        import base64

        src = base64.b64encode(infographic).decode()
        from prc.presentation.infographic import DISCLOSURE as _D

        figure = f"<figure class='infographic'><img src='data:image/png;base64,{src}' alt='{html.escape(_D)}'><figcaption>{html.escape(_D)}</figcaption></figure>"
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        + f"<meta http-equiv='Content-Security-Policy' content='{CSP}'>"
        + "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        + "<meta name='color-scheme' content='dark light'>"
        + "<meta name='referrer' content='no-referrer'>"
        + "<link rel='icon' href='data:,'>"
        + f"<title>{html.escape(m['title'])}</title><style>{CSS}</style></head>"
        + "<body class='doc'>"
        + header_html(m, duration, has_video, infographic is not None)
        + nav
        + figure
        + sections
        + _not_covered(board, m)
        + f"<footer><p>Built by prc explain from the checked board.</p><p><code>{m['head_sha']}</code></p></footer></body></html>"
    )
    (out_dir / "page.html").write_text(page)
    return page
