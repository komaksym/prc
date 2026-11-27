"""Looks: one CSS file per look on top of the dark engine and page CSS.

This module is the only owner of the look names. A look changes paper, ink, type and
card shape. It never changes the storyboard, the narration, the timing or the color
meanings, so every look of one pull request tells the same story.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"


@dataclass(frozen=True)
class Look:
    name: str
    label: str
    ink: str  # "dark" or "light": which tones ink set the key uses

    def css(self) -> str:
        """The look's CSS; the dark baseline adds nothing to engine.css and page.css."""
        if self.name == "dark":
            return ""
        return (ASSETS / "themes" / f"{self.name}.css").read_text()


LOOKS: dict[str, Look] = {
    look.name: look
    for look in (
        Look("dark", "Baseline (dark)", "dark"),
        Look("paper", "Control on paper", "light"),
        Look("essay", "Essay", "light"),
        Look("labsheet", "Lab sheet", "light"),
        Look("workspace", "Workspace", "light"),
    )
}


def look(name: str) -> Look:
    if name not in LOOKS:
        raise ValueError(f"look {name!r} is not one of {', '.join(LOOKS)}")
    return LOOKS[name]
