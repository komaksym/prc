"""Board helpers: show the diff with refs, find lines by needle, measure coverage."""

from __future__ import annotations

from typing import Any

from prc.explainer.preflight import cited_refs, coverage_summary, line_coverage


def show(m: dict[str, Any], wanted: list[str]) -> str:
    """The PR diff from map.json, each hunk line with the ref a board uses."""
    kinds = {f["path"]: f for f in m["brief"]["files"]}
    lines = [f"{m['pr']}  {m['title']}  ({m['author']})"]
    for f in m["files"]:
        if wanted and not any(w in f["path"] for w in wanted):
            continue
        b = kinds.get(f["path"], {})
        lines.append(
            f"\n== {f['path']}  [{b.get('kind', '?')} +{b.get('added', '?')} -{b.get('removed', '?')}]"
        )
        for h in f["hunks"]:
            lines.append("   ...")
            for line in h["lines"]:
                ref = f"-{line['old']}" if line["op"] == "-" else str(line["new"])
                lines.append(f"{ref:>7} {line['op'] if line['op'] in '+-' else ' '} {line['text']}")
    return "\n".join(lines) + "\n"


def find(m: dict[str, Any], needles: list[str], only: str | None = None) -> str:
    """Diff lines containing each needle: path:N for head lines, path:-N for removed lines."""
    out = []
    for needle in needles:
        out.append(f"== {needle!r}")
        for f in m["files"]:
            if only and only not in f["path"]:
                continue
            for h in f["hunks"]:
                for line in h["lines"]:
                    if needle in line["text"]:
                        ref = (
                            f"{f['path']}:{line['new']}"
                            if line["op"] != "-"
                            else f"{f['path']}:-{line['old']}"
                        )
                        out.append(f"  {line['op'] or ' '} {ref:<48} {line['text'].strip()[:110]}")
    return "\n".join(out) + "\n"


def coverage(board: dict[str, Any], m: dict[str, Any]) -> str:
    """How much of the PR a board accounts for. Changed-line counts are literal."""
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

    syms = {s["id"]: s for s in m["symbols"]}
    code = [
        s
        for s in m["symbols"]
        if s["status"] in ("added", "modified") and kinds.get(s["path"]) == "code"
    ]
    stops = [t for t in m["tour"] if t["focus"]]
    stop_hit = [any(hit(syms[f]) for f in t["focus"] if f in syms) for t in stops]
    files_shown = {p for p, _ in shown}
    cov = line_coverage(board, m)

    name = board.get("name", "board")
    covered_files = len(files_shown & set(kinds))
    out = [
        f"{name}: tour stops {sum(stop_hit)}/{len(stops)} · code symbols {sum(map(hit, code))}/{len(code)} · "
        f"files {covered_files}/{len(kinds)}",
        f"covers {covered_files} of {len(kinds)} changed files",
        coverage_summary(cov),
    ]
    if cov["missing"]:
        rest = len(cov["missing"]) - 12
        listed = ", ".join(cov["missing"][:12])
        out.append("  missing changed lines: " + listed + (" ..." if rest > 0 else ""))
    for t, h in zip(stops, stop_hit, strict=True):
        out.append(
            f"  {'x' if h else ' '} {t['kind']:<7} {', '.join(f.split('::')[-1] for f in t['focus'])[:90]}"
        )
    return "\n".join(out) + "\n"


def guide() -> str:
    from pathlib import Path

    return (Path(__file__).resolve().parent / "assets" / "BOARD.md").read_text()
