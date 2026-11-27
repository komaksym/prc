"""The color key: one meaning per color, shared by the video, the page and the infographic.

This module is the only owner of the key words and colors. The video engine reads
them from `key_script()`, the page header renders `key_html()`, and the
infographic brief names them, so a key word cannot differ between outputs.
"""

from __future__ import annotations

import html
import json

# Okabe-Ito shades. Each tone: key word, color name, full color, pale tint for fills behind dark text.
TONES: dict[str, tuple[str, str, str, str]] = {
    "problem": ("Problem", "vermillion", "#D55E00", "#FBE3D3"),
    "change": ("Change", "orange", "#E69F00", "#FDF0D2"),
    "part": ("Part", "sky blue", "#56B4E9", "#DDF0FB"),
    "proof": ("Proof", "bluish green", "#009E73", "#D5F1E8"),
    "context": ("Context", "grey", "#8A93A6", "#ECEEF2"),
}

# The same five hues, darkened so text and strokes read on a light page. Each look picks
# one ink set; the key words never change between inks.
LIGHT: dict[str, str] = {
    "problem": "#C2412D",
    "change": "#B7791F",
    "part": "#1F5FBF",
    "proof": "#2F7D4F",
    "context": "#6E675C",
}


def key_pairs(ink: str = "dark") -> list[tuple[str, str]]:
    """Key word and color of each tone, in key order, for the dark or the light ink."""
    if ink not in ("dark", "light"):
        raise ValueError(f"ink {ink!r} is not dark or light")
    return [
        (word, LIGHT[tone] if ink == "light" else color)
        for tone, (word, _, color, _) in TONES.items()
    ]


def key_script(ink: str = "dark") -> str:
    """The script tag that gives engine.js its key; engine.js has no key of its own."""
    return "<script>window.PRC_KEY=" + json.dumps(key_pairs(ink)) + ";</script>"


def key_html(ink: str = "dark") -> str:
    return (
        "<p class='pg-key' aria-label='Color key'>"
        + "".join(
            f"<span class='pg-key-i'><i style='background:{color}'></i>{html.escape(word)}</span>"
            for word, color in key_pairs(ink)
        )
        + "</p>"
    )
