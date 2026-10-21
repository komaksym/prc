"""Voice backends for the explainer: Kokoro, macOS say, or a silent estimate.

Kokoro is a lazy import behind the `voice` extra and never loads unless the
kokoro backend synthesizes. `none` measures nothing and imports nothing.
"""

from __future__ import annotations

import array
import importlib.util
import os
import subprocess
import sys
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Characters per second of Kokoro af_heart narration, measured from
# prototypes/explainer/out/mdp12-baseline/ (680 caption characters over
# 47.93 s of sentence audio; per-sentence range 12.9-15.7, median 14.2).
NONE_CHARS_PER_SEC = 14.2

SAY = "/usr/bin/say"


class VoiceError(RuntimeError):
    """A voice backend that cannot run, worded for the person running the CLI."""


def probe_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout)


def loudness(wav: Path) -> list[bool]:
    """Per 5 ms window, whether the clip is louder than -40 dBFS."""
    with wave.open(str(wav)) as w:
        rate, pcm = w.getframerate(), array.array("h", w.readframes(w.getnframes()))
    win = rate // 200
    return [max(map(abs, pcm[n : n + win])) > 328 for n in range(0, len(pcm), win)]


def audible(wav: Path) -> tuple[float, float]:
    loud = [i for i, x in enumerate(loudness(wav)) if x]
    return (loud[0] * 0.005, (loud[-1] + 1) * 0.005) if loud else (0.0, 0.0)


def pauses(wav: Path) -> list[tuple[float, float]]:
    runs, start = [], None
    for i, x in enumerate(loudness(wav) + [True]):
        if not x and start is None:
            start = i
        if x and start is not None:
            runs.append((start * 0.005, i * 0.005))
            start = None
    return runs


def estimate_seconds(text: str) -> float:
    return max(len(text) / NONE_CHARS_PER_SEC, 0.2)


@dataclass
class Backend:
    name: str
    has_audio: bool

    def synth(self, text: str, wav: Path) -> float:
        """Write narration audio, return its duration. `none` writes nothing."""
        raise NotImplementedError


@dataclass
class KokoroBackend(Backend):
    voice: str = "af_heart"

    def __init__(self, voice: str = "af_heart") -> None:
        super().__init__("kokoro", True)
        self.voice = voice
        self._pipe: Any = None

    def _pipeline(self) -> Any:
        """Build the Kokoro pipeline once and reuse it for later synthesis."""
        if self._pipe is None:
            from kokoro import KPipeline  # type: ignore[import-not-found]

            os.environ.setdefault("ESPEAK_DATA_PATH", "/opt/homebrew/share/espeak-ng-data")
            os.environ.setdefault(
                "PHONEMIZER_ESPEAK_LIBRARY", "/opt/homebrew/lib/libespeak-ng.dylib"
            )
            self._pipe = KPipeline(lang_code=self.voice[0], repo_id="hexgrad/Kokoro-82M")
        return self._pipe

    def synth(self, text: str, wav: Path) -> float:
        import numpy as np
        import soundfile  # type: ignore[import-not-found]

        pipe = self._pipeline()
        raw = wav.with_suffix(".24k.wav")
        soundfile.write(
            raw, np.concatenate([r.audio.numpy() for r in pipe(text, voice=self.voice)]), 24000
        )
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-ar", "48000", "-ac", "1", str(wav)],
            check=True,
        )
        return probe_seconds(wav)


@dataclass
class SayBackend(Backend):
    def __init__(self) -> None:
        super().__init__("say", True)

    def synth(self, text: str, wav: Path) -> float:
        if not Path(SAY).exists():
            raise VoiceError(f"{SAY} is not on this machine, so --voice say cannot run.")
        aiff = wav.with_suffix(".aiff")
        subprocess.run([SAY, "-o", str(aiff), text], check=True)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", "48000", "-ac", "1", str(wav)],
            check=True,
        )
        return probe_seconds(wav)


@dataclass
class NoneBackend(Backend):
    def __init__(self) -> None:
        super().__init__("none", False)

    def synth(self, text: str, wav: Path) -> float:
        return estimate_seconds(text)


def available(name: str) -> bool:
    if name == "kokoro":
        # Probe installed packages and the spaCy model without importing torch
        # or spaCy. This does not prove that the Kokoro weight cache is complete.
        try:
            return all(
                importlib.util.find_spec(module) is not None
                for module in ("kokoro", "soundfile", "en_core_web_sm")
            )
        except (ImportError, ModuleNotFoundError, ValueError):
            return False
    if name == "say":
        return Path(SAY).exists()
    if name == "none":
        return True
    raise VoiceError(f"unknown voice {name!r}; choose kokoro, say or none")


def select(name: str = "auto") -> Backend:
    """The named backend, or the first one that works: kokoro, say, none."""
    if name != "auto":
        if not available(name):
            if name == "kokoro":
                raise VoiceError(
                    "Kokoro is not installed. Run `uv sync --extra voice` "
                    "(asks before downloading PyTorch, spaCy and the Kokoro weights)."
                )
            raise VoiceError(f"--voice {name} is not available on this machine.")
        makers: dict[str, Callable[[], Backend]] = {
            "kokoro": KokoroBackend,
            "say": SayBackend,
            "none": NoneBackend,
        }
        return makers[name]()
    for candidate in ("kokoro", "say", "none"):
        if available(candidate):
            if candidate != "kokoro":
                print(
                    f"--voice auto selected {candidate} (Kokoro dependencies are unavailable, "
                    "including `en_core_web_sm`); run `uv sync --extra voice`; first synthesis "
                    "may still download model weights.",
                    file=sys.stderr,
                )
            return select(candidate)
    raise VoiceError("no voice backend works, not even the silent estimate")
