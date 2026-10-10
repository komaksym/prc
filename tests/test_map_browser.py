"""The rendered page in real Chromium, with settled pixel evidence."""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import re
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest
from playwright import sync_api as playwright

from map_sample import CHECKOUT, large_map, shop_map
from pngcheck import luminance, variance
from prc.changemap import ChangeMap
from prc.presentation.graphdoc import to_graph_doc
from prc.presentation.render_map import render_map

VIEWPORT = {"width": 1440, "height": 900}
SHOTS = Path("/private/tmp/step1-workB-shots")
WORLD_VARIANCE_MIN = 100.0


def world_variance(png: bytes) -> float:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
        tmp.write(png)
        tmp.flush()
        return variance(luminance(tmp.name))


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with playwright.sync_playwright() as driver:
        launched = driver.chromium.launch()
        yield launched
        launched.close()


@dataclass
class Opened:
    page: Any
    problems: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)


@pytest.fixture
def open_map(browser: Any, tmp_path: Path) -> Iterator[Callable[[ChangeMap], Opened]]:
    SHOTS.mkdir(parents=True, exist_ok=True)
    pages: list[Any] = []

    def open_(change_map: ChangeMap) -> Opened:
        path = tmp_path / ("map-" + str(len(pages)) + ".html")
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
        settle(page)
        return opened

    yield open_

    for page in pages:
        page.close()


def settle(page: Any) -> None:
    page.wait_for_function(
        "() => [...document.images].every(img => img.complete && img.naturalWidth > 0)"
    )
    page.evaluate("() => document.fonts.ready")
    page.evaluate("""() => new Promise(resolve => {
        let last = '', stable = 0;
        function frame() {
            const state = ['world', 'drawer'].map(id =>
                getComputedStyle(document.getElementById(id)).transform).join('|');
            stable = state === last ? stable + 1 : 0;
            last = state;
            if (stable >= 5) resolve();
            else requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
    })""")


def shot(page: Any, tmp_path: Path, name: str) -> Path:
    settle(page)
    out = tmp_path / (name + ".png")
    page.screenshot(path=str(out))
    assert variance(luminance(str(out))) > WORLD_VARIANCE_MIN
    (SHOTS / (name + ".png")).write_bytes(out.read_bytes())
    return out


def assert_drawer_fits(page: Any) -> None:
    page.wait_for_function("""() => {
        const drawer = document.querySelector('#drawer');
        return drawer.getAttribute('aria-hidden') === 'false'
            && getComputedStyle(drawer).transform === 'none';
    }""")
    settle(page)
    bounds = page.evaluate("""() => {
        const drawer = document.querySelector('#drawer');
        const box = drawer.getBoundingClientRect();
        const chips = [...drawer.querySelectorAll('.etag, .fact, .pill')];
        return {right: box.right, width: innerWidth,
            overflow: chips.filter(chip => {
                const rect = chip.getBoundingClientRect();
                return rect.left < box.left || rect.right > box.right;
            }).map(chip => chip.textContent),
            body: drawer.querySelector('.d-body').scrollWidth,
            client: drawer.querySelector('.d-body').clientWidth};
    }""")
    assert bounds["right"] <= bounds["width"], bounds
    assert bounds["overflow"] == [], bounds
    assert bounds["body"] <= bounds["client"], bounds


def test_map_browser_legend_samples_have_visible_strokes(
    open_map: Callable[[ChangeMap], Opened], tmp_path: Path
) -> None:
    page = open_map(shop_map()).page
    settle(page)
    paths = page.locator(".legend svg path")
    assert paths.count() == 4
    for i in range(paths.count()):
        style = paths.nth(i).evaluate("""path => {
            const style = getComputedStyle(path);
            return {stroke: style.stroke, width: parseFloat(style.strokeWidth),
                opacity: parseFloat(style.opacity)};
        }""")
        assert style["stroke"] not in ("none", "transparent", "rgba(0, 0, 0, 0)"), style
        assert style["width"] > 0 and style["opacity"] > 0, style
        png = page.locator(".legend svg").nth(i).screenshot(path=str(tmp_path / f"legend-{i}.png"))
        assert world_variance(png) > 5
    assert "name-only" in page.locator(".legend").inner_text()
    assert "dotted" not in page.locator(".legend").inner_text()


def test_map_browser_pixel_probe_rejects_blank_diagram(
    browser: Any, open_map: Callable[[ChangeMap], Opened], tmp_path: Path
) -> None:
    page = browser.new_page(viewport=VIEWPORT)
    try:
        page.set_content("<style>body { margin: 0; background: #fafafa; }</style>")
        path = tmp_path / "blank.png"
        page.screenshot(path=str(path))
        assert variance(luminance(str(path))) < 0.01
    finally:
        page.close()
    page = open_map(shop_map()).page
    page.locator(".diagram").evaluate("""img => {
        img.src = 'data:image/svg+xml,' + encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" width="2142" height="522">'
            + '<rect width="100%" height="100%" fill="#fafafa"/></svg>');
    }""")
    settle(page)
    blank = page.locator("#world").screenshot(path=str(tmp_path / "blank-diagram.png"))
    assert world_variance(blank) < WORLD_VARIANCE_MIN


