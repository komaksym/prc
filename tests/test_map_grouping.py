"""Grouped overview for large PRs: one card per folder, summed edges, expand in place."""

from __future__ import annotations

import dataclasses
import json
import random
import re
import shutil
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from map_sample import large_map, shop_map
from prc.changemap import ChangeMap, DiffLine, FileNode, Hunk, Symbol
from prc.presentation.map_layout import folder_edges, folders_of, layout_map
from prc.presentation.render_map import render_map

playwright = pytest.importorskip("playwright.sync_api")

VIEWPORT = {"width": 1280, "height": 800}


def changed_ids(change_map: ChangeMap) -> set[str]:
    return {s.id for s in change_map.symbols if s.status != "context"}


def test_small_map_has_no_folders() -> None:
    change_map = shop_map()

    assert len(changed_ids(change_map)) <= 40
    assert folders_of(change_map) == ()
    assert folder_edges(change_map, ()) == ()

    layout = layout_map(change_map)

    assert all(box.lane != "folders" for box in layout.boxes)


def test_threshold_boundary_is_forty_changed_symbols() -> None:
    assert len(changed_ids(large_map(32))) == 40
    assert folders_of(large_map(32)) == ()

    assert len(changed_ids(large_map(33))) == 41
    assert folders_of(large_map(33)) != ()


def test_large_map_groups_by_folder() -> None:
    change_map = large_map(60)
    folders = folders_of(change_map)

    assert {f.label for f in folders} == {"src/pkg", "tests"}

    seen: list[str] = []

    for folder in folders:
        assert folder.members
        seen.extend(folder.members)

    assert sorted(seen) == sorted(changed_ids(change_map))


def scattered_map() -> ChangeMap:
    """Shop plus 41 changed symbols: a 10-file folder and a one-file folder."""
    base = shop_map()
    extra: list[Symbol] = []
    paths: dict[str, list[str]] = {}

    def add(sid: str) -> None:
        path, qualname = sid.split("::", 1)
        hunk = Hunk(
            1,
            1,
            (DiffLine("-", 1, None, "    old()"), DiffLine("+", 1, None, "    new()"),),
        )
        extra.append(
            Symbol(sid, path, qualname, "function", "modified", (1, 1), (1, 1), 1, 1, (hunk,), 0)
        )
        paths.setdefault(path, []).append(sid)

    for i in range(40):
        add(f"src/big/m{i // 4}.py::big_func_{i:02d}")

    add("lonely/only.py::solo")

    files = base.files + tuple(
        FileNode(path, "code", "modified", "python", None, len(ids), len(ids), (), tuple(sorted(ids)))
        for path, ids in sorted(paths.items())
    )

    return dataclasses.replace(
        base,
        files=files,
        symbols=tuple(sorted(base.symbols + tuple(extra), key=lambda s: s.id)),
    )


def test_small_folder_uses_one_card_per_file() -> None:
    folders = folders_of(scattered_map())
    by_label = {f.label: f for f in folders}

    assert by_label["src/big"].is_dir
    assert len(by_label["src/big"].members) == 40
    assert not by_label["lonely/only.py"].is_dir
    assert by_label["lonely/only.py"].members == ("lonely/only.py::solo",)
    assert by_label["src/shop"].is_dir
    assert not by_label["web/src/cart.ts"].is_dir


def test_group_counts_equal_member_sums() -> None:
    for make in (lambda: large_map(33), lambda: large_map(60)):
        change_map = make()
        by_id = {s.id: s for s in change_map.symbols}
        kinds = {f.path: f.kind for f in change_map.files}

        for folder in folders_of(change_map):
            members = [by_id[sid] for sid in folder.members]

            assert folder.added == sum(s.status == "added" for s in members)
            assert folder.modified == sum(s.status == "modified" for s in members)
            assert folder.deleted == sum(s.status == "deleted" for s in members)
            assert folder.tests == sum(kinds[s.path] == "test" for s in members)


def test_folder_edges_sum_member_calls() -> None:
    change_map = large_map(60)
    folders = folders_of(change_map)
    edges = folder_edges(change_map, folders)
    owner = {sid: i for i, f in enumerate(folders) for sid in f.members}
    cross = [
        (e.source, e.target)
        for e in change_map.edges
        if e.source in owner and e.target in owner and owner[e.source] != owner[e.target]
    ]

    assert sum(e.count for e in edges) == len(cross)
    assert all(e.count >= 1 for e in edges)
    assert {(e.source, e.target) for e in edges} == {
        (owner[s], owner[t]) for s, t in cross
    }


