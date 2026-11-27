from __future__ import annotations

import html
import re


def shown(entry: str | dict[str, str]) -> str:
    return entry if isinstance(entry, str) else entry["show"]


def shown_html(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))
