"""Board helpers: show the diff with refs, find lines by needle, measure coverage."""

from __future__ import annotations

from typing import Any


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
    """How much of the PR a board accounts for. A part counts when a line of it is on screen."""
    kinds = {f["path"]: f["kind"] for f in m["files"]}

    shown = set()
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
    by_kind: dict[str, list[int]] = {}
    for f in m["files"]:
        k = by_kind.setdefault(f["kind"], [0, 0])
        k[0] += f["added"]
        k[1] += f["added"] if f["path"] in files_shown else 0

    name = board.get("name", "board")
    out = [
        f"{name}: tour stops {sum(stop_hit)}/{len(stops)} · code symbols {sum(map(hit, code))}/{len(code)} · "
        f"files {len(files_shown & set(kinds))}/{len(kinds)}",
        "  added lines in files on screen, by kind: "
        + ", ".join(f"{k} {v[1]}/{v[0]}" for k, v in by_kind.items()),
    ]
    for t, h in zip(stops, stop_hit, strict=True):
        out.append(
            f"  {'x' if h else ' '} {t['kind']:<7} {', '.join(f.split('::')[-1] for f in t['focus'])[:90]}"
        )
    return "\n".join(out) + "\n"


def guide() -> str:
    from pathlib import Path

    return (Path(__file__).resolve().parent / "assets" / "BOARD.md").read_text()
