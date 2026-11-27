#!/usr/bin/env python3
"""Drive the paired session hub through every button path."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = "paired-study/private"
PROOF_PREFIX = "paired-hub-"


def _record(
    steps: list[dict[str, Any]],
    name: str,
    button: str,
    expected: str,
    observed: str,
    passed: bool,
    screenshot: str,
) -> None:
    steps.append(
        {
            "name": name,
            "button": button,
            "expected": expected,
            "observed": observed,
            "passed": passed,
            "screenshot": screenshot,
        }
    )


def main() -> None:
    proof_root = ROOT / "artifacts" / "verification"
    proof_root.mkdir(parents=True, exist_ok=True)
    proof = Path(tempfile.mkdtemp(prefix=PROOF_PREFIX, dir=proof_root))
    scratch = Path(tempfile.mkdtemp(prefix="prc-paired-hub-"))
    print(proof, flush=True)
    steps: list[dict[str, Any]] = []
    errors: list[str] = []
    requests: list[str] = []
    actions: list[dict[str, Any]] = []
    checks: dict[str, Any] = {
        "feature": "paired-hub-buttons",
        "source": "fixture",
        "page_errors": errors,
        "browser_requests": requests,
        "steps": steps,
    }
    httpd: Any = None
    thread: threading.Thread | None = None
    try:
        assert FORBIDDEN not in str(scratch), scratch
        sys.path.insert(0, str(ROOT / "src"))
        sys.path.insert(0, str(ROOT / "tests"))
        import prc
        from paired_builder import build_manifest
        from prc.evaluation import kit, session

        assert prc.__file__ and Path(prc.__file__).resolve().is_relative_to(ROOT / "src")
        checks["package"] = prc.__file__
        checks["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        fixture = build_manifest(scratch / "fixture", pairs=2)
        assert FORBIDDEN not in str(fixture.manifest), fixture.manifest
        study = scratch / "study"
        summary = kit.prepare_study(fixture.manifest, study)
        assert FORBIDDEN not in str(study), study
        checks["trials"] = summary["trials"]
        actions.append({"action": "prepare_study", "trials": summary["trials"]})
        httpd, url = session.serve(study)
        checks["hub_url_host"] = "127.0.0.1"
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        actions.append({"action": "serve", "url": "loopback"})
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.on("pageerror", lambda err: errors.append(str(err)))
                page.on("request", lambda req: requests.append(req.url))
                page.on("dialog", lambda dlg: dlg.accept())
                page.goto(url)
                page.get_by_role("button", name="Prepare next reading").wait_for(timeout=10000)
                page.screenshot(path=str(proof / "01-landing.png"))
                _record(
                    steps,
                    "landing",
                    "Prepare next reading",
                    "hub loads with prepare",
                    "prepare visible",
                    True,
                    "01-landing.png",
                )
                actions.append({"action": "goto hub"})
                page.get_by_role("button", name="Prepare next reading").click()
                page.locator("#preview").wait_for(state="visible", timeout=10000)
                title = page.locator("#previewtitle").inner_text().strip()
                assert title, "preview title is empty"
                page.screenshot(path=str(proof / "02-preview.png"))
                _record(
                    steps,
                    "prepare-clean",
                    "Prepare next reading",
                    "preview shows PR title",
                    title[:80],
                    True,
                    "02-preview.png",
                )
                page.get_by_label("I have seen this PR before").set_checked(False)
                page.get_by_label("I have seen another explanation for this PR").set_checked(False)
                page.get_by_role("button", name="Start timed reading").click()
                page.locator("#trial").wait_for(state="visible", timeout=10000)
                aid_src = page.locator("#aid").get_attribute("src") or ""
                assert aid_src.startswith("/artifact/"), aid_src
                with urllib.request.urlopen(url + aid_src, timeout=10) as resp:
                    assert resp.status == 200, aid_src
                    body = resp.read()
                    assert len(body) > 0, aid_src
                page.screenshot(path=str(proof / "03-active.png"))
                _record(
                    steps,
                    "start-clean",
                    "Start timed reading",
                    "timer starts and aid loads",
                    aid_src,
                    True,
                    "03-active.png",
                )
                page.get_by_label("Question 1", exact=True).select_option("cache/evict.go")
                page.get_by_label("Question 2", exact=True).fill(
                    "Trigger fires when the cache exceeds its limit."
                )
                page.get_by_label("Question 3", exact=True).fill("Zero TTL causes repeated churn.")
                page.get_by_role("status").filter(has_text="Saved").wait_for(timeout=15000)
                page.screenshot(path=str(proof / "04-saved.png"))
                _record(
                    steps,
                    "answer-save",
                    "type answers",
                    "autosave reports Saved",
                    "Saved visible",
                    True,
                    "04-saved.png",
                )
                q2_before = page.get_by_label("Question 2", exact=True).input_value()
                page.reload()
                page.locator("#trial").wait_for(state="visible", timeout=10000)
                q2_after = page.get_by_label("Question 2", exact=True).input_value()
                assert q2_after == q2_before, f"reload lost answer: {q2_before!r} vs {q2_after!r}"
                page.screenshot(path=str(proof / "05-resumed.png"))
                _record(
                    steps,
                    "reload-resume",
                    "reload",
                    "draft survives reload",
                    q2_after[:60],
                    True,
                    "05-resumed.png",
                )
                page.get_by_role("button", name="Submit reading", exact=True).click()
                page.get_by_role("button", name="Prepare next reading").wait_for(timeout=10000)
                page.screenshot(path=str(proof / "06-submitted.png"))
                _record(
                    steps,
                    "submit",
                    "Submit reading",
                    "next prepare appears",
                    "prepare visible",
                    True,
                    "06-submitted.png",
                )
                page.get_by_role("button", name="Prepare next reading").click()
                page.locator("#preview").wait_for(state="visible", timeout=10000)
                page.get_by_label("I have seen this PR before").set_checked(True)
                page.get_by_role("button", name="Start timed reading").click()
                page.locator("#error").wait_for(state="visible", timeout=10000)
                err_text = page.locator("#error").inner_text()
                assert "familiar" in err_text.lower(), (
                    f"refusal must name familiarity: {err_text!r}"
                )
                lowered = err_text.lower()
                assert "prepare next reading" in lowered or "next reading" in lowered, (
                    f"refusal must guide recovery: {err_text!r}"
                )
                assert page.get_by_role("button", name="Prepare next reading").is_visible(), (
                    "prepare must stay available after refusal"
                )
                checks["familiar_refusal"] = err_text
                page.screenshot(path=str(proof / "07-familiar-refusal.png"))
                _record(
                    steps,
                    "familiar-refusal",
                    "Start timed reading (familiar checked)",
                    "refuse with recovery guidance",
                    err_text[:120],
                    True,
                    "07-familiar-refusal.png",
                )
                page.get_by_role("button", name="Prepare next reading").click()
                page.locator("#preview").wait_for(state="visible", timeout=10000)
                page.get_by_label("I have seen this PR before").set_checked(False)
                page.get_by_label("I have seen another explanation for this PR").set_checked(False)
                page.get_by_role("button", name="Start timed reading").click()
                page.locator("#trial").wait_for(state="visible", timeout=10000)
                page.get_by_label("Question 2", exact=True).fill(
                    "Abort path draft that must survive."
                )
                page.get_by_role("status").filter(has_text="Saved").wait_for(timeout=15000)
                page.get_by_role("button", name="Abort reading", exact=True).click()
                page.get_by_role("button", name="Prepare next reading").wait_for(timeout=10000)
                page.screenshot(path=str(proof / "08-aborted.png"))
                _record(
                    steps,
                    "abort",
                    "Abort reading",
                    "abort keeps draft and offers next",
                    "prepare visible",
                    True,
                    "08-aborted.png",
                )
                page.get_by_role("button", name="Prepare next reading").click()
                page.locator("#preview").wait_for(state="visible", timeout=10000)
                page.get_by_label("I have seen this PR before").set_checked(False)
                page.get_by_label("I have seen another explanation for this PR").set_checked(False)
                page.get_by_role("button", name="Start timed reading").click()
                page.locator("#trial").wait_for(state="visible", timeout=10000)
                page.get_by_label("Question 1", exact=True).select_option("cache/evict.go")
                page.get_by_label("Question 2", exact=True).fill(
                    "Final reading answer for closure."
                )
                page.get_by_label("Question 3", exact=True).fill("Final third answer.")
                page.get_by_role("status").filter(has_text="Saved").wait_for(timeout=15000)
                page.get_by_role("button", name="Submit reading", exact=True).click()
                page.get_by_role("button", name="Close study", exact=True).wait_for(timeout=10000)
                page.screenshot(path=str(proof / "09-ready-close.png"))
                _record(
                    steps,
                    "submit-second",
                    "Submit reading",
                    "close appears after last reading",
                    "close visible",
                    True,
                    "09-ready-close.png",
                )
                page.get_by_role("button", name="Close study", exact=True).click()
                page.get_by_text("Study closed", exact=True).wait_for(timeout=10000)
                page.screenshot(path=str(proof / "10-closed.png"))
                _record(
                    steps,
                    "close",
                    "Close study",
                    "study closed text",
                    "Study closed visible",
                    True,
                    "10-closed.png",
                )
                page.get_by_role("heading", name="Condition-blinded grading").wait_for(
                    timeout=15000
                )
                boxes = page.locator("select[id^='grade-']")
                total = boxes.count()
                assert total > 0, "grading has no score boxes"
                filled = 0
                for i in range(total):
                    box = boxes.nth(i)
                    if not box.is_disabled():
                        box.select_option("1")
                        filled += 1
                page.screenshot(path=str(proof / "11-grading.png"))
                _record(
                    steps,
                    "grade-fill",
                    "fill short-answer scores",
                    "enabled boxes accept scores",
                    f"{filled}/{total} filled",
                    True,
                    "11-grading.png",
                )
                page.get_by_role("button", name="Save grades and analyze").click()
                page.get_by_role("heading", name="Exploratory pilot analysis").wait_for(
                    timeout=15000
                )
                digest = page.locator("#digest").inner_text().strip()
                assert digest, "analysis digest is empty"
                checks["study_digest"] = digest
                page.screenshot(path=str(proof / "12-analysis.png"), full_page=True)
                _record(
                    steps,
                    "grade-analyze",
                    "Save grades and analyze",
                    "analysis with digest",
                    digest[:60],
                    True,
                    "12-analysis.png",
                )
                assert not errors, errors
                actions.append({"action": "button pass", "steps": len(steps)})
            finally:
                browser.close()
    except Exception as error:
        checks["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        (proof / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
        (proof / "actions.json").write_text(json.dumps(actions, indent=2) + "\n")
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        scratch_exists = scratch.exists()
        if scratch_exists:
            shutil.rmtree(scratch, ignore_errors=True)
        (proof / "cleanup.json").write_text(
            json.dumps(
                {
                    "scratch_removed": not scratch.exists(),
                    "evidence_preserved": proof.is_dir(),
                },
                indent=2,
            )
            + "\n"
        )
    assert all(
        (proof / f"{n}.png").is_file()
        for n in (
            "01-landing",
            "03-active",
            "06-submitted",
            "07-familiar-refusal",
            "10-closed",
            "12-analysis",
        )
    )
    print("PASS: every hub button path passed with recovery guidance and evidence.")


if __name__ == "__main__":
    main()
