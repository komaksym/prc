from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from prc.evaluation import kit, session


def test_browser_saves_immediate_submit_and_resumes_without_reopening_artifact(
    make_paired: Any,
) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = session.serve(fixture.study)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    out = Path(__file__).parents[1] / "artifacts/e2e/paired-browser"
    out.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url)
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_label("I have seen this PR before").set_checked(False)
            page.get_by_role("button", name="Start timed reading").click()
            page.frame_locator("#aid").get_by_role(
                "heading", name="Frozen Lens CI fixture"
            ).wait_for(timeout=3000)
            page.route(
                "**/api/answers",
                lambda route: route.fulfill(
                    status=503,
                    content_type="application/json",
                    body='{"error":"Planted temporary save failure"}',
                ),
                times=1,
            )
            page.get_by_label("Question 2", exact=True).fill("First save fails.")
            page.get_by_role("status").filter(has_text="Save failed").wait_for()
            page.get_by_label("Question 2", exact=True).fill("This answer must survive a refresh.")
            page.get_by_role("status").filter(has_text="Saved").wait_for()
            before = json.loads((fixture.study / "session.json").read_text())
            started = before["trials"][before["active_trial"]]["started_at"]
            page.reload()
            page.frame_locator("#aid").get_by_role(
                "heading", name="Frozen Lens CI fixture"
            ).wait_for(timeout=3000)
            assert (
                page.get_by_label("Question 2", exact=True).input_value()
                == "This answer must survive a refresh."
            )
            page.get_by_label("Question 3", exact=True).fill(
                "Submitted immediately, without waiting for autosave."
            )
            page.screenshot(path=str(out / "active.png"), full_page=True)
            page.get_by_role("button", name="Submit reading", exact=True).click()
            page.get_by_role("button", name="Prepare next reading").wait_for()
            saved = json.loads((fixture.study / "session.json").read_text())
            first = next(t for t in saved["trials"].values() if t["state"] == "submitted")
            assert first["started_at"] == started
            assert first["answers"]["q3"] == "Submitted immediately, without waiting for autosave."
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").click()
            page.get_by_role("button", name="Abort reading", exact=True).click()
            page.get_by_role("button", name="Close study", exact=True).click()
            page.get_by_text("Study closed", exact=True).wait_for()
            page.screenshot(path=str(out / "closed.png"), full_page=True)
            assert not errors, errors
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
