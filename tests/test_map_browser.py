"""The rendered page in Chromium. Skips with the launch error where no browser can start."""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from map_sample import CHECKOUT, CI, hostile_map, large_map, shop_map
from prc.brief import Check, CheckState
from prc.changemap import ChangeMap, Step
from prc.identity import to_jsonable
from prc.presentation.card import compute_stats
from prc.presentation.map_layout import folders_of, layout_map
from prc.presentation.render_map import render_map
from test_changemap import custom_map

playwright = pytest.importorskip("playwright.sync_api")

VIEWPORT = {"width": 1440, "height": 900}


@pytest.mark.parametrize("state", ["pending", "failed"])
def test_ci_state_is_honest_in_header_and_summary(open_map: Any, state: CheckState) -> None:
    change = shop_map()
    change = dataclasses.replace(
        change, brief=dataclasses.replace(change.brief, checks=(Check("ci", state),))
    )
    opened = open_map(change)
    opened.page.evaluate("window.prcTour.seek(window.prcTour.duration)")
    path = (
        Path(__file__).resolve().parents[1]
        / "artifacts/trustworthiness/2026-10-09/regressions"
        / f"ci-{state}-{os.environ.get('PRC_TRUST_PHASE', 'green')}.png"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    opened.page.screenshot(path=str(path))
    header = opened.page.locator("#stats").text_content()
    summary = opened.page.locator("#summary").text_content()
    assert f"CI {state}" in header
    assert f"CI {state}" in summary
    assert "CI passed" not in header + summary


def test_statistics_match_card_for_multiple_tests_in_one_file(
    open_map: Any, tmp_path: Path
) -> None:
    change = custom_map(
        tmp_path,
        {"m.py": b"def run():\n    return 0\n"},
        {
            "m.py": b"def run():\n    return 1\n",
            "tests/test_m.py": b"from m import run\ndef test_a():\n    run()\ndef test_b():\n    run()\n",
        },
    )
    stats = compute_stats(to_jsonable(change))
    opened = open_map(change)
    phase = os.environ.get("PRC_TRUST_PHASE", "green")
    artifact = (
        Path(__file__).resolve().parents[1]
        / "artifacts/trustworthiness/2026-10-09/regressions"
        / f"stats-{phase}.png"
    )
    artifact.parent.mkdir(parents=True, exist_ok=True)
    opened.page.screenshot(path=str(artifact))
    actual = opened.page.locator("#stats .stat").all_text_contents()
    assert any(str(stats.tests_touched) in cell and "test file" in cell for cell in actual), actual
    assert any(str(stats.call_sites) in cell and "call site" in cell for cell in actual), actual
    assert opened.problems == []


STATE = """() => ({
  world: document.getElementById("world").style.transform,
  caption: document.getElementById("caption").textContent,
  captionOpacity: document.getElementById("caption").style.opacity,
  summary: document.getElementById("summary").style.opacity,
  nodes: [...document.querySelectorAll("[data-node]")].map((n) => n.style.opacity),
  edges: [...document.querySelectorAll("[data-edge]")].map((e) => e.style.opacity),
})"""


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with playwright.sync_playwright() as driver:
        try:
            launched = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            lines = str(error).splitlines()
            exit_line = next((line.strip() for line in lines if "process did exit" in line), "")
            pytest.skip(f"Chromium cannot launch here: {lines[0]} {exit_line}".strip())

        yield launched
        launched.close()


@dataclass
class Opened:
    page: Any
    problems: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)


@pytest.fixture
def open_map(browser: Any, tmp_path: Path) -> Iterator[Callable[[ChangeMap], Opened]]:
    pages: list[Any] = []

    def open_(change_map: ChangeMap) -> Opened:
        path = tmp_path / f"map-{len(pages)}.html"
        path.write_text(render_map(change_map))
        page = browser.new_page(viewport=VIEWPORT)
        pages.append(page)
        opened = Opened(page)
        page.on(
            "console",
            lambda m: opened.problems.append(m.text) if m.type in ("error", "warning") else None,
        )
        page.on("pageerror", lambda e: opened.problems.append(str(e)))

        def dialog(d: Any) -> None:
            opened.dialogs.append(d.message)
            d.dismiss()

        page.on("dialog", dialog)
        page.goto(path.as_uri())
        page.wait_for_function("() => window.prcTour !== undefined")

        return opened

    yield open_

    for page in pages:
        page.close()


