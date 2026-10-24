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

import base64
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from prc.explainer.evidence import copy_shots
from prc.explainer.highlight import _git_reader, paint_map
from prc.explainer.preflight import cited_refs, line_coverage
from prc.explainer.themes import look
from prc.explainer.units import Unit, units
from prc.explainer.units import key as unit_key
from prc.tones import key_html, key_script

_URL = re.compile(r"https?://[^\s'\"<>`]+[^\s'\"<>`.,;:)\]}]")
# Reference-shaped tokens in a code line: a URL, a file:line, a commit SHA, or owner/repo#N.
# The page links each one to its line on GitHub, so no reference shows as bare text.
_REF = re.compile(
    _URL.pattern
    + r"|\b[\w+./~-]+\.(?:py|js|jsx|ts|tsx|mts|cts|rb|go|rs|java|kt|swift|md|markdown|html|css"
    r"|scss|json|yaml|yml|toml|ini|cfg|sh|bash|sql|r|php):\d+\b"
    r"|\b[0-9a-f]{7,40}\b"
    r"|\b[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#\d+\b"
)


def _runs(text: str, tokens: list[dict[str, Any]] | None) -> list[tuple[str, str]]:
    """Highlight tokens merged into runs of one colour; plain text when they do not match it."""
    if not tokens or "".join(t["text"] for t in tokens) != text.expandtabs(4).rstrip():
        return [(text, "")]
    runs: list[tuple[str, str]] = []
    for t in tokens:
        c = str(t.get("cls") or "")
        if runs and runs[-1][1] == c:
            runs[-1] = (runs[-1][0] + t["text"], c)
        else:
            runs.append((t["text"], c))
    return runs


def _code_html(text: str, line_url: str, tokens: list[dict[str, Any]] | None = None) -> str:
    """One code line in the video's syntax colours; each reference in it links to the line
    on GitHub, since it is a value. A link may span several colour runs."""
    runs = _runs(text, tokens)
    full = "".join(t for t, _ in runs)
    refs = [(r.start(), r.end()) for r in _REF.finditer(full)]
    starts: list[tuple[int, str]] = []
    cuts = {0, len(full)}
    at = 0
    for t, c in runs:
        starts.append((at, c))
        at += len(t)
        cuts.add(at)
    for ra, rb in refs:
        cuts |= {ra, rb}
    edges = sorted(cuts)
    out: list[str] = []
    open_ref: tuple[int, int] | None = None
    for a, b in zip(edges, edges[1:], strict=False):
        ref = next(((ra, rb) for ra, rb in refs if ra <= a < rb), None)
        if ref != open_ref:
            if open_ref is not None:
                out.append("</a>")
            if ref is not None:
                out.append(f"<a href='{html.escape(line_url)}' target='_blank' rel='noopener'>")
            open_ref = ref
        c = next(c for s0, c in reversed(starts) if s0 <= a)
        piece = html.escape(full[a:b])
        out.append(f"<span class='t-{c}'>{piece}</span>" if c else piece)
    if open_ref is not None:
        out.append("</a>")
    return "".join(out)


ASSETS = Path(__file__).resolve().parent / "assets"
FILES_LISTED = 6
ROLE_TITLES = {
    "code": "Code",
    "ci": "CI workflows",
    "config": "Configuration",
    "test": "Tests",
    "docs": "Docs",
    "data": "Other files",
}
# A unit's color says what the unit is, in the key's words: tests are proof, docs and
# other files are context, code, CI and configuration are the change. The status word
# (added, removed, modified) and the diff signs say what happened to its lines.
ROLE_TONE = {"test": "proof", "docs": "context", "data": "context"}


def files_url(
    owner_repo: str, number: str, path: str, line: int | None = None, removed: bool = False
) -> str:
    anchor = hashlib.sha256(path.encode()).hexdigest()
    side = "" if line is None else ("L" if removed else "R") + str(line)
    return f"https://github.com/{owner_repo}/pull/{number}/files#diff-{anchor}{side}"


