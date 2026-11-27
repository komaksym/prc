"""Code names in narration, rewritten into words a voice can say.

Captions keep the code; only the voice hears the rewrite. Kokoro reads
`s2e3` as "ess ee" and `ErrNotExist` as "earn not exist", so each code
token is split into its parts before synthesis. A comma after the first word
keeps its last sound ("find next" ran together into "fine next"), and verbs
Kokoro reads in the past tense get a respelling ("read" became "red").
The listening gate expects the plain written words, from `heard_as`.
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
SOUNDS = {"read": "reed"}
TOKEN_SOUNDS = {"LinkedIn": "linked inn"}

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


def _words(word: str) -> list[str]:
    return [_say_part(p) for chunk in word.split("_") for p in PART.findall(chunk)]


def say_token(word: str, voice: bool = True) -> str:
    """A code token as words: with pauses and respellings for the voice, or as written."""
    if voice and word in TOKEN_SOUNDS:
        return TOKEN_SOUNDS[word]
    if _is_file(word):
        stem, _, ext = word.rpartition(".")
        name = " dot ".join(say_token(p, voice) if is_code(p) else p for p in stem.split("."))
        return f"{name} dot {' '.join(ext.upper()) if len(ext) <= 3 else ext}"
    words = _words(word)
    if not voice:
        return " ".join(words)
    words = [SOUNDS.get(w, w) for w in words]
    if (
        "_" not in word
        and len(words) > 1
        and len(words[0]) > 1
        and words[0].isalpha()
        and words[1].isalpha()
    ):
        words[0] += ","
    return " ".join(words)


def heard_as(token: str) -> str:
    """How a listener writes a code token down: the words, without voice respellings."""
    return say_token(token, voice=False)


def code_tokens(text: str) -> list[str]:
    """Code tokens in narration text, in spoken order."""
    return [w for w in WORD.findall(text.replace("`", "")) if is_code(w)]


def speakable(text: str) -> str:
    """Narration text with every code token rewritten into words. Stable when reapplied."""
    return WORD.sub(lambda m: say_token(m[0]) if is_code(m[0]) else m[0], text.replace("`", ""))
