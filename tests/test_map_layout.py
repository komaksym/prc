from __future__ import annotations

import dataclasses
import random
from collections import Counter
from collections.abc import Callable
from functools import partial

import pytest

from map_sample import (
    CART_CLASS,
    CHECKOUT,
    CI,
    DISCOUNT,
    FORMAT,
    LEGACY,
    NEW_TEST,
    OLD_TEST,
    POST,
    PREVIEW,
    SUBTOTAL,
    TAX,
    TOTAL,
    VIEW,
    large_map,
    shop_map,
)
from prc.changemap import ChangeMap, Edge, Step
from prc.presentation.map_layout import (
    DENSE_ROWS,
    GAP_X,
    GRID,
    ROW_H,
    Box,
    Layout,
    cubics,
    layout_map,
)


def boxes(layout: Layout) -> dict[str, Box]:
    return {box.id: box for box in layout.boxes}


def right(box: Box) -> int:
    return box.x + box.w


def bottom(box: Box) -> int:
    return box.y + box.h


def overlaps(a: Box, b: Box) -> bool:
    return a.x < right(b) and b.x < right(a) and a.y < bottom(b) and b.y < bottom(a)


def assert_well_formed(layout: Layout, change_map: ChangeMap) -> None:
    found = layout.boxes
    ids = [(box.kind, box.id) for box in found]

    assert len(ids) == len(set(ids))
    assert {box.id for box in found if box.kind == "symbol"} == {s.id for s in change_map.symbols}

    for box in found:
        assert box.x >= 0 and right(box) <= layout.width, box
        assert box.y >= 0 and bottom(box) <= layout.height, box
        assert all(v % GRID == 0 for v in (box.x, box.y, box.w, box.h)), box

    for i, a in enumerate(found):
        for b in found[i + 1 :]:
            assert not overlaps(a, b), (a, b)


def test_shop_lanes_follow_the_call_direction() -> None:
    change_map = shop_map()
    layout = layout_map(change_map)
    by_id = boxes(layout)

    assert_well_formed(layout, change_map)
    assert {box_id: box.lane for box_id, box in by_id.items()} == {
        POST: "callers",
        PREVIEW: "callers",
        CHECKOUT: "changed",
        VIEW: "changed",
        DISCOUNT: "changed",
        TAX: "changed",
        LEGACY: "changed",
        FORMAT: "changed",
        SUBTOTAL: "callees",
        CART_CLASS: "callees",
        TOTAL: "callees",
        NEW_TEST: "tests",
        OLD_TEST: "tests",
        CI: "files",
        "README.md": "files",
    }

    main = [b for b in by_id.values() if b.lane in ("callers", "changed", "callees")]
    lane = {name: [b for b in main if b.lane == name] for name in ("callers", "changed", "callees")}

    assert max(map(right, lane["callers"])) < min(b.x for b in lane["changed"])
    assert max(map(right, lane["changed"])) < min(b.x for b in lane["callees"])
    assert by_id[CHECKOUT].x == by_id[VIEW].x
    assert {by_id[s].x for s in (DISCOUNT, TAX, LEGACY, FORMAT)} == {right(by_id[CHECKOUT]) + GAP_X}

    files = [by_id[CI], by_id["README.md"]]
    tests = [by_id[NEW_TEST], by_id[OLD_TEST]]

    assert max(map(bottom, files)) < min(b.y for b in main)
    assert max(map(bottom, main)) < min(b.y for b in tests)


def test_files_with_changed_symbols_are_drawn_through_their_symbols() -> None:
    by_id = boxes(layout_map(shop_map()))

    assert {box_id for box_id, box in by_id.items() if box.kind == "file"} == {CI, "README.md"}


def test_layout_is_independent_of_input_order() -> None:
    change_map = shop_map()
    rng = random.Random(7)

    def shuffled[T](items: tuple[T, ...]) -> tuple[T, ...]:
        copy = list(items)
        rng.shuffle(copy)

        return tuple(copy)

    for _ in range(5):
        variant = dataclasses.replace(
            change_map,
            symbols=shuffled(change_map.symbols),
            edges=shuffled(change_map.edges),
            files=shuffled(change_map.files),
        )

        assert layout_map(variant) == layout_map(change_map)


def test_callers_are_ordered_to_avoid_crossings() -> None:
    change_map = shop_map()
    a, b = "src/zz.py::a_caller", "src/zz.py::b_caller"
    extra = tuple(
        dataclasses.replace(change_map.symbols[0], id=sid, path="src/zz.py", qualname=sid[-8:])
        for sid in (a, b)
    )
    variant = dataclasses.replace(
        change_map,
        symbols=change_map.symbols + extra,
        edges=change_map.edges
        + (Edge(a, VIEW, "kept", "exact"), Edge(b, CHECKOUT, "kept", "exact")),
    )
    by_id = boxes(layout_map(variant))

    assert (by_id[b].y < by_id[a].y) == (by_id[CHECKOUT].y < by_id[VIEW].y)


