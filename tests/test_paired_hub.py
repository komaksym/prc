"""Paired-eval hub recovery: every refusal names the next action."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import sync_playwright

from prc.evaluation import kit
from prc.evaluation import session as session_mod
from prc.evaluation.assets import study_page


def _serve(fixture: Any) -> tuple[HTTPServer, str]:
    httpd, url = session_mod.serve(fixture.study)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    return httpd, url


def _get(url: str, path: str) -> tuple[int, str]:
    request = urllib.request.Request(url + path)

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def _post(url: str, path: str, payload: dict[str, Any]) -> tuple[int, str]:
    request = urllib.request.Request(
        url + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": url},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def _preview_id(url: str) -> str:
    status, body = _get(url, "/api/preview")
    assert status == 200

    return str(json.loads(body)["trial_id"])


def _clean_report(trial_id: str) -> dict[str, Any]:
    return {
        "trial_id": trial_id,
        "familiarity": {"seen_before": False},
        "cross_tool_exposure": {"saw_other_aid": False},
    }


def _submit(url: str, trial_id: str) -> None:
    status, _ = _post(
        url, "/api/submit", {"trial_id": trial_id, "cross_tool_exposure": {"saw_other_aid": False}}
    )
    assert status == 200


def test_prior_explanation_refusal_is_recorded_unknown_and_skipped(make_paired: Any) -> None:
    fixture = make_paired()
    kit.prepare_study(fixture.manifest, fixture.study)
    owner = session_mod.StudySession(fixture.study)
    try:
        first = owner.preview()["trial_id"]
        with pytest.raises(session_mod.SessionError, match="familiar"):
            owner.start(
                {
                    "trial_id": first,
                    "familiarity": {"seen_before": False},
                    "cross_tool_exposure": {"saw_other_aid": True},
                }
            )
        assert owner.public_state()["active"] is None
        assert owner.state["trials"][first]["state"] == "pending"
        assert (
            owner.state["trials"][first]["ineligible"]
            == "prior familiarity or prior explanation exposure"
        )
        assert owner.preview()["trial_id"] != first
    finally:
        owner.close()


def test_close_while_active_names_submit_or_abort(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        status, _ = _post(url, "/api/start", _clean_report(_preview_id(url)))
        assert status == 200
        status, body = _post(url, "/api/close", {})
        assert status == 409
        assert "submit or abort" in body
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_preview_while_active_names_next_action(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        status, _ = _post(url, "/api/start", _clean_report(_preview_id(url)))
        assert status == 200
        status, body = _get(url, "/api/preview")
        assert status == 403
        assert "already active" in body
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_preview_after_final_reading_points_to_close(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        first = _preview_id(url)
        status, _ = _post(url, "/api/start", _clean_report(first))
        assert status == 200
        _submit(url, first)
        second = _preview_id(url)
        status, _ = _post(url, "/api/start", _clean_report(second))
        assert status == 200
        _submit(url, second)
        status, body = _get(url, "/api/preview")
        assert status == 403
        assert "close the study" in body
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_landing_offers_early_close(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        status, body = _get(url, "/")
        assert status == 200
        assert 'id="close-early"' in body
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_hub_scripts_guidance_and_recovery() -> None:
    html = study_page()
    assert "recorded as unknown" in html
    assert "Prepare next reading to continue" in html
    assert "recoveryNote" in html
    assert "Saved answers are kept" in html
    assert "20-minute" in html
    assert 'id="back"' in html


def test_browser_refusal_guides_operator_to_next_reading(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url)
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").wait_for()
            page.get_by_label("I have seen this PR before").set_checked(True)
            page.get_by_role("button", name="Start timed reading").click()
            page.locator("#error:not([hidden])").wait_for()
            notice = page.locator("#error").inner_text()
            assert "recorded as unknown" in notice
            assert "Prepare next reading" in notice
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").wait_for()
            page.get_by_role("button", name="Start timed reading").click()
            page.get_by_role("button", name="Submit reading").wait_for()
            assert not errors, errors
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_browser_stale_start_recovers_to_current_reading(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url)
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").wait_for()
            trial_id = _preview_id(url)
            status, _ = _post(url, "/api/start", _clean_report(trial_id))
            assert status == 200
            page.get_by_role("button", name="Start timed reading").click()
            page.locator("#error:not([hidden])").wait_for()
            assert "already in progress" in page.locator("#error").inner_text()
            page.get_by_role("button", name="Submit reading").wait_for()
            browser.close()
        _post(
            url,
            "/api/abort",
            {"trial_id": trial_id, "cross_tool_exposure": {"saw_other_aid": False}},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_browser_timeout_notifies_and_keeps_saved_answers(
    make_paired: Any, monkeypatch: Any
) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url)
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").wait_for()
            page.get_by_role("button", name="Start timed reading").click()
            page.get_by_role("button", name="Submit reading").wait_for()
            started = time.time()
            page.get_by_label("Question 2", exact=True).fill("deadline draft answer")
            page.get_by_role("status").filter(has_text="Saved").wait_for()
            monkeypatch.setattr(session_mod, "_now", lambda: started + 1300.0)
            page.get_by_text("Saved answers are kept").wait_for(timeout=30000)
            page.get_by_role("button", name="Prepare next reading").wait_for()
            saved = json.loads(Path(fixture.study, "session.json").read_text())
            timed = [t for t in saved["trials"].values() if t["state"] == "timed_out"]
            assert len(timed) == 1
            assert timed[0]["answers"]["q2"] == "deadline draft answer"
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_browser_early_close_freezes_study_for_grading(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url)
            page.get_by_role("button", name="Close study now").click()
            page.get_by_text("Study closed", exact=True).wait_for()
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    saved = json.loads(Path(fixture.study, "session.json").read_text())
    assert saved["closed"] is True


def test_browser_start_confirm_and_back_guard(make_paired: Any) -> None:
    fixture = make_paired(pairs=1)
    kit.prepare_study(fixture.manifest, fixture.study)
    httpd, url = _serve(fixture)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            decisions = {"accept": False}
            page.on(
                "dialog",
                lambda dialog: dialog.accept() if decisions["accept"] else dialog.dismiss(),
            )
            page.goto(url)
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").wait_for()
            preview_text = page.locator("#preview").inner_text()
            assert "20-minute" in preview_text
            assert "uses one reading" in preview_text
            assert "six readings" not in preview_text
            page.get_by_role("button", name="Back without starting").click()
            page.get_by_role("button", name="Prepare next reading").wait_for()
            status, body = _get(url, "/api/state")
            assert status == 200
            assert json.loads(body)["active"] is None
            saved = json.loads(Path(fixture.study, "session.json").read_text())
            assert all(t["state"] == "pending" for t in saved["trials"].values())
            page.get_by_role("button", name="Prepare next reading").click()
            page.get_by_role("button", name="Start timed reading").wait_for()
            decisions["accept"] = False
            page.get_by_role("button", name="Start timed reading").click()
            page.wait_for_timeout(500)
            assert page.locator("#preview").is_visible()
            status, body = _get(url, "/api/state")
            assert json.loads(body)["active"] is None
            decisions["accept"] = True
            page.get_by_role("button", name="Start timed reading").click()
            page.get_by_role("button", name="Submit reading").wait_for()
            status, body = _get(url, "/api/state")
            assert json.loads(body)["active"] is not None
            assert not errors, errors
            browser.close()
        active = json.loads(_get(url, "/api/state")[1])["active"]
        assert active is not None
        _post(
            url,
            "/api/abort",
            {"trial_id": active["trial_id"], "cross_tool_exposure": {"saw_other_aid": False}},
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
