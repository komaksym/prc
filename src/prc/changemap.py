"""Change map: the PR's changed symbols, how their calls moved, and a computed tour."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from prc.brief import Brief, Delta, Kind, kind_of
from prc.codegraph import Definition, Index, ParseCache, ParsedFile, ResolvedCall, index_tree
from prc.snapshot import Acquisition, diff_body

Language = Literal["python", "javascript", "typescript", "tsx"]
FileStatus = Literal["added", "modified", "deleted"]
SymbolKind = Literal["class", "function", "method"]
SymbolStatus = Literal["added", "modified", "deleted", "context"]
EdgeStatus = Literal["added", "removed", "kept"]
Resolution = Literal["exact", "name"]
LineOp = Literal["+", "-", " "]
StepKind = Literal["overview", "risky_file", "entry", "callee", "test", "summary"]


@dataclass(frozen=True, slots=True)
class DiffLine:
    op: LineOp
    old: int | None
    new: int | None
    text: str


@dataclass(frozen=True, slots=True)
class Hunk:
    old_start: int
    new_start: int
    lines: tuple[DiffLine, ...]


@dataclass(frozen=True, slots=True)
class FileNode:
    path: str
    kind: Kind
    status: FileStatus
    language: Language | None
    sensitive: str | None
    added: int
    removed: int
    hunks: tuple[Hunk, ...]
    symbols: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Symbol:
    id: str
    path: str
    qualname: str
    kind: SymbolKind
    status: SymbolStatus
    span: tuple[int, int] | None
    base_span: tuple[int, int] | None
    added: int
    removed: int
    hunks: tuple[Hunk, ...]
    call_sites: int


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    status: EdgeStatus
    resolution: Resolution


@dataclass(frozen=True, slots=True)
class Step:
    kind: StepKind
    focus: tuple[str, ...]
    via: str | None


@dataclass(frozen=True, slots=True)
class ChangeMap:
    pr: str
    url: str | None
    title: str
    author: str
    base_sha: str
    head_sha: str
    brief: Brief
    files: tuple[FileNode, ...]
    symbols: tuple[Symbol, ...]
    edges: tuple[Edge, ...]
    tour: tuple[Step, ...]


MAX_CONTEXT = 6
MAX_RISKY = 3
MAX_SYMBOL_STEPS = 10
MAX_TESTS = 6
CHANGED: frozenset[str] = frozenset({"added", "modified", "deleted"})
FILE_STATUS: dict[str, FileStatus] = {"A": "added", "D": "deleted"}
EDGE_STATUS: dict[tuple[bool, bool], EdgeStatus] = {
    (True, True): "kept",
    (True, False): "added",
    (False, True): "removed",
}
_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")

Pair = tuple[str, str]
Pairs = dict[Pair, tuple[Resolution, tuple[int, ...]]]
Weight = Literal["added", "removed", "touched", "kept"]
WEIGHTS: tuple[Weight, ...] = ("added", "removed", "touched", "kept")


def parse_hunks(body: str) -> tuple[Hunk, ...]:
    """Hunks of one unified diff body; lines before the first `@@` are file headers."""

    hunks: list[Hunk] = []
    lines: list[DiffLine] = []
    start: tuple[int, int] | None = None
    old = new = 0

    for raw in body.splitlines():
        header = _HUNK.match(raw)

        if header is not None:
            if start is not None:
                hunks.append(Hunk(*start, tuple(lines)))

            old, new = int(header[1]), int(header[2])
            start, lines = (old, new), []
        elif start is None:
            continue
        elif raw[:1] == "+":
            lines.append(DiffLine("+", None, new, raw[1:]))
            new += 1
        elif raw[:1] == "-":
            lines.append(DiffLine("-", old, None, raw[1:]))
            old += 1
        elif raw[:1] == " ":
            lines.append(DiffLine(" ", old, new, raw[1:]))
            old, new = old + 1, new + 1

    if start is not None:
        hunks.append(Hunk(*start, tuple(lines)))

    return tuple(hunks)


def _slice(hunks: tuple[Hunk, ...], keep: Callable[[DiffLine], bool]) -> tuple[Hunk, ...]:
    """Runs of kept lines as hunks of their own, dropping runs that change nothing."""

    runs: list[Hunk] = []

    for hunk in hunks:
        old, new = hunk.old_start, hunk.new_start
        run: list[DiffLine] = []
        start = (old, new)

        for line in hunk.lines:
            if keep(line):
                start = start if run else (old, new)
                run.append(line)
            else:
                runs += _changing(start, run)
                run = []

            old = old if line.old is None else line.old + 1
            new = new if line.new is None else line.new + 1

        runs += _changing(start, run)

    return tuple(runs)


def _changing(start: tuple[int, int], run: list[DiffLine]) -> list[Hunk]:
    return [Hunk(*start, tuple(run))] if any(line.op != " " for line in run) else []


@dataclass(frozen=True, slots=True)
class _Owners:
    """The innermost symbols holding a diff line: on the head side by its new number, on the
    base side by its old number."""

    head: ParsedFile | None
    base: ParsedFile | None

    def of(self, line: DiffLine) -> tuple[str | None, str | None]:
        head = None if self.head is None or line.new is None else self.head.innermost(line.new)
        base = None if self.base is None or line.old is None else self.base.innermost(line.old)

        return head, base

    def holds(self, qualname: str) -> Callable[[DiffLine], bool]:
        return lambda line: qualname in self.of(line)


def _pairs(calls: tuple[ResolvedCall, ...]) -> Pairs:
    """Symbol-to-symbol calls keyed by (source, target), with the best resolution and every line."""

    pairs: Pairs = {}

    for call in sorted(calls, key=lambda c: c.line):
        source = f"{call.path}::{call.scope}"

        if call.scope is None or source == call.target:
            continue

        seen = pairs.get((source, call.target))
        exact = call.resolution == "exact" or (seen is not None and seen[0] == "exact")
        pairs[source, call.target] = (
            "exact" if exact else "name",
            (*(seen[1] if seen else ()), call.line),
        )

    return pairs


def _split(symbol_id: str) -> tuple[str, str]:
    path, _, qualname = symbol_id.rpartition("::")

    return path, qualname


@dataclass(frozen=True, slots=True)
class _Trees:
    head: Index
    base: Index

    def definition(self, symbol_id: str) -> Definition:
        path, qualname = _split(symbol_id)
        found = self.head.definitions.get(path, {}).get(qualname)

        return found or self.base.definitions[path][qualname]


def _span(index: Index, symbol_id: str) -> tuple[int, int] | None:
    path, qualname = _split(symbol_id)
    found = index.definitions.get(path, {}).get(qualname)

    return None if found is None else found.span


def build_change_map(acquisition: Acquisition, repo: Path, brief: Brief) -> ChangeMap:
    comparison = acquisition.snapshot.comparison
    items = sorted(acquisition.inventory.items, key=lambda item: item.path)
    changes = {change.path: change for change in brief.files}
    opaque = frozenset(item.path for item in items if item.opaque)
    cache: ParseCache = {}
    trees = _Trees(
        index_tree(repo, comparison.head_sha, opaque, cache),
        index_tree(repo, comparison.merge_base_sha, opaque, cache),
    )
    head, base = trees.head, trees.base
    file_hunks = {
        item.path: parse_hunks(diff_body(acquisition.records.get(f"diff:{item.path}", "")))
        for item in items
        if not item.opaque
    }
    owners = {path: _Owners(head.files.get(path), base.files.get(path)) for path in file_hunks}
    tallies: Counter[tuple[str, LineOp]] = Counter()
    statuses: dict[str, SymbolStatus] = {}

    for path, hunks in file_hunks.items():
        for line in (line for hunk in hunks for line in hunk.lines):
            head_owner, base_owner = owners[path].of(line)
            holder = {"+": head_owner, "-": base_owner}.get(line.op)

            if holder is not None:
                tallies[f"{path}::{holder}", line.op] += 1

        head_defs = head.definitions.get(path, {})
        base_defs = base.definitions.get(path, {})

        for qualname in head_defs.keys() | base_defs.keys():
            symbol_id = f"{path}::{qualname}"

            if qualname not in base_defs:
                statuses[symbol_id] = "added"
            elif qualname not in head_defs:
                statuses[symbol_id] = "deleted"
            elif tallies[symbol_id, "+"] or tallies[symbol_id, "-"]:
                statuses[symbol_id] = "modified"

    head_calls = head.resolve_all()
    head_pairs, base_pairs = _pairs(head_calls), _pairs(base.resolve_all())
    linked = sorted(p for p in head_pairs.keys() | base_pairs.keys() if statuses.keys() & set(p))

    plus = {
        path: {line.new for hunk in hunks for line in hunk.lines if line.op == "+"}
        for path, hunks in file_hunks.items()
    }

    def weight(pair: Pair) -> Weight:
        status = EDGE_STATUS[pair in head_pairs, pair in base_pairs]
        lines = head_pairs[pair][1] if status == "kept" else ()

        return "touched" if plus.get(_split(pair[0])[0], set()) & set(lines) else status

    def rank(near: tuple[Weight, str]) -> tuple[int, str, int, str]:
        symbol_id = near[1]

        return (
            WEIGHTS.index(near[0]),
            _split(symbol_id)[0],
            trees.definition(symbol_id).span[0],
            symbol_id,
        )

    context: set[str] = set()

    for symbol_id in statuses:
        callers = [(weight(p), p[0]) for p in linked if p[1] == symbol_id and p[0] not in statuses]
        callees = [(weight(p), p[1]) for p in linked if p[0] == symbol_id and p[1] not in statuses]
        drawn = [near for near in callees if near[0] != "kept"]

        for near in (callers, drawn):
            context.update(symbol for _, symbol in sorted(near, key=rank)[:MAX_CONTEXT])

    shown = statuses.keys() | context
    sites = Counter(call.target for call in head_calls)
    symbols: list[Symbol] = []

    for symbol_id in sorted(shown):
        path, qualname = _split(symbol_id)
        status = statuses.get(symbol_id, "context")
        changed = status != "context"
        owner = owners.get(path)
        symbols.append(
            Symbol(
                id=symbol_id,
                path=path,
                qualname=qualname,
                kind=trees.definition(symbol_id).kind,
                status=status,
                span=_span(head, symbol_id),
                base_span=_span(base, symbol_id),
                added=tallies[symbol_id, "+"] if changed else 0,
                removed=tallies[symbol_id, "-"] if changed else 0,
                hunks=_slice(file_hunks[path], owner.holds(qualname)) if changed and owner else (),
                call_sites=sites[symbol_id],
            )
        )

    edges = tuple(
        Edge(
            source,
            target,
            EDGE_STATUS[(source, target) in head_pairs, (source, target) in base_pairs],
            (head_pairs.get((source, target)) or base_pairs[source, target])[0],
        )
        for source, target in linked
        if source in shown and target in shown
    )

    def kind(path: str) -> Kind:
        change = changes.get(path)

        return change.kind if change is not None else kind_of(Delta(path, path in opaque, 0, 0))

    files = tuple(
        FileNode(
            path=item.path,
            kind=kind(item.path),
            status=FILE_STATUS.get(item.status, "modified"),
            language=_language(head.files.get(item.path) or base.files.get(item.path)),
            sensitive=changes[item.path].sensitive if item.path in changes else None,
            added=item.added_lines,
            removed=item.removed_lines,
            hunks=file_hunks.get(item.path, ()),
            symbols=tuple(s.id for s in symbols if s.path == item.path),
        )
        for item in items
    )
    metadata = acquisition.metadata

    return ChangeMap(
        pr=f"{comparison.repo}#{comparison.pr_number}",
        url=None,
        title=metadata.title,
        author=metadata.author,
        base_sha=comparison.merge_base_sha,
        head_sha=comparison.head_sha,
        brief=brief,
        files=files,
        symbols=tuple(symbols),
        edges=edges,
        tour=_tour(brief, tuple(symbols), edges, head_pairs, base_pairs, kind),
    )


def _language(parsed: ParsedFile | None) -> Language | None:
    return None if parsed is None else parsed.language


def _tour(
    brief: Brief,
    symbols: tuple[Symbol, ...],
    edges: tuple[Edge, ...],
    head_pairs: Pairs,
    base_pairs: Pairs,
    kind: Callable[[str], Kind],
) -> tuple[Step, ...]:
    changed = {s.id: s for s in symbols if s.status in CHANGED}
    code = {symbol_id for symbol_id, s in changed.items() if kind(s.path) != "test"}
    callees: dict[str, list[tuple[int, int, str]]] = {}
    called: set[str] = set()

    for edge in edges:
        if edge.source in code and edge.target in code:
            removed = edge.status == "removed"
            line = (base_pairs if removed else head_pairs)[edge.source, edge.target][1][0]
            callees.setdefault(edge.source, []).append((int(removed), line, edge.target))
            called.add(edge.target)

    risky = sorted(
        (f for f in brief.files if f.sensitive is not None), key=lambda f: (f.named, f.path)
    )
    steps = [Step("overview", (), None)]
    steps += [Step("risky_file", (f.path,), None) for f in risky[:MAX_RISKY]]
    seen: set[str] = set()
    walked: list[Step] = []

    def walk(root: str) -> Iterator[Step]:
        stack = [(root, iter(sorted(callees.get(root, []))))]

        while stack:
            caller, pending = stack[-1]
            following = next(pending, None)

            if following is None:
                stack.pop()
            elif following[2] not in seen:
                target = following[2]
                seen.add(target)
                yield Step("callee", (target,), caller)
                stack.append((target, iter(sorted(callees.get(target, [])))))

    def size(symbol_id: str) -> int:
        return changed[symbol_id].added + changed[symbol_id].removed

    for entry in sorted(code - called, key=lambda symbol_id: (-size(symbol_id), symbol_id)):
        if entry not in seen:
            seen.add(entry)
            walked.append(Step("entry", (entry,), None))
            walked += walk(entry)

    walked += [Step("entry", (symbol_id,), None) for symbol_id in sorted(code - seen)]
    steps += walked[:MAX_SYMBOL_STEPS]
    tests = tuple(sorted(changed.keys() - code))[:MAX_TESTS]
    steps += [Step("test", tests, None)] if tests else []
    steps.append(Step("summary", (), None))

    return tuple(steps)
