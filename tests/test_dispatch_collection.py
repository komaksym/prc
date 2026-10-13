"""Rule table collection keeps each agent rule paired with its enforcement."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAIN_AGENTS = Path("/Users/koval/dev/prc/AGENTS.md")
HUB_MARKERS = ("button-level end-to-end", "verify_paired_hub")


def _agents_text() -> str:
    local = REPO / "AGENTS.md"
    if local.is_file():
        return local.read_text(encoding="utf-8")
    return MAIN_AGENTS.read_text(encoding="utf-8")


def test_close_dispatch_row_is_present() -> None:
    assert "Close every dispatch" in _agents_text()


def test_hub_button_pass_row_is_present() -> None:
    text = _agents_text()
    for marker in HUB_MARKERS:
        assert marker in text, f"AGENTS.md rule table must name {marker}"


def test_hub_row_names_its_enforcement() -> None:
    text = _agents_text()
    assert "test_verify_paired_hub" in text


HANDOFF_MARKERS = ("handoff_study_hub", "artifacts/handoff")


def test_handoff_row_is_present() -> None:
    text = _agents_text()
    for marker in HANDOFF_MARKERS:
        assert marker in text, "AGENTS.md rule table must name the supervised handoff"


def test_handoff_row_names_its_enforcement() -> None:
    text = _agents_text()
    assert "test_verify_paired_hub" in text
    assert "test_dispatch_collection" in text
