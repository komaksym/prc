#!/usr/bin/env python3
"""Drive PRC's shop map through the real CLI and a background browser."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]


def main() -> None:
    proof_root = ROOT / "artifacts/verification"
    proof_root.mkdir(parents=True, exist_ok=True)
    proof = Path(tempfile.mkdtemp(prefix="map-", dir=proof_root))
    scratch = Path(tempfile.mkdtemp(prefix="prc-verify-"))
    actions: list[dict[str, object]] = []
    errors: list[str] = []
    requests: list[str] = []
    checks: dict[str, object] = {
        "feature": "map-drawer",
        "source": "fixture:shop",
        "page_errors": errors,
        "browser_requests": requests,
    }
    print(proof, flush=True)

    def cli(label: str, *args: str) -> str:
        command = [sys.executable, "-m", "prc.cli", *args]
        result = subprocess.run(command, cwd=scratch, capture_output=True, text=True, check=False)
        (proof / f"{label}.stdout").write_text(result.stdout)
        (proof / f"{label}.stderr").write_text(result.stderr)
        actions.append({"action": label, "command": command, "exit_code": result.returncode})
        assert result.returncode == 0, result.stderr
        return result.stdout

    try:
        import prc

        assert prc.__file__ and Path(prc.__file__).resolve().is_relative_to(ROOT / "src"), (
            prc.__file__
        )
        checks["package"] = prc.__file__
        checks["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        doctor = cli("doctor", "doctor")
        assert "chromium ok" in doctor, doctor
        result = json.loads(
            cli(
                "map",
                "map",
                "--source",
                "fixture:shop",
                "--store",
                str(scratch / "store"),
                "--out",
                str(scratch / "maps"),
            )
        )
        assert result["source"] == "fixture" and result["live_verified"] is False
        assert (result["symbols"], result["edges"], result["steps"]) == (7, 12, 10)
        html = Path(result["html"])
        data = json.loads(Path(result["json"]).read_text())
        assert html.is_file() and html.stat().st_size > 0
        shutil.copytree(html.parent, proof / "output")
        index = next(i for i, s in enumerate(data["symbols"]) if s["qualname"] == "checkout")
        checks["counts"] = result
        checks["map_sha256"] = hashlib.sha256((proof / "output/map.json").read_bytes()).hexdigest()
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: requests.append(request.url))
                page.route("https://**/*", lambda route: route.abort())
                page.route("http://**/*", lambda route: route.abort())
                page.goto((proof / "output" / html.name).as_uri())
                page.wait_for_function("window.prcTour !== undefined")

                def shot(name: str) -> None:
                    page.screenshot(path=str(proof / f"{name}.png"))
                    (proof / f"{name}.txt").write_text(page.locator("body").inner_text())

                shot("overview")
                actions.append({"action": "click checkout", "selector": f'[data-node="s{index}"]'})
                page.locator(f'[data-node="s{index}"]').click()
                drawer = page.locator("#drawer")
                assert drawer.get_attribute("aria-hidden") == "false"
                assert "apply_discount" in drawer.inner_text()
                page.wait_for_function(
                    "() => getComputedStyle(document.querySelector('#drawer')).transform === 'none'"
                )
                shot("drawer")
                actions.append({"action": "press Escape"})
                page.keyboard.press("Escape")
                assert drawer.get_attribute("aria-hidden") == "true"
                page.wait_for_function(
                    "() => document.querySelector('#drawer').getBoundingClientRect().left >= innerWidth"
                )
                shot("closed")
                assert not [url for url in requests if url.startswith(("http:", "https:"))], (
                    requests
                )
                assert not errors, errors
            finally:
                browser.close()
    except Exception as error:
        checks["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        (proof / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
        shutil.rmtree(scratch)
        (proof / "actions.json").write_text(json.dumps(actions, indent=2) + "\n")
        (proof / "cleanup.json").write_text(
            json.dumps(
                {
                    "scratch": str(scratch),
                    "scratch_removed": not scratch.exists(),
                    "evidence_preserved": proof.is_dir(),
                },
                indent=2,
            )
            + "\n"
        )
    assert all((proof / f"{name}.png").is_file() for name in ("overview", "drawer", "closed"))
    print("PASS: CLI map, browser drawer, Escape, offline page, and cleanup.")


if __name__ == "__main__":
    main()
