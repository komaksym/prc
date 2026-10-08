"""E2E: prc explain on fixture:shop with --voice none writes a real video."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "e2e" / "explain"
BOARD = ROOT / "tests" / "data" / "boards" / "shop.json"

needs_ffmpeg = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe not on PATH"
)


def probe(path: Path) -> Any:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries",
            "stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames:format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout  # fmt: skip

    return json.loads(out)


@pytest.fixture(scope="module")
def chromium() -> Iterator[None]:
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        try:
            driver.chromium.launch().close()
        except Exception as error:  # noqa: BLE001
            lines = str(error).splitlines()
            pytest.skip(f"Chromium cannot launch here: {lines[0]}")

    yield


@needs_ffmpeg
@pytest.mark.parametrize("stored", [False, True], ids=["default-output", "stored-no-git"])
def test_explain_shop_none(chromium: None, tmp_path: Path, stored: bool) -> None:
    extra = []
    if stored:
        mapped = subprocess.run(
            [sys.executable, "-m", "prc.cli", "map", "--source", "fixture:shop",
             "--store", str(tmp_path / "store"), "--out", str(tmp_path / "maps")],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            check=False,
        )  # fmt: skip
        assert mapped.returncode == 0, mapped.stderr
        extra = ["--map", str(next((tmp_path / "maps").glob("*/map.json")))]
    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", "explain", "--source", "fixture:shop",
         "--board", str(BOARD), "--voice", "none",
         "--store", str(tmp_path / "store"), *extra],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )  # fmt: skip

    assert completed.returncode == 0, completed.stderr

    printed = json.loads(completed.stdout)
    assert printed["check_passed"] is True

    out = tmp_path / printed["out"]
    for name in (
        "map.json",
        "map.html",
        "board.json",
        "video.mp4",
        "doc.html",
        "run.json",
        "card.html",
        "card.png",
        "comment.md",
    ):
        assert (out / name).exists(), name

    run = json.loads((out / "run.json").read_text())
    assert run["check"]["passed"] is True
    assert run["voice"] == "none"
    assert run["map_source"] == ("stored" if stored else "live")
    assert run["live_head_sha"] == (None if stored else run["stored_head_sha"])
    assert (tmp_path / run["comment"]).exists()
    assert (tmp_path / run["card"]).exists()

    info = probe(out / "video.mp4")
    stream = info["streams"][0]
    assert (stream["codec_name"], stream["pix_fmt"]) == ("h264", "yuv420p")
    assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (1920, 1080, "30/1")
    # Voice-aware prediction is exact for `none`; the encoder must land within 10%.
    assert float(info["format"]["duration"]) == pytest.approx(run["predicted_seconds"], rel=0.10)

    artifact = ARTIFACT / ("stored" if stored else "live") / out.name
    shutil.rmtree(artifact, ignore_errors=True)
    shutil.copytree(out, artifact)

    if stored:
        before = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
        replacement = json.loads((out / "map.json").read_text())
        replacement["title"] = "A new stored capture"
        replacement_path = tmp_path / "replacement.json"
        replacement_path.write_text(json.dumps(replacement))
        invalid = json.loads(BOARD.read_text())
        invalid["scenes"][1]["cite"][0]["match"] = "not_a_real_receipt"
        invalid_path = tmp_path / "invalid-board.json"
        invalid_path.write_text(json.dumps(invalid))
        command = [
            sys.executable, "-m", "prc.cli", "explain", "--source", "fixture:shop",
            "--map", str(replacement_path), "--voice", "none",
            "--store", str(tmp_path / "store"),
        ]  # fmt: skip
        failed = subprocess.run(
            [*command, "--board", str(invalid_path)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert failed.returncode == 2, failed.stderr
        assert {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()} == before

        fallback = subprocess.run(
            command,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert fallback.returncode == 0, fallback.stderr
        assert json.loads(fallback.stdout)["video"] is None
        assert not any((out / name).exists() for name in ("board.json", "doc.html", "video.mp4"))
        assert json.loads((out / "map.json").read_text())["title"] == replacement["title"]
        shutil.copytree(out, ARTIFACT / "fallback" / out.name, dirs_exist_ok=True)


@pytest.mark.parametrize("evidence", ["added-line", "captured-head"])
def test_stored_map_card_and_comment_carry_the_rebuilt_brief(tmp_path: Path, evidence: str) -> None:
    stored = json.loads((ROOT / "tests" / "data" / "explainer" / "maps" / "pr12.json").read_text())
    for file in stored["brief"]["files"]:
        file["sensitive"] = None
    target = next(f for f in stored["files"] if f["kind"] == "code")
    if evidence == "added-line":
        target["hunks"][0]["lines"].append(
            {"op": "+", "old": None, "new": 0, "text": 'URL = "https://api.linkedin.com/v2/me"'}
        )
    else:
        next(f for f in stored["brief"]["files"] if f["path"] == target["path"])["sensitive"] = (
            "external calls"
        )
    stored_path = tmp_path / "stored.json"
    stored_path.write_text(json.dumps(stored))

    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", "explain", "--source", "fixture:shop",
         "--map", str(stored_path), "--voice", "none",
         "--store", str(tmp_path / "store"), "--out", str(tmp_path / "out")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )  # fmt: skip

    assert completed.returncode == 0, completed.stderr
    out = Path(json.loads(completed.stdout)["out"])
    assert "external calls" in (out / "card.html").read_text()
    assert "external calls" in (out / "comment.md").read_text()
    rebuilt = json.loads((out / "map.json").read_text())
    assert any(f.get("sensitive") == "external calls" for f in rebuilt["brief"]["files"])
    assert json.loads((out / "run.json").read_text())["live_head_sha"] is None


def test_stored_map_reclassifies_end_to_end_checks_consistently(tmp_path: Path) -> None:
    stored = json.loads((ROOT / "tests" / "data" / "explainer" / "maps" / "pr12.json").read_text())
    target = next(f for f in stored["files"] if f["kind"] == "code")
    old_path = target["path"]
    target["path"] = "diagnostics/e2e_private_source.py"
    target["sensitive"] = "external calls"
    for file in stored["brief"]["files"]:
        if file["path"] == old_path:
            file["path"] = target["path"]
            file["sensitive"] = "external calls"
    stored["brief"]["look_first"] = [
        {"path": target["path"], "reason": "largest code change", "lines": []}
    ]
    stored_path = tmp_path / "stored.json"
    stored_path.write_text(json.dumps(stored))
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "prc.cli",
            "explain",
            "--source",
            "fixture:shop",
            "--map",
            str(stored_path),
            "--voice",
            "none",
            "--out",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    out = Path(json.loads(completed.stdout)["out"])
    rebuilt = json.loads((out / "map.json").read_text())
    for records in (rebuilt["brief"]["files"], rebuilt["files"]):
        file = next(f for f in records if f["path"] == target["path"])
        assert (file["kind"], file["sensitive"]) == ("test", None)
    assert target["path"] not in {p["path"] for p in rebuilt["brief"]["look_first"]}


@needs_ffmpeg
def test_stored_map_check_and_outputs_share_reclassified_facts(
    chromium: None, tmp_path: Path
) -> None:
    from prc.explainer.check import verify_board

    stored = json.loads((ROOT / "tests/data/explainer/maps/pr12.json").read_text())
    path = "diagnostics/e2e_probe.py"
    sid = f"{path}::test_probe"
    hunk = {
        "old_start": 0,
        "new_start": 1,
        "lines": [{"op": "+", "old": None, "new": 1, "text": "def test_probe(): pass"}],
    }
    stored["files"] = [
        {
            "path": path,
            "kind": "code",
            "status": "added",
            "language": "python",
            "sensitive": None,
            "added": 1,
            "removed": 0,
            "hunks": [hunk],
            "symbols": [sid],
        }
    ]
    stored["brief"]["files"] = [
        {
            "path": path,
            "kind": "code",
            "named": False,
            "sensitive": None,
            "added": 1,
            "removed": 0,
        }
    ]
    stored["brief"]["look_first"] = []
    stored["symbols"] = [
        {
            "id": sid,
            "path": path,
            "qualname": "test_probe",
            "kind": "function",
            "status": "added",
            "span": [1, 1],
            "base_span": None,
            "added": 1,
            "removed": 0,
            "hunks": [hunk],
            "call_sites": 0,
        }
    ]
    stored["edges"] = []
    stored["tour"] = [{"kind": "overview", "focus": [], "via": None}]
    board = {
        "name": "reclassified-test",
        "scenes": [
            {
                "type": "title",
                "kicker": "Added test",
                "say": ["A test was added."],
                "assert": [{"fact": "changed", "equals": 0}, {"fact": "tests_added", "equals": 1}],
            },
            {
                "type": "diff",
                "file": path,
                "lines": ["1"],
                "say": ["The probe passes."],
                "cues": [{"at": [0, 0], "do": "step", "n": 1}],
            },
        ],
    }
    stored_path, board_path = tmp_path / "map.json", tmp_path / "board.json"
    stored_path.write_text(json.dumps(stored))
    board_path.write_text(json.dumps(board))
    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", "explain", "--source", "fixture:shop",
         "--map", str(stored_path), "--board", str(board_path), "--voice", "none",
         "--out", str(tmp_path / "out")],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )  # fmt: skip
    assert completed.returncode == 0, completed.stderr
    out = Path(json.loads(completed.stdout)["out"])
    rebuilt = json.loads((out / "map.json").read_text())
    facts = verify_board(json.loads((out / "board.json").read_text()), rebuilt)
    run = json.loads((out / "run.json").read_text())
    assert (facts["changed"], facts["tests_added"]) == (0, 1)
    assert (run["check"]["changed"], run["check"]["tests_added"]) == (0, 1)
    for name in ("card.html", "comment.md"):
        assert "No production symbols changed" in (out / name).read_text()
    assert "def test_probe" in (out / "doc.html").read_text()
    artifact = ARTIFACT / "stored-reclassified"
    shutil.rmtree(artifact, ignore_errors=True)
    shutil.copytree(out, artifact)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            for name in ("map", "card", "doc"):
                page.goto((artifact / f"{name}.html").as_uri())
                if name == "doc":
                    page.wait_for_function("() => window.docReady === true")
                    assert "def test_probe(): pass" in page.locator("body").inner_text()
                page.screenshot(path=str(artifact / f"{name}.png"), full_page=True)
        finally:
            browser.close()
