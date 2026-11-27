"""Render failure modes: missing tools say what to install, heads get own folders."""

from __future__ import annotations

import builtins
import importlib.util
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from prc.explainer import doctor, render, voice
from prc.explainer.check import find_phrase, spoken
from prc.explainer.timing import at as cue_at
from prc.explainer.voice import KokoroBackend, NoneBackend, available, estimate_seconds, select
from prc.model import PrRef
from prc.pipeline import explain_slug

DATA = Path(__file__).resolve().parent / "data" / "explainer"


def test_none_needs_no_kokoro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "kokoro", None)
    monkeypatch.setitem(sys.modules, "soundfile", None)

    assert not available("kokoro")

    backend = select("none")

    assert backend.name == "none"
    assert backend.synth("hello world", Path("/nonexistent/x.wav")) == pytest.approx(
        estimate_seconds("hello world")
    )


def test_default_voice_skips_missing_kokoro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "kokoro", None)
    monkeypatch.setitem(sys.modules, "soundfile", None)

    assert select("auto").name in ("say", "none")


def test_kokoro_availability_checks_the_model_without_importing_packages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    found: list[str] = []
    imported: list[str] = []

    def find_spec(name: str, path: object = None, target: object = None) -> object:
        found.append(name)
        return object() if name != "en_core_web_sm" else None

    def record_import(name: str, *args: object, **kwargs: object) -> Any:
        imported.append(name)
        raise AssertionError(f"availability imported {name}")

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)
    monkeypatch.setattr(builtins, "__import__", record_import)

    assert not available("kokoro")
    assert found == ["kokoro", "soundfile", "en_core_web_sm"]
    assert not {"kokoro", "soundfile", "en_core_web_sm"} & set(imported)


def test_auto_selects_installed_kokoro_without_importing_packages(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())

    def reject_import(name: str, *args: object, **kwargs: object) -> Any:
        raise AssertionError(f"selection imported {name}")

    monkeypatch.setattr(builtins, "__import__", reject_import)

    assert select("auto").name == "kokoro"
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("fail_first", [False, True])
def test_kokoro_pipeline_is_built_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fail_first: bool
) -> None:
    constructed: list[KokoroBackend] = []
    calls: list[tuple[str, str]] = []

    class Audio:
        def numpy(self) -> list[float]:
            return [0.25]

    class Result:
        audio = Audio()

    class Pipeline:
        def __init__(self, *, lang_code: str, repo_id: str) -> None:
            assert (lang_code, repo_id) == ("a", "hexgrad/Kokoro-82M")
            constructed.append(backend)
            if fail_first and len(constructed) == 1:
                raise RuntimeError("model initialization failed")

        def __call__(self, text: str, *, voice: str) -> list[Result]:
            calls.append((text, voice))
            return [Result()]

    kokoro = types.ModuleType("kokoro")
    monkeypatch.setattr(kokoro, "KPipeline", Pipeline, raising=False)
    numpy = types.ModuleType("numpy")
    monkeypatch.setattr(numpy, "concatenate", lambda values: values, raising=False)
    soundfile = types.ModuleType("soundfile")
    monkeypatch.setattr(soundfile, "write", lambda *args: None, raising=False)
    monkeypatch.setitem(sys.modules, "kokoro", kokoro)
    monkeypatch.setitem(sys.modules, "numpy", numpy)
    monkeypatch.setitem(sys.modules, "soundfile", soundfile)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(voice, "probe_seconds", lambda path: 0.5)

    backend = KokoroBackend()
    if fail_first:
        with pytest.raises(RuntimeError, match="model initialization failed"):
            backend.synth("retry", tmp_path / "retry.wav")
    assert backend.synth("first", tmp_path / "one.wav") == 0.5
    assert backend.synth("second", tmp_path / "two.wav") == 0.5

    assert len(constructed) == (2 if fail_first else 1)
    assert calls == [("first", "af_heart"), ("second", "af_heart")]


