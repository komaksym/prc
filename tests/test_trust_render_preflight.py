from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

DATA = Path(__file__).resolve().parent / "data" / "explainer"
ACCEPT = Path(__file__).resolve().parent / "data" / "trustworthiness"


def tiny_map() -> dict[str, Any]:
    lines = [
        {"op": " ", "old": 1, "new": 1, "text": "def a():"},
        {"op": "+", "old": None, "new": 2, "text": "    x = 1"},
        {"op": "+", "old": None, "new": 3, "text": "    y = 2"},
        {"op": "+", "old": None, "new": 4, "text": "    return x + y"},
    ]
    return {
        "pr": "o/r#1",
        "title": "t",
        "author": "a",
        "base_sha": "b" * 40,
        "head_sha": "h" * 40,
        "url": None,
        "brief": {
            "files": [{"path": "a.py", "kind": "code", "added": 3, "removed": 0}],
            "checks": [],
        },
        "files": [
            {
                "path": "a.py",
                "kind": "code",
                "added": 3,
                "removed": 0,
                "hunks": [{"old_start": 1, "new_start": 1, "lines": lines}],
            }
        ],
        "symbols": [
            {
                "id": "a",
                "path": "a.py",
                "qualname": "a",
                "status": "added",
                "span": [1, 4],
                "base_span": None,
            }
        ],
        "edges": [],
        "tour": [],
    }


def tiny_board(diff_lines: list[Any], *, fine: str | None = "fine print") -> dict[str, Any]:
    outro: dict[str, Any] = {
        "type": "outro",
        "l1": "Change adds two values.",
        "l2": "Start at a in a.py.",
        "say": ["Change adds two values."],
        "cues": [
            {"at": [0, 0.0], "do": "l1"},
            {"at": [0, 0.5], "do": "l2"},
            {"at": [0, 0.9], "do": "cmd"},
        ],
    }
    if fine is not None:
        outro["fine"] = fine
    return {
        "name": "tiny",
        "scenes": [
            {
                "type": "diff",
                "file": "a.py",
                "label": "change",
                "lines": diff_lines,
                "say": ["The change adds values."],
                "cues": [{"at": [0, 0.1], "do": "step", "n": 1}],
            },
            outro,
        ],
    }


def wrapped_change() -> tuple[dict[str, Any], dict[str, Any]]:
    m = tiny_map()
    lines = [
        {"op": "+", "old": None, "new": n, "text": f'value{n} = "' + "x" * 190 + '"'}
        for n in range(1, 13)
    ]
    m["files"][0]["hunks"][0]["lines"] = lines
    m["files"][0]["added"] = m["brief"]["files"][0]["added"] = 12
    b = tiny_board([str(n) for n in range(1, 13)])
    b["scenes"][0]["hold"] = 3
    return m, b


def test_check_rejects_wrapped_diff_beyond_visible_stage() -> None:
    from prc.explainer.check import verify_board

    m, b = wrapped_change()
    with pytest.raises(SystemExit, match=r"diff.*fit|diff.*overflow"):
        verify_board(b, m)


def test_coverage_does_not_claim_clipped_wrapped_diff_is_complete() -> None:
    from prc.explainer.doc import _not_covered
    from prc.explainer.preflight import line_coverage

    m, b = wrapped_change()
    assert line_coverage(b, m)["shown"] < 12
    assert "Everything changed is on screen" not in _not_covered(b, m)


