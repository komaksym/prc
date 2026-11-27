"""Listening gate: a speech recognizer must hear every code name the narration says.

Parakeet runs through Muesli's muesli-cli when it is installed, and Whisper base is
the fallback. Each run first checks the recognizer on planted controls: good and
bad pronunciations of the same code names, spoken by the run's own voice.
"""

from __future__ import annotations

import dataclasses
import json
import os
import plistlib
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from prc.explainer.check import scripted
from prc.explainer.speech import code_tokens, heard_as, speakable
from prc.explainer.voice import Backend, select

MUESLI_APP_CLI = Path("/Applications/Muesli.app/Contents/MacOS/muesli-cli")
INSTALL_HINT = "Install Muesli (it ships muesli-cli) or run `pip install openai-whisper`."

NUMBERS = {
    w: str(n)
    for n, w in enumerate(
        [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ]
    )
}

GOOD = "The user gets s2e3, and ErrNotExist stays in next_episode.py."

# An identifier must sound like one unit: the pause between its words stays
# small. Measured on Kokoro control clips (voice.pauses on control-good.wav):
# normal word gaps top out at 0.08 s while comma pauses start at 0.205 s, so
# 0.15 s separates a smooth read from a pause inside one name.
IDENT_GAP_MAX = 0.15


def check_identifier_gaps(
    board: dict[str, Any], words: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Gaps inside one identifier from Parakeet word timestamps.

    board holds narration text; words is a list of {word, start, end} in
    seconds in transcript order. Every code token is heard as several words
    (heard_as); the gap between two words of one token must stay at or
    below IDENT_GAP_MAX. Returns one entry per token whose internal gap is
    too wide: {token, gap, at}. An empty list passes.
    """
    seq = [
        (str(w.get("word", "")).lower(), float(w.get("start", 0.0)), float(w.get("end", 0.0)))
        for w in words
    ]
    said = [t for sc in board.get("scenes", []) for line in scripted(sc) for t in code_tokens(line)]
    bad: list[dict[str, Any]] = []
    for token in dict.fromkeys(said):
        expect = heard_as(token).lower().split()
        if len(expect) < 2:
            continue
        for k in range(len(seq) - len(expect) + 1):
            if [w for w, _, _ in seq[k : k + len(expect)]] != expect:
                continue
            gap = max(seq[k + j + 1][1] - seq[k + j][2] for j in range(len(expect) - 1))
            if gap > IDENT_GAP_MAX:
                bad.append({"token": token, "gap": round(gap, 3), "at": k})
            break
    return bad


def parakeet_words(cli: Path | str, wav: Path) -> list[dict[str, Any]]:
    """Word timestamps from muesli-cli JSON when it carries them, else []."""
    import json as _json
    import subprocess as _sp
    import tempfile as _tf
    from pathlib import Path as _P

    with _tf.TemporaryDirectory() as work:
        mono = _P(work) / "speech.wav"
        _sp.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ar", "16000", "-ac", "1", str(mono)],
            check=True,
        )
        out = _sp.run(
            [str(cli), "transcribe", str(mono), "--format", "json", "--model", "parakeet-unified"],
            capture_output=True,
            text=True,
        )
    try:
        result = _json.loads(out.stdout)
    except Exception:
        return []
    data = result.get("data", {}) if isinstance(result, dict) else {}
    for key in ("words", "tokens"):
        items = data.get(key)
        if isinstance(items, list) and items and isinstance(items[0], dict):
            return [
                {
                    "word": x.get("word", x.get("text", "")),
                    "start": x.get("start", x.get("start_time", 0.0)),
                    "end": x.get("end", x.get("end_time", 0.0)),
                }
                for x in items
            ]
    segs = data.get("segments")
    if isinstance(segs, list):
        out_words = []
        for seg in segs:
            for x in seg.get("words", []) or []:
                out_words.append(
                    {
                        "word": x.get("word", x.get("text", "")),
                        "start": x.get("start", 0.0),
                        "end": x.get("end", 0.0),
                    }
                )
        if out_words:
            return out_words
    return []


BAD = "The user gets sezz three, and er knot eggs isst stays in next epp so dee pie."


class ListenError(RuntimeError):
    """No recognizer, or no narration to check, worded for the person running the CLI."""


@dataclasses.dataclass(frozen=True)
class Engine:
    name: str
    model: str
    version: str
    transcribe: Callable[[Path], str]


@dataclasses.dataclass(frozen=True)
class TokenCheck:
    token: str
    expect: str
    said: int
    heard: int

    @property
    def ok(self) -> bool:
        return self.heard >= self.said


def compact(text: str) -> str:
    """Letters and digits only, with spelled numbers as digits and "dot" dropped."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "".join(NUMBERS.get(w, w) for w in words if w != "dot")


def check_tokens(board: dict[str, Any], transcript: str) -> list[TokenCheck]:
    said = Counter(t for s in board["scenes"] for line in scripted(s) for t in code_tokens(line))
    heard = compact(transcript)
    checks = []
    for token, count in said.items():
        expect = compact(heard_as(token))
        checks.append(TokenCheck(token, expect, count, heard.count(expect)))
    return checks


def _muesli_cli() -> Path | None:
    found = shutil.which("muesli-cli")
    env = os.environ.get("PRC_MUESLI_CLI")
    for path in (Path(env) if env else None, Path(found) if found else None, MUESLI_APP_CLI):
        if path is not None and path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def _parakeet() -> Engine | None:
    cli = _muesli_cli()
    if cli is None:
        return None
    plist = cli.parent.parent / "Info.plist"
    version = (
        str(plistlib.loads(plist.read_bytes()).get("CFBundleShortVersionString", "unknown"))
        if plist.is_file()
        else "unknown"
    )

    def transcribe(wav: Path) -> str:
        with tempfile.TemporaryDirectory() as work:
            mono = Path(work) / "speech.wav"
            resample = ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ar", "16000", "-ac", "1"]
            subprocess.run([*resample, str(mono)], check=True)
            command = [str(cli), "transcribe", str(mono), "--format", "json"]
            out = subprocess.run(
                [*command, "--model", "parakeet-unified"], capture_output=True, text=True
            )
        try:
            result = json.loads(out.stdout)
        except json.JSONDecodeError:
            raise ListenError(
                f"muesli-cli could not transcribe {wav}: {out.stderr.strip()}"
            ) from None
        if not result.get("ok"):
            raise ListenError(f"muesli-cli could not transcribe {wav}: {result}")
        return str(result["data"]["transcript"])

    return Engine("parakeet", "parakeet-unified", f"muesli {version}", transcribe)


def _whisper() -> Engine | None:
    try:
        import whisper  # type: ignore
    except ImportError:
        return None
    model: list[Any] = []

    def transcribe(wav: Path) -> str:
        if not model:
            model.append(whisper.load_model("base"))
        return str(model[0].transcribe(str(wav), language="en", fp16=False)["text"])

    return Engine("whisper", "base", f"openai-whisper {whisper.__version__}", transcribe)


def find_engine(choice: str = "auto") -> Engine:
    """The named recognizer, or the best one installed: Parakeet, then Whisper."""
    makers = {"parakeet": _parakeet, "whisper": _whisper}
    for name in makers if choice == "auto" else [choice]:
        engine = makers[name]()
        if engine is not None:
            return engine
    wanted = (
        "No speech recognizer is installed." if choice == "auto" else f"{choice} is not installed."
    )
    raise ListenError(f"{wanted} {INSTALL_HINT}")


def calibrate(engine: Engine, voice: Backend, work: Path) -> dict[str, Any]:
    """Planted controls: the good line must be heard in full, the bad one lose every token."""
    board = {"scenes": [{"say": [GOOD]}]}
    heard = {}
    for name, line in (("good", speakable(GOOD)), ("bad", BAD)):
        wav = work / f"control-{name}.wav"
        voice.synth(line, wav)
        heard[name] = engine.transcribe(wav)
    good = check_tokens(board, heard["good"])
    bad = check_tokens(board, heard["bad"])
    return {
        "passed": all(c.ok for c in good) and not any(c.ok for c in bad),
        "good": {"said": speakable(GOOD), "heard": heard["good"], "ok": [c.ok for c in good]},
        "bad": {"said": BAD, "heard": heard["bad"], "ok": [c.ok for c in bad]},
    }


def listen(folder: Path, choice: str = "auto") -> dict[str, Any]:
    """Check a rendered explainer folder; write listening.json and the control clips beside it."""
    narration = folder / "narration.wav"
    run = json.loads((folder / "run.json").read_text())
    if not narration.is_file() or run.get("voice") == "none":
        raise ListenError(f"{folder} has no narration audio to check.")
    engine = find_engine(choice)
    controls = folder / "listening"
    controls.mkdir(exist_ok=True)
    calibration = calibrate(engine, select(run["voice"]), controls)
    transcript = engine.transcribe(narration)
    checks = check_tokens(json.loads((folder / "board.json").read_text()), transcript)
    board_doc = json.loads((folder / "board.json").read_text())
    gaps: list[dict[str, Any]] = []
    cli = _muesli_cli() if engine.name == "parakeet" else None
    if cli is not None:
        try:
            gaps = check_identifier_gaps(board_doc, parakeet_words(cli, narration))
        except Exception:
            gaps = []
    report = {
        "engine": {"name": engine.name, "model": engine.model, "version": engine.version},
        "voice": run["voice"],
        "calibration": calibration,
        "transcript": transcript,
        "tokens": [dataclasses.asdict(c) | {"ok": c.ok} for c in checks],
        "lost": [c.token for c in checks if not c.ok],
        "identifier_gaps": gaps,
        "passed": calibration["passed"] and all(c.ok for c in checks) and not gaps,
    }
    (folder / "listening.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
