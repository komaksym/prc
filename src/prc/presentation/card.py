"""The PR card: a 1200x630 summary page screenshotted at 2x.

Stat definitions live here so EVAL gate 6 can reuse them: files is the number
of files in the brief, symbols changed counts added/modified/deleted, call
sites sums `call_sites` over changed symbols, tests touched counts brief files
of kind `test`, CI is passed/total checks or "no CI", and no-direct-test is a
changed symbol outside test files with no incoming edge from a test symbol.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files as _files
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _escape

CHANGED = ("added", "modified", "deleted")
TEMPLATE = _files("prc.presentation") / "assets" / "card.html"


class CardError(RuntimeError):
    """A missing tool or a failed capture, worded for the person running the CLI."""


@dataclass(frozen=True, slots=True)
class CardStats:
    files: int
    symbols_changed: int
    call_sites: int
    tests_touched: int
    ci_passed: int
    ci_total: int
    ci_text: str
    untested_total: int


@dataclass(frozen=True, slots=True)
class LookEntry:
    id: str
    name: str
    path: str
    status: str


@dataclass(frozen=True, slots=True)
class RiskEntry:
    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class UntestedEntry:
    id: str
    name: str
    path: str


def _brief_dict(brief: Any) -> dict[str, Any]:
    """The brief as a plain map.json dict, from a dict or a prc.brief.Brief."""
    if brief is None or isinstance(brief, dict):
        return brief if brief is not None else {}
    return {
        "files": [{"path": f.path, "kind": f.kind, "sensitive": f.sensitive} for f in brief.files],
        "checks": [{"name": c.name, "state": c.state} for c in brief.checks],
    }


def _brief_of(m: dict[str, Any], brief: Any) -> dict[str, Any]:
    if brief is not None:
        return _brief_dict(brief)
    raw = m.get("brief")
    return _brief_dict(raw) if not isinstance(raw, dict) else raw


def _test_paths(brief: dict[str, Any]) -> set[str]:
    return {f["path"] for f in brief.get("files", []) if f.get("kind") == "test"}


def _changed(m: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in m.get("symbols", []) if s.get("status") in CHANGED]


def compute_stats(m: dict[str, Any], brief: Any = None) -> CardStats:
    """Shared stat code: the card shows these, and EVAL gate 6 recomputes them."""
    b = _brief_of(m, brief)
    changed = _changed(m)
    checks = b.get("checks", [])
    passed = sum(1 for c in checks if c.get("state") == "passed")
    return CardStats(
        files=len(b.get("files", [])),
        symbols_changed=len(changed),
        call_sites=sum(s.get("call_sites", 0) for s in changed),
        tests_touched=sum(1 for f in b.get("files", []) if f.get("kind") == "test"),
        ci_passed=passed,
        ci_total=len(checks),
        ci_text=f"{passed}/{len(checks)}" if checks else "no CI",
        untested_total=len(untested(m, b)),
    )


def headline(m: dict[str, Any], board: dict[str, Any] | None = None) -> str:
    """Prefer the final change summary, then the introduction or PR title."""
    if board is not None:
        for scene in board.get("scenes", []):
            if scene.get("type") == "outro" and scene.get("l1"):
                return str(scene["l1"])
        for scene in board.get("scenes", []):
            if scene.get("type") == "title" and scene.get("say"):
                return str(scene["say"][0])
    return str(m.get("title", ""))


def _receipt_refs(board: dict[str, Any] | None) -> list[str]:
    """Displayed diff receipts first, then context receipts in board order."""
    if not board:
        return []
    refs: list[str] = []
    scenes = board.get("scenes", [])
    for scene in scenes:
        if scene.get("type") == "diff" and isinstance(scene.get("file"), str) and scene["file"]:
            for item in scene.get("lines", []):
                ref = item.get("ref", "") if isinstance(item, dict) else item
                if isinstance(ref, str) and ref:
                    refs.append(f"{scene['file']}:{ref}")
            for cue in scene.get("cues", []):
                if isinstance(cue, dict) and isinstance(cue.get("line"), str) and cue["line"]:
                    refs.append(f"{scene['file']}:{cue['line']}")
    for scene in scenes:
        cites = scene.get("cite")
        if isinstance(cites, list):
            for cite in cites:
                if isinstance(cite, dict) and isinstance(cite.get("line"), str) and cite["line"]:
                    refs.append(cite["line"])
        if scene.get("type") == "list" and isinstance(scene.get("items"), list):
            for item in scene["items"]:
                if isinstance(item, dict) and isinstance(item.get("cite"), str) and item["cite"]:
                    refs.append(item["cite"])
        if scene.get("type") == "receipt" and isinstance(scene.get("rows"), list):
            for row in scene["rows"]:
                if not isinstance(row, dict):
                    continue
                if isinstance(row.get("symbol"), str) and row["symbol"]:
                    refs.append(row["symbol"])
                edge = row.get("edge")
                if isinstance(edge, list) and len(edge) == 2:
                    refs.extend(sid for sid in edge if isinstance(sid, str) and sid)
                if isinstance(row.get("line"), str) and row["line"]:
                    refs.append(row["line"])
    return refs


def quoted_files(board: dict[str, Any] | None) -> frozenset[str]:
    """Files the board writer quoted: diff scenes plus cited receipt lines."""
    if not board:
        return frozenset()
    paths: set[str] = set()
    for scene in board.get("scenes", []):
        if isinstance(scene.get("file"), str):
            paths.add(scene["file"])
    for line in _receipt_refs(board):
        if "::" in line:
            continue
        path, _, num = line.rpartition(":")
        try:
            int(num)
        except ValueError:
            continue
        path = path.strip()
        if path:
            paths.add(path)
    return frozenset(paths)


def look_first(
    m: dict[str, Any], brief: Any = None, limit: int = 3, board: dict[str, Any] | None = None
) -> tuple[LookEntry, ...]:
    """Changed symbols displayed in the diff, then cited context and quoted files.

    Displayed symbols lead, then context symbols in cite order. Quoted-file symbols follow by
    changed lines, then coverage, then callers. Quoted lines outside changed symbols
    get a file-level entry. Unquoted symbols keep the coverage-first order.
    """
    tests = _test_paths(_brief_of(m, brief))
    callers: dict[str, int] = {}
    for e in m.get("edges", []):
        callers[e.get("source", "")] = callers.get(e.get("source", ""), 0) + 1
        callers[e.get("target", "")] = callers.get(e.get("target", ""), 0) + 1
    test_symbols = {s["id"] for s in m.get("symbols", []) if s.get("path") in tests}
    covered = {e["target"] for e in m.get("edges", []) if e.get("source") in test_symbols}
    cands = [
        sym
        for sym in m.get("symbols", [])
        if sym.get("status") in CHANGED and sym.get("path") not in tests
    ]
    quoted = quoted_files(board)
    cited = cited_symbol_ids(cands, board)
    rank = {sid: i for i, sid in enumerate(cited)}

    def key(s: dict[str, Any]) -> tuple[int, int, int, int, int]:
        churn = s.get("added", 0) + s.get("removed", 0)
        if s["id"] in rank:
            return (0, rank[s["id"]], 0, 0, 0)
        if s.get("path") in quoted:
            return (1, 0, -churn, int(s["id"] not in covered), -callers.get(s["id"], 0))
        return (2, 0, int(s["id"] not in covered), -callers.get(s["id"], 0), -churn)

    ordered = sorted(cands, key=key)
    entries = [LookEntry(s["id"], s["qualname"], s["path"], s["status"]) for s in ordered]
    fallbacks = _file_fallbacks(m, brief, board, quoted)
    if fallbacks:
        first_rest = next((i for i, s in enumerate(ordered) if key(s)[0] != 0), len(entries))
        entries[first_rest:first_rest] = fallbacks
    return tuple(entries[:limit])


def _symbols_at_ref(cands: list[dict[str, Any]], ref: str) -> list[str]:
    if "::" in ref:
        return [sym["id"] for sym in cands if sym["id"] == ref]
    path, _, num = ref.rpartition(":")
    try:
        lineno = int(num)
    except ValueError:
        return []
    found: list[str] = []
    for sym in cands:
        if sym.get("path") != path.strip():
            continue
        span = sym.get("base_span") if lineno < 0 else sym.get("span")
        if isinstance(span, (list, tuple)) and len(span) == 2 and span[0] <= abs(lineno) <= span[1]:
            found.append(sym["id"])
    return found


def cited_symbol_ids(cands: list[dict[str, Any]], board: dict[str, Any] | None) -> list[str]:
    """Displayed diff symbols first, then cited lines, symbols and edge endpoints."""
    return list(
        dict.fromkeys(sid for ref in _receipt_refs(board) for sid in _symbols_at_ref(cands, ref))
    )


def _file_fallbacks(
    m: dict[str, Any],
    brief: Any,
    board: dict[str, Any] | None,
    quoted: frozenset[str],
) -> list[LookEntry]:
    """One entry per quoted code file with a line outside its changed symbols."""
    if not board:
        return []
    changed = _changed(m)
    with_symbols = {s.get("path") for s in changed}
    unmatched: set[str] = set()
    for ref in _receipt_refs(board):
        if "::" in ref:
            continue
        path, _, num = ref.rpartition(":")
        try:
            int(num)
        except ValueError:
            continue
        if not _symbols_at_ref(changed, ref):
            unmatched.add(path.strip())
    status = {f.get("path"): f.get("status") for f in m.get("files", []) if isinstance(f, dict)}
    return [
        LookEntry(
            f"file:{f['path']}", "top-level change", f["path"], status.get(f["path"]) or "modified"
        )
        for f in _brief_of(m, brief).get("files", [])
        if f.get("kind") == "code"
        and f["path"] in quoted
        and (f["path"] in unmatched or f["path"] not in with_symbols)
    ]


def risky(m: dict[str, Any], brief: Any = None) -> tuple[RiskEntry, ...]:
    """Brief files with a sensitive reason, round-robin by reason."""
    groups: dict[str, list[RiskEntry]] = {}
    for f in _brief_of(m, brief).get("files", []):
        if f.get("sensitive"):
            groups.setdefault(f["sensitive"], []).append(RiskEntry(f["path"], f["sensitive"]))
    for entries in groups.values():
        entries.sort(key=lambda r: r.path)
    ordered: list[RiskEntry] = []
    for i in range(max((len(v) for v in groups.values()), default=0)):
        for entries in groups.values():
            if i < len(entries):
                ordered.append(entries[i])
    return tuple(ordered)


def untested(m: dict[str, Any], brief: Any = None) -> tuple[UntestedEntry, ...]:
    """Changed symbols outside test files with no incoming edge from a test symbol."""
    b = _brief_of(m, brief)
    tests = _test_paths(b)
    test_symbols = {s["id"] for s in m.get("symbols", []) if s.get("path") in tests}
    covered = {e["target"] for e in m.get("edges", []) if e.get("source") in test_symbols}
    return tuple(
        sorted(
            (
                UntestedEntry(s["id"], s["qualname"], s["path"])
                for s in _changed(m)
                if s.get("path") not in tests and s["id"] not in covered
            ),
            key=lambda u: u.id,
        )
    )


def _stat(value: object, label: str, tone: str = "") -> str:
    return (
        f'<div class="stat{tone}"><div class="stat-value">{_escape(str(value))}</div>'
        f'<div class="stat-label">{_escape(label)}</div></div>'
    )


def build_card_html(
    m: dict[str, Any], brief: Any = None, board: dict[str, Any] | None = None
) -> str:
    """Render the card.html template. Every PR-controlled string is HTML-escaped."""
    stats = compute_stats(m, brief)
    entries = look_first(m, brief, 3, board)
    surfaces = risky(m, brief)
    missing = untested(m, brief)
    repo = str(m.get("pr", ""))
    sha = str(m.get("head_sha", ""))

    stats_html = "".join(
        [
            _stat(stats.files, "files"),
            _stat(stats.symbols_changed, "symbols changed"),
            _stat(stats.call_sites, "call sites"),
            _stat(stats.tests_touched, "tests touched"),
            _stat(
                stats.ci_text,
                "CI passed",
                "" if stats.ci_total == 0 or stats.ci_passed == stats.ci_total else " bad",
            ),
            _stat(
                stats.untested_total,
                "no direct test",
                "" if stats.untested_total == 0 else " warn",
            ),
        ]
    )
    look_html = (
        "".join(
            f'<li class="st-{_escape(e.status)}"><span class="name">{_escape(e.name)}</span><br>'
            f'<span class="path">{_escape(e.path)}</span></li>'
            for e in entries
        )
        or '<li><span class="reason">Nothing stands out.</span></li>'
    )
    risky_html = (
        "".join(
            f'<li class="st-modified"><span class="name">{_escape(r.path)}</span><br>'
            f'<span class="reason">{_escape(r.reason)}</span></li>'
            for r in surfaces[:3]
        )
        or '<li><span class="reason">None.</span></li>'
    )
    if len(surfaces) > 3:
        shown_reasons = {r.reason for r in surfaces[:3]}
        hidden = sorted({r.reason for r in surfaces[3:] if r.reason not in shown_reasons})
        suffix = _escape(f": {', '.join(hidden)}") if hidden else ""
        risky_html += f'<li><span class="reason">+{len(surfaces) - 3} more{suffix}</span></li>'
    if not _changed(m):
        untested_html = "<strong>No code symbols changed.</strong>"
    elif all(s.get("path") in _test_paths(_brief_of(m, brief)) for s in _changed(m)):
        untested_html = "No production symbols changed."
    elif missing:
        shown = ", ".join(f'<span class="mono">{_escape(u.name)}</span>' for u in missing[:3])
        rest = f" +{len(missing) - 3} more" if len(missing) > 3 else ""
        untested_html = f"<strong>No direct test:</strong> {shown}{_escape(rest)}"
    else:
        untested_html = "Every changed symbol has a direct test."

    page = TEMPLATE.read_text()
    for token, value in (
        ("EYEBROW", f"PR card · {repo}"),
        ("HEADLINE", headline(m, board)),
        ("STATS", stats_html),
        ("LOOK_FIRST", look_html),
        ("RISKY", risky_html),
        ("UNTESTED", untested_html),
        ("FOOTER", f"computed from the code · {repo} · head {sha[:12]}"),
    ):
        page = page.replace(
            "{{" + token + "}}",
            _escape(value) if token in ("EYEBROW", "HEADLINE", "FOOTER") else value,
        )
    return page


def render_card_png(html_path: Path, out_path: Path) -> Path:
    """Screenshot card.html at 1200x630, scale 2, with the map_video Chromium pattern."""
    from prc.presentation.map_video import CARD_SCALE, CARD_VIEWPORT

    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as error:
        raise CardError(
            "Playwright is not installed. Run `uv sync --extra video` (or "
            "`pip install 'prc[video]'`), then `playwright install chromium`."
        ) from error
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            raise CardError(
                f"Chromium cannot launch ({str(error).splitlines()[0]}). "
                "Run `playwright install chromium`."
            ) from error
        try:
            context = browser.new_context(
                viewport={"width": CARD_VIEWPORT["width"], "height": CARD_VIEWPORT["height"]},
                device_scale_factor=CARD_SCALE,
                color_scheme="dark",
            )
            page = context.new_page()
            page.goto(html_path.resolve().as_uri())
            page.evaluate("document.fonts.ready.then(() => true)")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(page.screenshot(type="png"))
        finally:
            browser.close()
    return out_path
