"""prc doctor: one line per dependency, ok or missing, with the install command."""

from __future__ import annotations

import os
import shutil


def _ffmpeg() -> str:
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return "ffmpeg ok"

    return "ffmpeg missing. Install it (for example `brew install ffmpeg`)."


def _chromium() -> str:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return (
            "chromium missing. Run `uv sync --extra video` "
            "(or `pip install 'prc[video]'`), then `playwright install chromium`."
        )

    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as driver:
            driver.chromium.launch().close()
    except Exception as error:  # noqa: BLE001
        return (
            f"chromium missing ({str(error).splitlines()[0]}). Run `playwright install chromium`."
        )

    return "chromium ok"


def _voice() -> str:
    from prc.explainer.voice import SAY, available

    parts = []
    parts.append(
        "kokoro ok" if available("kokoro") else "kokoro missing (extra `voice` not installed)"
    )
    parts.append("say ok" if available("say") else f"say missing ({SAY} not on this machine)")
    parts.append("none ok (silent estimate, always works)")

    return "voice " + ", ".join(parts)


def _token() -> str:
    return "GITHUB_TOKEN " + ("set" if os.environ.get("GITHUB_TOKEN") else "unset")


def report() -> str:
    import sys

    lines = [
        f"python {sys.version.split()[0]} ok",
        _ffmpeg(),
        _chromium(),
        _voice(),
        _token(),
    ]

    return "\n".join(lines) + "\n"
