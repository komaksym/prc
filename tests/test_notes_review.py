"""Notes review hub: page lists every PR, notes autosave and survive restart."""

from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from prc.evaluation import notes as notes_mod

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)
PAGE_HTML = (
    "<!doctype html><html><head><meta charset=utf-8>"
    "<title>note fixture</title></head>"
    "<body><p>clickable fixture page</p></body></html>"
)


def make_notes_dir(root: Path) -> Path:
    """Build a two-PR notes dir with fixture PRC output trees."""
    notes_dir = root / "notes"
    prepared_root = root / "v3-prepared"
    roster = []
    for idx, slug in enumerate(("v3-p1a", "v3-p1b")):
        out = root / "outputs" / slug
        out.mkdir(parents=True)
        (out / "infographic.png").write_bytes(PNG_1PX)
        (out / "video.mp4").write_bytes(bytes([0, 0, 0, 24]) + b"ftypmp42" + bytes(64))
        (out / "page.html").write_text(PAGE_HTML, encoding="utf-8")
        prep = prepared_root / slug
        prep.mkdir(parents=True)
        (prep / "render-identity.json").write_text(
            json.dumps({"output": str(out)}), encoding="utf-8"
        )
        roster.append(
            {
                "id": slug,
                "pr_identity": "owner/repo#" + str(idx + 1),
                "title": "Fixture change " + slug,
            }
        )
    notes_dir.mkdir(parents=True)
    (notes_dir / "roster.json").write_text(json.dumps(roster), encoding="utf-8")
    (notes_dir / "prepared_root").write_text(str(prepared_root), encoding="utf-8")
    return notes_dir


def http_get(url: str, path: str) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url + path)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return int(resp.status), resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        return int(err.code), err.read(), ""