def _key(op: str, n: int) -> str:
    return ("-" if op == "-" else "+") + str(n)


def _row(ln: dict[str, Any], owner_repo: str, number: str, path: str, dim: bool = False) -> str:
    """One diff row the way GitHub draws it: old line number, new line number, sign, text."""
    op = ln.get("op") or " "
    num = int(ln["old"] if op == "-" else ln["new"])
    line_url = files_url(owner_repo, number, path, num, op == "-")
    cls = {"+": "hk-add", "-": "hk-del"}.get(op, "hk-ctx") + (" hk-dim" if dim else "")
    sign = {"+": "+", "-": "−"}.get(op, "")

    def cell(n: Any) -> str:
        if n is None:
            return "<td class='hk-n'></td>"
        return (
            f"<td class='hk-n'><a href='{html.escape(line_url)}' target='_blank' rel='noopener'>"
            f"{n}</a></td>"
        )

    old = ln.get("old") if op != "+" else None
    new = ln.get("new") if op != "-" else None
    return (
        f"<tr class='{cls}' data-k='{_key(op, num)}'>{cell(old)}{cell(new)}"
        f"<td class='hk-s'>{sign}</td>"
        f"<td class='hk-t'>{_code_html(str(ln.get('text', '')), line_url, ln.get('tokens'))}</td></tr>"
    )


def _gap(count: int | None, say: str = "unchanged") -> str:
    """A folded run of lines, with its count; None marks a jump of unknown size."""
    if count is None:
        text = "⋯"
    elif say == "unchanged":
        text = f"⋯ {count} unchanged " + ("line" if count == 1 else "lines")
    else:
        text = f"⋯ {count} " + ("line" if count == 1 else "lines") + " " + say
    return (
        "<tr class='hk-gap'><td class='hk-n'></td><td class='hk-n'></td><td class='hk-s'></td>"
        f"<td class='hk-t'>{text}</td></tr>"
    )


def _hunk_html(h: dict[str, Any], owner_repo: str, number: str, path: str) -> str:
    rows = [_row(ln, owner_repo, number, path) for ln in h.get("lines", [])]
    head = f"@@ −{h.get('old_start', '?')} +{h.get('new_start', '?')} @@"
    return f"<p class='hk-head'>{head}</p><table class='hk'><tbody>{''.join(rows)}</tbody></table>"


CONTEXT = 3


def _num(ln: dict[str, Any]) -> int | None:
    """The new-side line number, else the old one: where the line sits in the file."""
    n = ln.get("new") if ln.get("op") != "-" else ln.get("old")
    return None if n is None else int(n)


