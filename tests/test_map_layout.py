from __future__ import annotations

import dataclasses
import random
from collections import Counter

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
from prc.presentation.map_layout import GAP_X, GRID, MAX_ROWS, Box, Layout, layout_map


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

    columns = Counter((box.lane, box.x) for box in layout.boxes if box.lane != "files")

    assert max(n for (lane, _), n in columns.items() if lane != "tests") <= MAX_ROWS
    assert 0.8 <= layout.width / layout.height <= 3.5, (layout.width, layout.height)


def test_bands_cover_their_boxes() -> None:
    layout = layout_map(large_map(60))
    bands = {band.lane: band for band in layout.bands}

    for box in layout.boxes:
        band = bands[box.lane]

        assert band.x <= box.x and right(box) <= band.x + band.w
        assert band.y <= box.y and bottom(box) <= band.y + band.h