def test_grouped_layout_stays_well_formed_and_deterministic() -> None:
    change_map = large_map(60)
    layout = layout_map(change_map)
    boxes = [b for b in layout.boxes if b.lane == "folders"]

    assert boxes
    assert len({(b.kind, b.id) for b in layout.boxes}) == len(layout.boxes)

    for box in boxes:
        assert all(v % 8 == 0 for v in (box.x, box.y, box.w, box.h))
        assert box.x >= 0 and box.x + box.w <= layout.width
        assert box.y >= 0 and box.y + box.h <= layout.height

    flat = list(layout.boxes)

    for i, a in enumerate(flat):
        for b in flat[i + 1 :]:
            assert not (
                a.x < b.x + b.w
                and b.x < a.x + a.w
                and a.y < b.y + b.h
                and b.y < a.y + a.h
            ), (a, b)

    bands = {band.lane: band for band in layout.bands}

    for box in boxes:
        band = bands["folders"]

        assert band.x <= box.x and box.x + box.w <= band.x + band.w
        assert band.y <= box.y and box.y + box.h <= band.y + band.h

    rng = random.Random(11)

    def shuffled[T](items: tuple[T, ...]) -> tuple[T, ...]:
        copy = list(items)
        rng.shuffle(copy)

        return tuple(copy)

    variant = dataclasses.replace(
        change_map,
        symbols=shuffled(change_map.symbols),
        edges=shuffled(change_map.edges),
        files=shuffled(change_map.files),
    )

    assert layout_map(variant) == layout


def test_grouped_map_json_carries_folders_and_edges() -> None:
    html = render_map(large_map(60))
    payload = json.loads(re.search(r"<script>(const LAYOUT = .*?;\n)", html, re.DOTALL)[1][len("const LAYOUT = ") : -2])

    assert [f["label"] for f in payload["folderInfo"]] == ["src/pkg", "tests"]
    assert len(payload["folders"]) == 2
    assert sum(count for _, _, count, _ in payload["folderEdges"]) == sum(
        e.count for e in folder_edges(large_map(60), folders_of(large_map(60)))
    )

    small = json.loads(
        re.search(r"<script>(const LAYOUT = .*?;\n)", render_map(shop_map()), re.DOTALL)[1][len("const LAYOUT = ") : -2]
    )

    assert small["folders"] == [] and small["folderEdges"] == [] and small["folderInfo"] == []


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with playwright.sync_playwright() as driver:
        try:
            launched = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            lines = str(error).splitlines()
            pytest.skip(f"Chromium cannot launch here: {lines[0]}")

        yield launched
        launched.close()


@pytest.fixture
def open_map(browser: Any, tmp_path: Path) -> Iterator[Callable[[ChangeMap], Any]]:
    pages: list[Any] = []

    def open_(change_map: ChangeMap) -> Any:
        path = tmp_path / f"grouped-{len(pages)}.html"
        path.write_text(render_map(change_map))
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
        pages.append(page)
        page.goto(path.as_uri())
        page.wait_for_function("() => window.prcTour !== undefined")

        return page

    yield open_

    for page in pages:
        page.close()


def folder_cards(page: Any) -> Any:
    return page.locator("[data-folder]")


def test_grouped_first_screen_lists_every_folder(open_map: Callable[[ChangeMap], Any]) -> None:
    page = open_map(large_map(60))

    assert folder_cards(page).count() == 2
    assert page.locator("[data-folder-edge]").count() >= 1
    assert page.locator("[data-node]").count() == sum(
        1 for b in layout_map(large_map(60)).boxes if b.kind != "group"
    )
    assert page.locator("[data-edge]").count() == len(large_map(60).edges)
    assert page.evaluate("window.prcTour.steps[0].kind") == "overview"