@pytest.mark.parametrize("width", [360, 1440])
def test_map_browser_drawer_stays_inside_viewport(
    open_map: Callable[[ChangeMap], Opened], tmp_path: Path, width: int
) -> None:
    page = open_map(shop_map()).page
    page.set_viewport_size({"width": width, "height": 900})
    page.click("#zoom-fit")
    page.click(checkout_node(shop_map()))
    assert_drawer_fits(page)
    shot(page, tmp_path, f"drawer-bounds-{width}")


def test_map_browser_long_diff_and_chip_stay_inside_drawer(
    open_map: Callable[[ChangeMap], Opened], tmp_path: Path
) -> None:
    change_map = shop_map()
    file = change_map.files[0]
    line = dataclasses.replace(file.hunks[0].lines[0], text="x" * 400)
    hunk = dataclasses.replace(file.hunks[0], lines=(line,))
    file = dataclasses.replace(file, sensitive="CIworkflow" * 40, hunks=(hunk,))
    change_map = dataclasses.replace(change_map, files=(file, *change_map.files[1:]))
    page = open_map(change_map).page
    page.click('[data-node="f0"]')
    assert_drawer_fits(page)
    diff = page.locator(".diff")
    assert diff.evaluate("box => box.scrollWidth > box.clientWidth")
    diff.evaluate("box => { box.scrollLeft = box.scrollWidth; }")
    assert diff.evaluate("box => box.scrollLeft > 0")
    shot(page, tmp_path, "drawer-long-diff")


def checkout_node(change_map: ChangeMap) -> str:
    return '[data-node="s' + str([s.id for s in change_map.symbols].index(CHECKOUT)) + '"]'


def test_map_browser_hooks(open_map: Callable[[ChangeMap], Opened], tmp_path: Path) -> None:
    change_map = shop_map()
    plotted = to_graph_doc(change_map)
    opened = open_map(change_map)
    page = opened.page
    assert page.locator("img.diagram").count() == 1
    assert page.locator(".fallback").count() == 0
    assert page.locator("[data-node]").count() == len(plotted.doc["nodes"])
    alignment = page.evaluate("""() => {
        const block = JSON.parse(document.getElementById('map-data').textContent);
        const atlas = prcLens.render(block.graph, {lens: 'architecture', theme: 'light'}).atlas;
        return [...document.querySelectorAll('[data-node]')].map(hit => {
            const box = atlas.nodes[hit.dataset.node];
            return [parseFloat(hit.style.left) - box.x, parseFloat(hit.style.top) - box.y,
                parseFloat(hit.style.width) - box.width, parseFloat(hit.style.height) - box.height];
        });
    }""")
    assert alignment and all(delta == 0 for box in alignment for delta in box)
    assert page.locator("#title").text_content() == change_map.title
    assert "no AI drew this" in page.locator("footer").text_content()
    world = world_variance(
        page.locator("#world").screenshot(path=str(tmp_path / "shop-diagram.png"))
    )
    assert world > WORLD_VARIANCE_MIN, world
    drawer = page.locator("#drawer")
    assert drawer.get_attribute("aria-hidden") == "true"
    page.click(checkout_node(change_map))
    assert drawer.get_attribute("aria-hidden") == "false"
    assert "apply_discount" in drawer.text_content()
    assert "total = apply_discount(cart.subtotal(), code)" in drawer.text_content()
    assert "post_checkout" in drawer.text_content()
    assert_drawer_fits(page)
    shot(page, tmp_path, "shop-drawer")
    page.keyboard.press("Escape")
    assert drawer.get_attribute("aria-hidden") == "true"
    page.wait_for_function(
        "() => document.querySelector('#drawer').getBoundingClientRect().left >= innerWidth"
    )
    page.click("#zoom-fit")
    shot(page, tmp_path, "shop")
    page.click("#play")
    page.wait_for_timeout(600)
    assert page.evaluate("document.body.classList.contains('touring')")
    page.keyboard.press("Escape")
    assert not page.evaluate("document.body.classList.contains('touring')")
    before = page.locator("#world").evaluate("world => getComputedStyle(world).transform")
    page.click("#zoom-in")
    zoomed = page.locator("#world").evaluate("world => getComputedStyle(world).transform")
    assert zoomed != before
    page.click("#zoom-out")
    assert page.locator("#world").evaluate("world => getComputedStyle(world).transform") == before
    page.click("#zoom-fit")
    duration = page.evaluate("window.prcTour.duration")
    steps = page.evaluate("window.prcTour.steps")
    assert 20 <= duration <= 45
    assert [s["kind"] for s in steps] == [s.kind for s in change_map.tour]
    assert [s["via"] for s in steps] == [s.via for s in change_map.tour]
    assert all(set(s) == {"kind", "focus", "via", "start", "duration", "caption"} for s in steps)
    page.evaluate("t => window.prcTour.seek(t)", 0)
    assert page.locator(".spot").count() == 1
    assert page.locator(".spot").evaluate("spot => getComputedStyle(spot).opacity") == "1"
    for i, step in enumerate(steps):
        page.evaluate("t => window.prcTour.seek(t)", step["start"] + step["duration"] / 2)
        shot(page, tmp_path, f"shop-step-{i:02d}-{step['kind']}")
    assert opened.problems == []


