"""ChangeMap to PR Lens GraphDoc (graph contract 0.2.0)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Literal

from prc.brief import Delta, kind_of
from prc.changemap import ChangeMap, FileNode, Step, Symbol
from prc.facts import compute_facts
from prc.identity import to_jsonable

SCHEMA_VERSION = "0.2.0"
MAX_NODES = 256
MAX_EDGES = 512
MAX_STEPS = 12
MAX_LABEL = 120
MAX_HEADING = 48
MAX_BODY = 140
MAX_RISKY_FILES = 12
GROUPED_AT = 40
LANE_ORDER = ("files", "callers", "changed", "callees", "tests")
LANE_LABELS = {
    "files": "Changed files",
    "callers": "Callers",
    "changed": "Changed code",
    "callees": "Callees",
    "tests": "Tests",
}
LaneName = Literal["files", "callers", "changed", "callees", "tests"]
SYMBOL_DELTA = {
    "added": "added",
    "modified": "modified",
    "deleted": "removed",
    "context": "unchanged",
}
FILE_DELTA = {"added": "added", "modified": "modified", "deleted": "removed"}
EDGE_DELTA = {"added": "added", "removed": "removed", "kept": "unchanged"}
_ID = re.compile("^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_SHA = re.compile("^[0-9a-f]{7,40}$")
_PR = re.compile("^([^/]+)/([^#]+)#([0-9]+)$")
_PACKAGE_NAMES = frozenset(
    {
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.toml",
        "Cargo.lock",
        "go.mod",
        "go.sum",
        "pyproject.toml",
        "poetry.lock",
        "uv.lock",
        "Gemfile",
        "Gemfile.lock",
        "composer.json",
        "composer.lock",
        "requirements.txt",
        "setup.py",
        "setup.cfg",
    }
)


@dataclass(frozen=True, slots=True)
class Plotted:
    """A converted map: the GraphDoc, index maps into map.json, and drop counts."""

    doc: dict[str, Any]
    symbol_index: dict[str, int]
    file_index: dict[str, int]
    dropped_symbols: int
    dropped_edges: int


def _lanes(change_map: ChangeMap) -> dict[str, LaneName]:
    kinds = {f.path: f.kind for f in change_map.files}

    def is_test(path: str) -> bool:
        return kinds.get(path, kind_of(Delta(path, False, 0, 0))) == "test"

    lanes: dict[str, LaneName] = {}
    for symbol in change_map.symbols:
        if is_test(symbol.path):
            lanes[symbol.id] = "tests"
        elif symbol.status != "context":
            lanes[symbol.id] = "changed"
    for symbol in change_map.symbols:
        if symbol.id not in lanes:
            calls_change = any(
                e.source == symbol.id and lanes.get(e.target) == "changed" for e in change_map.edges
            )
            lanes[symbol.id] = "callers" if calls_change else "callees"
    return lanes


def _shorten(text: str, cap: int) -> str:
    """Cut at a whole word to cap characters; fall back to a hard cut."""
    if len(text) <= cap:
        return text
    cut = text[:cap].rsplit(" ", 1)[0]
    return cut if cut else text[:cap]


def _left_cut(path: str, cap: int) -> str:
    """Cut from the left so the file name stays."""
    if len(path) <= cap:
        return path
    return "..." + path[-(cap - 3) :]


def _symbol_kind(kind: str, lane: LaneName) -> str:
    if lane == "tests":
        return "test"
    if kind == "class":
        return "module"
    return "function"


def _file_kind(kind: str, path: str) -> str:
    if kind == "test":
        return "test"
    if kind == "config":
        return "config"
    name = path.rsplit("/", 1)[-1]
    if name in _PACKAGE_NAMES or name.endswith(".lock"):
        return "package"
    if kind == "code":
        return "module"
    return "other"


def _node_files(path: str, span: tuple[int, int] | None, revision: str) -> list[dict[str, Any]]:
    ref: dict[str, Any] = {"path": path}
    if span is not None and span[0] >= 1 and span[1] >= span[0]:
        ref["startLine"] = span[0]
        ref["endLine"] = span[1]
    ref["revision"] = revision
    return [ref]


def _badges(added: int, removed: int, sensitive: str | None) -> list[str]:
    out: list[str] = []
    if added or removed:
        out.append("+" + str(added) + " / -" + str(removed))
    if sensitive:
        out.append(_shorten(sensitive, MAX_LABEL))
    return out[:6]


def _risky_paths(change_map: ChangeMap) -> list[str]:
    seen: list[str] = []
    paths = {f.path for f in change_map.files}
    for step in change_map.tour:
        if step.kind != "risky_file":
            continue
        for focus in step.focus:
            if focus in paths and focus not in seen:
                seen.append(focus)
    return seen[:MAX_RISKY_FILES]


@dataclass(frozen=True, slots=True)
class Group:
    """One overview card: a folder, or one file when its folder holds few files."""

    label: str
    is_dir: bool
    members: tuple[str, ...]
    added: int
    modified: int
    deleted: int
    tests: int


def _folder_of(path: str) -> str:
    return str(PurePosixPath(path).parent)


def _make_group(label: str, is_dir: bool, members: list[Symbol], kinds: Mapping[str, str]) -> Group:
    by_id = sorted(members, key=lambda s: s.id)
    return Group(
        label,
        is_dir,
        tuple(s.id for s in by_id),
        sum(s.status == "added" for s in by_id),
        sum(s.status == "modified" for s in by_id),
        sum(s.status == "deleted" for s in by_id),
        sum(kinds.get(s.path) == "test" for s in by_id),
    )


def groups_of(change_map: ChangeMap) -> tuple[Group, ...]:
    """Overview cards for PRs changing more than GROUPED_AT symbols, else none.

    One card per folder, or per file when a folder holds fewer than 3 changed files.
    Members are the changed symbols; context symbols stay outside the groups.
    Sorted by label, so the result never depends on input order.
    """
    kinds = {f.path: f.kind for f in change_map.files}
    changed = sorted((s for s in change_map.symbols if s.status != "context"), key=lambda s: s.id)
    if len(changed) <= GROUPED_AT:
        return ()
    by_file: dict[str, list[Symbol]] = {}
    for symbol in changed:
        by_file.setdefault(symbol.path, []).append(symbol)
    by_folder: dict[str, list[str]] = {}
    for path in by_file:
        by_folder.setdefault(_folder_of(path), []).append(path)
    out: list[Group] = []
    for folder in sorted(by_folder):
        paths = sorted(by_folder[folder])
        if len(paths) >= 3:
            out.append(
                _make_group(folder, True, [s for path in paths for s in by_file[path]], kinds)
            )
        else:
            for path in paths:
                out.append(_make_group(path, False, by_file[path], kinds))
    return tuple(sorted(out, key=lambda g: g.label))


def _group_subtitle(group: Group) -> str:
    total = group.added + group.modified + group.deleted
    return _shorten(
        str(total)
        + " changed: "
        + str(group.added)
        + " added, "
        + str(group.modified)
        + " modified, "
        + str(group.deleted)
        + " deleted",
        MAX_LABEL,
    )


def _select(change_map: ChangeMap) -> tuple[list[int], list[int], list[str]]:
    """Map indices of plotted symbols and files, plus aggregate file paths.

    Deterministic under the 256-node cap: risky files first, then changed
    symbols by churn, then context symbols, then remaining file nodes.
    """
    symbols = list(change_map.symbols)
    files = list(change_map.files)
    file_at = {f.path: i for i, f in enumerate(files)}
    risky = [file_at[p] for p in _risky_paths(change_map) if p in file_at][: max(0, MAX_NODES)]
    if not symbols:
        remaining = [i for i in range(len(files)) if i not in risky]
        return [], sorted(risky + remaining[: max(0, MAX_NODES - len(risky))]), []
    changed = [i for i, s in enumerate(symbols) if s.status != "context"]
    changed.sort(key=lambda i: (-(symbols[i].added + symbols[i].removed), i))
    context = [i for i, s in enumerate(symbols) if s.status == "context"]
    picked = (changed + context)[: max(0, MAX_NODES - len(risky))]
    shown_paths = {symbols[i].path for i in picked} | {files[i].path for i in risky}
    aggregates = [path for path in sorted(file_at) if path not in shown_paths]
    room = max(0, MAX_NODES - len(risky) - len(picked))
    return picked, risky, aggregates[:room]


def picked_steps(change_map: ChangeMap) -> tuple[Step | None, ...]:
    """Tour steps behind the walkthrough: None marks synthetic overview/summary."""
    tour = list(change_map.tour)
    risky = [s for s in tour if s.kind == "risky_file"][:2]
    walk = [s for s in tour if s.kind in ("entry", "callee")][:8]
    tests = [s for s in tour if s.kind == "test"][:1]
    middle: tuple[Step | None, ...] = tuple(risky + walk + tests)
    room = MAX_STEPS - 2
    if len(middle) > room:
        middle = middle[:room]
    return (None,) + middle + (None,)


def _walk_ids(middle: tuple[Step, ...]) -> set[str]:
    ids: set[str] = set()
    for step in middle:
        ids.update(step.focus)
        if step.via is not None:
            ids.add(step.via)
    return ids


def _order_edges(
    change_map: ChangeMap, at: dict[str, int], walk: set[str]
) -> tuple[list[int], int | None]:
    """Edge map indices between plotted nodes in priority order, plus hero index."""
    order = {"added": 0, "removed": 1, "kept": 2}
    scored: list[tuple[tuple[int, int, int, int], int]] = []
    for k, e in enumerate(change_map.edges):
        if e.source not in at or e.target not in at:
            continue
        tour = 0 if e.source in walk and e.target in walk else 1
        res = 0 if e.resolution == "exact" else 1
        scored.append(((tour, order[e.status], res, k), k))
    scored.sort()
    kept = [k for _, k in scored[:MAX_EDGES]]
    hero: int | None = None
    for _, k in scored:
        e = change_map.edges[k]
        if (
            e.status == "added"
            and e.resolution == "exact"
            and e.source in walk
            and e.target in walk
        ):
            hero = k
            break
    if hero is not None and hero not in kept:
        hero = None
    return kept, hero


def _status_word(status: str) -> str:
    return {"added": "New", "modified": "Changed", "deleted": "Deleted"}.get(status, "Unchanged")


def _short_name(symbol_id: str) -> str:
    return symbol_id.rsplit("::", 1)[-1].rsplit(".", 1)[-1]


def _overview(change_map: ChangeMap) -> tuple[str, str]:
    changed = sum(1 for s in change_map.symbols if s.status != "context")
    added = sum(1 for e in change_map.edges if e.status == "added")
    removed = sum(1 for e in change_map.edges if e.status == "removed")
    heading = "What changed"
    body = _shorten(
        change_map.title
        + " - "
        + str(len(change_map.files))
        + " files, "
        + str(changed)
        + " symbols, "
        + str(added)
        + " calls added, "
        + str(removed)
        + " removed.",
        MAX_BODY,
    )
    return heading, body


def _risky_step(change_map: ChangeMap, step: Step) -> tuple[str, str]:
    path = step.focus[0] if step.focus else ""
    base = path.rsplit("/", 1)[-1]
    reason = "Sensitive file"
    for f in change_map.files:
        if f.path == path and f.sensitive:
            reason = f.sensitive
    heading = _shorten("Risky: " + base if base else "Risky file", MAX_HEADING)
    return heading, _shorten(reason + ": " + path if path else reason, MAX_BODY)


def _symbol_step(change_map: ChangeMap, step: Step) -> tuple[str, str]:
    sid = step.focus[0] if step.focus else ""
    by_id = {s.id: s for s in change_map.symbols}
    sym = by_id.get(sid)
    name = _shorten(_short_name(sid) if sid else step.kind, MAX_HEADING)
    if sym is None:
        return name, _shorten(step.kind + " " + sid if sid else step.kind, MAX_BODY)
    if step.kind == "test":
        targets = sorted(
            {e.target for e in change_map.edges if e.source == sid and e.target != sid}
        )
        cover = "calls " + ", ".join(_short_name(t) for t in targets[:2]) if targets else "changed"
        return _shorten("Test " + sym.qualname, MAX_HEADING), _shorten(
            _status_word(sym.status) + " test " + cover + ".", MAX_BODY
        )
    via = _short_name(step.via) if step.via else ""
    tail = "called by " + via if via else sym.path
    return _shorten(sym.qualname, MAX_HEADING), _shorten(
        _status_word(sym.status)
        + " +"
        + str(sym.added)
        + " -"
        + str(sym.removed)
        + "; "
        + tail
        + ".",
        MAX_BODY,
    )


def _summary_step(change_map: ChangeMap) -> tuple[str, str]:
    facts = compute_facts(to_jsonable(change_map))
    return "Summary", _shorten(facts.test_verdict if facts.test_verdict else "Done.", MAX_BODY)


def _focus_ids(step: Step, at: dict[str, int], file_at: dict[str, int]) -> list[str]:
    ids: list[str] = []
    for focus in step.focus:
        if focus in at and "s" + str(at[focus]) not in ids:
            ids.append("s" + str(at[focus]))
        elif focus in file_at and "f" + str(file_at[focus]) not in ids:
            ids.append("f" + str(file_at[focus]))
    return ids


def _provenance(change_map: ChangeMap) -> dict[str, Any]:
    match = _PR.match(change_map.pr)
    if match:
        owner, name, number = match.group(1), match.group(2), int(match.group(3))
    else:
        owner, name, number = "local", "prc", 0
    prov: dict[str, Any] = {
        "repo": {"owner": owner, "name": name},
        "base": {"sha": change_map.base_sha},
        "head": {"sha": change_map.head_sha},
    }
    if number >= 1:
        pr: dict[str, Any] = {"number": number}
        if change_map.title:
            pr["title"] = _shorten(change_map.title, 512)
        if change_map.url and change_map.url.startswith("http"):
            pr["url"] = change_map.url
        prov["pullRequest"] = pr
    prov["generator"] = {"name": "prc"}
    return prov


def _file_node(
    path: str,
    index: int,
    kind: str,
    delta: str,
    added: int,
    removed: int,
    sensitive: str | None,
    subtitle: str | None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": "f" + str(index),
        "label": _left_cut(path, MAX_LABEL),
        "kind": kind,
        "delta": delta,
        "lane": "files",
        "files": [{"path": path, "revision": "base" if delta == "removed" else "head"}],
        "badges": _badges(added, removed, sensitive),
    }
    if subtitle is not None:
        node["subtitle"] = subtitle
    return node


def _symbol_node(symbols: list[Symbol], index: int, lane: LaneName) -> dict[str, Any]:
    s = symbols[index]
    rev = "base" if s.status == "deleted" else "head"
    span = s.base_span if s.status == "deleted" else s.span
    return {
        "id": "s" + str(index),
        "label": _shorten(s.qualname or s.id, MAX_LABEL),
        "kind": _symbol_kind(s.kind, lane),
        "delta": SYMBOL_DELTA[s.status],
        "lane": lane,
        "files": _node_files(s.path, span, rev),
        "badges": _badges(s.added, s.removed, None),
    }


def _group_delta(group: Group) -> str:
    total = group.added + group.modified + group.deleted
    if group.added == total:
        return "added"
    if group.deleted == total:
        return "removed"
    return "modified"


def _group_node(
    group: Group, index: int, kinds: Mapping[str, str], lines: dict[str, tuple[int, int]]
) -> dict[str, Any]:
    kind = "module" if group.is_dir else _file_kind(kinds.get(group.label, "code"), group.label)
    added = sum(lines.get(sid, (0, 0))[0] for sid in group.members)
    removed = sum(lines.get(sid, (0, 0))[1] for sid in group.members)
    badges = _badges(added, removed, None)
    if group.tests:
        badges = (badges + [str(group.tests) + " tests"])[:6]
    return {
        "id": "g" + str(index),
        "label": _left_cut(group.label, MAX_LABEL),
        "kind": kind,
        "delta": _group_delta(group),
        "lane": "files",
        "subtitle": _group_subtitle(group),
        "files": []
        if group.is_dir
        else [
            {
                "path": group.label,
                "revision": "base" if _group_delta(group) == "removed" else "head",
            }
        ],
        "badges": badges,
    }


def to_graph_doc(change_map: ChangeMap) -> Plotted:
    """Convert a ChangeMap into a fully inflated GraphDoc with index maps."""
    lanes = _lanes(change_map)
    symbols = list(change_map.symbols)
    files = list(change_map.files)
    file_at = {f.path: i for i, f in enumerate(files)}
    groups = groups_of(change_map)
    if groups:
        return _overview_doc(change_map, groups, lanes, symbols, files, file_at)
    picked, risky, aggs = _select(change_map)
    at = {symbols[i].id: i for i in picked}
    plotted_files = set(risky) | {file_at[p] for p in aggs if p in file_at}
    counts: dict[str, int] = {}
    for s in symbols:
        counts[s.path] = counts.get(s.path, 0) + 1
    nodes: list[dict[str, Any]] = []
    for i in picked:
        nodes.append(_symbol_node(symbols, i, lanes[symbols[i].id]))
    for j in risky:
        f = files[j]
        nodes.append(
            _file_node(
                f.path,
                j,
                _file_kind(f.kind, f.path),
                FILE_DELTA[f.status],
                f.added,
                f.removed,
                f.sensitive,
                None,
            )
        )
    for p in aggs:
        if p not in file_at:
            continue
        j = file_at[p]
        f = files[j]
        shown = sum(1 for i in picked if symbols[i].path == p)
        total = counts.get(p, 0)
        nodes.append(
            _file_node(
                f.path,
                j,
                _file_kind(f.kind, f.path),
                FILE_DELTA[f.status],
                f.added,
                f.removed,
                f.sensitive,
                str(shown) + " of " + str(total) + " symbols shown" if total else None,
            )
        )
    return _finish(change_map, symbols, files, nodes, at, plotted_files)


def _finish(
    change_map: ChangeMap,
    symbols: list[Symbol],
    files: list[FileNode],
    nodes: list[dict[str, Any]],
    at: dict[str, int],
    plotted_files: set[int],
) -> Plotted:
    middle = [s for s in picked_steps(change_map) if s is not None]
    kept, hero = _order_edges(change_map, at, _walk_ids(tuple(middle)))
    edges: list[dict[str, Any]] = []
    for k in kept:
        e = change_map.edges[k]
        if k == hero:
            emphasis = "hero"
        elif e.status == "removed" or e.resolution == "name":
            emphasis = "muted"
        else:
            emphasis = "normal"
        item: dict[str, Any] = {
            "id": "e" + str(k),
            "from": "s" + str(at[e.source]),
            "to": "s" + str(at[e.target]),
            "kind": "call",
            "delta": EDGE_DELTA[e.status],
            "emphasis": emphasis,
            "animated": False,
            "files": [],
        }
        if e.resolution == "name":
            item["label"] = "name-only"
        edges.append(item)
    tour_steps = picked_steps(change_map)
    steps_doc: list[dict[str, Any]] = []
    file_index = {files[j].path: j for j in plotted_files}
    for n, step in enumerate(tour_steps):
        if step is None:
            heading, body = _overview(change_map) if n == 0 else _summary_step(change_map)
            focus: dict[str, Any] = {"kind": "all"}
        elif step.kind == "risky_file":
            heading, body = _risky_step(change_map, step)
            ids = _focus_ids(step, at, file_index)
            focus = _selection(ids)
        elif step.kind in ("entry", "callee", "test"):
            heading, body = _symbol_step(change_map, step)
            ids = _focus_ids(step, at, file_index)
            focus = _selection(ids)
        else:
            heading, body = _shorten(step.kind, MAX_HEADING), _shorten(step.kind, MAX_BODY)
            focus = {"kind": "all"}
        if step is not None:
            missing = [ref for ref in step.focus if ref not in at and ref not in file_index]
            if missing:
                names = [
                    _short_name(ref) if "::" in ref else ref.rsplit("/", 1)[-1]
                    for ref in missing[:2]
                ]
                names = [name if len(name) <= 32 else name[:29] + "..." for name in names]
                note = "Not shown: " + ", ".join(names)
                if len(missing) > len(names):
                    note += " (+" + str(len(missing) - len(names)) + " more)"
                note += "."
                body = _shorten(body, max(0, MAX_BODY - len(note) - 1)) + " " + note
        steps_doc.append({"id": "w" + str(n), "heading": heading, "body": body, "focus": focus})
    used = [lane for lane in LANE_ORDER if any(node["lane"] == lane for node in nodes)]
    doc: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "graph",
        "title": _shorten(change_map.title or change_map.pr, MAX_LABEL),
        "lenses": ["architecture"],
        "provenance": _provenance(change_map),
        "lanes": [{"id": lane, "label": LANE_LABELS[lane]} for lane in used],
        "nodes": nodes,
        "edges": edges,
        "flows": [],
        "views": [],
        "walkthrough": {"steps": steps_doc},
        "layout": {"direction": "right", "laneOrder": used},
    }
    issues = validate_contract(doc)
    if issues:
        raise ValueError("graphdoc defects: " + "; ".join(issues))
    return Plotted(
        doc,
        {symbols[i].id: i for i in at.values()},
        file_index,
        len(symbols) - len(at),
        len(change_map.edges) - len(kept),
    )


def _overview_doc(
    change_map: ChangeMap,
    groups: tuple[Group, ...],
    lanes: dict[str, LaneName],
    symbols: list[Symbol],
    files: list[FileNode],
    file_at: dict[str, int],
) -> Plotted:
    by_id = {s.id: i for i, s in enumerate(symbols)}
    kinds = {f.path: f.kind for f in files}
    lines = {s.id: (s.added, s.removed) for s in symbols}
    middle = [s for s in picked_steps(change_map) if s is not None]
    walk: list[int] = []
    for step in middle:
        if step.kind in ("entry", "callee", "test"):
            refs = list(step.focus) + ([step.via] if step.via is not None else [])
            for ref in refs:
                i = by_id.get(ref)
                if i is not None and i not in walk:
                    walk.append(i)
    walk.sort(key=lambda i: (-(symbols[i].added + symbols[i].removed), i))
    risky = [file_at[p] for p in _risky_paths(change_map) if p in file_at][: max(0, MAX_NODES)]
    walk = walk[: max(0, MAX_NODES - len(risky))]
    room = max(0, MAX_NODES - len(walk) - len(risky))
    nodes = [_group_node(group, n, kinds, lines) for n, group in enumerate(groups[:room])]
    at = {symbols[i].id: i for i in walk}
    for i in walk:
        nodes.append(_symbol_node(symbols, i, lanes[symbols[i].id]))
    symbol_paths = {s.path for s in symbols}
    ordinary = [i for i, f in enumerate(files) if f.path not in symbol_paths and i not in risky]
    room = max(0, room - len(groups))
    plotted_files = risky + ordinary[:room]
    for j in plotted_files:
        f = files[j]
        nodes.append(
            _file_node(
                f.path,
                j,
                _file_kind(f.kind, f.path),
                FILE_DELTA[f.status],
                f.added,
                f.removed,
                f.sensitive,
                None,
            )
        )
    return _finish(change_map, symbols, files, nodes, at, set(plotted_files))


def _selection(ids: list[str]) -> dict[str, Any]:
    if not ids:
        return {"kind": "all"}
    return {"kind": "selection", "lanes": [], "nodes": ids, "edges": [], "messages": []}


def _check_files(refs: Any, where: str, issues: list[str]) -> None:
    if not isinstance(refs, list):
        issues.append(where + ": files is not a list")
        return
    for n, ref in enumerate(refs):
        at = where + ".files[" + str(n) + "]"
        path = ref.get("path", "") if isinstance(ref, dict) else ""
        if not path or not isinstance(path, str):
            issues.append(at + ": empty path")
            continue
        if path.startswith("/") or ".." in path.split("/") or chr(92) in path:
            issues.append(at + ": bad path " + path)
        start = ref.get("startLine") if isinstance(ref, dict) else None
        end = ref.get("endLine") if isinstance(ref, dict) else None
        if start is not None and (not isinstance(start, int) or start < 1):
            issues.append(at + ": bad startLine")
        if end is not None and (not isinstance(end, int) or end < 1):
            issues.append(at + ": bad endLine")
        if isinstance(start, int) and isinstance(end, int) and end < start:
            issues.append(at + ": endLine before startLine")
        rev = ref.get("revision") if isinstance(ref, dict) else None
        if rev is not None and rev not in ("head", "base"):
            issues.append(at + ": bad revision")


def validate_contract(doc: dict[str, Any]) -> tuple[str, ...]:
    """Restate the pinned graph contract 0.2.0 in Python."""
    issues: list[str] = []
    if doc.get("schemaVersion") != SCHEMA_VERSION:
        issues.append("schemaVersion must be " + SCHEMA_VERSION)
    if doc.get("kind") != "graph":
        issues.append("kind must be graph")
    title = doc.get("title", "")
    if not isinstance(title, str) or not (1 <= len(title) <= MAX_LABEL):
        issues.append("title length out of range")
    lenses = doc.get("lenses", [])
    if not isinstance(lenses, list) or not lenses:
        issues.append("lenses must be non-empty")
    elif any(lens not in ("architecture", "data-flow") for lens in lenses):
        issues.append("lenses holds an unknown lens")
    prov = doc.get("provenance", {})
    repo = prov.get("repo", {}) if isinstance(prov, dict) else {}
    if not (1 <= len(str(repo.get("owner", ""))) <= 64):
        issues.append("provenance.repo.owner length out of range")
    if not (1 <= len(str(repo.get("name", ""))) <= 128):
        issues.append("provenance.repo.name length out of range")
    for side in ("base", "head"):
        sha = prov.get(side, {}).get("sha", "") if isinstance(prov, dict) else ""
        if not isinstance(sha, str) or _SHA.match(sha) is None:
            issues.append("provenance." + side + ".sha is not hex")
    lanes = doc.get("lanes", [])
    lane_ids = [lane.get("id", "") for lane in lanes if isinstance(lane, dict)]
    if not (1 <= len(lanes) <= 16):
        issues.append("lanes count out of range")
    if len(set(lane_ids)) != len(lane_ids) or any(_ID.match(i) is None for i in lane_ids):
        issues.append("lane ids must be unique and match charset")
    for lane in lanes:
        label = lane.get("label", "") if isinstance(lane, dict) else ""
        if not isinstance(label, str) or not (1 <= len(label) <= MAX_LABEL):
            issues.append("lane label length out of range")
    nodes = doc.get("nodes", [])
    node_ids = [node.get("id", "") for node in nodes if isinstance(node, dict)]
    if not (1 <= len(nodes) <= MAX_NODES):
        issues.append("nodes count out of range")
    if len(set(node_ids)) != len(node_ids) or any(_ID.match(i) is None for i in node_ids):
        issues.append("node ids must be unique and match charset")
    kinds = (
        "service",
        "app",
        "module",
        "function",
        "route",
        "job",
        "queue",
        "datastore",
        "cache",
        "external",
        "ui",
        "config",
        "test",
        "package",
        "other",
    )
    deltas = ("added", "modified", "removed", "unchanged")
    for n, node in enumerate(nodes):
        at = "nodes[" + str(n) + "]"
        if not isinstance(node, dict):
            issues.append(at + ": not an object")
            continue
        label = node.get("label", "")
        if not isinstance(label, str) or not (1 <= len(label) <= MAX_LABEL):
            issues.append(at + ": label length out of range")
        if node.get("kind") not in kinds:
            issues.append(at + ": bad kind")
        if node.get("delta") not in deltas:
            issues.append(at + ": bad delta")
        if node.get("lane") not in lane_ids:
            issues.append(at + ": unknown lane")
        badges = node.get("badges", [])
        if not isinstance(badges, list) or len(badges) > 6:
            issues.append(at + ": too many badges")
        elif any(not isinstance(b, str) or not (1 <= len(b) <= MAX_LABEL) for b in badges):
            issues.append(at + ": badge length out of range")
        _check_files(node.get("files", []), at, issues)
    edges = doc.get("edges", [])
    edge_ids = [edge.get("id", "") for edge in edges if isinstance(edge, dict)]
    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        issues.append("edges count out of range")
    if len(set(edge_ids)) != len(edge_ids) or any(_ID.match(i) is None for i in edge_ids):
        issues.append("edge ids must be unique and match charset")
    for n, edge in enumerate(edges):
        at = "edges[" + str(n) + "]"
        if not isinstance(edge, dict):
            issues.append(at + ": not an object")
            continue
        if edge.get("from") not in node_ids:
            issues.append(at + ": unknown from node")
        if edge.get("to") not in node_ids:
            issues.append(at + ": unknown to node")
        if edge.get("kind") != "call":
            issues.append(at + ": kind must be call")
        if edge.get("delta") not in deltas:
            issues.append(at + ": bad delta")
        if edge.get("emphasis") not in ("normal", "hero", "muted"):
            issues.append(at + ": bad emphasis")
        if not isinstance(edge.get("animated"), bool):
            issues.append(at + ": animated must be bool")
        label = edge.get("label", "")
        if label != "" and (not isinstance(label, str) or len(label) > MAX_LABEL):
            issues.append(at + ": label length out of range")
        _check_files(edge.get("files", []), at, issues)
    for key in ("flows", "views"):
        if not isinstance(doc.get(key), list):
            issues.append(key + " must be a list")
    walk = (
        doc.get("walkthrough", {}).get("steps", [])
        if isinstance(doc.get("walkthrough"), dict)
        else []
    )
    step_ids = [step.get("id", "") for step in walk if isinstance(step, dict)]
    if not (2 <= len(walk) <= MAX_STEPS):
        issues.append("walkthrough steps count out of range")
    if len(set(step_ids)) != len(step_ids) or any(_ID.match(i) is None for i in step_ids):
        issues.append("step ids must be unique and match charset")
    for n, step in enumerate(walk):
        at = "walkthrough.steps[" + str(n) + "]"
        if not isinstance(step, dict):
            issues.append(at + ": not an object")
            continue
        heading = step.get("heading", "")
        if not isinstance(heading, str) or not (1 <= len(heading) <= MAX_HEADING):
            issues.append(at + ": heading length out of range")
        body = step.get("body", "")
        if not isinstance(body, str) or not (1 <= len(body) <= MAX_BODY):
            issues.append(at + ": body length out of range")
        focus = step.get("focus", {})
        if not isinstance(focus, dict) or focus.get("kind") not in ("all", "selection"):
            issues.append(at + ": bad focus kind")
        elif focus.get("kind") == "selection":
            refs = list(focus.get("nodes", [])) + list(focus.get("lanes", []))
            if not refs:
                issues.append(at + ": empty selection")
            for ref in focus.get("nodes", []):
                if ref not in node_ids:
                    issues.append(at + ": unknown focus node " + str(ref))
            for ref in focus.get("lanes", []):
                if ref not in lane_ids:
                    issues.append(at + ": unknown focus lane " + str(ref))
    for lane in lane_ids:
        if not any(node.get("lane") == lane for node in nodes if isinstance(node, dict)):
            issues.append("lane " + lane + " is unused")
    return tuple(issues)
