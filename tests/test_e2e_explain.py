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
def test_explain_shop_none(chromium: None, tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", "explain", "--source", "fixture:shop",
         "--board", str(BOARD), "--voice", "none",
         "--store", str(tmp_path / "store"), "--out", str(tmp_path / "out")],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )  # fmt: skip

    assert completed.returncode == 0, completed.stderr

    printed = json.loads(completed.stdout)
    assert printed["check_passed"] is True

    out = Path(printed["out"])
    for name in (
        "map.json",
        "map.html",
        "board.json",
        "video.mp4",
        "run.json",
        "card.html",
        "card.png",
        "comment.md",
    ):
        assert (out / name).exists(), name

    run = json.loads((out / "run.json").read_text())
    assert run["check"]["passed"] is True
    assert run["voice"] == "none"
    assert Path(run["comment"]).exists()
    assert Path(run["card"]).exists()

    info = probe(out / "video.mp4")
    stream = info["streams"][0]
    assert (stream["codec_name"], stream["pix_fmt"]) == ("h264", "yuv420p")
    assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (1920, 1080, "30/1")
    # Voice-aware prediction is exact for `none`; the encoder must land within 10%.
    assert float(info["format"]["duration"]) == pytest.approx(run["predicted_seconds"], rel=0.10)

    shutil.rmtree(ARTIFACT, ignore_errors=True)
    shutil.copytree(out, ARTIFACT / out.name)