def test_map_browser_swarm_renders(open_map: Callable[[ChangeMap], Opened], tmp_path: Path) -> None:
    import json

    from prc.pipeline import _change_map_from_stored

    stored = json.loads(
        (
            Path(__file__).resolve().parent / "data" / "graphdoc" / "inputs" / "swarm-116.json"
        ).read_text()
    )
    change_map = _change_map_from_stored(stored)
    opened = open_map(change_map)
    page = opened.page
    assert page.locator("[data-node]").count() == 7
    assert page.locator(".fallback").count() == 0
    assert (
        world_variance(page.locator("#world").screenshot(path=str(tmp_path / "swarm-diagram.png")))
        > WORLD_VARIANCE_MIN
    )
    shot(page, tmp_path, "swarm-116-map")
    assert opened.problems == []


def test_map_browser_grouped(open_map: Callable[[ChangeMap], Opened], tmp_path: Path) -> None:
    change_map = large_map(60)
    plotted = to_graph_doc(change_map)
    groups = [n for n in plotted.doc["nodes"] if n["id"].startswith("g")]
    assert len(groups) == 2
    opened = open_map(change_map)
    page = opened.page
    assert page.locator("[data-node]").count() == len(plotted.doc["nodes"])
    assert page.locator(".fallback").count() == 0
    assert (
        world_variance(
            page.locator("#world").screenshot(path=str(tmp_path / "grouped-diagram.png"))
        )
        > WORLD_VARIANCE_MIN
    )
    shot(page, tmp_path, "grouped")
    drawer = page.locator("#drawer")
    page.click('[data-node="g0"]')
    assert drawer.get_attribute("aria-hidden") == "false"
    assert "changed:" in drawer.text_content()
    rows = page.locator("#drawer .link")
    assert rows.count() == 60, rows.count()
    assert "func_000" in drawer.text_content()
    assert_drawer_fits(page)
    shot(page, tmp_path, "grouped-drawer")
    rows.first.click()
    page.wait_for_timeout(300)
    assert "@@" in drawer.text_content()
    assert "func_000" in drawer.text_content()
    assert_drawer_fits(page)
    shot(page, tmp_path, "grouped-member-diff")
    assert opened.problems == []


def throwing_html(change_map: ChangeMap) -> str:
    html = render_map(change_map)
    bundle = (files("prc.presentation") / "map_assets" / "prlens.bundle.js").read_text()
    boom = 'var prcLens={render:function(){throw new Error("boom")}};'
    assert bundle in html
    html = html.replace(bundle, boom)
    player = (files("prc.presentation") / "map_assets" / "map.js").read_text()
    first = base64.b64encode(hashlib.sha256(boom.encode()).digest()).decode()
    second = base64.b64encode(hashlib.sha256(player.encode()).digest()).decode()
    html, count = re.subn(
        r"script-src 'sha256-[^']+' 'sha256-[^']+'",
        "script-src 'sha256-" + first + "' 'sha256-" + second + "'",
        html,
    )
    assert count == 1
    return html


def test_map_browser_render_error_falls_back(browser: Any, tmp_path: Path) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "fallback.html"
    path.write_text(throwing_html(shop_map()))
    page = browser.new_page(viewport=VIEWPORT)
    problems: list[str] = []
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
    try:
        page.goto(path.as_uri())
        page.wait_for_function("() => window.prcTour !== undefined")
        assert page.locator(".fallback").count() == 1
        assert page.locator("[data-node]").count() == 0
        drawer = page.locator("#drawer")
        assert drawer.get_attribute("aria-hidden") == "true"
        page.locator(".flink").first.click()
        assert drawer.get_attribute("aria-hidden") == "false"
        assert ".github/workflows/ci.yml" in drawer.text_content()
        assert_drawer_fits(page)
        shot(page, tmp_path, "fallback-drawer")
        assert problems == [], problems
    finally:
        page.close()
