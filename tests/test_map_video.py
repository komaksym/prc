"""Video export: the schedule and encoder without a browser, then the CLI end to end."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from prc.presentation import map_video
from prc.presentation.map_video import VideoError, encode, frame_count, frame_times

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "e2e" / "maps" / "video"
needs_ffmpeg = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe not on PATH"
)


def probe(path: Path) -> dict[str, Any]:
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
    result: dict[str, Any] = json.loads(out)

    return result


def test_frame_schedule_includes_both_endpoints() -> None:
    assert frame_count(1.0, 30) == 31
    assert frame_times(0.1, 30) == pytest.approx([0.0, 1 / 30, 2 / 30, 3 / 30])
    assert frame_times(0.0, 30) == [0.0]
    assert frame_times(12.34, 30)[-1] == pytest.approx(round(12.34 * 30) / 30)


def test_missing_ffmpeg_names_the_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(VideoError, match="ffmpeg"):
        map_video.check_tools()


def test_missing_playwright_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    with pytest.raises(VideoError, match=r"video.*playwright install chromium"):
        map_video.check_tools()


@pytest.fixture
def lavfi_frames(tmp_path: Path) -> list[bytes]:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")

    pattern = tmp_path / "f%02d.jpg"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30",
         "-frames:v", "12", str(pattern)],
        check=True,
    )  # fmt: skip

    return [p.read_bytes() for p in sorted(tmp_path.glob("f*.jpg"))]


@needs_ffmpeg
def test_encode_pipes_frames_into_h264(tmp_path: Path, lavfi_frames: list[bytes]) -> None:
    out = tmp_path / "t.mp4"
    encode(iter(lavfi_frames), out)
    info = probe(out)
    stream = info["streams"][0]

    assert (stream["codec_name"], stream["pix_fmt"]) == ("h264", "yuv420p")
    assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (320, 180, "30/1")
    assert int(stream["nb_read_frames"]) == len(lavfi_frames)


@needs_ffmpeg
def test_encode_reports_ffmpeg_failure(tmp_path: Path) -> None:
    with pytest.raises(VideoError, match="ffmpeg"):
        encode(iter([b"not a jpeg"] * 3), tmp_path / "bad.mp4")

    assert not (tmp_path / "bad.mp4").exists()


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
def test_cli_writes_video_and_card(chromium: None) -> None:
    shutil.rmtree(ARTIFACT, ignore_errors=True)
    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", "map", "--source", "fixture:shop",
         "--store", str(ARTIFACT / "store"), "--out", str(ARTIFACT / "out"), "--video"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )  # fmt: skip

    assert completed.returncode == 0, completed.stderr

    printed = json.loads(completed.stdout)
    mp4, card = Path(printed["mp4"]), Path(printed["card"])
    info = probe(mp4)
    stream = info["streams"][0]

    assert (stream["codec_name"], stream["pix_fmt"]) == ("h264", "yuv420p")
    assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (1920, 1080, "30/1")
    assert int(stream["nb_read_frames"]) == frame_count(printed["video_seconds"], 30)
    assert float(info["format"]["duration"]) == pytest.approx(printed["video_seconds"], abs=0.1)

    header = card.read_bytes()[:24]

    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (2400, 1260)