def node(change_map: ChangeMap, sid: str) -> str:
    return f'[data-node="s{[s.id for s in change_map.symbols].index(sid)}"]'


@pytest.mark.parametrize("make", [shop_map, large_map], ids=["shop", "large"])
def test_page_draws_every_node_without_errors(
    make: Callable[[], ChangeMap], open_map: Callable[[ChangeMap], Opened]
) -> None:
    change_map = make()
    opened = open_map(change_map)

    cards = [b for b in layout_map(change_map).boxes if b.kind != "group"]

    assert opened.page.locator("[data-node]").count() == len(cards)
    assert opened.page.locator("[data-edge]").count() == len(change_map.edges)
    assert opened.page.locator("#title").text_content() == change_map.title
    assert "no AI drew this" in opened.page.locator("footer").text_content()
    assert opened.problems == []


def test_clicking_a_node_opens_its_diff(open_map: Callable[[ChangeMap], Opened]) -> None:
    change_map = shop_map()
    opened = open_map(change_map)
    drawer = opened.page.locator("#drawer")

    assert drawer.get_attribute("aria-hidden") == "true"

    opened.page.click(node(change_map, CHECKOUT))

    assert drawer.get_attribute("aria-hidden") == "false"
    assert "total = apply_discount(cart.subtotal(), code)" in drawer.text_content()
    assert "post_checkout" in drawer.text_content()

    opened.page.keyboard.press("Escape")

    assert drawer.get_attribute("aria-hidden") == "true"
    assert opened.problems == []


def test_tour_seek_is_a_pure_function_of_time(open_map: Callable[[ChangeMap], Opened]) -> None:
    change_map = shop_map()
    page = open_map(change_map).page
    duration = page.evaluate("window.prcTour.duration")
    steps = page.evaluate("window.prcTour.steps")

    assert 20 <= duration <= 45
    assert [step["kind"] for step in steps] == [step.kind for step in change_map.tour]

    mid = duration / 2
    frames: dict[float, list[Any]] = {}

    for t in (mid, 0, duration, mid, 0):
        page.evaluate("t => window.prcTour.seek(t)", t)
        frames.setdefault(t, []).append(page.evaluate(STATE))

    assert frames[mid][0] == frames[mid][1]
    assert frames[0][0] == frames[0][1]
    assert frames[0][0] != frames[mid][0]
    assert float(frames[duration][0]["summary"]) == 1

    risky = steps[1]
    page.evaluate("t => window.prcTour.seek(t)", risky["start"] + risky["duration"] / 2)

    assert "CI workflow changed" in page.locator("#caption").text_content()
    assert CI in page.locator("#caption").text_content()


def test_keys_step_through_the_tour(open_map: Callable[[ChangeMap], Opened]) -> None:
    page = open_map(shop_map()).page
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(1500)

    assert "CI workflow changed" in page.locator("#caption").text_content()

    page.keyboard.press("Space")
    page.wait_for_timeout(1500)

    assert "checkout" in page.locator("#caption").text_content()


def test_hostile_map_renders_inert(open_map: Callable[[ChangeMap], Opened]) -> None:
    change_map = hostile_map()
    opened = open_map(change_map)
    page = opened.page

    for i in range(page.locator("[data-node]").count()):
        page.locator("[data-node]").nth(i).click(force=True)

    duration = page.evaluate("window.prcTour.duration")

    for frame in range(9):
        page.evaluate("t => window.prcTour.seek(t)", duration * frame / 8)

    injected = page.evaluate(
        """() => ({
          img: document.querySelectorAll("img, iframe, object, embed").length,
          scripts: document.scripts.length,
          handlers: [...document.querySelectorAll("*")].flatMap((el) =>
            [...el.attributes].filter((a) => a.name.startsWith("on")).map((a) => a.name)),
          links: [...document.querySelectorAll("a[href]")].map((a) => a.getAttribute("href")),
        })"""
    )

    assert injected == {"img": 0, "scripts": 2, "handlers": [], "links": []}
    assert page.locator("#title").text_content() == change_map.title
    assert opened.dialogs == [] and opened.problems == []


def scale(page: Any) -> float:
    transform = page.locator("#world").evaluate("w => w.style.transform")

    return float(transform.split("scale(")[1].rstrip(")"))


