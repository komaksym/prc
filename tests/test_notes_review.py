"""Notes review hub: page lists every PR, notes autosave and survive restart."""

from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

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


def _line(path: str, n: int) -> dict[str, str]:
    from prc.explainer.page import files_url

    return {"text": f"{path}:{n}", "url": files_url("o/r", "1", path, n)}


SPOTCHECK: list[dict[str, Any]] = [
    {
        "id": "s1",
        "pr": "o/r#1",
        "where": "Video and page, scene 2 “Nightly run”, narration",
        "text": "The workflow runs every night at 04:30.",
        "label": "supported",
        "reason": "The cron line is 30 2 * * *, which is 04:30 in Warsaw.",
        "evidence": [_line("a.yml", 5)],
    },
    {
        "id": "s2",
        "pr": "o/r#1",
        "where": "Page reading path, the entry for ‘prune’",
        "text": "The script deletes old events.",
        "label": "unsupported",
        "reason": "No line deletes events.",
        "evidence": [_line("prune.py", 12)],
    },
]


def test_hub_refuses_a_spotcheck_item_a_reader_cannot_judge(tmp_path: Path) -> None:
    """The 2026-10-15 v5 spot-check: a bare box label, no PR, a local diff cite, no link."""
    from prc.evaluation.notes import NotesError, NotesStore

    notes_dir = make_notes_dir(tmp_path)
    shipped = [
        {"id": "s10", "text": "delegates", "label": "supported", "reason": "r",
         "evidence": [{"text": "src/p.py:193", "url": "https://github.com/o/r/pull/1/files#diff-aR5"}]},
        {"id": "s12", "text": "This pull request changes how names match.", "label": "supported",
         "reason": "r", "evidence": [{"text": "original.diff:44-70", "url": ""}]},
        {"id": "s16", "text": "Mock reply — from httpx.MockTransport", "label": "supported",
         "reason": "r", "evidence": []},
    ]  # fmt: skip
    (notes_dir / "spotcheck.json").write_text(json.dumps(shipped), encoding="utf-8")
    with pytest.raises(NotesError) as caught:
        NotesStore(notes_dir)
    said = str(caught.value)
    assert "s10: needs pr as owner/repo#N" in said
    assert "s10: text 'delegates' is a label, not a sentence" in said
    assert "s12: evidence cites original.diff" in said
    assert "s16: needs at least one GitHub line link" in said


def test_spotcheck_verdicts_and_note_survive_restart(tmp_path: Path) -> None:
    notes_dir = make_notes_dir(tmp_path)
    (notes_dir / "spotcheck.json").write_text(json.dumps(SPOTCHECK), encoding="utf-8")
    httpd, url = serve_live(notes_dir)
    try:
        status, body, _ = http_get(url, "/")
        page = body.decode()
        assert status == 200
        assert "The script deletes old events." in page
        assert 'href="' + SPOTCHECK[0]["evidence"][0]["url"] + '"' in page
        assert "r #1 · Video and page, scene 2 “Nightly run”, narration" in page
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


def _one_scene_kit() -> Any:
    from prc.evaluation.spotcheck import Kit

    return Kit(
        pr="o/r#1",
        title="Fixture change",
        claims=[],
        labels=[],
        board={"scenes": [{"type": "title", "say": ["A small change lands."], "cues": []}]},
        m={"pr": "o/r#1", "files": []},
        diff="",
        fixes={},
    )


def test_place_rejects_scene_index_out_of_range() -> None:
    from prc.evaluation.spotcheck import SpotcheckError, place

    kit = _one_scene_kit()
    with pytest.raises(SpotcheckError) as caught:
        place(kit, {"kind": "narration", "scene": 5, "text": "A line runs nightly."})
    assert "5" in str(caught.value)


def test_build_rejects_label_id_missing_from_claims() -> None:
    from prc.evaluation.spotcheck import SpotcheckError, build

    kit = _one_scene_kit()
    kit.claims.append(
        {
            "id": "c1",
            "text": "The script deletes old events.",
            "kind": "narration",
            "scene": 0,
            "cites": [],
        }
    )
    kit.labels.append(
        {
            "id": "c9",
            "label": "unsupported",
            "reason": "No line deletes events.",
            "evidence": "",
        }
    )
    with pytest.raises(SpotcheckError) as caught:
        build([kit], seed=0)
    assert "c9" in str(caught.value)


def test_validate_rejects_non_list_evidence() -> None:
    from prc.evaluation.spotcheck import SpotcheckError, validate

    bad = dict(SPOTCHECK[0])
    bad["evidence"] = "https://github.com/o/r/pull/1/files#diff-abcR5"
    with pytest.raises(SpotcheckError):
        validate([bad])


def test_validate_rejects_non_dict_evidence_entry() -> None:
    from prc.evaluation.spotcheck import SpotcheckError, validate

    bad = dict(SPOTCHECK[0])
    bad["evidence"] = ["not a dict"]
    with pytest.raises(SpotcheckError) as caught:
        validate([bad])
    assert "not a dict" in str(caught.value)


def test_pr_card_names_the_pr_as_the_spotcheck_items_do() -> None:
    """2026-10-16 vision review: cards showed only the title, the spot-check list said
    "linkedin-mdp #5", so a reader could not match the two; the video had no caption."""
    from prc.evaluation.assets import _pr_section

    pr = {"id": "v5-c", "title": "feat(report): publish reports", "github_url": "https://github.com/komaksym/linkedin-mdp/pull/5",
          "artifacts": {"infographic": "i.png", "video": "v.mp4", "page": "p.html"}}  # fmt: skip
    card = _pr_section(pr, "")
    assert '<p class="where">linkedin-mdp #5</p>' in card
    assert card.index("linkedin-mdp #5") < card.index("feat(report)")
    assert 'class="cap">Video walkthrough' in card
