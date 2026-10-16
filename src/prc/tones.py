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


def key_pairs() -> list[tuple[str, str]]:
    """Key word and full color of each tone, in key order."""
    return [(word, color) for word, _, color, _ in TONES.values()]


def key_script() -> str:
    """The script tag that gives engine.js its key; engine.js has no key of its own."""
    return "<script>window.PRC_KEY=" + json.dumps(key_pairs()) + ";</script>"


def key_html() -> str:
    return (
        "<p class='pg-key' aria-label='Color key'>"
        + "".join(
            f"<span class='pg-key-i'><i style='background:{color}'></i>{html.escape(word)}</span>"
            for word, color in key_pairs()
        )
        + "</p>"
    )
