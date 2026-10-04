"""Frame-stepped video and social card of a written map page, through headless Chromium."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FPS = 30
VIDEO_VIEWPORT = {"width": 1280, "height": 720}
VIDEO_SCALE = 1.5
CARD_VIEWPORT = {"width": 1200, "height": 630}
CARD_SCALE = 2
# JPEG q95 feeds a lossy H.264 encode anyway and skips PNG's zlib cost per 1920x1080 frame.
JPEG_QUALITY = 95

CAPTURE_CSS = """
.legend, .zoom, .hints, #drawer, #play { display: none !important; }
*, *::before, *::after { animation: none !important; transition: none !important; }
"""


class VideoError(RuntimeError):
    """A missing tool or a failed capture, worded for the person running the CLI."""


@dataclass(frozen=True)
class VideoResult:
    mp4: Path
    card: Path
    seconds: float
    frames: int


def frame_count(duration: float, fps: int = FPS) -> int:
    return round(duration * fps) + 1


def frame_times(duration: float, fps: int = FPS) -> list[float]:
    return [i / fps for i in range(frame_count(duration, fps))]


def check_tools() -> None:
    if not shutil.which("ffmpeg"):
        raise VideoError("ffmpeg is not on PATH. Install it (for example `brew install ffmpeg`).")

    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as error:
        raise VideoError(
            "Playwright is not installed. Run `uv sync --extra video` (or "
            "`pip install 'prc[video]'`), then `playwright install chromium`."
        ) from error


def encode(frames: Iterable[bytes], out: Path, fps: int = FPS) -> None:
    """Pipe JPEG frames into ffmpeg. `out` exists only when ffmpeg succeeded."""
    with tempfile.TemporaryDirectory() as scratch:
        partial = Path(scratch) / "tour.mp4"
        log = Path(scratch) / "ffmpeg.log"

        with log.open("wb") as errors:
            ffmpeg = subprocess.Popen(
                [
                    "ffmpeg", "-v", "error", "-y",
                    "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
                    "-vf", "scale=out_range=tv,format=yuv420p",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-an", str(partial),
                ],
                stdin=subprocess.PIPE,
                stderr=errors,
            )  # fmt: skip
            assert ffmpeg.stdin is not None

            try:
                for frame in frames:
                    ffmpeg.stdin.write(frame)
                ffmpeg.stdin.close()
            except BrokenPipeError:
                pass
            except BaseException:
                ffmpeg.kill()
                raise
            finally:
                code = ffmpeg.wait()

        if code != 0 or not partial.exists():
            detail = log.read_text(errors="replace").strip()
            raise VideoError(f"ffmpeg failed (exit {code}): {detail}")

        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(partial), out)


def _open(browser: Any, html: Path, viewport: dict[str, int], scale: float) -> Any:
    context = browser.new_context(viewport=viewport, device_scale_factor=scale, color_scheme="dark")
    page = context.new_page()
    page.goto(html.resolve().as_uri())
    page.wait_for_function("() => window.prcTour !== undefined")
    page.add_style_tag(content=CAPTURE_CSS)
    page.evaluate("document.fonts.ready.then(() => true)")

    return page


def _frames(page: Any, times: list[float]) -> Iterator[bytes]:
    for t in times:
        page.evaluate("t => window.prcTour.seek(t)", t)
        yield page.screenshot(type="jpeg", quality=JPEG_QUALITY)


def make_video(html: Path, out_dir: Path) -> VideoResult:
    check_tools()

    from playwright.sync_api import sync_playwright

    mp4, card = out_dir / "tour.mp4", out_dir / "card.png"

    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as error:  # noqa: BLE001
            raise VideoError(
                f"Chromium cannot launch ({str(error).splitlines()[0]}). "
                "Run `playwright install chromium`."
            ) from error

        try:
            page = _open(browser, html, VIDEO_VIEWPORT, VIDEO_SCALE)
            duration = float(page.evaluate("window.prcTour.duration"))
            times = frame_times(duration)
            encode(_frames(page, times), mp4)

            page = _open(browser, html, CARD_VIEWPORT, CARD_SCALE)
            card.write_bytes(page.screenshot(type="png"))
        finally:
            browser.close()

    return VideoResult(mp4, card, duration, len(times))
