"""The rendered page in Chromium. Skips with the launch error where no browser can start."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from map_sample import CHECKOUT, CI, hostile_map, large_map, shop_map
from prc.changemap import ChangeMap
from prc.presentation.map_layout import layout_map
from prc.presentation.render_map import render_map

playwright = pytest.importorskip("playwright.sync_api")

VIEWPORT = {"width": 1440, "height": 900}
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

    assert opened.page.locator("[data-node]").count() == len(layout_map(change_map).boxes)
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