def test_cli_rejects_wrapped_assignment_rows_beyond_stage() -> None:
    import subprocess
    import sys

    m, b = wrapped_change()
    lines = m["files"][0]["hunks"][0]["lines"][:6]
    for line in lines:
        line["text"] = "result = " + " + ".join(["variable_" + "x" * 25] * 3)
    m["files"][0]["hunks"][0]["lines"] = lines
    m["files"][0]["added"] = m["brief"]["files"][0]["added"] = 6
    b["scenes"][0]["lines"] = [str(n) for n in range(1, 7)]
    root = Path(__file__).resolve().parents[1]
    proof = root / "artifacts/e2e/wrapped-token-boundaries"
    proof.mkdir(parents=True, exist_ok=True)
    board_path, map_path = proof / "board.json", proof / "map.json"
    board_path.write_text(json.dumps(b, indent=2))
    map_path.write_text(json.dumps(m, indent=2))
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "prc.cli",
            "board",
            "check",
            str(board_path),
            "--map",
            str(map_path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    (proof / "check.json").write_text(
        json.dumps(
            {"exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr}, indent=2
        )
    )
    assert run.returncode == 2, run.stdout + run.stderr
    assert "diff cannot fit" in run.stderr
    assert "6/6 on screen" not in run.stdout


def test_wrapped_diff_fits_in_real_browser() -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, b = wrapped_change()
    b["scenes"][0]["lines"] = ["1", "2", "3"]
    proof = Path(__file__).resolve().parents[1] / "artifacts/e2e/wrapped-diff"
    facts = verify_board(b, m)
    render(b, m, facts, proof, NoneBackend(), None, keys_only=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((proof / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        page.evaluate("window.seek(window.BOARD.scenes[0].end - 0.5)")
        page.screenshot(path=str(proof / "settled.png"))
        bounds = page.locator(".drow:not(.gap)").evaluate_all(
            """rows => rows.map(row => ({
                row: row.getBoundingClientRect().toJSON(),
                text: row.querySelector('.ct').getBoundingClientRect().toJSON()
            }))"""
        )
        (proof / "bounds.json").write_text(json.dumps(bounds, indent=2))
        assert len(bounds) == 3
        assert all(bound["row"]["bottom"] <= 862 for bound in bounds), bounds
        assert all(bound["text"]["bottom"] <= bound["row"]["bottom"] + 1 for bound in bounds), (
            bounds
        )
        browser.close()


def test_wrapped_diff_sign_sits_on_first_line() -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m, b = wrapped_change()
    m["files"][0]["hunks"][0]["lines"][2]["text"] = "ok = 1"
    b["scenes"][0]["lines"] = ["1", "2", "3"]
    proof = Path(__file__).resolve().parents[1] / "artifacts/e2e/wrapped-diff-sign"
    facts = verify_board(b, m)
    render(b, m, facts, proof, NoneBackend(), None, keys_only=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((proof / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        page.evaluate("window.seek(window.BOARD.scenes[0].end - 0.5)")
        page.screenshot(path=str(proof / "settled.png"))
        bounds = page.locator(".drow:not(.gap)").evaluate_all(
            """rows => rows.map(row => {
                const rects = row.querySelector('.ct').getClientRects();
                return {
                    row: row.getBoundingClientRect().toJSON(),
                    sg: row.querySelector('.sg').getBoundingClientRect().toJSON(),
                    first: rects[0].toJSON(),
                    count: rects.length,
                    wrapped: rects.length > 1,
                };
            })"""
        )
        (proof / "bounds.json").write_text(json.dumps(bounds, indent=2))
        assert [bound["wrapped"] for bound in bounds] == [True, True, False]
        for bound in bounds:
            sg_cy = bound["sg"]["y"] + bound["sg"]["height"] / 2
            line_cy = bound["first"]["y"] + bound["first"]["height"] / 2
            assert abs(sg_cy - line_cy) <= 2, bound
        browser.close()


def test_doc_prose_matches_video_captions_in_real_browser() -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.doc import render_doc
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m = tiny_map()
    b = tiny_board(["2", "3", "4"])
    b["scenes"][0]["say"] = [
        '`a` now returns <x> & "y".',
        {"show": "The `AI` step stays.", "speak": "The A.I. step stays."},
        "An unpaired ` stays literal.",
    ]
    proof = Path(__file__).resolve().parents[1] / "artifacts/e2e/caption-parity"
    facts = verify_board(b, m)
    rendered = render(b, m, facts, proof, NoneBackend(), None, keys_only=True)
    render_doc(b, m, proof, rendered.duration, has_video=False)
    read = """el => ({
        text: el.textContent,
        code: [...el.querySelectorAll('code')].map(c => c.textContent),
    })"""
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((proof / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        video = []
        for n, sentence in enumerate(page.evaluate("window.BOARD.scenes[0].sentences")):
            page.evaluate(f"window.seek({sentence['start'] + sentence['dur'] / 2})")
            video.append(page.locator(".ecap").evaluate(read))
            page.screenshot(path=str(proof / f"video-caption-{n}.png"))
        page.goto((proof / "doc.html").as_uri())
        doc = page.locator("#scene-0 .prose").evaluate_all(f"els => els.map({read})")
        page.locator("#scene-0").screenshot(path=str(proof / "doc-scene.png"))
        browser.close()
    assert video == doc
    assert doc == [
        {"text": 'a now returns <x> & "y".', "code": ["a"]},
        {"text": "The AI step stays.", "code": ["AI"]},
        {"text": "An unpaired ` stays literal.", "code": []},
    ]


def test_card_and_video_outro_render_code_names() -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend
    from prc.presentation.card import render_card

    m, b = tiny_map(), tiny_board(["2", "3", "4"])
    b["scenes"][-1]["l1"] = '`a` now returns <x> & "y".'
    b["scenes"][-1]["l2"] = "Start at `a` in `a.py`."
    proof = Path(__file__).resolve().parents[1] / "artifacts/e2e/caption-headlines"
    facts = verify_board(b, m)
    render(b, m, facts, proof, NoneBackend(), None, keys_only=True)
    shown = {"show": "The `a` step stays.", "speak": "The A step stays."}
    title = {"scenes": [{"type": "title", "say": [shown]}]}
    for name, board in (("outro", b), ("spoken", title)):
        render_card(m, m["brief"], board, proof / f"{name}.html", proof / f"{name}.png")
    read = """el => ({
        text: el.textContent,
        code: [...el.querySelectorAll('code')].map(c => c.textContent),
    })"""
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto((proof / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        page.evaluate("window.seek(window.BOARD.scenes.at(-1).end - 0.5)")
        page.screenshot(path=str(proof / "video-outro.png"))
        outro = page.locator(".outro .l1, .outro .l2").evaluate_all(f"els => els.map({read})")
        page.set_viewport_size({"width": 1200, "height": 630})
        cards = []
        for name in ("outro", "spoken"):
            page.goto((proof / f"{name}.html").as_uri())
            cards.append(page.locator(".headline").evaluate(read))
        browser.close()
    expected = {"text": 'a now returns <x> & "y".', "code": ["a"]}
    assert outro == [expected, {"text": "Start at a in a.py.", "code": ["a", "a.py"]}]
    assert cards == [expected, {"text": "The a step stays.", "code": ["a"]}]


@pytest.mark.parametrize("verb", ["l1", "l2", "cmd"])
def test_check_rejects_outro_reveal_at_scene_end(verb: str) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import scene_windows

    m, b = tiny_map(), tiny_board(["2"])
    start, end = scene_windows(b)[-1]
    next(c for c in b["scenes"][-1]["cues"] if c["do"] == verb)["at"] = end - start
    with pytest.raises(SystemExit, match=r"outro.*reveal"):
        verify_board(b, m)


def test_fitted_outro_reveal_must_finish_before_settled_frame(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import check_stamped_cues, fit_sentences
    from prc.explainer.voice import NoneBackend

    m, b = tiny_map(), tiny_board(["2"])
    verify_board(b, m)
    fit_sentences(b, NoneBackend(), tmp_path, [])
    s = b["scenes"][-1]
    next(c for c in s["cues"] if c["do"] == "cmd")["t"] = s["end"]
    assert any("outro" in problem and "reveal" in problem for problem in check_stamped_cues(b))


def test_outro_fine_print_must_finish_its_delayed_reveal() -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import scene_windows

    m, b = tiny_map(), tiny_board(["2"])
    start, end = scene_windows(b)[-1]
    next(c for c in b["scenes"][-1]["cues"] if c["do"] == "cmd")["at"] = end - start - 1
    with pytest.raises(SystemExit, match=r"outro.*reveal"):
        verify_board(b, m)


@pytest.mark.parametrize(
    ("case", "board"),
    [
        ("missing-scenes", {}),
        ("null-scenes", {"scenes": None}),
        ("missing-type", {"scenes": [{}]}),
        ("null-scene", {"scenes": [None]}),
        ("missing-file", {"scenes": [{"type": "diff", "lines": ["2"]}]}),
        ("missing-say", {"scenes": [{"type": "outro", "cues": [{"do": "cmd", "at": [0, 0.5]}]}]}),
        ("invalid-hold", {"scenes": [{"type": "outro", "hold": "x"}]}),
        ("missing-receipt-rows", {"scenes": [{"type": "receipt", "say": ["x"]}]}),
        ("invalid-receipt-row", {"scenes": [{"type": "receipt", "rows": [None]}]}),
        ("invalid-timeline-row", {"scenes": [{"type": "timeline", "rows": [None]}]}),
        ("invalid-list-item", {"scenes": [{"type": "list", "items": ["x"]}]}),
        ("invalid-stat-card", {"scenes": [{"type": "stats", "cards": [True]}]}),
        ("invalid-bar", {"scenes": [{"type": "bars", "bars": [1]}]}),
        ("invalid-group", {"scenes": [{"type": "groups", "groups": [[]]}]}),
    ],
)
def test_malformed_board_fails_cli_without_traceback(tmp_path: Path, case: str, board: Any) -> None:
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    proof = root / "artifacts/e2e/board-shape" / case
    proof.mkdir(parents=True, exist_ok=True)
    map_path, board_path = tmp_path / "map.json", tmp_path / "board.json"
    map_path.write_text(json.dumps(tiny_map()))
    board_path.write_text(json.dumps(board))
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "prc.cli",
            "board",
            "check",
            str(board_path),
            "--map",
            str(map_path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    (proof / "check.json").write_text(
        json.dumps(
            {
                "case": case,
                "board": board,
                "exit_code": run.returncode,
                "stdout": run.stdout,
                "stderr": run.stderr,
            },
            indent=2,
        )
    )
    assert run.returncode == 2, run.stderr
    assert "Traceback" not in run.stderr
    assert "receipts failed" in run.stderr


def test_line_coverage_counts_changed_lines_not_files() -> None:
    from prc.explainer.preflight import line_coverage

    m = tiny_map()
    b = tiny_board(["2"])
    cov = line_coverage(b, m)
    assert cov["total"] == 3, cov
    assert cov["shown"] == 1, cov
    assert len(cov["missing"]) == 2, cov


def test_board_coverage_and_doc_agree_on_missing_lines() -> None:
    from prc.explainer import boards
    from prc.explainer.doc import uncovered

    m = tiny_map()
    b = tiny_board(["2"])
    text = boards.coverage(b, m)
    assert "1/3" in text, text
    files, syms = uncovered(b, m)
    assert files == [] and syms == [], (files, syms)
    from prc.explainer.preflight import line_coverage

    cov = line_coverage(b, m)
    assert cov["missing"], "partial board must list missing changed lines"


def test_missing_lines_list_removed_ascending_then_added_ascending() -> None:
    import re

    from prc.explainer import boards
    from prc.explainer.doc import _not_covered
    from prc.explainer.preflight import line_coverage

    m = tiny_map()
    m["files"][0]["hunks"][0]["lines"] = [
        {"op": "-", "old": 178, "new": None, "text": "gone 178"},
        {"op": "-", "old": 171, "new": None, "text": "gone 171"},
        {"op": "-", "old": 81, "new": None, "text": "gone 81"},
        {"op": "+", "old": None, "new": 9, "text": "new 9"},
        {"op": "+", "old": None, "new": 3, "text": "new 3"},
        {"op": " ", "old": 1, "new": 1, "text": "def a():"},
    ]
    m["files"][0].update(added=2, removed=3)
    m["brief"]["files"][0].update(added=2, removed=3)
    b = tiny_board([])
    b["scenes"][0]["cues"] = []

    cov = line_coverage(b, m)
    assert cov["missing"] == ["a.py:-81", "a.py:-171", "a.py:-178", "a.py:3", "a.py:9"]

    html = _not_covered(b, m)
    labels = re.findall(r'<a class="leftout"[^>]*>([^<]+)</a>', html)
    assert labels == [
        "a.py#L81 (removed)",
        "a.py#L171 (removed)",
        "a.py#L178 (removed)",
        "a.py#L3",
        "a.py#L9",
    ]

    text = boards.coverage(b, m)
    assert "missing changed lines: a.py:-81, a.py:-171, a.py:-178, a.py:3, a.py:9" in text


def test_check_rejects_blank_changed_line_like_render() -> None:
    import pytest

    from prc.explainer.check import verify_board

    m = tiny_map()
    m["files"][0]["hunks"][0]["lines"].insert(2, {"op": "+", "old": None, "new": 5, "text": ""})
    b = tiny_board(["2", "5"])
    with pytest.raises(SystemExit) as err:
        verify_board(b, m)
    assert "blank" in str(err.value).lower() or "cut" in str(err.value).lower(), err.value


@pytest.mark.parametrize("refs", [["2", "5"], []])
def test_check_rejects_context_blank_and_empty_diff(refs: list[str]) -> None:
    from prc.explainer.check import verify_board

    m = tiny_map()
    m["files"][0]["hunks"][0]["lines"].append({"op": " ", "old": 5, "new": 5, "text": ""})
    b = tiny_board(refs)
    if not refs:
        b["scenes"][0]["cues"] = []
    with pytest.raises(SystemExit, match=r"CUT_NOT_SPACES|no expected refs"):
        verify_board(b, m)


def replacement() -> tuple[dict[str, Any], dict[str, Any]]:
    m = tiny_map()
    m["files"][0]["hunks"][0]["lines"] = [
        {"op": "-", "old": 2, "new": None, "text": "    x = 0"},
        {"op": "+", "old": None, "new": 2, "text": "    x = 1"},
    ]
    m["files"][0].update(added=1, removed=1)
    m["brief"]["files"][0].update(added=1, removed=1)
    return m, tiny_board(["-2", "2"])


def test_check_rejects_replacement_revealed_after_scene() -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import scene_windows

    m, b = replacement()
    end = scene_windows(b)[0][1]
    b["scenes"][0]["cues"][0]["at"] = end - 0.25
    with pytest.raises(SystemExit, match=r"row 2.*reveal|reveal.*row 2"):
        verify_board(b, m)


def test_coverage_excludes_replacement_that_never_appears() -> None:
    from prc.explainer.preflight import line_coverage
    from prc.explainer.timing import scene_windows

    m, b = replacement()
    b["scenes"][0]["cues"][0]["at"] = scene_windows(b)[0][1] - 0.25
    cov = line_coverage(b, m)
    assert cov["shown"] == 1, cov
    assert cov["missing"] == ["a.py:2"], cov


def test_fitted_timing_checks_effective_replacement_reveal(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import check_stamped_cues, fit_sentences
    from prc.explainer.voice import NoneBackend

    m, b = replacement()
    verify_board(b, m)
    fit_sentences(b, NoneBackend(), tmp_path, [])
    b["scenes"][0]["cues"][0]["t"] = b["scenes"][0]["end"] - 0.25
    problems = check_stamped_cues(b)
    assert any("row 2" in problem and "reveal" in problem for problem in problems), problems


def test_replacement_is_visible_in_real_settled_frame(tmp_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.timing import scene_windows
    from prc.explainer.voice import NoneBackend

    m, b = replacement()
    b["scenes"][0]["cues"][0]["at"] = scene_windows(b)[0][1] - 1.6
    facts = verify_board(b, m)
    render(b, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((tmp_path / "player.html").as_uri())
        page.wait_for_function("window.ready === true")
        page.evaluate("window.seek(window.BOARD.scenes[0].end - 0.5)")
        page.screenshot(path=str(tmp_path / "settled-replacement.png"))
        row = page.locator(".drow").filter(has_text="x = 1")
        assert row.count() == 1
        assert row.evaluate("el => Number(getComputedStyle(el).opacity)") == 1
        assert row.evaluate("el => el.getBoundingClientRect().height") > 0
        assert row.evaluate("el => getComputedStyle(el.closest('.scene')).visibility") == "visible"
        assert errors == []
        browser.close()


@pytest.mark.parametrize(
    "cue",
    [
        {"at": [0.0, 0.2], "do": "note", "line": "2", "text": "changed"},
        {"at": [0, "bad"], "do": "note", "line": "2", "text": "changed"},
        {"at": [True, 0.2], "do": "note", "line": "2", "text": "changed"},
        {"at": 0.1, "do": "step"},
        {"at": float("nan"), "do": "step", "n": 1},
        {"at": 0.1, "do": "note", "line": "2", "text": "changed", "until": float("nan")},
        {"at": 0.1, "do": "note", "line": "2", "text": "changed", "until": float("inf")},
    ],
)
def test_malformed_cue_fails_check_without_traceback(cue: dict[str, Any]) -> None:
    from prc.explainer.check import verify_board

    m, b = replacement()
    b["scenes"][0]["cues"].append(cue)
    with pytest.raises(SystemExit, match=r"cue|step"):
        verify_board(b, m)


@pytest.mark.parametrize("field", ["t", "until"])
def test_actual_fitted_stamps_must_be_finite(tmp_path: Path, field: str) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import check_stamped_cues, fit_sentences
    from prc.explainer.voice import NoneBackend

    m, b = replacement()
    verify_board(b, m)
    fit_sentences(b, NoneBackend(), tmp_path, [])
    b["scenes"][0]["cues"][0][field] = float("nan")
    assert any("finite" in issue for issue in check_stamped_cues(b))


def test_check_outro_fine_defaults_empty() -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.render import fill

    m = tiny_map()
    b = tiny_board(["2", "3", "4"], fine=None)
    facts = verify_board(b, m)
    assert b["scenes"][-1]["fine"] == "", b["scenes"][-1]
    fill(b, m, facts)
    assert b["scenes"][-1]["fine"] == "", b["scenes"][-1]


def test_verify_board_reports_trustworthy_silent_estimate() -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import predict
    from prc.explainer.voice import NoneBackend

    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    b = json.loads((DATA / "boards" / "mdp12.json").read_text())
    facts = verify_board(b, m)
    assert "estimate_none_seconds" in facts, sorted(facts)
    assert facts["estimate_none_seconds"] == predict(b, NoneBackend())


def test_note_overlap_risk_is_flagged_not_silent() -> None:
    from prc.explainer.check import verify_board

    m = json.loads((DATA / "maps" / "pr12.json").read_text())
    b = json.loads((DATA / "boards" / "mdp12.json").read_text())
    facts = verify_board(b, m)
    risks = facts.get("note_risks", [])
    assert risks, "mdp12 scene 3 clamps its note over line 1031; check must flag it"
    assert "1031" in risks[0] and "overlap" in risks[0].lower(), risks


def test_fitting_note_stays_silent() -> None:
    from prc.explainer.check import verify_board

    m = tiny_map()
    b = tiny_board(["2", "3", "4"])
    b["scenes"][0]["cues"] = [
        {"at": [0, 0.1], "do": "step", "n": 1},
        {"at": [0, 0.5], "do": "note", "line": "2", "text": "short"},
    ]
    facts = verify_board(b, m)
    assert facts.get("note_risks") == [], facts.get("note_risks")


def test_guide_names_installed_commands_and_preview() -> None:
    from prc.explainer.boards import guide

    text = guide()
    assert "prc board check" in text, text[:800]
    assert "prc board preview" in text, text[:800]
    assert "python3 show.py" not in text
    assert "Read tool" not in text


def test_highlight_hunk_fallback_survives_trailing_blank_lines() -> None:
    from prc.explainer.highlight import attach_tokens

    hunks = [
        {
            "old_start": 18,
            "new_start": 18,
            "lines": [
                {"op": " ", "old": 18, "new": 18, "text": "    released: list[int],"},
                {"op": "+", "old": None, "new": 21, "text": "    ordered = list(released)"},
                {"op": "+", "old": None, "new": 22, "text": ""},
                {"op": " ", "old": 19, "new": 23, "text": ""},
                {"op": " ", "old": 20, "new": 24, "text": ""},
            ],
        }
    ]
    rows: list[dict[str, Any]] = [
        {"ref": "18", "op": " ", "num": 18},
        {"ref": "21", "op": "+", "num": 21},
        {"ref": "22", "op": "+", "num": 22},
        {"ref": "23", "op": " ", "num": 23},
        {"ref": "24", "op": " ", "num": 24},
    ]
    attach_tokens(rows, "a.py", 4, None, "h" * 40, "b" * 40, hunks)
    by_ref = {r["ref"]: r for r in rows}
    assert by_ref["22"]["tokens"] == [], by_ref["22"]
    assert by_ref["23"]["tokens"] == [], by_ref["23"]
    assert "".join(t["text"] for t in by_ref["21"]["tokens"]) == ("ordered = list(released)"), (
        by_ref["21"]
    )


def test_keys_only_check_tools_skip_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    from prc.explainer import render as explain_render

    real_which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda name: None if name in ("ffmpeg", "ffprobe") else real_which(name)
    )
    explain_render.check_tools(need_video=False)
    with pytest.raises(explain_render.RenderError, match="ffmpeg"):
        explain_render.check_tools(need_video=True)


def test_preview_keys_only_writes_stills_without_video(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    real_which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda name: None if name in ("ffmpeg", "ffprobe") else real_which(name)
    )
    m = tiny_map()
    b = tiny_board(["2", "3", "4"])
    facts = verify_board(b, m)
    rendered = render(b, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    assert rendered.frames > 0
    assert sorted(p.name for p in (tmp_path / "keys").glob("*.png")) == [
        "00a.png",
        "00b.png",
        "01a.png",
        "01b.png",
    ]
    assert not (tmp_path / "video.mp4").exists()
    assert not (tmp_path / "narration.wav").exists()


def test_preview_em5756_note_is_not_flagged_as_overlap(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m = json.loads((ACCEPT / "em-5756" / "map.json").read_text())
    b = json.loads((ACCEPT / "em-5756" / "board.json").read_text())
    facts = verify_board(b, m)
    rendered = render(b, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    assert not [w for w in rendered.layout_warnings if "overlaps code" in w], (
        rendered.layout_warnings
    )


def long_map() -> dict[str, Any]:
    lines = [{"op": " ", "old": 1, "new": 1, "text": "def f():"}]
    for n in range(2, 8):
        lines.append({"op": "+", "old": None, "new": n, "text": "    v = (" + "q" * 56 + ")"})
    m = tiny_map()
    m["files"][0]["hunks"] = [{"old_start": 1, "new_start": 1, "lines": lines}]
    m["brief"]["files"][0]["added"] = 6
    return m


def stacked_notes_board() -> dict[str, Any]:
    cues: list[dict[str, Any]] = [{"at": [0, 0.1], "do": "step", "n": 1}]
    for k in range(4):
        cues.append(
            {
                "at": [0, 0.2 + 0.1 * k],
                "do": "note",
                "line": "2",
                "text": "note number " + str(k) + " explains the value here",
            }
        )
    return {
        "name": "stacked",
        "scenes": [
            {
                "type": "diff",
                "file": "a.py",
                "label": "change",
                "lines": ["2", "3", "4", "5", "6", "7"],
                "say": ["The change adds six values."],
                "cues": cues,
            },
            {
                "type": "outro",
                "l1": "Change adds six values.",
                "l2": "Start at f in a.py.",
                "fine": "small print",
                "say": ["Change adds six values."],
                "cues": [
                    {"at": [0, 0.0], "do": "l1"},
                    {"at": [0, 0.5], "do": "l2"},
                    {"at": [0, 0.9], "do": "cmd"},
                ],
            },
        ],
    }


def test_stacked_clamped_notes_still_flag_overlap(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.render import render
    from prc.explainer.voice import NoneBackend

    m = long_map()
    b = stacked_notes_board()
    facts = verify_board(b, m)
    assert facts.get("note_risks"), "four long notes on one row must warn in check"
    rendered = render(b, m, facts, tmp_path, NoneBackend(), None, keys_only=True)
    assert any("overlaps code" in w for w in rendered.layout_warnings), rendered.layout_warnings


def test_late_numeric_cue_rejected_in_check() -> None:
    from prc.explainer.check import verify_board

    m = tiny_map()
    b = tiny_board(["2", {"ref": "3", "step": 1}, "4"])
    b["scenes"][0]["cues"] = [{"at": 999, "do": "step", "n": 1}]
    with pytest.raises(SystemExit) as err:
        verify_board(b, m)
    assert "999" in str(err.value) and "end" in str(err.value).lower(), err.value


def test_stamped_cues_validated_after_fit(tmp_path: Path) -> None:
    from prc.explainer.check import verify_board
    from prc.explainer.timing import check_stamped_cues, fit_sentences
    from prc.explainer.voice import NoneBackend

    m = tiny_map()
    b = tiny_board(["2", "3", "4"])
    verify_board(b, m)
    fit_sentences(b, NoneBackend(), tmp_path, [])
    assert check_stamped_cues(b) == []
    b["scenes"][0]["cues"][0]["t"] = b["scenes"][0]["end"] + 10.0
    problems = check_stamped_cues(b)
    assert problems and "never show" in problems[0], problems


def test_board_preview_command_exists() -> None:
    from prc.cli import build_parser

    parser = build_parser()
    ns = parser.parse_args(["board", "preview", "b.json", "--map", "m.json"])
    assert ns.board_command == "preview"


def opaque_map() -> dict[str, Any]:
    m = tiny_map()
    m["files"].append(
        {
            "path": "yarn.lock",
            "kind": "opaque",
            "added": 50,
            "removed": 10,
            "hunks": [],
        }
    )
    return m


def test_refless_lines_produce_honest_partial_coverage() -> None:
    from prc.explainer import boards
    from prc.explainer.preflight import line_coverage

    m = opaque_map()
    b = tiny_board(["2"])
    cov = line_coverage(b, m)
    assert cov["total"] == 63, cov
    assert cov["known"] == 3, cov
    assert cov["shown"] == 1, cov
    assert cov["unavailable"] == 60, cov
    assert len(cov["missing"]) == 2, cov
    text = boards.coverage(b, m)
    assert "1/63" in text, text
    assert "60 without diff references" in text, text
    assert "opaque or oversize" not in text, text