def test_long_title_never_hides_play_at_1280(open_map: Callable[[ChangeMap], Opened]) -> None:
    long = "Refactor the session verification pipeline and " * 4
    opened = open_map(dataclasses.replace(shop_map(), title=long))
    opened.page.set_viewport_size({"width": 1280, "height": 800})
    play = opened.page.locator("#play").bounding_box()
    title = opened.page.locator("#title").bounding_box()

    assert play is not None and title is not None
    assert play["x"] + play["width"] <= 1280
    assert title["x"] + title["width"] <= play["x"]


def test_dense_map_draws_edges_only_for_the_hovered_symbol(
    open_map: Callable[[ChangeMap], Opened],
) -> None:
    change_map = large_map(60)
    opened = open_map(change_map)
    opacity = "e => getComputedStyle(e).opacity"
    edges = opened.page.locator("[data-edge]")

    assert scale(opened.page) >= 0.55
    assert {edges.nth(i).evaluate(opacity) for i in range(edges.count())} == {"0"}

    cards = opened.page.locator("[data-folder]")

    for i in range(cards.count()):
        cards.nth(i).click()

    sid = folders_of(change_map)[0].members[0]
    cards.first.locator(".fmem").first.click()
    opened.page.hover(node(change_map, sid))
    opened.page.wait_for_timeout(300)
    lit = opened.page.locator("[data-edge].lit")

    assert lit.count() == sum(sid in (e.source, e.target) for e in change_map.edges)
    assert all(lit.nth(i).evaluate(opacity) != "0" for i in range(lit.count()))
    assert opened.problems == []


def test_map_without_symbols_says_so(open_map: Callable[[ChangeMap], Opened]) -> None:
    change_map = shop_map()
    variant = dataclasses.replace(
        change_map,
        symbols=(),
        edges=(),
        files=tuple(dataclasses.replace(f, symbols=()) for f in change_map.files),
        tour=(Step("overview", (), None), Step("summary", (), None)),
    )
    opened = open_map(variant)

    assert "No function or class changed" in opened.page.locator(".empty").text_content()
    assert opened.problems == []


def test_untested_badge_fits_inside_its_card(open_map: Callable[[ChangeMap], Opened]) -> None:
    opened = open_map(shop_map())
    badges = opened.page.locator(".node .badge")
    clipped = badges.evaluate_all(
        """badges => badges.flatMap((badge) => {
          const card = badge.closest(".node").getBoundingClientRect();
          const box = badge.getBoundingClientRect();
          return box.right > card.right - 1 || box.left < card.left ? [badge.closest(".node").textContent] : [];
        })"""
    )

    assert badges.count() == 4
    assert clipped == []
    assert opened.problems == []


def test_header_keeps_both_revisions_and_the_link_visible(
    open_map: Callable[[ChangeMap], Opened], tmp_path: Path
) -> None:
    change = custom_map(
        tmp_path, {}, {f"internal/compose/f{i}.go": b"package compose\n" for i in range(7)}
    )
    change = dataclasses.replace(
        change,
        pr="swarm-deploy/swarm-deploy#116",
        url="https://github.com/swarm-deploy/swarm-deploy/pull/116",
        author="Copilot",
        title="Add shared faults package and structured compose errors",
    )
    opened = open_map(change)
    hidden = opened.page.evaluate(
        """() => {
          const meta = document.getElementById("meta").getBoundingClientRect();
          return [...document.querySelectorAll("#meta .mono, #meta a")].flatMap((el) => {
            const box = el.getBoundingClientRect();
            return box.right > meta.right + 0.5 || box.left < meta.left - 0.5 ? [el.textContent] : [];
          });
        }"""
    )

    assert opened.page.locator("#stats .stat").count() == 7
    assert opened.page.locator("#meta a").count() == 1
    assert hidden == []
    assert change.head_sha[:7] in opened.page.locator("#meta .mono").text_content()


def test_counts_of_one_read_singular_in_the_header(
    open_map: Callable[[ChangeMap], Opened], tmp_path: Path
) -> None:
    change = custom_map(
        tmp_path,
        {"m.py": b"def run():\n    return 0\n", "x.go": b"package x\n"},
        {
            "m.py": b"def run():\n    return helper()\n\n\ndef helper():\n    return 1\n",
            "x.go": b"package x\n\nvar y = 1\n",
        },
    )
    assert compute_stats(to_jsonable(change)).call_sites == 1
    opened = open_map(change)
    labels = opened.page.locator("#stats .stat-label").all_text_contents()

    assert "resolved call site" in labels
    assert "file without symbol analysis" in labels
    assert opened.problems == []
