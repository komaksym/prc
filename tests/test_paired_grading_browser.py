from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from prc.evaluation import kit, session


def test_browser_close_grade_analyze_with_frozen_blinded_items(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    for snap in fixture.data["pairs"][0]["snapshots"]:
        snap["questions"][1]["rubric_anchors"] = {
            "0.5": "Exactly one required element earns half credit."
        }
    fixture.save()
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = session.serve(fixture.study)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    out = Path(__file__).parents[1] / "artifacts/e2e/paired-grading"
    out.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors: list[str] = []
            grade_posts: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: (
                    grade_posts.append(request.url) if request.url.endswith("/api/grade") else None
                ),
            )
            page.goto(url)
            assert page.request.get(url + "/api/grading").status == 403
            assert page.request.get(url + "/api/analysis").status == 403
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").click()
            page.get_by_label("Question 1", exact=True).select_option("cache/evict.go")
            answer = '<img src=x onerror="window.gradeInjected=true"> trigger and evidence'
            page.get_by_label("Question 2", exact=True).fill(answer)
            page.screenshot(path=str(out / "active-no-keys.png"), full_page=True)
            assert page.request.get(url + "/api/grading").status == 403
            assert "trigger named with evidence" not in page.content()
            page.get_by_role("button", name="Submit reading", exact=True).click()
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").click()
            page.get_by_role("button", name="Abort reading", exact=True).click()
            page.get_by_role("button", name="Close study", exact=True).click()
            page.get_by_role("heading", name="Condition-blinded grading").wait_for()
            assert answer in page.locator("#grading-items").inner_text()
            assert page.locator("#grading-items img").count() == 0
            assert page.evaluate("window.gradeInjected === undefined")
            assert "vendor-" not in page.locator("body").inner_text()
            assert "Assigned condition" not in page.locator("body").inner_text()
            assert (
                page.locator("#grading-items")
                .get_by_text("Exactly one required element earns half credit.", exact=False)
                .count()
                == 2
            )
            assert (
                page.locator("#grading-items")
                .get_by_text("trigger named with evidence", exact=True)
                .count()
                == 2
            )
            assert page.locator("#grading-items select:not([disabled])").count() == 1
            page.get_by_role("button", name="Save grades and analyze", exact=True).click()
            assert not grade_posts
            assert not (fixture.study / "analysis.json").exists()
            page.locator("#grading-items select:not([disabled])").select_option("0.5")
            page.screenshot(path=str(out / "grading.png"), full_page=True)
            page.get_by_role("button", name="Save grades and analyze", exact=True).click()
            page.get_by_role("heading", name="Exploratory pilot analysis").wait_for()
            assert len(grade_posts) == 1
            assert "not evidence of release readiness" in page.locator("#analysis").inner_text()
            assert "adverse" in page.locator("#analysis").inner_text()
            sheet = json.loads((fixture.study / "grading.json").read_text())
            scores = json.loads((fixture.study / "scores.json").read_text())["scores"]
            for item in sheet["items"]:
                expected = 0.0 if item["answer"] in (None, "") else 0.5
                if item["kind"] == "multiple_choice":
                    expected = float(item["answer"] == item["key"])
                assert scores[item["trial_id"]][item["qid"]] == expected
            assert (
                json.loads(page.request.get(url + "/api/analysis").text())["study_digest"]
                == sheet["study_digest"]
            )
            page.reload()
            page.get_by_role("heading", name="Exploratory pilot analysis").wait_for()
            page.screenshot(path=str(out / "analysis.png"), full_page=True)
            assert not errors, errors
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
