"""Page: one storyboard drives the video and the clickable page."""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "tests/data/explainer/maps/pr12.json"


def _link_texts(fragment: str, href: str) -> list[str]:
    """The visible text of every link to href; syntax colour spans inside a link drop out."""
    pat = r"<a href='" + re.escape(href) + r"'[^>]*>(.*?)</a>"
    return [html.unescape(re.sub(r"<[^>]+>", "", x)) for x in re.findall(pat, fragment)]


def _change() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    m = json.loads(MAP.read_text())
    f = next(f for f in m["files"] if f["hunks"] and f["path"].startswith("src/"))
    line = next(ln for ln in f["hunks"][0]["lines"] if ln["op"] == "+")
    board = {
        "scenes": [
            {"type": "title", "say": ["A small change lands."], "cues": []},
            {
                "type": "diff",
                "file": f["path"],
                "lines": [str(line["new"])],
                "rows": [
                    {"ref": str(line["new"]), "op": "+", "num": line["new"], "text": line["text"]}
                ],
                "say": ["The diff adds one line."],
                "cues": [{"at": [0, 0.0], "do": "step", "n": 1}],
            },
        ]
    }
    return m, board, line


def _data(page: str) -> dict[str, Any]:
    found = re.search(r"<script>window\.PRC=(.*?);</script>", page)
    assert found
    return json.loads(found.group(1).replace("<\\/", "</"))  # type: ignore[no-any-return]


def test_files_url_points_at_the_line_in_the_pr_files_view() -> None:
    from prc.explainer.page import files_url

    anchor = hashlib.sha256(b"src/a.py").hexdigest()
    base = "https://github.com/acme/shop/pull/12/files#diff-" + anchor
    assert files_url("acme/shop", "12", "src/a.py") == base
    assert files_url("acme/shop", "12", "src/a.py", 42) == base + "R42"
    assert files_url("acme/shop", "12", "src/a.py", 7, removed=True) == base + "L7"


def test_page_carries_the_board_and_one_hunk_target_per_code_row(tmp_path: Path) -> None:
    from prc.explainer.page import files_url, render_page

    m, board, line = _change()
    path = board["scenes"][1]["file"]
    page = render_page(board, m, tmp_path, 12.5, has_video=True, infographic=b"png")
    data = _data(page)
    owner_repo, number = m["pr"].split("#")

    assert data["board"] == board
    assert data["targets"][0] == []
    [target] = data["targets"][1]
    assert target == {
        "label": f"{path} line {line['new']}",
        "url": files_url(owner_repo, number, path, line["new"]),
        "hunk": target["hunk"],
        "key": f"+{line['new']}",
    }
    hunk = data["hunks"][target["hunk"]]
    assert f"data-k='+{line['new']}'" in hunk
    assert (tmp_path / "page.html").read_text() == page
    assert "<audio id='narr' preload='auto' src=video.mp4>" in page
    assert "<img src='infographic.png'" in page
    for gone in ("card.png", "card.html", "no CI", " files · "):
        assert gone not in page


def test_page_without_video_or_infographic_has_no_audio_source_or_dialog(tmp_path: Path) -> None:
    from prc.explainer.page import render_page

    m, board, _ = _change()
    page = render_page(board, m, tmp_path, 0.0, has_video=False, infographic=None)
    assert "<audio id='narr' preload='auto'></audio>" in page
    assert "id='info'" not in page and "id='info-open'" not in page


