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
