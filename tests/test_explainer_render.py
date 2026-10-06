"""Render failure modes: missing tools say what to install, heads get own folders."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from prc import doctor
from prc.explainer import render
from prc.explainer.check import find_phrase, spoken
from prc.explainer.timing import at as cue_at
from prc.explainer.voice import NoneBackend, available, estimate_seconds, select
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