def fold_rows(
    u: Unit, f: dict[str, Any], owner_repo: str, number: str, inside: frozenset[str] = frozenset()
) -> list[str]:
    """The unit's lines in diff order, as GitHub shows them.

    Each hunk that holds a unit line contributes the span from the unit's first line to its
    last one, plus up to CONTEXT lines on each side, so the reader sees what the first line
    belongs to. Inside the span, a run of other lines longer than two CONTEXT windows keeps
    CONTEXT lines at each end and folds the rest to one counted gap row. Lines of nested
    helpers (keys in inside) draw as the unit's own; changed lines of other units draw grey.
    The jump between two hunks is a gap row with the count of lines it skips.
    """
    mine = {unit_key(ln) for ln in u["lines"]} | set(inside)
    path = str(f["path"])

    def own(ln: dict[str, Any]) -> bool:
        return (
            ln.get("op") in ("+", "-")
            and bool(str(ln.get("text", "")).strip())
            and unit_key(ln) in mine
        )

    def draw(ln: dict[str, Any]) -> str:
        # Blank lines belong to no unit, so they never draw grey as another card's lines.
        other = (
            ln.get("op") in ("+", "-")
            and bool(str(ln.get("text", "")).strip())
            and unit_key(ln) not in mine
        )
        return _row(ln, owner_repo, number, path, dim=other)

    def fold(run: list[dict[str, Any]]) -> str:
        changed = sum(1 for ln in run if ln.get("op") in ("+", "-"))
        if not changed:
            return _gap(len(run))
        return _gap(
            len(run), "from other cards" if changed == len(run) else "unchanged or in other cards"
        )

    rows: list[str] = []
    last: int | None = None
    tail: list[dict[str, Any]] = []
    for h in f.get("hunks", []):
        lines = h.get("lines", [])
        at = [i for i, ln in enumerate(lines) if own(ln)]
        if not at:
            continue
        lo, hi = max(0, at[0] - CONTEXT), at[-1] + 1 + CONTEXT
        span = lines[lo:hi]
        if rows:
            start = _num(span[0])
            hidden = None if start is None or last is None else start - last - 1
            # Lines between two hunks are unchanged; trimmed hunk ends may hold other cards' lines.
            trimmed = [*tail, *lines[:lo]]
            say = (
                "unchanged or in other cards"
                if any(x.get("op") in ("+", "-") for x in trimmed)
                else "unchanged"
            )
            rows.append(_gap(hidden, say) if hidden and hidden > 0 else _gap(None))
        tail = lines[hi:]
        run: list[dict[str, Any]] = []
        for ln in [*span, None]:
            if ln is not None and not own(ln):
                run.append(ln)
                continue
            if len(run) > 2 * CONTEXT:
                rows.extend(draw(x) for x in run[:CONTEXT])
                rows.append(fold(run[CONTEXT:-CONTEXT]))
                rows.extend(draw(x) for x in run[-CONTEXT:])
            else:
                rows.extend(draw(x) for x in run)
            run = []
            if ln is not None:
                rows.append(draw(ln))
        nums = [n for n in (_num(x) for x in span) if n is not None]
        last = nums[-1] if nums else last
    return rows


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
    if scene.get("type") == "screens":
        return []
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


# The full name goes in the tab tooltip; the tab itself ellipsizes at its CSS width.
TAB = 100


def _shorten(text: str, limit: int = TAB) -> str:
    # A code span that is a plain word keeps quotes, so "the text `old`" never reads as prose.
    text = re.sub(r"`([a-z]+)`", "“\\1”", text)
    text = re.sub(r"\s+", " ", text.replace("`", "")).strip().rstrip(".")
    if len(text) <= limit:
        return text
    # End before the last clause that does not fit, so the tab keeps a whole phrase.
    # Plain commas can sit inside a list, so only clause openers count as breaks.
    opener = r", (?:which|that|so|because|while|then) |; |: | — "
    breaks = [m.start() for m in re.finditer(opener, text[:limit])]
    if breaks and breaks[-1] >= limit // 3:
        return text[: breaks[-1]]
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"


def scene_names(board: dict[str, Any]) -> list[str]:
    """The tab name of each scene: what the scene shows, never its scene type.

    A scene label wins. Otherwise the first narration sentence names the scene, so two
    scenes over the same boxes still get different names.
    """
    names: list[str] = []
    used: set[str] = set()
    for s in board["scenes"]:
        say = [x.get("show", "") if isinstance(x, dict) else str(x) for x in s.get("say", [])]
        counts = s.get("type") in ("list", "bars", "stats")
        if counts and say and say[0].strip():
            # A count scene's label captions its number ("lines added"); the narration names it.
            name = _shorten(say[0])
        elif isinstance(s.get("label"), str) and s["label"].strip():
            name = _shorten(s["label"])
        elif s.get("type") == "title":
            name = "Title"
        elif s.get("type") == "outro":
            name = "Summary"
        elif say and say[0].strip():
            name = _shorten(say[0])
        elif s.get("type") == "diff":
            name = str(s.get("file", "")).rsplit("/", 1)[-1] or "Changed lines"
        else:
            name = _shorten(" · ".join(str(g.get("title", "")) for g in s.get("groups", [])))
        name = name or "Scene"
        # A plain lowercase first word reads as a fragment; a code name keeps its case.
        if re.match(r"[a-z]+\b(?![_.(])", name):
            name = name[0].upper() + name[1:]
        base, n = name, 2
        while name in used:
            name = f"{base} ({n})"
            n += 1
        used.add(name)
        names.append(name)
    return names


