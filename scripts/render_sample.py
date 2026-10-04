"""Write the hand-built sample maps to artifacts/dev/maps/ and screenshot them when Chromium runs.

Usage: .venv/bin/python scripts/render_sample.py [--light]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from map_sample import CHECKOUT, hostile_map, large_map, shop_map  # noqa: E402
from prc.presentation.render_map import render_map  # noqa: E402

OUT = ROOT / "artifacts" / "dev" / "maps"
VIEWPORT = {"width": 1440, "height": 900}


def screenshots(pages: dict[str, Path], scheme: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            print(f"no screenshots: {str(error).splitlines()[0]}")

            return

        suffix = "" if scheme == "dark" else "-light"

        for name, path in pages.items():
            page = browser.new_page(viewport=VIEWPORT, color_scheme=scheme, device_scale_factor=2)
            page.goto(path.as_uri())
            page.wait_for_function("() => window.prcTour !== undefined")
            page.screenshot(path=OUT / f"{name}-overview{suffix}.png")

            if name == "shop":
                index = [s.id for s in shop_map().symbols].index(CHECKOUT)
                page.click(f'[data-node="s{index}"]')
                page.wait_for_timeout(400)
                page.screenshot(path=OUT / f"{name}-drawer{suffix}.png")
                page.keyboard.press("Escape")

                for step in page.evaluate("window.prcTour.steps"):
                    at = step["start"] + step["duration"] * 0.6
                    page.evaluate("t => window.prcTour.seek(t)", at)
                    page.screenshot(path=OUT / f"{name}-tour-{step['kind']}-{at:05.1f}{suffix}.png")
            else:
                duration = page.evaluate("window.prcTour.duration")
                page.evaluate("t => window.prcTour.seek(t)", duration / 2)
                page.screenshot(path=OUT / f"{name}-tour-mid{suffix}.png")

            page.close()

        browser.close()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {}

    for name, make in (("shop", shop_map), ("large", large_map), ("hostile", hostile_map)):
        path = OUT / f"{name}.html"
        path.write_text(render_map(make()))
        pages[name] = path
        print(path)

    screenshots(pages, "light" if "--light" in sys.argv else "dark")


if __name__ == "__main__":
    main()
