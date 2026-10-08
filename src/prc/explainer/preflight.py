"""One preflight for board check and render: line coverage, join parity, note fit."""

from __future__ import annotations

import math
from typing import Any

from prc.explainer.diffrows import wrap_row

WRAP_WIDTH = 72
STAGE_RIGHT = 1700
NOTE_PX_PER_CHAR = 15
NOTE_PX_PAD = 37


def _post(text: str) -> str:
    """The render transform: expand tabs, strip trailing whitespace."""
    return text.expandtabs(4).rstrip()


def _order(m: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """(path, ref) -> hunk line, with ref str(new) or -old like boards use."""
    order: dict[tuple[str, str], dict[str, Any]] = {}
    for f in m.get("files", []):
        for h in f.get("hunks", []):
            for ln in h.get("lines", []):
                ref = "-" + str(ln["old"]) if ln.get("op") == "-" else str(ln.get("new"))
                order[(f["path"], ref)] = ln
    return order


def changed_refs(m: dict[str, Any]) -> dict[tuple[str, int], str]:
    """(path, signed line) -> raw text for every +/- hunk line of the PR."""
    out: dict[tuple[str, int], str] = {}
    for f in m.get("files", []):
        for h in f.get("hunks", []):
            for ln in h.get("lines", []):
                if ln.get("op") == "+":
                    out[(f["path"], int(ln["new"]))] = ln.get("text", "")
                elif ln.get("op") == "-":
                    out[(f["path"], -int(ln["old"]))] = ln.get("text", "")
    return out


def cited_refs(board: dict[str, Any]) -> set[tuple[str, int]]:
    """Every (path, signed line) a receipt names: cites, items, diff rows."""
    shown: set[tuple[str, int]] = set()

    def add(line: Any) -> None:
        if not isinstance(line, str) or ":" not in line:
            return
        path, n = line.rsplit(":", 1)
        try:
            shown.add((path, int(n)))
        except ValueError:
            return

    for s in board.get("scenes", []):
        for c in s.get("cite", []):
            add(c.get("line"))
        for it in s.get("items", []):
            if "cite" in it:
                add(it["cite"])
        if s.get("type") == "diff":
            rows = s.get("rows") or []
            if rows:
                for r in rows:
                    if "text" not in r:
                        continue
                    try:
                        shown.add((s["file"], int(r["ref"])))
                    except (ValueError, TypeError, KeyError):
                        continue
            else:
                for r in s.get("lines", []):
                    ref = r["ref"] if isinstance(r, dict) else r
                    try:
                        shown.add((s["file"], int(ref)))
                    except (ValueError, TypeError):
                        continue
    return shown


def rendered_refs(board: dict[str, Any]) -> set[tuple[str, int]]:
    """Changed lines the engine renders as code: diff rows only.

    Cites, list items, and symbol mentions never render the cited code text:
    the engine shows them as ref labels and receipt links. Only a diff scene
    paints the lines, so only diff refs count as displayed code.
    """
    shown: set[tuple[str, int]] = set()
    for s in board.get("scenes", []):
        if s.get("type") != "diff":
            continue
        rows = s.get("rows") or []
        if rows:
            for r in rows:
                if "text" not in r:
                    continue
                try:
                    shown.add((s["file"], int(r["ref"])))
                except (ValueError, TypeError, KeyError):
                    continue
        else:
            for r in s.get("lines", []):
                ref = r["ref"] if isinstance(r, dict) else r
                try:
                    shown.add((s["file"], int(ref)))
                except (ValueError, TypeError):
                    continue
    return shown


def _fmt(path: str, n: int) -> str:
    return path + ":-" + str(-n) if n < 0 else path + ":" + str(n)


def line_coverage(board: dict[str, Any], m: dict[str, Any]) -> dict[str, Any]:
    """Changed lines on screen, from original +/- hunks and rendered diff rows.

    The denominator is the file totals (added + removed), not the hunk refs:
    oversize and opaque files keep exact counts but no hunks, so their lines
    have no refs and cannot be quoted. Only engine-rendered diff rows count
    as shown; cites and mentions do not render code.
    """
    changed = changed_refs(m)
    rendered = rendered_refs(board)
    cited = cited_refs(board)
    shown = {k for k in changed if k in rendered}
    missing = sorted((k for k in changed if k not in shown), key=lambda k: (k[0], k[1]))
    total = sum(f.get("added", 0) + f.get("removed", 0) for f in m.get("files", []))
    unavailable = max(0, total - len(changed))
    kinds: dict[str, Any] = {}
    for f in m.get("files", []):
        if "path" in f:
            kinds[f["path"]] = f.get("kind")
    if not kinds:
        for f in m.get("brief", {}).get("files", []):
            if "path" in f:
                kinds[f["path"]] = f.get("kind")
    on_screen = {p for p, _ in cited}

    def hit(sym: dict[str, Any]) -> bool:
        for path, n in cited:
            if path != sym.get("path"):
                continue
            span = sym.get("span") if n > 0 else sym.get("base_span")
            if span and span[0] <= abs(n) <= span[1]:
                return True
        return False

    syms = m.get("symbols", [])
    changed_syms = [s for s in syms if s.get("status") in ("added", "modified")]
    return {
        "total": total,
        "shown": len(shown),
        "known": len(changed),
        "missing": [_fmt(p, n) for p, n in missing],
        "unavailable": unavailable,
        "files_shown": len(set(kinds) & on_screen),
        "files_total": len(kinds),
        "symbols_touched": sum(1 for s in changed_syms if hit(s)),
        "symbols_changed": len(changed_syms),
    }


def coverage_summary(cov: dict[str, Any]) -> str:
    """One honest line: changed lines on screen, never files-on-screen."""
    line = "changed lines " + str(cov["shown"]) + "/" + str(cov["total"]) + " on screen"
    if cov.get("unavailable"):
        line += "; " + str(cov["unavailable"]) + " without diff references"
    return line


def silent_estimate(board: dict[str, Any]) -> float:
    """Seconds of silent video: exact for voice none, before any synthesis."""
    from prc.explainer.timing import predict
    from prc.explainer.voice import NoneBackend

    return predict(board, NoneBackend())


def join_preflight(board: dict[str, Any], m: dict[str, Any]) -> list[str]:
    """Diff scenes the render join gate would reject: blank lines, bad cuts."""
    errs: list[str] = []
    order = _order(m)
    for i, s in enumerate(board.get("scenes", [])):
        if s.get("type") != "diff":
            continue
        refs = [(r["ref"] if isinstance(r, dict) else r) for r in s.get("lines", [])]
        texts: dict[str, tuple[str, str]] = {}
        for ref in refs:
            ln = order.get((s.get("file"), ref))
            if ln is None:
                continue
            texts[ref] = (ln.get("op", " "), _post(ln.get("text", "")))
        nonblank = [t for _, t in texts.values() if t.strip()]
        cut = min(len(t) - len(t.lstrip()) for t in nonblank) if nonblank else 0
        for ref in refs:
            if ref not in texts:
                continue
            op, t = texts[ref]
            if op in ("+", "-") and not t.strip():
                errs.append(
                    "scene "
                    + str(i)
                    + ": "
                    + ref
                    + " is a blank changed line; the render join gate fails it with [CUT_NOT_SPACES]"
                )
            elif t.strip():
                head = t[:cut]
                if head != " " * len(head) or len(t) < cut:
                    errs.append(
                        "scene "
                        + str(i)
                        + ": "
                        + ref
                        + " fails the render join gate [CUT_NOT_SPACES]: first "
                        + str(cut)
                        + " chars are not all spaces"
                    )
    return errs


def _scene_geom(
    rows: list[tuple[str, str]], nums: list[int], label: Any
) -> tuple[int, int, dict[str, Any], int]:
    """Gutter, wrap columns, per-row wrap map, and engine font size for a diff scene."""
    gutter = math.ceil((len(str(max(nums))) + 1) * 0.72) if nums else 1
    cols = WRAP_WIDTH - gutter
    wrapped: dict[str, Any] = {}
    longest = 0
    for ref, t in rows:
        toks = [{"text": t, "cls": ""}]
        hang, breaks = wrap_row(toks, cols)
        pieces = [x["text"] for x in toks]
        wrapped[ref] = (hang, breaks, pieces)
        w = 0
        for idx, piece in enumerate(pieces):
            if idx in breaks:
                longest = max(longest, w)
                w = hang
            w += len(piece)
        longest = max(longest, w)
    width_bound = math.floor(1560 / ((longest + gutter) * 0.6 + 2))

    def tall_at(fs: int) -> int:
        rh = round(fs * 1.75)
        n = sum(rh * (len(wrapped[ref][1]) + 1) for ref, _ in rows)
        return n + 24 + (72 if label else 0) + 48

    def top_at(tall: int) -> int:
        return max(118, round(489 - tall / 2))

    fs = min(40, width_bound)
    while fs > 22 and top_at(tall_at(fs)) + tall_at(fs) > 862:
        fs -= 1
    return gutter, cols, wrapped, max(22, fs)


def note_risks(board: dict[str, Any], m: dict[str, Any]) -> list[str]:
    """Diff notes whose box cannot fit beside their line: clamped notes cover code."""
    risks: list[str] = []
    order = _order(m)
    for i, s in enumerate(board.get("scenes", [])):
        if s.get("type") != "diff":
            continue
        refs = [(r["ref"] if isinstance(r, dict) else r) for r in s.get("lines", [])]
        rows: list[tuple[str, str]] = []
        nums: list[int] = []
        for ref in refs:
            ln = order.get((s.get("file"), ref))
            if ln is None:
                continue
            rows.append((ref, _post(ln.get("text", ""))))
            nums.append(ln["old"] if ln.get("op") == "-" else ln["new"])
        nonblank = [t for _, t in rows if t.strip()]
        cut = min(len(t) - len(t.lstrip()) for t in nonblank) if nonblank else 0
        rows = [(ref, t[cut:]) for ref, t in rows]
        if not rows:
            continue
        gutter, cols, wrapped, fs = _scene_geom(rows, nums, s.get("label"))
        char_w = 0.6 * fs
        digits = max(1, *[len(str(n)) for n in nums])
        code_start = (digits + 1) * char_w + 56
        for c in s.get("cues", []):
            if c.get("do") != "note" or "line" not in c:
                continue
            if c["line"] not in wrapped:
                continue
            hang, breaks, pieces = wrapped[c["line"]]
            tail = pieces[breaks[-1] :] if breaks else pieces
            last_cols = (hang if breaks else 0) + sum(len(p) for p in tail)
            note_w = len(c.get("text", "")) * NOTE_PX_PER_CHAR + NOTE_PX_PAD
            desired = code_start + last_cols * char_w + 32
            limit = STAGE_RIGHT - note_w - 20
            if desired > limit:
                risks.append(
                    "scene "
                    + str(i)
                    + ": note on line "
                    + str(c["line"])
                    + " overlaps code; shorten the note or pick shorter lines"
                )
    return risks
