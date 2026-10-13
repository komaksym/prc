"""Guard keeps the paired hub button pass required for hub handoffs."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RECIPE = REPO / ".agents" / "skills" / "verify" / "features" / "paired.md"
DRIVER = REPO / "scripts" / "verify_paired_hub.py"
INDEX = REPO / ".agents" / "skills" / "verify" / "features" / "README.md"
SKILL = REPO / ".agents" / "skills" / "verify" / "SKILL.md"
BUTTONS = (
    "Prepare next reading",
    "Start timed reading",
    "Submit reading",
    "Abort reading",
    "Close study",
    "Save grades and analyze",
)


def test_recipe_requires_driver_pass() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    assert "scripts/verify_paired_hub.py" in text
    assert "PASS" in text
    assert "checks.json" in text
    assert "artifacts/paired-study/private" in text


def test_recipe_lists_every_button_path() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    for button in BUTTONS:
        assert button in text, f"paired.md must list {button}"


def test_recipe_requires_refusal_recovery() -> None:
    text = RECIPE.read_text(encoding="utf-8").lower()
    assert "recovery" in text
    assert "prepare next reading" in text


def test_driver_covers_every_button_and_evidence() -> None:
    text = DRIVER.read_text(encoding="utf-8")
    for button in BUTTONS:
        assert button in text, f"driver must click {button}"
    assert "checks.json" in text
    assert "paired-study/private" in text
    assert "familiar" in text.lower()
    assert "prepare next reading" in text.lower()
    assert os.access(DRIVER, os.X_OK), "driver must stay executable"


def test_skill_index_points_to_recipe() -> None:
    assert "paired.md" in INDEX.read_text(encoding="utf-8")
    assert "verify_paired_hub" in SKILL.read_text(encoding="utf-8")


HANDOFF = REPO / "scripts" / "handoff_study_hub.py"


def test_handoff_recipe_requires_supervised_handoff() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    assert "scripts/handoff_study_hub.py" in text
    assert "artifacts/handoff" in text
    lowered = text.lower()
    assert "pidfile" in lowered
    assert "exact url" in lowered
    assert "supervised" in lowered


def test_skill_drive_requires_handoff_record() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "handoff_study_hub" in text
    assert "artifacts/handoff" in text
    lowered = text.lower()
    assert "exact url" in lowered
    assert "pidfile" in lowered or "supervised" in lowered


def test_handoff_script_meets_contract() -> None:
    assert HANDOFF.is_file(), "handoff script is missing"
    text = HANDOFF.read_text(encoding="utf-8")
    assert "start_new_session" in text or "setsid" in text
    assert "nohup" in text.lower()
    assert "pidfile" in text.lower()
    assert "silent" in text.lower()
    assert "preconnect" in text.lower()
    assert "Prepare next reading" in text
    assert "preview" in text.lower()
    assert "session.json" in text
    assert "--stop" in text
    assert "artifacts/handoff" in text
    assert "pageerror" in text.lower()
    assert "PLAYWRIGHT_BROWSERS_PATH" in text
    assert "HANDOFF REFUSED" in text
    for field in ('"url"', '"port"', '"pid"', '"pidfile"', '"screenshot"', '"checks"'):
        assert field in text
    assert os.access(HANDOFF, os.X_OK), "handoff script must stay executable"
