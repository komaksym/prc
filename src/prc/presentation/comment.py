"""The PR comment: headline, card placeholder, a Mermaid flowchart, and brief facts.

Mermaid rules (docs/mvp/PLAN.md Stage 5): nodes are `n1`, `n2`, ... with the
short qualname in double quotes. Labels strip backticks, newlines and control
characters, then escape `#` as `#35;` first, `"` as `#quot;`, `<` as `#lt;`
and `>` as `#gt;`, cut to 60 characters. Edges are `-->` (added, green),
`-.->` (removed, red) and `---` (kept), with `classDef` per change status.
Node order: changed symbols on the tour path, then symbols with the most
added/removed calls, then their direct callers. At most 12 nodes.

Every PR-controlled string in the Markdown text goes through
`render_brief.span()`. Mermaid labels never go through `span()`.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from prc.presentation.card import (
    compute_stats,
    headline,
    look_first,
    risky,
    untested,
)
from prc.presentation.render_brief import span

MAX_NODES = 12
LABEL_LIMIT = 60
CHANGED = ("added", "modified", "deleted")
_EDGE_FORM = {"added": "-->", "removed": "-.->", "kept": "---"}
_EDGE_COLOR = {"added": "#3fd68a", "removed": "#f4676f"}
_CLASS_DEF = {
    "added": "classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;",
    "modified": "classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;",
    "deleted": "classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;",
}
_NODE_DEF = re.compile(r'^n\d+\["((?:#(35|quot|lt|gt);|[^"#\n`<>])*)"\]$')
_EDGE_LINE = re.compile(r"^n\d+ (-->|-\.->|---) n\d+$")
_CLASS_LINE = re.compile(r"^class n\d+ (added|modified|deleted)$")
_LINK_LINE = re.compile(r"^linkStyle \d+ stroke:#[0-9a-fA-F]{6}(,stroke-width:\d+px)?$")
_DEF_LINES = (
    "classDef added fill:#123626,stroke:#3fd68a,color:#eceef3;",
    "classDef modified fill:#3a2b10,stroke:#f2b33d,color:#eceef3;",
    "classDef deleted fill:#3d1a1d,stroke:#f4676f,color:#eceef3;",
)


def short_label(qualname: str) -> str:
    """The last dotted segment: `LinkedInMDPClient._get_paged` becomes `_get_paged`."""
    return qualname.split(".")[-1].split("::")[-1]


def mermaid_label(qualname: str) -> str:
    """Escape a label in PLAN order: `#` first, then `"`, `<`, `>`. Cut to 60."""
    flat = "".join(
        ch
        for ch in short_label(qualname).replace("`", "")
        if not unicodedata.category(ch).startswith("C")
    )
    text = re.sub(r"\s+", " ", flat).strip()
    text = text.replace("#", "#35;").replace('"', "#quot;")
    return text.replace("<", "#lt;").replace(">", "#gt;")[:LABEL_LIMIT]


def select_nodes(m: dict[str, Any]) -> list[str]:
    """Up to 12 symbol ids: tour path first, then most changed calls, then callers."""
    by_id = {s["id"]: s for s in m.get("symbols", [])}
    changed = {sid for sid, s in by_id.items() if s.get("status") in CHANGED}
    tour_ids = [
        sid for step in m.get("tour", []) for sid in step.get("focus", ()) if sid in changed
    ]
    picked = list(dict.fromkeys(tour_ids))
    churn: dict[str, int] = {sid: 0 for sid in changed}
    for e in m.get("edges", []):
        if e.get("status") in ("added", "removed"):
            for end in (e.get("source"), e.get("target")):
                if end in churn:
                    churn[end] += 1
    volume = {sid: by_id[sid].get("added", 0) + by_id[sid].get("removed", 0) for sid in changed}
    for sid in sorted(changed, key=lambda i: (-churn[i], -volume[i], i)):
        if sid not in picked:
            picked.append(sid)
        if len(picked) >= MAX_NODES:
            break
    if len(picked) < MAX_NODES:
        callers = sorted(
            {
                e["source"]
                for e in m.get("edges", [])
                if e.get("target") in picked and e.get("source") in by_id
            }
        )
        for sid in callers:
            if sid not in picked:
                picked.append(sid)
            if len(picked) >= MAX_NODES:
                break
    return picked[:MAX_NODES]


def check_mermaid(block: str) -> list[str]:
    """The grammar gate: only the constructs select_nodes/mermaid_block emit."""
    errors: list[str] = []
    fenced = block.strip()
    if fenced.startswith("```mermaid"):
        fenced = fenced[len("```mermaid") :].split("```")[0]
    lines = [line.strip() for line in fenced.strip().splitlines() if line.strip()]
    if not lines or lines[0] != "flowchart LR":
        return ["first line must be `flowchart LR`"]
    defined: set[str] = set()
    edges: list[tuple[str, str, str]] = []
    for line in lines[1:]:
        node = _NODE_DEF.match(line)
        if node is not None:
            defined.add(line.split("[", 1)[0])
            continue
        edge = _EDGE_LINE.match(line)
        if edge is not None:
            edges.append((line.split(" ", 1)[0], edge.group(1), line.rsplit(" ", 1)[1]))
            continue
        if line in _DEF_LINES or _CLASS_LINE.match(line) or _LINK_LINE.match(line):
            continue
        errors.append(f"unknown construct: {line[:60]}")
    for src, _form, dst in edges:
        if src not in defined:
            errors.append(f"edge from undefined node: {src}")
        if dst not in defined:
            errors.append(f"edge to undefined node: {dst}")
    return errors


def mermaid_block(m: dict[str, Any]) -> str:
    """A fenced `flowchart LR` of the core change, at most 12 nodes."""
    by_id = {s["id"]: s for s in m.get("symbols", [])}
    ids = select_nodes(m)
    chosen = set(ids)
    node_of = {sid: f"n{i + 1}" for i, sid in enumerate(ids)}
    lines = ["```mermaid", "flowchart LR"]
    for sid in ids:
        lines.append(f'{node_of[sid]}["{mermaid_label(by_id[sid]["qualname"])}"]')
    lines += [_CLASS_DEF["added"], _CLASS_DEF["modified"], _CLASS_DEF["deleted"]]
    edges = sorted(
        (e["source"], e["target"], e["status"])
        for e in m.get("edges", [])
        if e.get("source") in chosen and e.get("target") in chosen
    )
    for n, (src, dst, status) in enumerate(edges):
        lines.append(f"{node_of[src]} {_EDGE_FORM[status]} {node_of[dst]}")
        if status in _EDGE_COLOR:
            lines.append(f"linkStyle {n} stroke:{_EDGE_COLOR[status]},stroke-width:2px")
    for sid in ids:
        status = by_id[sid].get("status")
        if status in CHANGED:
            lines.append(f"class {node_of[sid]} {status}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _brief_of(m: dict[str, Any], brief: Any) -> dict[str, Any]:
    if brief is not None and isinstance(brief, dict):
        return brief
    if brief is not None:
        return {
            "mismatches": [
                {"quote": x.quote, "fact": x.fact, "subjects": list(x.subjects)}
                for x in brief.mismatches
            ],
            "look_first": [
                {"path": p.path, "reason": p.reason, "lines": list(p.lines)}
                for p in brief.look_first
            ],
        }
    raw = m.get("brief", {})
    return raw if isinstance(raw, dict) else {}


def render_comment(
    m: dict[str, Any], brief: Any = None, board: dict[str, Any] | None = None
) -> str:
    """comment.md in PLAN order. PR strings via span(); Mermaid labels never."""
    b = _brief_of(m, brief)
    changed = [s for s in m.get("symbols", []) if s.get("status") in CHANGED]
    test_paths = (
        {f.path for f in brief.files if f.kind == "test"}
        if brief is not None and not isinstance(brief, dict)
        else {
            f["path"]
            for f in (brief or m.get("brief", {})).get("files", [])
            if f.get("kind") == "test"
        }
    )
    missing = untested(m, brief if brief is not None else m.get("brief"))
    lines = [f"# {span(headline(m, board))}", ""]
    lines += [
        "![PR card](card.png)",
        "",
        "Upload `card.png` with this comment: images do not embed from the repo.",
        "",
        mermaid_block(m),
    ]
    if len(changed) > MAX_NODES:
        lines += [f"Showing {MAX_NODES} of {len(changed)} changed symbols. Full map: map.html", ""]
    entries = look_first(m, brief if brief is not None else m.get("brief"), 3, board)
    lines += ["## Look here first", ""]
    if entries:
        lines += [f"- {span(e.name)} in {span(e.path)}" for e in entries]
    else:
        lines += ["Nothing stands out."]
    lines += ["", "## Risky surfaces and description vs diff", ""]
    surfaces = risky(m, brief if brief is not None else m.get("brief"))
    if surfaces:
        lines += [f"- {span(r.path)}: {r.reason}" for r in surfaces]
    else:
        lines += ["No risky surfaces."]
    mismatches = b.get("mismatches", [])
    if mismatches:
        for x in mismatches:
            subjects = ", ".join(span(s) for s in x.get("subjects", ()))
            lines.append(f"- {span(x['quote'])}")
            lines.append(f"  - {x['fact']} {subjects}".rstrip())
    elif not surfaces:
        lines += ["Everything the description names is in the diff."]
    lines += ["", "## Not covered by tests", ""]
    if not changed:
        lines += ["No code symbols changed."]
    elif all(s.get("path") in test_paths for s in changed):
        lines += ["No production symbols changed."]
    elif missing:
        lines += [f"- {span(u.name)} in {span(u.path)}" for u in missing]
    else:
        lines += ["Every changed symbol has a direct test."]
    stats = compute_stats(m, brief if brief is not None else m.get("brief"))
    lines += [
        "",
        f"Files {stats.files}, symbols {stats.symbols_changed}, CI {stats.ci_text}.",
        "",
        f"*Written by prc from the code at head `{m.get('head_sha', '')[:12]}`.*",
        "",
    ]
    return "\n".join(lines)
