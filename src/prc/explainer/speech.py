"""Code names in narration, rewritten into words a voice can say.

Captions keep the code; only the voice hears the rewrite. Kokoro reads
`s2e3` as "ess ee" and `ErrNotExist` as "earn not exist", so each code
token is split into its parts before synthesis.
"""

from __future__ import annotations

import re

EXTENSIONS = frozenset(
    [
        "c",
        "cpp",
        "css",
        "go",
        "h",
        "html",
        "java",
        "js",
        "json",
        "jsx",
        "kt",
        "md",
        "py",
        "rb",
        "rs",
        "sh",
        "sql",
        "swift",
        "toml",
        "ts",
        "tsx",
        "yaml",
        "yml",
    ]
)
ABBREVIATIONS = {"err": "error", "ctx": "context", "cfg": "config", "msg": "message"}

WORD = re.compile(r"(?<![\w.])[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*")
PART = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|[A-Z]+|\d+")
COUNT = re.compile(r"\d+(?:st|nd|rd|th|s|x|k|m|ms|px|kb|mb|gb|h|d)?", re.IGNORECASE)


def _is_file(word: str) -> bool:
    stem, dot, ext = word.rpartition(".")
    return bool(dot and stem and ext in EXTENSIONS)


def is_code(word: str) -> bool:
    if "." in word:
        return _is_file(word)
    if "_" in word.strip("_") or re.search(r"[a-z][A-Z]", word):
        return True
    return bool(re.search(r"[A-Za-z]", word) and re.search(r"\d", word)) and not COUNT.fullmatch(
        word
    )


def _say_part(part: str) -> str:
    if part.isdigit() or (part.isupper() and len(part) > 1):
        return part
    if len(part) == 1:
        return part.upper()
    return ABBREVIATIONS.get(part.lower(), part.lower())


def say_token(word: str) -> str:
    if _is_file(word):
        stem, _, ext = word.rpartition(".")
        name = " dot ".join(say_token(p) if is_code(p) else p for p in stem.split("."))
        return f"{name} dot {' '.join(ext.upper()) if len(ext) <= 3 else ext}"
    return " ".join(_say_part(p) for chunk in word.split("_") for p in PART.findall(chunk))


def code_tokens(text: str) -> list[str]:
    """Code tokens in narration text, in spoken order."""
    return [w for w in WORD.findall(text.replace("`", "")) if is_code(w)]


def speakable(text: str) -> str:
    """Narration text with every code token rewritten into words. Stable when reapplied."""
    return WORD.sub(lambda m: say_token(m[0]) if is_code(m[0]) else m[0], text.replace("`", ""))
