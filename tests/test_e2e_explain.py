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


def test_stored_map_card_and_comment_carry_the_rebuilt_brief(tmp_path: Path) -> None:
    """A stored map without brief signals still flags an external call it adds."""
    stored = json.loads((ROOT / "tests" / "data" / "explainer" / "maps" / "pr12.json").read_text())
    for file in stored["brief"]["files"]:
        file["sensitive"] = None
    target = next(f for f in stored["files"] if f["kind"] == "code")
    target["hunks"][0]["lines"].append(
        {"op": "+", "old": None, "new": 0, "text": 'URL = "https://api.linkedin.com/v2/me"'}
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