def test_call_cycles_terminate() -> None:
    change_map = shop_map()
    variant = dataclasses.replace(
        change_map,
        edges=change_map.edges
        + (Edge(DISCOUNT, CHECKOUT, "added", "exact"), Edge(TAX, DISCOUNT, "added", "exact")),
    )
    layout = layout_map(variant)

    assert_well_formed(layout, variant)
    assert all(boxes(layout)[s].lane == "changed" for s in (CHECKOUT, DISCOUNT, TAX))


def test_map_without_symbols_lays_out_file_chips() -> None:
    change_map = shop_map()
    variant = dataclasses.replace(
        change_map,
        symbols=(),
        edges=(),
        files=tuple(dataclasses.replace(f, symbols=()) for f in change_map.files),
        tour=(Step("overview", (), None), Step("summary", (), None)),
    )
    layout = layout_map(variant)

    assert_well_formed(layout, variant)
    assert len(layout.boxes) == len(variant.files)
    assert all(box.lane == "files" for box in layout.boxes)


def test_sixty_symbols_stay_compact() -> None:
    change_map = large_map(60)
    layout = layout_map(change_map)

    assert_well_formed(layout, change_map)

    columns = Counter(
        (box.lane, box.x) for box in layout.boxes if box.kind == "symbol" and box.lane != "files"
    )

    assert max(n for (lane, _), n in columns.items() if lane != "tests") <= DENSE_ROWS
    assert 0.8 <= layout.width / layout.height <= 3.5, (layout.width, layout.height)


def test_bands_cover_their_boxes() -> None:
    layout = layout_map(large_map(60))
    bands = {band.lane: band for band in layout.bands}

    for box in layout.boxes:
        band = bands[box.lane]

        assert band.x <= box.x and right(box) <= band.x + band.w
        assert band.y <= box.y and bottom(box) <= band.y + band.h


def with_cycle() -> ChangeMap:
    change_map = shop_map()

    return dataclasses.replace(
        change_map,
        edges=change_map.edges
        + (Edge(DISCOUNT, CHECKOUT, "added", "exact"), Edge(TAX, DISCOUNT, "added", "exact")),
    )


def point_at(c: tuple[float, ...], t: float) -> tuple[float, float]:
    u = 1 - t
    x = u**3 * c[0] + 3 * u * u * t * c[2] + 3 * u * t * t * c[4] + t**3 * c[6]
    y = u**3 * c[1] + 3 * u * u * t * c[3] + 3 * u * t * t * c[5] + t**3 * c[7]

    return x, y


def on_border(box: Box, x: float, y: float) -> bool:
    inside_x = box.x <= x <= right(box)
    inside_y = box.y <= y <= bottom(box)

    return (inside_x and y in (box.y, bottom(box))) or (inside_y and x in (box.x, right(box)))


MAPS: dict[str, Callable[[], ChangeMap]] = {
    "shop": shop_map,
    "cycle": with_cycle,
    "large20": partial(large_map, 20),
    "large60": partial(large_map, 60),
}


@pytest.mark.parametrize("name", sorted(MAPS))
def test_every_edge_has_one_route_between_its_cards(name: str) -> None:
    change_map = MAPS[name]()
    layout = layout_map(change_map)
    by_id = boxes(layout)

    assert sorted((r.source, r.target) for r in layout.routes) == sorted(
        (e.source, e.target) for e in change_map.edges if e.source in by_id and e.target in by_id
    )

    for route in layout.routes:
        first, last = route.points[0], route.points[-1]

        assert on_border(by_id[route.source], first[0], first[1]), route
        assert on_border(by_id[route.target], last[0], last[1]), route


@pytest.mark.parametrize("name", sorted(MAPS))
def test_no_edge_passes_through_a_card(name: str) -> None:
    layout = layout_map(MAPS[name]())
    solid = [b for b in layout.boxes if b.kind in ("symbol", "group")]

    for route in layout.routes:
        for curve in cubics(route.points):
            for step in range(41):
                x, y = point_at(curve, step / 40)

                for box in solid:
                    inside = box.x + 1 < x < right(box) - 1 and box.y + 1 < y < bottom(box) - 1

                    assert not inside, (route.source, route.target, box.id, x, y)


def test_maps_over_thirty_symbols_use_rows_grouped_by_file() -> None:
    assert not layout_map(shop_map()).dense

    change_map = large_map(60)
    layout = layout_map(change_map)
    path = {s.id: s.path for s in change_map.symbols}
    main = [b for b in layout.boxes if b.lane in ("callers", "changed", "callees")]

    assert layout.dense
    assert {b.h for b in main if b.kind == "symbol"} == {ROW_H}

    for x in {b.x for b in main}:
        column = sorted((b for b in main if b.x == x), key=lambda b: b.y)
        seen: list[str] = []

        for box in column:
            if box.kind == "group":
                seen.append(path[box.id])
            else:
                assert seen and seen[-1] == path[box.id], box

        assert len(seen) == len(set(seen)), seen


def test_tests_fill_rows_left_to_right() -> None:
    layout = layout_map(large_map(60))
    tests = [b for b in layout.boxes if b.lane == "tests"]
    rows = Counter(b.y for b in tests)
    per_row = max(rows.values())

    assert len(tests) == 8
    assert len(rows) == -(-len(tests) // per_row)
    assert per_row > 1