GREY_KEY = (
    "<p class='hk-key'>Bright rows are this card's lines. Grey rows are nearby lines that "
    "another card explains.</p>"
)


def _anchor(uid: str) -> str:
    return "u-" + hashlib.sha256(uid.encode()).hexdigest()[:12]


def nesting(found: list[Unit]) -> dict[str, Unit]:
    """Each nested helper's enclosing function: a def inside a def, named parent.child.

    The page draws the helper's lines inside its parent's fold, so its own card only
    points there. A method under a class keeps its own card: classes own no method lines.
    """
    funcs = {
        (u["path"], u["name"]): u for u in found if u["kind"] in ("function", "method", "test")
    }
    out: dict[str, Unit] = {}
    for u in found:
        parent = funcs.get((u["path"], str(u["name"]).rsplit(".", 1)[0]))
        if "." in str(u["name"]) and parent is not None and parent["id"] != u["id"]:
            out[u["id"]] = parent
    return out


IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
IMAGE_LIMIT = 2 * 1024 * 1024


def _image_html(
    path: str,
    status: str,
    file_url: str,
    git_dir: str | None,
    head_sha: str,
    base_sha: str,
) -> str | None:
    """An added or modified image file shown inline, or a one-line note linking to GitHub.

    Returns None when the path is not an image the page inlines. Bytes come from the PR
    head commit through git_dir, capped at IMAGE_LIMIT; a missing git_dir, a failed read,
    or an oversized file keeps the one-line GitHub note.
    """
    mime = IMAGE_MIME.get(Path(path).suffix.lower())
    if mime is None or status not in ("added", "modified"):
        return None
    link = f"<a href='{html.escape(file_url)}' target='_blank' rel='noopener'>open it on GitHub</a>"
    data = b""
    if git_dir:
        try:
            data = _git_reader(git_dir, head_sha, base_sha)("new", path)
        except (RuntimeError, OSError):
            data = b""
    if data and len(data) <= IMAGE_LIMIT:
        b64 = base64.b64encode(data).decode("ascii")
        return (
            f"<p class='rd-img'><a href='{html.escape(file_url)}' target='_blank' rel='noopener'>"
            f"<img src='data:{mime};base64,{b64}' alt='{html.escape(path)}' "
            f"style='max-width:100%'></a></p>"
        )
    return f"<p class='rd-bin'>Image file; {link}</p>"


