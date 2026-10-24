"""Voice gate: a missing Kokoro fails loudly instead of silently degrading."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from prc.explainer.voice import available, select

INSTALL_HINT = "uv sync --extra video --extra voice"
SHOP_BOARD = Path(__file__).resolve().parent / "data" / "boards" / "shop.json"


def _hide_kokoro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "kokoro", None)
    monkeypatch.setitem(sys.modules, "soundfile", None)
    monkeypatch.setitem(sys.modules, "en_core_web_sm", None)


def test_explicit_kokoro_missing_fails_with_hint_and_no_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defect caught: an explicit --voice kokoro that degrades to another backend and publishes."""
    _hide_kokoro(monkeypatch)
    from prc.cli import main

    out = tmp_path / "out"
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "explain",
                "--source",
                "fixture:shop",
                "--store",
                str(tmp_path / "store"),
                "--board",
                str(SHOP_BOARD),
                "--voice",
                "kokoro",
                "--out",
                str(out),
            ]
        )
    assert INSTALL_HINT in str(exc.value)
    assert not out.exists() or not any(out.iterdir())


def test_auto_fallback_warns_on_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Defect: --voice auto silently picked say, so nobody noticed Kokoro was gone."""
    _hide_kokoro(monkeypatch)

    backend = select("auto")

    assert backend.name in ("say", "none")
    err = capsys.readouterr().err
    assert backend.name in err
    assert INSTALL_HINT in err


def test_available_false_when_only_spacy_model_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defect: Kokoro reported available, then tried to download the model on first use."""
    monkeypatch.setitem(sys.modules, "en_core_web_sm", None)

    assert not available("kokoro")