def test_outro_hands_off_to_github_in_video_and_clickable_page(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, board, _ = _change()
    board["scenes"].append(
        {
            "type": "outro",
            "l1": "The diff adds one line.",
            "l2": "Start with this change.",
            "say": ["Start with this change."],
            "cues": [
                {"at": [0, 0.0], "do": "l1"},
                {"at": [0, 0.5], "do": "l2"},
                {"at": [0, 0.9], "do": "cmd"},
            ],
        }
    )
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["scenes"][-1]["end"], has_video=False)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto((tmp_path / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        page.evaluate("window.seek(window.BOARD.scenes.at(-1).end - 0.5)")
        assert page.locator(".outro .cmd").inner_text().startswith("Review on GitHub ")
        assert "prc map" not in page.locator(".outro").inner_text()
        page.screenshot(path=str(tmp_path / "video-outro.png"))
        page.goto((tmp_path / "page.html").as_uri())
        page.locator("#strip button").last.click()
        assert page.locator(".outro .cmd").inner_text().startswith("Review on GitHub ")
        assert board["scenes"][-1]["url"] in page.locator(".outro .cmd").inner_text()
        page.screenshot(path=str(tmp_path / "page-outro.png"))
        browser.close()


def _groups_change() -> tuple[dict[str, Any], dict[str, Any], list[tuple[str, int, str]]]:
    """A groups scene whose two items are different names, each cited from its own added line.

    The names come from the pull request's code file, so the board shows its behavior file.
    """
    m = json.loads(MAP.read_text())
    picks: list[tuple[str, int, str]] = []
    for f in (f for f in m["files"] if f["path"].startswith("src/")):
        for h in f["hunks"]:
            for ln in h["lines"]:
                words = re.findall(r"[A-Za-z_][A-Za-z_0-9]{5,}", ln["text"])
                if ln["op"] == "+" and words and all(words[0] != p[2] for p in picks):
                    picks.append((f["path"], ln["new"], words[0]))
                if len(picks) == 2:
                    break
            if len(picks) == 2:
                break
        if len(picks) == 2:
            break
    (pa, na, wa), (pb, nb, wb) = picks
    board = {
        "scenes": [
            {"type": "title", "say": ["A small change lands."], "cues": []},
            {
                "type": "groups",
                "groups": [
                    {
                        "id": "g0",
                        "title": "Source",
                        "col": 0,
                        "row": True,
                        "items": [{"id": "a0", "text": wa}],
                    },
                    {
                        "id": "g1",
                        "title": "Target",
                        "col": 1,
                        "row": True,
                        "items": [{"id": "a1", "text": wb}],
                    },
                ],
                "cite": [{"line": f"{pa}:{na}", "match": wa}, {"line": f"{pb}:{nb}", "match": wb}],
                "say": ["The first name now feeds the second name in this change."],
                "cues": [
                    {"at": [0, 0.0], "do": "show", "ids": ["g0", "g1"], "step": 0.3},
                    {"at": [0, 0.2], "do": "arrow", "from": "a0", "to": "a1", "label": "feeds"},
                ],
                "hold": 1,
            },
        ]
    }
    return m, board, picks


def test_page_footer_receipts_open_their_lines_on_github(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import files_url, render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, board, picks = _groups_change()
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["scenes"][-1]["end"], has_video=False)
    owner_repo, number = str(m["pr"]).split("#")
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.route("https://github.com/**", lambda route: route.fulfill(body="github"))
        page = context.new_page()
        page.goto((tmp_path / "page.html").as_uri())
        page.locator("#strip button").nth(1).click()
        links = page.locator(".efoot a")
        page.wait_for_function("document.querySelectorAll('.efoot a').length > 0")
        hrefs = [links.nth(i).get_attribute("href") for i in range(links.count())]
        assert hrefs == [files_url(owner_repo, number, p, n) for p, n, _ in picks]
        with context.expect_page() as opened:
            links.first.click()
        assert opened.value.url == hrefs[0]
        page.locator("#strip button").first.click()
        heads = page.locator(".efoot a")
        page.wait_for_function("document.querySelectorAll('.efoot a').length === 2")
        assert (
            heads.nth(1).get_attribute("href")
            == f"https://github.com/{owner_repo}/commit/{m['head_sha']}"
        )
        assert (
            page.locator(".meta a").get_attribute("href")
            == f"https://github.com/{owner_repo}/pull/{number}"
        )
        page.screenshot(path=str(tmp_path / "page-receipts.png"))
        browser.close()


def test_url_in_a_code_row_opens_its_line_on_github(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import files_url, render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    url = "https://mvgzdcqhdruhjoexbdqp.supabase.co"
    m, board, line = _change()
    line["text"] = f"base = os.environ.get('SUPABASE_URL') or '{url}'"
    board["scenes"][1]["rows"][0]["text"] = line["text"]
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    page_html = render_page(board, m, tmp_path, 4.0, has_video=False)
    data = _data(page_html)
    hunk = data["hunks"][data["targets"][1][0]["hunk"]]
    owner_repo, number = str(m["pr"]).split("#")
    line_url = files_url(owner_repo, number, board["scenes"][1]["file"], line["new"])
    assert url in _link_texts(hunk, line_url), "the URL is not one link to its line"
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.goto((tmp_path / "page.html").as_uri())
        page.locator("#strip button").nth(1).click()
        page.wait_for_function("document.querySelectorAll('.drow a').length > 0")
        links = page.locator(".drow a")
        assert [links.nth(i).get_attribute("href") for i in range(links.count())] == [line_url]
        assert links.first.text_content() == url
        browser.close()


def test_commit_sha_and_file_line_in_a_code_row_open_the_line(tmp_path: Path) -> None:
    # 2026-10-15 click audit on linkedin-mdp #5: action pins and a `client.py:124` note
    # in changed lines showed as bare references.
    from prc.explainer.check import verify_board
    from prc.explainer.page import files_url, render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    sha = "11d5960a326750d5838078e36cf38b85af677262"
    m, board, line = _change()
    line["text"] = f"pin = 'actions/checkout@{sha}'  # see client.py:124"
    board["scenes"][1]["rows"][0]["text"] = line["text"]
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    data = _data(render_page(board, m, tmp_path, 4.0, has_video=False))
    hunk = data["hunks"][data["targets"][1][0]["hunk"]]
    owner_repo, number = str(m["pr"]).split("#")
    line_url = files_url(owner_repo, number, board["scenes"][1]["file"], line["new"])
    for ref in (sha, "client.py:124"):
        assert ref in _link_texts(hunk, line_url), ref + " is not one link to its line"


def test_arrow_points_from_source_edge_to_target_edge_and_renames_nothing(
    tmp_path: Path,
) -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, board, picks = _groups_change()
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    arrow = next(c for c in board["scenes"][1]["cues"] if c["do"] == "arrow")
    probe = (
        "(() => { const box = id => document.querySelector('.pill[data-id=' + JSON.stringify(id) + ']');"
        " const rect = el => { const r = el.getBoundingClientRect();"
        " return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };"
        " const a = document.querySelector('.garrow');"
        " const head = a && a.querySelector('.head');"
        " return { texts: [box('a0'), box('a1')].map(el => el.querySelector('.pt').textContent),"
        " clones: document.querySelectorAll('.pill.fly').length,"
        " op: a ? +getComputedStyle(a).opacity : -1,"
        " points: head ? head.getAttribute('points') : '',"
        " tip: a ? [+a.dataset.x2, +a.dataset.y2] : [], tail: a ? [+a.dataset.x1, +a.dataset.y1] : [],"
        " src: rect(box('a0')), dst: rect(box('a1')),"
        " label: a ? document.querySelector('.galabel').textContent : '' }; })()"
    )

    def near_edge(point: list[float], r: dict[str, float]) -> bool:
        x, y = point
        inside = r["l"] - 14 <= x <= r["r"] + 14 and r["t"] - 14 <= y <= r["b"] + 14
        deep = r["l"] + 14 < x < r["r"] - 14 and r["t"] + 14 < y < r["b"] - 14
        return inside and not deep

    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((tmp_path / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        names = [picks[0][2], picks[1][2]]
        page.evaluate(f"window.seek({arrow['t'] - 0.1})")
        before = page.evaluate(probe)
        assert before["op"] == 0 and before["texts"] == names
        for later in (0.25, 0.6, 1.2):
            page.evaluate(f"window.seek({arrow['t'] + later})")
            seen = page.evaluate(probe)
            assert seen["texts"] == names and seen["clones"] == 0
        assert seen["op"] == 1 and seen["label"] == "feeds"
        assert len(seen["points"].split()) == 3
        assert near_edge(seen["tail"], seen["src"]) and near_edge(seen["tip"], seen["dst"])
        assert seen["tip"][0] > seen["tail"][0]
        page.screenshot(path=str(tmp_path / "arrow.png"))
        browser.close()


def test_list_scene_cites_open_their_lines_on_github(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import files_url, render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, board, picks = _groups_change()
    board["scenes"].append(
        {
            "type": "list",
            "big": "Names",
            "label": "Cited names",
            "code": True,
            "items": [{"text": w, "cite": f"{p}:{n}"} for p, n, w in picks],
            "say": ["Both names come from added lines."],
            "cues": [{"at": [0, 0.0], "do": "items", "step": 0.3}],
        }
    )
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["scenes"][-1]["end"], has_video=False)
    owner_repo, number = str(m["pr"]).split("#")
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.route("https://github.com/**", lambda route: route.fulfill(body="github"))
        page = context.new_page()
        page.goto((tmp_path / "page.html").as_uri())
        page.locator("#strip button").nth(2).click()
        page.wait_for_function("document.querySelectorAll('.list .c a').length === 2")
        links = page.locator(".list .c a")
        hrefs = [links.nth(i).get_attribute("href") for i in range(links.count())]
        assert hrefs == [files_url(owner_repo, number, p, n) for p, n, _ in picks]
        assert [links.nth(i).inner_text() for i in range(2)] == [
            f"{p.rsplit('/', 1)[-1]}:{n}" for p, n, _ in picks
        ]
        page.screenshot(path=str(tmp_path / "list-cites.png"))
        browser.close()


def test_group_boxes_open_their_lines_and_the_reading_path_links_every_unit(
    tmp_path: Path,
) -> None:
    """The v4-a review: boxes on the first scenes were dead, and the page skipped most units."""
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import files_url, render_page
    from prc.explainer.render import render
    from prc.explainer.units import units
    from prc.explainer.voice import NoneBackend

    m, board, picks = _groups_change()
    all_units = units(m)
    board["reading"] = [
        {"units": [u["id"]], "say": "The change touches this part."} for u in all_units
    ]
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["scenes"][-1]["end"], has_video=False)
    owner_repo, number = str(m["pr"]).split("#")
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.route("https://github.com/**", lambda route: route.fulfill(body="github"))
        page = context.new_page()
        page.goto((tmp_path / "page.html").as_uri())
        page.locator("#strip button").nth(1).click()
        page.wait_for_function("document.querySelectorAll('#scale .pill.pg-hit').length === 2")
        for (path, n, _), box in zip(picks, ("a0", "a1"), strict=True):
            page.locator(f"#scale .pill[data-id='{box}']").click()
            assert page.locator("#panel").is_visible()
            assert page.locator("#panel-title").inner_text() == f"{path} line {n}"
            assert page.locator("#panel-gh").get_attribute("href") == files_url(
                owner_repo, number, path, n
            )
            assert page.locator("#panel-diff .hk-hit").count() == 1
        receipts = page.locator("#receipts a")
        assert [receipts.nth(i).get_attribute("href") for i in range(receipts.count())] == [
            files_url(owner_repo, number, p, n) for p, n, _ in picks
        ]
        assert page.locator(".pg-key-i").count() == 5
        assert "reading path" in page.locator("#not-covered").inner_text()
        names = page.locator("#reading .rd-name")
        assert names.count() == len(all_units)
        hrefs = {names.nth(i).get_attribute("href") for i in range(names.count())}
        assert hrefs == {
            files_url(owner_repo, number, u["path"], u["line"], u["removed"]) for u in all_units
        }
        # 2026-10-15 click audit: the path:line label beside each name was plain text.
        cites = page.locator("#reading .rd-p")
        assert cites.count() == len(all_units)
        for i in range(cites.count()):
            assert cites.nth(i).evaluate("e => e.tagName") == "A"
            assert cites.nth(i).get_attribute("href") == names.nth(i).get_attribute("href")
        fold = page.locator("#reading details.rd-code").first
        fold.locator("summary").click()
        assert fold.locator("table.hk tr").first.is_visible()
        with context.expect_page() as opened:
            names.first.click()
        assert opened.value.url == names.first.get_attribute("href")
        page.screenshot(path=str(tmp_path / "page-boxes.png"), full_page=True)
        browser.close()


def test_scene_tabs_name_each_scene_and_the_key_reads_the_same_on_page_and_stage(
    tmp_path: Path,
) -> None:
    """The 2026-10-16 v5 vision pass: the tabs read "2 groups" and "3 groups", and the page
    key said "Problem or removed" while the title scene said "Problem"."""
    import copy

    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.page import render_page
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from prc.tones import TONES

    m, board, _ = _groups_change()
    again = copy.deepcopy(board["scenes"][1])
    again["say"] = ["Then the second name takes over from the first name."]
    board["scenes"].insert(2, again)
    facts = verify_board(board, m)
    render(board, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    render_page(board, m, tmp_path, board["scenes"][-1]["end"], has_video=False)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto((tmp_path / "page.html").as_uri())
        tabs = page.locator("#strip button")
        names = [tabs.nth(i).get_attribute("title") for i in range(tabs.count())]
        assert names == [
            "Title",
            "The first name now feeds the second name in this change",
            "Then the second name takes over from the first name",
        ]
        header = page.locator(".pg-key-i").all_inner_texts()
        tabs.first.click()
        page.wait_for_selector("#scale .ckey span")
        stage = page.locator("#scale .ckey span").all_inner_texts()
        assert header == stage == [t[0] for t in TONES.values()]
        browser.close()


def test_scene_names_suffix_collision_picks_smallest_free_suffix() -> None:
    from prc.explainer.page import scene_names

    board = {
        "scenes": [
            {"type": "groups", "groups": [], "label": "X (2)", "say": [], "cues": []},
            {"type": "groups", "groups": [], "label": "X", "say": [], "cues": []},
            {"type": "groups", "groups": [], "label": "X", "say": [], "cues": []},
        ]
    }
    assert scene_names(board) == ["X (2)", "X", "X (3)"]


def test_reading_fold_reads_like_a_github_hunk() -> None:
    """The v5-b `main` fold ran −126, +156, +157, −132: changed lines only, one number column.

    The fold now keeps diff order with the unchanged lines between, an old and a new number
    column, and each unit line once."""
    from prc.explainer.page import reading_html
    from prc.explainer.units import key, units

    m = json.loads((ROOT / "tests/data/explainer/maps/pr14.json").read_text())
    u = next(u for u in units(m) if u["id"].endswith("collect_private_source.py::collect_sources"))
    f = next(f for f in m["files"] if f["path"] == u["path"])
    board = {"scenes": [], "reading": [{"units": [u["id"]], "say": "It collects the sources."}]}
    fold = reading_html(board, m)
    rows = re.findall(
        r"<tr class='(hk-add|hk-del|hk-ctx)[^']*' data-k='([^']*)'>"
        r"<td class='hk-n'>(.*?)</td><td class='hk-n'>(.*?)</td>",
        fold,
    )
    shown = [k for _, k, _, _ in rows]
    order = [key(ln) for h in f["hunks"] for ln in h["lines"]]
    assert shown == sorted(shown, key=order.index), "fold rows leave diff order"
    assert {key(ln) for ln in u["lines"]} <= set(shown)
    assert any(cls == "hk-ctx" for cls, _, _, _ in rows), "no unchanged line between changes"
    for cls, _, old, new in rows:
        assert bool(old) == (cls != "hk-add") and bool(new) == (cls != "hk-del"), cls


def _ln(op: str, n: int, text: str, old: int | None = None) -> dict[str, Any]:
    """One diff line; added lines carry a new number, removed an old one, context both."""
    if op == "+":
        return {"op": "+", "new": n, "text": text}
    if op == "-":
        return {"op": "-", "old": n, "text": text}
    return {"op": " ", "old": old if old is not None else n, "new": n, "text": text}


def test_fold_shows_only_its_unit_with_github_context_and_counted_gaps() -> None:
    """2026-10-16 v5 vision review: a "module lines" card dumped 119 rows of other cards' code,
    grey with no key; a fold opened on "self._client, request," with no line above it; and a
    bare "⋯" hid lines between hunks without a count."""
    import re as _re

    from prc.explainer.page import fold_rows

    first = [_ln(" ", n, f"ctx {n}") for n in range(1, 8)]
    first += [_ln("+", 8, "return _call("), _ln("+", 9, "self._client,")]
    first += [_ln("+", n, f"other {n}") for n in range(10, 30)]
    first += [_ln("+", 30, "CONSTANT = 1"), _ln(" ", 31, "tail 31"), _ln(" ", 32, "tail 32")]
    second = [_ln(" ", 60, "far 60"), _ln("+", 61, "LAST = 2")]
    f = {"path": "pkg/mod.py", "hunks": [{"lines": first}, {"lines": second}]}
    u = {
        "lines": [
            ln
            for ln in first + second
            if ln["text"] in ("self._client,", "CONSTANT = 1", "LAST = 2")
        ]
    }
    rows = fold_rows(u, f, "o/r", "1")
    shown = [int(k) for k in _re.findall(r"data-k='\+(\d+)'", "".join(rows))]
    gaps = [r for r in rows if "hk-gap" in r]
    assert 8 in shown and 6 in shown, "no lead-in context above the unit's first line"
    assert 5 not in shown, "more than 3 lines of lead-in context"
    assert not any(15 <= n <= 24 for n in shown), "other cards' lines dumped into this fold"
    assert any("14 lines" in g and "other cards" in g for g in gaps), gaps
    assert any("27 unchanged lines" in g for g in gaps), (
        "the jump between hunks: no count, or a new name"
    )
    assert all(_re.search(r"\d", g) for g in gaps), "a gap row without a count"


def test_fold_draws_nested_helper_lines_as_its_own() -> None:
    """A nested handler showed twice: grey inside its test, then again as its own card."""
    from prc.explainer.page import fold_rows

    lines = [_ln("+", n, f"line {n}") for n in range(1, 10)]
    f = {"path": "tests/t.py", "hunks": [{"lines": lines}]}
    u = {"lines": [ln for ln in lines if ln["new"] not in (4, 5, 6)]}
    inner = frozenset({"+4", "+5", "+6"})
    rows = fold_rows(u, f, "o/r", "1", inside=inner)
    assert not any("hk-dim" in r for r in rows), "nested helper lines drawn grey"
    assert len(rows) == 9


def test_fold_rows_carry_the_video_syntax_colors_and_keep_links() -> None:
    """2026-10-16 review: fold rows were one grey colour, so keywords, strings and names
    read the same. The page now paints rows with the video's highlighter."""
    import re as _re

    from prc.explainer.highlight import paint_map
    from prc.explainer.page import fold_rows

    line = {"op": "+", "new": 1, "text": "def fetch(n: int) -> str:  # one call"}
    url = {"op": "+", "new": 2, "text": '    return "https://example.com/x" * 2'}
    m = {
        "head_sha": "",
        "base_sha": "",
        "files": [{"path": "a.py", "hunks": [{"lines": [line, url]}]}],
    }
    f = paint_map(m, None)["files"][0]
    rows = "".join(fold_rows({"lines": f["hunks"][0]["lines"]}, f, "o/r", "1"))
    assert "<span class='t-k'>def</span>" in rows, rows
    assert _re.search(r"<span class='t-c'>[^<]*one call", rows), "comment not painted"
    assert _re.search(r"<span class='t-n'>2</span>", rows), "number not painted"
    link = _re.search(r"<a href='[^']*'[^>]*>(.*?)</a>", rows.split("return", 1)[1])
    assert link and _re.sub(r"<[^>]+>", "", link.group(1)) == "https://example.com/x", (
        "URL link split"
    )
    assert "t-s" in link.group(1), "string colour lost inside the link"


def test_blank_changed_lines_never_draw_grey() -> None:
    """2026-10-16 review: removed blank lines 152-153 drew grey, so the caption claimed another
    card explained them. Blank lines belong to no card."""
    from prc.explainer.page import fold_rows

    lines = [
        _ln("-", 1, "def gone():"),
        _ln("-", 2, "    return 1"),
        _ln("-", 3, ""),
        _ln(" ", 4, "def kept():", old=4),
    ]
    f = {"path": "a.py", "hunks": [{"lines": lines}]}
    rows = fold_rows({"lines": lines[:2]}, f, "o/r", "1")
    assert not any("hk-dim" in r for r in rows), rows


def test_fold_summary_counts_bright_rows_including_nested_helper() -> None:
    """2026-10-16 PR komaksym/leads-discovery#43: the card said 16 changed lines while its
    fold showed 28 bright added rows: nested helper lines draw bright by design, and the
    summary must count the bright rows the reader sees, never another card's dimmed lines."""
    import re as _re

    from prc.explainer.page import _unit_html
    from prc.explainer.units import key as unit_key

    own = [_ln("+", n, f"own {n}") for n in (10, 11, 12)]
    helper = [_ln("+", n, f"helper {n}") for n in (13, 14)]
    other = [_ln("+", n, f"other {n}") for n in (15, 16)]
    f = {
        "path": "pkg/mod.py",
        "status": "added",
        "hunks": [
            {
                "lines": [
                    _ln(" ", 7, "ctx 7"),
                    _ln(" ", 8, "ctx 8"),
                    _ln(" ", 9, "ctx 9"),
                    *own,
                    *helper,
                    *other,
                    _ln(" ", 17, "ctx 17"),
                ]
            }
        ],
    }
    u = {
        "id": "pkg/mod.py::test_x",
        "path": "pkg/mod.py",
        "role": "test",
        "kind": "test",
        "name": "test_x",
        "status": "added",
        "line": 10,
        "removed": False,
        "lines": own,
    }
    frag = _unit_html(u, f, "o/r", "1", None, frozenset(unit_key(ln) for ln in helper))
    summary = _re.search(r"<summary>(\d+) changed lines?</summary>", frag)
    assert summary, frag
    bright = len(_re.findall(r"<tr class='hk-add'", frag))
    assert bright == len(own) + len(helper) == 5
    assert int(summary.group(1)) == bright
    for ln in other:
        row = _re.search(f"<tr class='([^']*)' data-k='[+]{ln['new']}'>", frag)
        assert row and "hk-dim" in row.group(1), f"line {ln['new']} of another card draws bright"


def test_added_image_file_renders_inline_with_github_link(tmp_path: Path) -> None:
    """2026-10-16 PR komaksym/linkedin-mdp#5: an added jpg showed only the binary note."""
    import base64 as _b64
    import re as _re
    import subprocess as _sp

    from prc.explainer.page import _unit_html, files_url

    png = _b64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    repo = tmp_path / "repo"
    (repo / "docs/images").mkdir(parents=True)
    (repo / "docs/images/pic.png").write_bytes(png)
    _sp.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    _sp.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    _sp.run(
        ["git", "-c", "user.email=t@t.t", "-c", "user.name=t", "commit", "-m", "img"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    head = _sp.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    u: dict[str, Any] = {
        "id": "docs/images/pic.png",
        "path": "docs/images/pic.png",
        "role": "docs",
        "kind": "file",
        "name": "docs/images/pic.png",
        "status": "added",
        "line": None,
        "removed": False,
        "lines": [],
    }
    f = {"path": "docs/images/pic.png", "status": "added", "hunks": []}
    frag = _unit_html(u, f, "o/r", "1", git_dir=str(repo / ".git"), head_sha=head, base_sha=head)
    url = files_url("o/r", "1", "docs/images/pic.png")
    assert f"<img src='data:image/png;base64,{_b64.b64encode(png).decode()}'" in frag
    assert "alt='docs/images/pic.png'" in frag
    assert "max-width:100%" in frag
    assert f"<a href='{url}'" in frag
    plain = _unit_html(u, f, "o/r", "1")
    assert "<img" not in plain
    assert "Image file; open it on GitHub" in _re.sub(r"<[^>]+>", "", plain)
    assert f"<a href='{url}'" in plain


def test_long_scene_tab_name_ends_on_a_clause_and_keeps_lists_whole() -> None:
    """2026-10-16 PR #43: the tab read \"checks connect errors, size...\", cut inside a list."""
    from prc.explainer.page import scene_names

    say = (
        "Now `_call` hands each request to `safe_transport_call`, "
        "which checks connect errors, response size and HTTP status before any body read."
    )
    listed = (
        "Four new tests cover normalize, similarity, match_names, tier, score, rank, "
        "the old loop and a lot more words"
    )
    board = {"scenes": [{"type": "groups", "say": [say]}, {"type": "groups", "say": [listed]}]}
    first, second = scene_names(board)
    assert first == "Now _call hands each request to safe_transport_call"
    assert second.endswith("…") and "normalize, similarity" in second


def test_scene_tab_keeps_quotes_on_a_plain_word_code_span() -> None:
    """2026-10-16 PR #5: the tab read \"the text old\" after the backticks were dropped."""
    from prc.explainer.page import scene_names

    say = "The test Doc has a note, a begin marker, the text `old`, an end marker and `_call`."
    (name,) = scene_names({"scenes": [{"type": "groups", "say": [say]}]})
    assert "the text “old”," in name
    assert name.endswith("and _call")
