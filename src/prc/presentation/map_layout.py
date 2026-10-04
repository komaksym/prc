"""Deterministic layout of a change map: callers, changed symbols by call depth, callees.

Positions depend only on ids and edges, never on input order, so the page is byte-stable.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from prc.brief import Delta, kind_of
from prc.changemap import ChangeMap, FileNode, Symbol

Lane = Literal["files", "callers", "changed", "callees", "tests"]
BoxKind = Literal["symbol", "file"]
MAIN: tuple[Lane, ...] = ("callers", "changed", "callees")

GRID = 8
CARD_W = 240
CHANGED_H = 80
CONTEXT_H = 56
CHIP_H = 40
GAP_X = 112
GAP_Y = 16
CHIP_GAP = 16
PAD = 40
LABEL = 24
BAND_PAD = 16
LANE_GAP = 72
MAX_ROWS = 10
MIN_ROW_W = 3 * CARD_W + 2 * GAP_X
SWEEPS = 4


@dataclass(frozen=True, slots=True)
class Box:
    kind: BoxKind
    id: str
    lane: Lane
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True, slots=True)
class Band:
    lane: Lane
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True, slots=True)
class Layout:
    width: int
    height: int
    bands: tuple[Band, ...]
    boxes: tuple[Box, ...]


def _snap(value: float) -> int:
    return int(value) // GRID * GRID


def _lanes(change_map: ChangeMap) -> dict[str, Lane]:
    kinds = {f.path: f.kind for f in change_map.files}

    def is_test(path: str) -> bool:
        return kinds.get(path, kind_of(Delta(path, False, 0, 0))) == "test"

    lanes: dict[str, Lane] = {}

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


def _depths(nodes: list[str], succ: dict[str, list[str]]) -> dict[str, int]:
    """Longest-path layering after dropping DFS back edges, so cycles still terminate."""

    state: dict[str, bool] = {}
    finished: list[str] = []
    dag: dict[str, list[str]] = {node: [] for node in nodes}

    for root in nodes:
        if root in state:
            continue

        state[root] = False
        stack = [(root, iter(succ[root]))]

        while stack:
            node, rest = stack[-1]
            nxt = next(rest, None)

            if nxt is None:
                state[node] = True
                finished.append(node)
                stack.pop()
            elif state.get(nxt) is not False:
                dag[node].append(nxt)

                if nxt not in state:
                    state[nxt] = False
                    stack.append((nxt, iter(succ[nxt])))

    depth = dict.fromkeys(nodes, 0)

    for node in reversed(finished):
        for nxt in dag[node]:
            depth[nxt] = max(depth[nxt], depth[node] + 1)

    return depth


def _line(symbol: Symbol) -> int:
    span = symbol.span or symbol.base_span

    return span[0] if span else 0


def _columns(
    change_map: ChangeMap, lanes: dict[str, Lane], neighbors: dict[str, set[str]]
) -> list[tuple[Lane, list[str]]]:
    symbols = sorted(change_map.symbols, key=lambda s: (s.path, _line(s), s.id))
    rank = {s.id: i for i, s in enumerate(symbols)}
    changed = [s.id for s in symbols if lanes[s.id] == "changed"]
    succ: dict[str, list[str]] = {sid: [] for sid in changed}
    incoming: set[str] = set()

    for edge in sorted(change_map.edges, key=lambda e: (e.source, e.target)):
        if edge.source in succ and edge.target in succ and edge.source != edge.target:
            succ[edge.source].append(edge.target)
            incoming.add(edge.target)

    depth = _depths(sorted(changed, key=lambda s: (s in incoming, s)), succ)
    layers: dict[int, list[str]] = defaultdict(list)

    for sid in changed:
        layers[depth[sid]].append(sid)

    columns: list[tuple[Lane, list[str]]] = [
        ("callers", [s.id for s in symbols if lanes[s.id] == "callers"]),
        *(("changed", layers[d]) for d in sorted(layers)),
        ("callees", [s.id for s in symbols if lanes[s.id] == "callees"]),
    ]
    columns = [(lane, ids) for lane, ids in columns if ids]

    for sweep in range(SWEEPS):
        indices = range(len(columns)) if sweep % 2 == 0 else reversed(range(len(columns)))
        position = {sid: (i + 0.5) / len(ids) for _, ids in columns for i, sid in enumerate(ids)}

        for index in indices:
            lane, ids = columns[index]

            def key(
                sid: str, own: list[str] = ids, at: dict[str, float] = position
            ) -> tuple[float, int]:
                near = [at[n] for n in neighbors[sid] if n in at and n not in own]

                return (sum(near) / len(near) if near else at[sid], rank[sid])

            columns[index] = (lane, sorted(ids, key=key))
            position.update({sid: (i + 0.5) / len(ids) for i, sid in enumerate(columns[index][1])})

    split: list[tuple[Lane, list[str]]] = []

    for lane, ids in columns:
        count = -(-len(ids) // MAX_ROWS)
        size = -(-len(ids) // count)
        split.extend((lane, ids[i : i + size]) for i in range(0, len(ids), size))

    return split


def _chip_width(f: FileNode) -> int:
    name = PurePosixPath(f.path).name or f.path
    badge = 24 + 7 * len(f.sensitive) if f.sensitive else 0

    return max(128, min(_snap(56 + 7.5 * len(name) + badge + GRID - 1), 360))


def _flow(
    items: Iterable[tuple[str, int, float]], left: int, top: int, limit: int, h: int, gap: int
) -> list[tuple[str, int, int, int]]:
    """Place (id, width, wanted x) items in rows, each as close to its wanted x as order allows."""

    placed: list[tuple[str, int, int, int]] = []
    x, y = left, top

    for item_id, w, wanted in items:
        if x > left and x + w > limit:
            x, y = left, y + h + gap

        x = max(x, min(_snap(wanted - w / 2), limit - w))
        placed.append((item_id, x, y, w))
        x += w + gap

    return placed


def layout_map(change_map: ChangeMap) -> Layout:
    lanes = _lanes(change_map)
    neighbors: dict[str, set[str]] = {s.id: set() for s in change_map.symbols}

    for edge in change_map.edges:
        if edge.source in neighbors and edge.target in neighbors:
            neighbors[edge.source].add(edge.target)
            neighbors[edge.target].add(edge.source)

    status = {s.id: s.status for s in change_map.symbols}
    height = {sid: CHANGED_H if status[sid] != "context" else CONTEXT_H for sid in status}
    columns = _columns(change_map, lanes, neighbors)
    limit = PAD + max(MIN_ROW_W, len(columns) * (CARD_W + GAP_X) - GAP_X)
    drawn = {s.path for s in change_map.symbols if s.status != "context"}
    chips = sorted(
        (f for f in change_map.files if f.path not in drawn),
        key=lambda f: (f.sensitive is None, f.path),
    )
    boxes = [
        Box("file", path, "files", x, y, w, CHIP_H)
        for path, x, y, w in _flow(
            ((f.path, _chip_width(f), 0.0) for f in chips),
            PAD,
            PAD + LABEL,
            limit,
            CHIP_H,
            CHIP_GAP,
        )
    ]
    files_bottom = max((b.y + b.h for b in boxes), default=PAD)
    main_top = files_bottom + LANE_GAP if boxes else PAD + LABEL + BAND_PAD
    column_h = [sum(height[sid] for sid in ids) + GAP_Y * (len(ids) - 1) for _, ids in columns]
    main_h = max(column_h, default=0)
    main: list[Box] = []

    for index, ((lane, ids), col_h) in enumerate(zip(columns, column_h, strict=True)):
        x = PAD + index * (CARD_W + GAP_X)
        y = main_top + _snap((main_h - col_h) / 2)

        for sid in ids:
            main.append(Box("symbol", sid, lane, x, y, CARD_W, height[sid]))
            y += height[sid] + GAP_Y

    boxes.extend(main)
    main_right = max((b.x + b.w for b in main), default=PAD)
    centers = {b.id: b.x + b.w / 2 for b in main}
    tests = []

    for s in change_map.symbols:
        if lanes[s.id] == "tests":
            targets = [centers[n] for n in neighbors[s.id] if n in centers]
            wanted = sum(targets) / len(targets) if targets else float(main_right)
            tests.append((wanted, s.id))

    tests_top = (main_top + main_h if main else files_bottom) + LANE_GAP + LABEL
    boxes.extend(
        Box("symbol", sid, "tests", x, y, w, height[sid])
        for sid, x, y, w in _flow(
            ((sid, CARD_W, wanted) for wanted, sid in sorted(tests)),
            PAD,
            tests_top,
            limit,
            CHANGED_H,
            GAP_Y,
        )
    )

    width = max((b.x + b.w for b in boxes), default=PAD) + PAD
    canvas_h = max((b.y + b.h for b in boxes), default=PAD) + PAD
    bands: list[Band] = []

    for lane in ("files", *MAIN, "tests"):
        members = [b for b in boxes if b.lane == lane]

        if not members:
            continue

        if lane in MAIN:
            left = min(b.x for b in members) - BAND_PAD
            span_w = max(b.x + b.w for b in members) + BAND_PAD - left
            top, bottom = main_top, main_top + main_h
        else:
            left, span_w = PAD - BAND_PAD, width - 2 * (PAD - BAND_PAD)
            top, bottom = min(b.y for b in members), max(b.y + b.h for b in members)

        bands.append(
            Band(lane, left, top - LABEL - BAND_PAD, span_w, bottom - top + LABEL + 2 * BAND_PAD)
        )

    return Layout(width, canvas_h, tuple(bands), tuple(boxes))
