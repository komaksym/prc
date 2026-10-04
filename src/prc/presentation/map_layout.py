"""Deterministic layout of a change map: callers, changed symbols by call depth, callees, and
the route of every edge around the cards.

Positions depend only on ids and edges, never on input order, so the page is byte-stable.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import pairwise
from pathlib import PurePosixPath
from typing import Literal

from prc.brief import Delta, kind_of
from prc.changemap import ChangeMap, FileNode, Symbol

Lane = Literal["files", "callers", "changed", "callees", "tests"]
BoxKind = Literal["symbol", "file", "group"]
Side = Literal["l", "r", "t"]
Point = tuple[float, float, Literal["h", "v"]]
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
DENSE = 30
DENSE_ROWS = 16
ROW_H = 32
ROW_GAP = 8
GROUP_H = 24
TEST_GAP = 24
CLEAR = 12
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
class Route:
    """Waypoints from the source card's border to the target's, each with its tangent."""

    source: str
    target: str
    points: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class Layout:
    width: int
    height: int
    dense: bool
    bands: tuple[Band, ...]
    boxes: tuple[Box, ...]
    routes: tuple[Route, ...]


def cubics(points: tuple[Point, ...]) -> Iterator[tuple[float, ...]]:
    """Each leg leaves and enters along its waypoint's tangent, so a leg between two horizontal
    waypoints stays inside their x range and a leg between vertical ones inside their y range."""

    for (x0, y0, d0), (x1, y1, d1) in pairwise(points):
        c1 = (x0 + (x1 - x0) / 2, y0) if d0 == "h" else (x0, y0 + (y1 - y0) / 2)
        c2 = (x1 - (x1 - x0) / 2, y1) if d1 == "h" else (x1, y1 - (y1 - y0) / 2)
        yield (x0, y0, *c1, *c2, x1, y1)


def path_data(points: tuple[Point, ...]) -> str:
    def num(v: float) -> str:
        return f"{round(v, 1):g}"

    legs = "".join("C" + " ".join(num(v) for v in c[2:]) for c in cubics(points))

    return f"M{num(points[0][0])} {num(points[0][1])}{legs}"


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

    rows = DENSE_ROWS if len(change_map.symbols) > DENSE else MAX_ROWS
    split: list[tuple[Lane, list[str]]] = []

    for lane, ids in columns:
        count = -(-len(ids) // rows)
        size = -(-len(ids) // count)
        split.extend((lane, ids[i : i + size]) for i in range(0, len(ids), size))

    return split


def _grouped(ids: list[str], path: dict[str, str]) -> list[list[str]]:
    """Runs of one file, in the order each file first appears in the column."""

    groups: dict[str, list[str]] = {}

    for sid in ids:
        groups.setdefault(path[sid], []).append(sid)

    return list(groups.values())


def _chip_width(f: FileNode) -> int:
    name = PurePosixPath(f.path).name or f.path
    badge = 24 + 7 * len(f.sensitive) if f.sensitive else 0

    return max(128, min(_snap(56 + 7.5 * len(name) + badge + GRID - 1), 360))


def _flow(
    items: Iterable[tuple[str, int]],
    left: int,
    top: int,
    limit: int,
    h: int,
    gap: tuple[int, int],
) -> list[tuple[str, int, int, int]]:
    """Place (id, width) items in rows, left to right, `gap` apart across and down."""

    placed: list[tuple[str, int, int, int]] = []
    x, y = left, top

    for item_id, w in items:
        if x > left and x + w > limit:
            x, y = left, y + h + gap[1]

        placed.append((item_id, x, y, w))
        x += w + gap[0]

    return placed


class _Router:
    """Routes run through gutters between columns and through the free gaps inside a column."""

    def __init__(
        self,
        main: list[list[Box]],
        tests: dict[str, Box],
        main_bottom: int,
        tests_top: int,
    ) -> None:
        self.main = main
        self.tests = tests
        self.main_bottom = main_bottom
        self.tests_top = tests_top
        self.column = {b.id: i for i, col in enumerate(main) for b in col if b.kind == "symbol"}
        self.box = {b.id: b for col in main for b in col if b.kind == "symbol"} | tests
        self.used: dict[tuple[int, int], int] = defaultdict(int)

    def centre_y(self, sid: str) -> float:
        box = self.box[sid]

        return box.y + box.h / 2

    def gutter(self, column: int, k: int) -> float:
        x = self.main[column][0].x
        floor = x - GAP_X + CLEAR if column else GRID

        return max(x - 2 * GRID - GRID * k, floor)

    def passage(self, column: int, at: float) -> float:
        """The y of a straight run through `column` closest to `at` that touches no card."""

        col = sorted(self.main[column], key=lambda b: b.y)
        gaps: list[tuple[float, float]] = [(-1e9, col[0].y)]
        gaps += [(a.y + a.h, b.y) for a, b in pairwise(col)]
        gaps.append((col[-1].y + col[-1].h, 1e9))
        best: tuple[float, int, float] | None = None

        for index, (lo, hi) in enumerate(gaps):
            margin = min(CLEAR, (hi - lo) / 2)
            y = min(max(at, lo + margin), hi - margin)

            if best is None or abs(y - at) < best[0]:
                best = (abs(y - at), index, y)

        assert best is not None
        _, index, y = best
        lo, hi = gaps[index]
        n = self.used[(column, index)]
        self.used[(column, index)] += 1
        room = (hi - lo) / 2 - 2

        if hi - lo < 1e8:
            y = (lo + hi) / 2 + min(room, 4 * ((n + 1) // 2)) * (1 if n % 2 else -1) * (n > 0)

        return y

    def across(
        self, start: tuple[float, float], end: tuple[float, float], a: int, b: int
    ) -> list[Point]:
        """Waypoints from a port on column `a` to a port on column `b`, crossing every column between."""

        step = 1 if b > a else -1
        points: list[Point] = [(start[0], start[1], "h")]
        x, y = start

        for c in range(a + step, b, step):
            left = self.main[c][0].x - CLEAR
            right = self.main[c][0].x + CARD_W + CLEAR
            mid = (left + right) / 2
            at = y + (end[1] - y) * (mid - x) / (end[0] - x)
            run = self.passage(c, at)
            near, far = (left, right) if step > 0 else (right, left)
            points += [(near, run, "h"), (far, run, "h")]
            x, y = far, run

        points.append((end[0], end[1], "h"))

        return points

    def bracket(self, start: tuple[float, float], end: tuple[float, float]) -> list[Point]:
        out = start[0] + 4 * GRID

        return [
            (start[0], start[1], "h"),
            (out, (start[1] + end[1]) / 2, "v"),
            (end[0], end[1], "h"),
        ]

    def climb(
        self, test: Box, start: tuple[float, float], end: tuple[float, float], gx: float
    ) -> list[Point]:
        """From a test's left port up the slot gap, across the strip under the main lanes, then up
        the gutter left of the target's column and into its left port."""

        channel = test.x - TEST_GAP / 2
        strip = self.main_bottom + CLEAR
        points: list[Point] = [
            (start[0], start[1], "h"),
            (channel, start[1] - CLEAR, "v"),
            (channel, self.tests_top - CLEAR, "v"),
            (gx, strip, "v"),
        ]

        if end[1] + 2 * CLEAR < strip:
            points.append((gx, end[1] + 2 * CLEAR, "v"))

        points.append((end[0], end[1], "h"))

        return points

    def arch(self, start: tuple[float, float], end: tuple[float, float]) -> list[Point]:
        top = min(start[1], end[1]) - 2 * CLEAR

        return [
            (start[0], start[1], "v"),
            ((start[0] + end[0]) / 2, top, "h"),
            (end[0], end[1], "v"),
        ]