def _unit_html(
    u: Unit,
    f: dict[str, Any],
    owner_repo: str,
    number: str,
    parent: Unit | None = None,
    inside: frozenset[str] = frozenset(),
    git_dir: str | None = None,
    head_sha: str = "",
    base_sha: str = "",
) -> str:
    url = files_url(owner_repo, number, u["path"], u["line"], u["removed"])
    tone = ROLE_TONE.get(str(u["role"]), "change")
    name = u["name"] if u["kind"] != "module" else f"{u['path'].rsplit('/', 1)[-1]} module lines"
    where = f"{u['path']}:{u['line']}" if u["line"] else u["path"]
    count = len(u["lines"])
    rows = [] if parent is not None else fold_rows(u, f, owner_repo, number, inside)
    if parent is not None:
        code = (
            f"<p class='rd-in'>Its {count} "
            + ("line" if count == 1 else "lines")
            + " show inside the fold of "
            f"<a href='#{_anchor(parent['id'])}'><code>{html.escape(str(parent['name']))}</code></a>.</p>"
        )
    elif rows:
        joined = "".join(rows)
        # The reader sees every bright row as this card's lines (own lines, nested helper
        # lines, and blank lines, which belong to no card and never dim), so the summary
        # counts the bright changed rows actually drawn, not just the unit's own lines.
        shown = sum(
            1
            for r in rows
            if r.startswith("<tr class='hk-add'") or r.startswith("<tr class='hk-del'")
        )
        code = (
            f"<details class='rd-code'><summary>{shown} changed "
            + ("line" if shown == 1 else "lines")
            + "</summary>"
            + (GREY_KEY if "hk-dim" in joined else "")
            + f"<table class='hk'><tbody>{joined}</tbody></table></details>"
        )
    else:
        changed = int(f.get("added") or 0) + int(f.get("removed") or 0)
        unread = (
            f"<p class='rd-bin'>{changed} changed "
            + ("line is" if changed == 1 else "lines are")
            + " not shown here: the file is too large or not text. "
            f"<a href='{html.escape(files_url(owner_repo, number, str(u['path'])))}' "
            "target='_blank' rel='noopener'>Read them on GitHub</a>.</p>"
            if changed
            else "<p class='rd-bin'>No text lines (binary or empty file).</p>"
        )
        code = (
            _image_html(
                str(u["path"]),
                str(f.get("status", "")),
                files_url(owner_repo, number, str(u["path"])),
                git_dir,
                head_sha,
                base_sha,
            )
            or unread
        )
    return (
        f"<li class='rd-u tone-{tone}' id='{_anchor(u['id'])}' data-unit='{html.escape(u['id'])}'>"
        f"<a class='rd-name' href='{html.escape(url)}' target='_blank' rel='noopener'>"
        f"<code>{html.escape(name)}</code></a> <span class='rd-st'>{html.escape(str(u['status']))}"
        f"</span> <a class='rd-p' href='{html.escape(url)}' target='_blank' rel='noopener'>"
        f"{html.escape(where)}</a>{code}</li>"
    )


def reading_html(board: dict[str, Any], m: dict[str, Any], git_dir: str | None = None) -> str:
    """The reading path: each role's entries in board order, each unit linked to its line."""
    entries = board.get("reading")
    if not isinstance(entries, list):
        return ""
    owner_repo, number = str(m["pr"]).split("#")
    known = {u["id"]: u for u in units(m)}
    files = {str(f["path"]): f for f in m.get("files", [])}
    shown = [known[x] for e in entries for x in e.get("units", []) if x in known]
    parents = nesting(shown)
    inside: dict[str, set[str]] = {}
    for child, parent in parents.items():
        inside.setdefault(parent["id"], set()).update(unit_key(ln) for ln in known[child]["lines"])
    head_sha = str(m.get("head_sha", ""))
    base_sha = str(m.get("base_sha", ""))
    by_role: dict[str, list[str]] = {}
    for e in entries:
        found = [known[x] for x in e.get("units", []) if x in known]
        if not found:
            continue
        items = "".join(
            _unit_html(
                u,
                files[u["path"]],
                owner_repo,
                number,
                parents.get(u["id"]),
                frozenset(inside.get(u["id"], set())),
                git_dir,
                head_sha,
                base_sha,
            )
            for u in found
        )
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
        "<section id='reading' class='pg-read'><h2>The reading path: every change, in order</h2>"
        f"<p class='rd-lead'>{len(known)} changed units. Each name opens its line on GitHub; "
        "each fold shows its changed lines.</p>" + sections + "</section>"
    )