def http_post(url: str, path: str, payload: dict[str, str]) -> tuple[int, str]:
    req = urllib.request.Request(
        url + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": url},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return int(resp.status), resp.read().decode()
    except urllib.error.HTTPError as err:
        return int(err.code), err.read().decode()


def serve_live(notes_dir: Path) -> tuple[Any, str]:
    httpd, url = notes_mod.serve(notes_dir, 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, url


def test_page_lists_every_pr_with_links_and_notes_box(tmp_path: Path) -> None:
    notes_dir = make_notes_dir(tmp_path)
    httpd, url = serve_live(notes_dir)
    try:
        status, body, ctype = http_get(url, "/")
        assert status == 200
        assert "text/html" in ctype
        text = body.decode()
        for slug in ("v3-p1a", "v3-p1b"):
            assert ("Fixture change " + slug) in text
            assert "https://github.com/owner/repo/pull/" in text
            assert ("/artifacts/" + slug + "/infographic.png") in text
            assert ("/artifacts/" + slug + "/video.mp4") in text
            assert ("/artifacts/" + slug + "/page.html") in text
            assert ('data-notes-id="' + slug + '"') in text
        assert "confidence" not in text.lower()
        assert "question" not in text.lower()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_note_saves_and_survives_restart(tmp_path: Path) -> None:
    notes_dir = make_notes_dir(tmp_path)
    httpd, url = serve_live(notes_dir)
    try:
        post_status, post_body = http_post(
            url, "/api/notes", {"id": "v3-p1a", "text": "risk: cache"}
        )
        assert post_status == 200, post_body
        saved = json.loads(post_body)
        assert saved["id"] == "v3-p1a"
        assert "updated_at" in saved
        get_status, raw, _ = http_get(url, "/api/state")
        assert get_status == 200
        state = json.loads(raw.decode())
        assert state["notes"]["v3-p1a"]["text"] == "risk: cache"
    finally:
        httpd.shutdown()
        httpd.server_close()
    httpd2, url2 = serve_live(notes_dir)
    try:
        status2, raw2, _ = http_get(url2, "/api/state")
        assert status2 == 200
        state = json.loads(raw2.decode())
        assert state["notes"]["v3-p1a"]["text"] == "risk: cache"
        assert state["notes"]["v3-p1a"]["updated_at"]
        assert state["notes"]["v3-p1b"]["text"] == ""
    finally:
        httpd2.shutdown()
        httpd2.server_close()


def test_artifacts_serve_from_live_output_dir(tmp_path: Path) -> None:
    notes_dir = make_notes_dir(tmp_path)
    httpd, url = serve_live(notes_dir)
    try:
        status, body, ctype = http_get(url, "/artifacts/v3-p1a/infographic.png")
        assert status == 200
        assert body == PNG_1PX
        assert "image" in ctype
        status, body, ctype = http_get(url, "/artifacts/v3-p1a/page.html")
        assert status == 200
        assert b"clickable fixture page" in body
        status, _, _ = http_get(url, "/artifacts/v3-p1a/missing.png")
        assert status == 404
        status, _, _ = http_get(url, "/artifacts/nope/page.html")
        assert status == 404
        status, _, _ = http_get(url, "/artifacts/v3-p1a/../../roster.json")
        assert status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()


LIVE_PAGE_HTML = (
    "<!doctype html><html><head><meta charset=utf-8><title>live page</title>"
    "<style>body { color: rgb(1, 2, 3); }</style></head>"
    "<body><img id=info src='infographic.png'>"
    "<script>document.body.dataset.ran = 'yes';</script></body></html>"
)


def test_hub_served_page_runs_its_inline_script_style_and_image(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    notes_dir = make_notes_dir(tmp_path)
    (tmp_path / "outputs" / "v3-p1a" / "page.html").write_text(LIVE_PAGE_HTML, encoding="utf-8")
    httpd, url = serve_live(notes_dir)
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page()
            page.goto(url + "/artifacts/v3-p1a/page.html")
            page.wait_for_function("document.getElementById('info').complete")
            assert page.evaluate("document.body.dataset.ran") == "yes"
            assert page.evaluate("getComputedStyle(document.body).color") == "rgb(1, 2, 3)"
            assert page.evaluate("document.getElementById('info').naturalWidth") == 1
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()


SPOTCHECK = [
    {
        "id": "s1",
        "text": "The workflow runs every night at 04:30.",
        "label": "supported",
        "reason": "The cron line is 30 2 * * *, which is 04:30 in Warsaw.",
        "evidence": [{"text": "a.yml:5", "url": "https://github.com/o/r/pull/1/files#diff-aR5"}],
    },
    {
        "id": "s2",
        "text": "The script deletes old events.",
        "label": "unsupported",
        "reason": "No line deletes events.",
        "evidence": [],
    },
]


def test_spotcheck_verdicts_and_note_survive_restart(tmp_path: Path) -> None:
    notes_dir = make_notes_dir(tmp_path)
    (notes_dir / "spotcheck.json").write_text(json.dumps(SPOTCHECK), encoding="utf-8")
    httpd, url = serve_live(notes_dir)
    try:
        status, body, _ = http_get(url, "/")
        page = body.decode()
        assert status == 200
        assert "The script deletes old events." in page
        assert 'href="https://github.com/o/r/pull/1/files#diff-aR5"' in page
        assert http_post(url, "/api/verdict", {"id": "s2", "verdict": "wrong"})[0] == 200
        assert http_post(url, "/api/notes", {"id": "spotcheck", "text": "s2 is fine"})[0] == 200
        assert http_post(url, "/api/verdict", {"id": "s9", "verdict": "right"})[0] == 404
        assert http_post(url, "/api/verdict", {"id": "s1", "verdict": "maybe"})[0] == 400
    finally:
        httpd.shutdown()
        httpd.server_close()
    httpd, url = serve_live(notes_dir)
    try:
        state = json.loads(http_get(url, "/api/state")[1])
        assert state["verdicts"] == {"s2": "wrong"}
        assert state["notes"]["spotcheck"]["text"] == "s2 is fine"
        assert [pr["id"] for pr in state["prs"]] == ["v3-p1a", "v3-p1b"]
        assert [item["id"] for item in state["spotcheck"]] == ["s1", "s2"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_hub_without_spotcheck_has_no_spotcheck_section(tmp_path: Path) -> None:
    httpd, url = serve_live(make_notes_dir(tmp_path))
    try:
        page = http_get(url, "/")[1].decode()
        state = json.loads(http_get(url, "/api/state")[1])
        assert "Spot-check" not in page
        assert state["spotcheck"] == []
        assert "spotcheck" not in state["notes"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_spotcheck_button_click_persists_after_reload(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    notes_dir = make_notes_dir(tmp_path)
    (notes_dir / "spotcheck.json").write_text(json.dumps(SPOTCHECK), encoding="utf-8")
    httpd, url = serve_live(notes_dir)
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.locator("[data-verdict-for='s2'][data-verdict='wrong']").click()
            page.wait_for_function(
                "document.querySelector(\"[data-verdict-saved='s2']\").textContent === 'Saved'"
            )
            page.reload()
            pressed = page.locator("[data-verdict-for='s2'][aria-pressed='true']")
            assert pressed.get_attribute("data-verdict") == "wrong"
            assert page.locator("[data-verdict-for='s1'][aria-pressed='true']").count() == 0
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_notes_reject_unknown_pr(tmp_path: Path) -> None:
    notes_dir = make_notes_dir(tmp_path)
    httpd, url = serve_live(notes_dir)
    try:
        status, _ = http_post(url, "/api/notes", {"id": "v3-zzz", "text": "x"})
        assert status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()