def _port(box: Box, side: Side, index: int, count: int) -> tuple[float, float]:
    f = 0.2 + 0.6 * (index + 1) / (count + 1)

    if side == "t":
        return (round(box.x + box.w * f, 1), box.y)

    return (box.x if side == "l" else box.x + box.w, round(box.y + box.h * f, 1))


def _routes(router: _Router, edges: list[tuple[str, str]]) -> tuple[Route, ...]:
    tested = {sid for sid in router.box if sid in router.tests}
    plans: list[tuple[str, str, Side, Side, float, float]] = []
    gutter_users: dict[int, list[tuple[float, float, str, str]]] = defaultdict(list)

    for source, target in edges:
        if source in tested and target not in tested:
            gutter_users[router.column[target]].append(
                (router.centre_y(target), router.box[source].x, source, target)
            )
        elif target in tested and source not in tested:
            gutter_users[router.column[source]].append(
                (router.centre_y(source), router.box[target].x, target, source)
            )

    gx: dict[tuple[str, str], float] = {}

    for column, users in gutter_users.items():
        for k, (_, _, test, other) in enumerate(sorted(users, reverse=True)):
            gx[(test, other)] = router.gutter(column, k)

    for source, target in edges:
        s_test, t_test = source in tested, target in tested

        keys: tuple[float, float]

        if s_test and t_test:
            sides: tuple[Side, Side] = ("t", "t")
            keys = (router.box[target].x, router.box[source].x)
        elif s_test or t_test:
            test, other = (source, target) if s_test else (target, source)
            sides = ("l", "l")
            keys = (router.centre_y(other), 1e6 + gx[(test, other)])
            keys = keys if s_test else (keys[1], keys[0])
        else:
            a, b = router.column[source], router.column[target]
            sides = ("r", "l") if b > a else ("l", "r") if b < a else ("r", "r")
            keys = (router.centre_y(target), router.centre_y(source))

        plans.append((source, target, sides[0], sides[1], keys[0], keys[1]))

    slots: dict[tuple[str, Side], list[tuple[float, int, int]]] = defaultdict(list)

    for i, (source, target, s_side, t_side, s_key, t_key) in enumerate(plans):
        slots[(source, s_side)].append((s_key, i, 0))
        slots[(target, t_side)].append((t_key, i, 1))

    ports: dict[tuple[int, int], tuple[float, float]] = {}

    for (sid, side), claims in slots.items():
        for index, (_, i, which) in enumerate(sorted(claims)):
            ports[(i, which)] = _port(router.box[sid], side, index, len(claims))

    routes = []

    for i, (source, target, s_side, t_side, _, _) in enumerate(plans):
        start, end = ports[(i, 0)], ports[(i, 1)]

        if s_side == "t":
            points = router.arch(start, end)
        elif source in tested:
            points = router.climb(router.box[source], start, end, gx[(source, target)])
        elif target in tested:
            points = router.climb(router.box[target], end, start, gx[(target, source)])[::-1]
        elif s_side == t_side:
            points = router.bracket(start, end)
        else:
            points = router.across(start, end, router.column[source], router.column[target])

        routes.append(Route(source, target, tuple(points)))

    return tuple(routes)


