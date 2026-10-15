"""Guard keeps the notes-hub browser pass required for hub handoffs."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RECIPE = REPO / ".agents" / "skills" / "verify" / "features" / "notes.md"
DRIVER = REPO / "scripts" / "verify_notes_hub.py"
INDEX = REPO / ".agents" / "skills" / "verify" / "features" / "README.md"
SKILL = REPO / ".agents" / "skills" / "verify" / "SKILL.md"
CONTROLS = (
    "GitHub",
    "infographic",
    "video",
    "page.html",
    "notes box",
)


def test_recipe_requires_driver_pass() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    assert "scripts/verify_notes_hub.py" in text
    assert "PASS" in text
    assert "checks.json" in text
    assert "paired-study/private" not in text


def test_recipe_lists_every_pr_control() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    for control in CONTROLS:
        assert control in text, f"notes.md must list {control}"


def test_recipe_forbids_old_study_content() -> None:
    text = RECIPE.read_text(encoding="utf-8").lower()
    assert "no questions" in text or "questions" in text
    assert "notes.json" in text
    assert "updated_at" in text


def test_driver_covers_every_control_and_evidence() -> None:
    text = DRIVER.read_text(encoding="utf-8")
    for control in ("github", "infographic", "currentTime", "page", "notes"):
        assert control.lower() in text.lower(), f"driver must cover {control}"
    assert "checks.json" in text
    assert "cleanup" in text.lower()
    assert "agent-browser" in text
    assert os.access(DRIVER, os.X_OK), "driver must stay executable"


def test_skill_index_points_to_recipe() -> None:
    assert "notes.md" in INDEX.read_text(encoding="utf-8")
    assert "verify_notes_hub" in SKILL.read_text(encoding="utf-8")


HANDOFF = REPO / "scripts" / "handoff_study_hub.py"


def test_handoff_recipe_requires_supervised_handoff() -> None:
    text = RECIPE.read_text(encoding="utf-8")
    assert "scripts/handoff_study_hub.py" in text
    assert "artifacts/study-v3/handoff/notes" in text
    lowered = text.lower()
    assert "pidfile" in lowered
    assert "exact url" in lowered
    assert "supervised" in lowered


def test_skill_drive_requires_handoff_record() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "handoff_study_hub" in text
    assert "artifacts/study-v3/handoff/notes" in text
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
    assert "notes.json" in text
    assert "notes-review" in text
    assert "--stop" in text
    assert "artifacts/study-v3/handoff/notes" in text
    assert "agent-browser" in text
    assert "HANDOFF REFUSED" in text
    for field in ('"url"', '"port"', '"pid"', '"pidfile"', '"screenshot"', '"checks"'):
        assert field in text
    assert os.access(HANDOFF, os.X_OK), "handoff script must stay executable"