def test_click_expands_group_in_place_and_escape_collapses(
    open_map: Callable[[ChangeMap], Any],
) -> None:
    change_map = large_map(60)
    ids = [s.id for s in change_map.symbols]
    member = next(s.id for s in change_map.symbols if s.status != "context")
    owner = next(
        i for i, f in enumerate(folders_of(change_map)) if member in f.members
    )
    hidden = "() => getComputedStyle(document.querySelector('[data-node=\"s" + str(
        ids.index(member)
    ) + "\"]')).opacity"
    page = open_map(change_map)

    assert page.evaluate(hidden) == "0"

    folder_cards(page).nth(owner).click()

    assert "open" in (folder_cards(page).nth(owner).get_attribute("class") or "")
    page.wait_for_function(hidden + " === '1'")

    page.keyboard.press("Escape")

    assert "open" not in (folder_cards(page).nth(owner).get_attribute("class") or "")
    page.wait_for_function(hidden + " === '0'")


def test_expanding_all_groups_yields_map_json_edge_total(
    open_map: Callable[[ChangeMap], Any],
) -> None:
    change_map = large_map(60)
    page = open_map(change_map)

    for i in range(folder_cards(page).count()):
        card = folder_cards(page).nth(i)

        if "open" not in (card.get_attribute("class") or ""):
            card.click()

    assert page.locator("[data-edge]").count() == len(change_map.edges)


def test_tour_visits_folders_first(open_map: Callable[[ChangeMap], Any]) -> None:
    page = open_map(large_map(60))
    kinds = page.evaluate("window.prcTour.steps.map((s) => s.kind)")

    assert kinds[0] == "overview"
    assert kinds[1] == "folder" and kinds[2] == "folder"
    assert kinds[-1] == "summary"

    page.evaluate("window.prcTour.seek(window.prcTour.steps[1].start + 0.1)")

    assert "src/pkg" in page.locator("#caption").text_content()


def test_folder_edge_width_grows_with_call_count(
    open_map: Callable[[ChangeMap], Any],
) -> None:
    page = open_map(large_map(60))
    widths = page.evaluate(
        """() => [...document.querySelectorAll("[data-folder-edge]")]
           .map((e) => [e.getAttribute("data-count"), parseFloat(e.style.strokeWidth || e.getAttribute("stroke-width"))])"""
    )

    assert widths
    assert all(w > 0 for _, w in widths)

    by_count = sorted(widths, key=lambda pair: int(pair[0]))

    assert [w for _, w in by_count] == sorted(w for _, w in by_count)


def ocr_text(png: Path) -> str:
    if not shutil.which("tesseract"):
        pytest.skip("tesseract not on PATH")

    out = subprocess.run(
        ["tesseract", str(png), "stdout", "--psm", "6"],
        capture_output=True,
        text=True,
        check=True,
    )

    return out.stdout


def test_grouped_first_screen_labels_pass_ocr(
    open_map: Callable[[ChangeMap], Any], tmp_path: Path
) -> None:
    page = open_map(large_map(60))
    shot = tmp_path / "groups.png"
    page.screenshot(path=str(shot))

    found = re.sub(r"[^a-z0-9/]", "", ocr_text(shot).lower())

    for label in ("src/pkg", "tests"):
        assert re.sub(r"[^a-z0-9/]", "", label) in found, found

    assert folder_cards(page).count() <= 25

    for i in range(folder_cards(page).count()):
        box = folder_cards(page).nth(i).bounding_box()

        assert box is not None and box["height"] >= 20
        assert 0 <= box["x"] and box["x"] + box["width"] <= VIEWPORT["width"]
        assert 0 <= box["y"] and box["y"] + box["height"] <= VIEWPORT["height"]


def test_board_coverage_states_changed_file_budget() -> None:
    from prc.explainer.boards import coverage

    change_map = {
        "files": [
            {"path": "a.py", "kind": "code", "added": 2},
            {"path": "b.py", "kind": "code", "added": 5},
        ],
        "brief": {
            "files": [
                {"path": "a.py", "kind": "code"},
                {"path": "b.py", "kind": "code"},
            ]
        },
        "symbols": [
            {
                "id": "a.py::f",
                "path": "a.py",
                "status": "modified",
                "span": [1, 10],
                "base_span": [1, 10],
            },
            {
                "id": "b.py::g",
                "path": "b.py",
                "status": "added",
                "span": [1, 4],
                "base_span": None,
            },
        ],
        "tour": [{"kind": "entry", "focus": ["a.py::f"]}],
    }
    board = {
        "name": "budget",
        "scenes": [{"type": "list", "cite": [{"line": "a.py:3"}]}],
    }

    out = coverage(board, change_map)

    assert "covers 1 of 2 changed files" in out
    assert "files 1/2" in out