def layout_map(change_map: ChangeMap) -> Layout:
    lanes = _lanes(change_map)
    dense = len(change_map.symbols) > DENSE
    neighbors: dict[str, set[str]] = {s.id: set() for s in change_map.symbols}

    for edge in change_map.edges:
        if edge.source in neighbors and edge.target in neighbors:
            neighbors[edge.source].add(edge.target)
            neighbors[edge.target].add(edge.source)

    status = {s.id: s.status for s in change_map.symbols}
    path = {s.id: s.path for s in change_map.symbols}
    gap = ROW_GAP if dense else GAP_Y

    def height(sid: str) -> int:
        return ROW_H if dense else CHANGED_H if status[sid] != "context" else CONTEXT_H

    columns = _columns(change_map, lanes, neighbors)
    limit = PAD + max(MIN_ROW_W, len(columns) * (CARD_W + GAP_X) - GAP_X)
    drawn = {s.path for s in change_map.symbols if s.status != "context"}
    chips = sorted(
        (f for f in change_map.files if f.path not in drawn),
        key=lambda f: (f.sensitive is None, f.path),
    )
    boxes = [
        Box("file", chip, "files", x, y, w, CHIP_H)
        for chip, x, y, w in _flow(
            ((f.path, _chip_width(f)) for f in chips),
            PAD,
            PAD + LABEL,
            limit,
            CHIP_H,
            (CHIP_GAP, CHIP_GAP),
        )
    ]
    files_bottom = max((b.y + b.h for b in boxes), default=PAD)
    main_top = files_bottom + LANE_GAP if boxes else PAD + LABEL + BAND_PAD
    stacks: list[list[tuple[str, BoxKind, int]]] = []

    for _, ids in columns:
        stack: list[tuple[str, BoxKind, int]] = []

        for group in _grouped(ids, path) if dense else [ids]:
            if dense:
                stack.append((group[0], "group", GROUP_H))

            stack.extend((sid, "symbol", height(sid)) for sid in group)

        stacks.append(stack)

    column_h = [sum(h for _, _, h in stack) + gap * (len(stack) - 1) for stack in stacks]
    main_h = max(column_h, default=0)
    main: list[list[Box]] = []

    for index, ((lane, _), stack, col_h) in enumerate(zip(columns, stacks, column_h, strict=True)):
        x = PAD + index * (CARD_W + GAP_X)
        y = main_top + _snap((main_h - col_h) / 2)
        col = []

        for sid, kind, h in stack:
            col.append(Box(kind, sid, lane, x, y, CARD_W, h))
            y += h + gap

        main.append(col)

    flat = [b for col in main for b in col]
    boxes.extend(flat)
    main_right = max((b.x + b.w for b in flat), default=PAD)
    centers = {b.id: b.x + b.w / 2 for b in flat if b.kind == "symbol"}
    tests = []

    for s in change_map.symbols:
        if lanes[s.id] == "tests":
            targets = [centers[n] for n in neighbors[s.id] if n in centers]
            wanted = sum(targets) / len(targets) if targets else float(main_right)
            tests.append((wanted, s.id))

    main_bottom = main_top + main_h if flat else files_bottom
    tests_top = main_bottom + LANE_GAP + LABEL
    test_h = ROW_H if dense else CHANGED_H
    placed = _flow(
        ((sid, CARD_W) for _, sid in sorted(tests)),
        PAD,
        tests_top,
        limit,
        test_h,
        (TEST_GAP, gap),
    )
    test_boxes = {sid: Box("symbol", sid, "tests", x, y, w, test_h) for sid, x, y, w in placed}
    boxes.extend(test_boxes.values())

    router = _Router(main, test_boxes, main_bottom, tests_top)
    routes = _routes(
        router,
        sorted(
            (e.source, e.target)
            for e in change_map.edges
            if e.source in router.box and e.target in router.box
        ),
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

    return Layout(width, canvas_h, dense, tuple(bands), tuple(boxes), tuple(routes))
