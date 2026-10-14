"""Listening gate: a speech recognizer must hear every code name the narration says."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from prc.explainer import listen
from prc.explainer.listen import ListenError, check_tokens, find_engine
from prc.explainer.voice import available

SHOP_BOARD = Path(__file__).resolve().parent / "data" / "boards" / "shop.json"

LIBRARYSYNC_SAY = [
    "Now up next starts after the furthest watched episode.",
    "Earlier unwatched episodes are skipped, and the user gets s2e3.",
    "Now it calls `select_next_episode` for each show.",
    "Start review at `select_next_episode` in next_episode.py.",
]
# Parakeet's transcript of the 2026-10-09 librarysync-98 narration, cut to these sentences.
LIBRARYSYNC_HEARD = (
    "Now Up Next starts after the furthest watched episode. Earlier unwatched episodes are "
    "skipped, and the user gets SC. Now it calls select next episode for each show. "
    "Start review at select next episode in next episode. Pie."
)


def _board(*say: str) -> dict[str, Any]:
    return {"scenes": [{"say": list(say)}]}


def test_recorded_defects_are_lost() -> None:
    """Regression: the shipped narration lost s2e3 and .py, and the gate has to say so."""
    checks = check_tokens(_board(*LIBRARYSYNC_SAY), LIBRARYSYNC_HEARD)
    assert {c.token for c in checks if not c.ok} == {"s2e3", "next_episode.py"}
    assert {c.token for c in checks if c.ok} == {"select_next_episode"}


def test_error_name_heard_as_other_words_is_lost() -> None:
    board = _board("The read-error test preserves ErrNotExist in the error chain.")
    garbled = "The readerror test preserves or not exist in the error chain."
    clear = "The red error test preserves error not exist in the error chain."
    assert not check_tokens(board, garbled)[0].ok
    assert check_tokens(board, clear)[0].ok


def test_spelled_numbers_and_spacing_count_as_heard() -> None:
    board = _board("The user gets s2e3.", "A WELCOME10 code, in note.ts.")
    heard = "The user gets S two E three. A welcome ten code, in Note, TS."
    assert all(c.ok for c in check_tokens(board, heard))


def test_every_occurrence_must_be_heard() -> None:
    """Defect: one clear mention hides a garbled second one."""
    board = _board("It calls `apply_discount`.", "Then `apply_discount` runs again.")
    (check,) = check_tokens(board, "It calls apply discount. Then apply this count runs again.")
    assert (check.said, check.heard, check.ok) == (2, 1, False)


def test_no_engine_fails_with_install_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRC_MUESLI_CLI", "/nonexistent/muesli-cli")
    monkeypatch.setattr(listen, "MUESLI_APP_CLI", Path("/nonexistent/app-cli"))
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "whisper", None)
    with pytest.raises(ListenError, match="Muesli") as error:
        find_engine("auto")
    assert "openai-whisper" in str(error.value)


def test_explain_then_listen_hears_every_code_name(tmp_path: Path) -> None:
    """E2E: a Kokoro video naming code passes the gate, which checks itself on planted controls.

    macOS say reads "S 2 E 3" as "season 2, episode 3", so only Kokoro can stand in here.
    """
    if not available("kokoro"):
        pytest.skip("needs the voice extra: uv sync --extra voice")
    try:
        find_engine("auto")
    except ListenError as error:
        pytest.skip(str(error))
    from prc.cli import main

    board = json.loads(SHOP_BOARD.read_text())
    board["scenes"][-1]["say"].append(
        "Start review at `apply_discount` in cart.py, with the WELCOME10 code."
    )
    board_path = tmp_path / "board.json"
    board_path.write_text(json.dumps(board))
    from test_e2e_infographic import brief_without_infographic, render_brief_png

    seed = brief_without_infographic(tmp_path, board_path)
    drawn = render_brief_png(
        json.loads((seed / "infographic" / "brief.json").read_text()), tmp_path / "drawn.png"
    )
    out = tmp_path / "out"
    explain = ["explain", "--source", "fixture:shop", "--store", str(tmp_path / "store")]
    explain += ["--board", str(board_path), "--voice", "kokoro", "--out", str(out)]
    explain += ["--infographic", str(drawn)]
    assert main(explain) == 0
    (folder,) = [p for p in out.iterdir() if (p / "narration.wav").is_file()]

    assert main(["listen", str(folder)]) == 0

    report = json.loads((folder / "listening.json").read_text())
    assert report["passed"] is True
    assert report["engine"]["name"] in ("parakeet", "whisper") and report["engine"]["model"]
    assert report["calibration"]["passed"] is True
    assert (folder / "listening" / "control-good.wav").is_file()
    heard = {t["token"]: t for t in report["tokens"]}
    assert {"apply_discount", "cart.py", "WELCOME10"} <= set(heard)
    assert all(t["ok"] for t in heard.values())
