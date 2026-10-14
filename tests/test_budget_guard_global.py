"""The redline policy lives in exactly one place: the global skill."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GLOBAL_SKILL = Path.home() / ".agents" / "skills" / "budget-guard" / "SKILL.md"


def test_no_project_copy_redefines_the_threshold() -> None:
    hits = [
        path for path in (REPO / ".agents" / "skills").rglob("*.md")
        if "95 pct" in path.read_text(encoding="utf-8") or "REDLINE" in path.read_text(encoding="utf-8")
    ]
    assert hits == [], f"project skill redefines the redline: {hits}"


def test_global_skill_owns_the_policy() -> None:
    if not GLOBAL_SKILL.exists():
        pytest.skip("global budget-guard skill is not installed on this machine")
    text = GLOBAL_SKILL.read_text(encoding="utf-8")
    assert "95" in text and "resetsAt" in text and "budget-guard/v1" in text