@pytest.mark.parametrize("fallback", ["say", "none"])
def test_auto_fallback_says_why_and_how_to_install(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fallback: str
) -> None:
    monkeypatch.setattr(voice, "available", lambda name: name == fallback)

    assert select("auto").name == fallback

    warning = capsys.readouterr().err
    assert f"auto selected {fallback}" in warning
    assert "Kokoro" in warning
    assert "uv sync --extra video --extra voice" in warning
    assert "python -m spacy download en_core_web_sm" in warning
    assert "download model weights" in warning


def test_explicit_missing_kokoro_explains_model_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice, "available", lambda name: False)

    with pytest.raises(voice.VoiceError) as error:
        select("kokoro")

    assert "uv sync --extra video --extra voice" in str(error.value)
    assert "python -m spacy download en_core_web_sm" in str(error.value)
    assert "download model weights" in str(error.value)


def test_missing_ffmpeg_names_the_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    with pytest.raises(render.RenderError, match="ffmpeg"):
        render.check_tools()

    assert "ffmpeg" in doctor.report()


def test_missing_playwright_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    with pytest.raises(render.RenderError, match=r"playwright install chromium"):
        render.check_tools()

    assert "playwright install chromium" in doctor.report()


def test_heads_get_their_own_folders() -> None:
    ref = PrRef("o", "r", 12)

    assert explain_slug(ref, "a" * 40) != explain_slug(ref, "b" * 40)
    assert explain_slug(ref, "a" * 40).endswith("12-" + "a" * 12)


def test_hostile_text_cannot_break_the_page(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    board: dict[str, Any] = {
        "name": "hostile",
        "scenes": [
            {
                "type": "title",
                "kicker": "Open pull request",
                "say": ['A title with a quote " and </script> inside.'],
            },
            {
                "type": "outro",
                "l1": "First line with </script> in it.",
                "l2": "Second line.",
                "fine": "Small print.",
                "say": ["Closing out."],
                "cues": [
                    {"at": [0, 0.0], "do": "l1"},
                    {"at": [0, 0.5], "do": "l2"},
                    {"at": [0, 0.9], "do": "cmd"},
                ],
            },
        ],
    }
    out = tmp_path / "hostile"
    rendered = render.render_board(
        _write(board, tmp_path), DATA / "maps" / "pr12.json", out, NoneBackend()
    )

    assert rendered.duration > 0
    html = (out / "player.html").read_text()
    assert html.count("</script>") == 2, "only the two real script tags may close"
    assert "</script>" not in html.replace("</script>", "", 2).replace("<\\/script>", "")


def _write(board: dict[str, Any], tmp_path: Path) -> Path:
    p = tmp_path / "board.json"
    p.write_text(json.dumps(board))

    return p


def test_phrase_cues_keep_narration_order() -> None:
    """Share timing (none) must order cues the way the narration says them."""
    board = json.loads((DATA / "boards" / "mdp17b.json").read_text())
    backend = NoneBackend()
    audio = Path("/nonexistent")
    log: list[dict[str, Any]] = []
    order: list[tuple[int, int]] = []

    for si, s in enumerate(board["scenes"]):
        s["i"] = si
        s["start"], t = 0.0, 0.45
        s["sentences"] = []
        for line, speak in zip(s["say"], spoken(s), strict=True):
            d = estimate_seconds(speak)
            s["sentences"].append({"text": line, "start": t, "dur": d, "on": 0.0, "off": d})
            t += d + 0.3
        s["onsets"] = {}
        for c in s.get("cues", []):
            if isinstance(c.get("at"), str):
                ((k, offset),) = find_phrase(s, c["at"])
                order.append((k, offset))
                c["t"] = cue_at(s, c["at"], audio, log, backend)
        for c in s.get("cues", []):
            if isinstance(c.get("at"), str):
                ((k, offset),) = find_phrase(s, c["at"])
                sent = s["sentences"][k]
                assert sent["start"] <= c["t"] <= sent["start"] + sent["dur"], (s["i"], c["at"])

    assert order, "mdp17b must have phrase cues to compare"