def _system_view_coverage(
    board: dict[str, Any], m: dict[str, Any], owner_repo: str, number: str
) -> str:
    """A System View shows no code lines by design, so it reports the changed files it cites."""
    changed = [str(f["path"]) for f in m.get("files", []) if "path" in f]
    cited = {path for path, _ in cited_refs(board)}
    uncited = [p for p in changed if p not in cited]
    summary = (
        f"System view: no code lines on screen. Scenes cite {len(changed) - len(uncited)} "
        f"of {len(changed)} changed files."
    )
    if not uncited:
        return f"<p id='not-covered' class='pg-nc'>{html.escape(summary)}</p>"
    rows = [
        f"<li><a href='{html.escape(files_url(owner_repo, number, path))}' target='_blank' "
        f"rel='noopener'><code>{html.escape(path)}</code></a> not cited</li>"
        for path in uncited
    ]
    return (
        "<details id='not-covered' class='pg-nc'>"
        f"<summary>{html.escape(summary)}</summary><ul>{''.join(rows)}</ul></details>"
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
    owner_repo, number = str(m["pr"]).split("#")
    if not any(s.get("type") == "diff" for s in board.get("scenes", [])):
        return _system_view_coverage(board, m, owner_repo, number)
    cov = line_coverage(board, m)
    total = int(cov["total"])
    hidden = max(0, total - int(cov["shown"]))
    if hidden == 0:
        return "<p id='not-covered' class='pg-nc'>Everything changed is on screen.</p>"
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


def _header(m: dict[str, Any], has_video: bool, has_info: bool, ink: str = "dark") -> str:
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
        f"<h1>{re.sub(r'`([^`]+)`', r'<code>\1</code>', html.escape(str(m['title'])))}</h1>"
        f"<p class='pg-meta'>{pr_link} · {html.escape(str(m['author']))} · head "
        f"<a href='{commit}'><code>{str(m['head_sha'])[:7]}</code></a></p>{key_html(ink)}</div>"
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
    git_dir: str | None = None,
    look_name: str = "dark",
    evidence_dir: Path | str | None = None,
) -> str:
    theme = look(look_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    copy_shots(board, Path(evidence_dir) if evidence_dir is not None else out_dir, out_dir)
    m = paint_map(m, git_dir)
    notice_html = ""
    notice = board.get("notice")
    if isinstance(notice, str) and notice.strip():
        notice_html = f"<p class='pg-notice'>{html.escape(notice)}</p>"
    hunks, where = _hunks(m)
    data = {
        "board": board,
        "hunks": hunks,
        "targets": _targets(board, m, where),
        "receipts": _receipts(board, m),
        "names": scene_names(board),
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
        _header(m, has_video, has_info, theme.ink)
        + notice_html
        + "<main id='main' class='pg-main'><section class='pg-col'>"
        + "<div id='stage' class='emount pg-stage'><div id='scale' class='escale'></div></div>"
        + "<div class='pg-controls'><button id='prev' type='button'>Previous</button>"
        + "<button id='play' type='button' class='pg-play'>Play</button>"
        + "<button id='next' type='button'>Next</button>"
        + "<span id='counter' class='pg-counter'></span><span id='hint' class='pg-hint'></span></div>"
        + "<p id='receipts' class='pg-rc'></p>"
        + "<nav id='strip' class='pg-strip' aria-label='Scenes'></nav>"
        + not_covered(board, m)
        + reading_html(board, m, git_dir)
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
        f"<meta name='color-scheme' content='{theme.ink}'><meta name='referrer' content='no-referrer'>"
        "<link rel='icon' href='data:,'>"
        f"<title>{html.escape(str(m['title']).replace('`', ''))}</title><style>"
        + (ASSETS / "engine.css").read_text()
        + (ASSETS / "page.css").read_text()
        + theme.css()
        + "</style></head><body class='pg'>"
        + body
        + f"<script>window.PRC={_json(data)};</script>"
        + key_script(theme.ink)
        + "<script>"
        + (ASSETS / "engine.js").read_text()
        + "</script><script>"
        + (ASSETS / "page.js").read_text()
        + "</script></body></html>"
    )
    (out_dir / "page.html").write_text(page)
    return page
