from __future__ import annotations

import ast
import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, TypeGuard

import numpy as np
import numpy.typing as npt
from pygments import lex  # type: ignore[import-untyped]
from pygments.lexers import GoLexer  # type: ignore[import-untyped]
from pygments.token import Comment, String  # type: ignore[import-untyped]

from prc import facts
from prc.presentation import card, diagram

Box = tuple[int, int, int, int]
"""Left, top, width and height of an OCR word, in image pixels."""
STABLE_READS = 3
SHORT_TOKEN = 2
ICON_HEIGHT = 1.6
GLYPH_WIDTH = 1.2
GLYPH_TOKEN = 3
BULLET_HEIGHT = 0.75
CLIPPED_PREFIX = 3
CONF_FLOOR = 70
WINDOW = 6
MAX_WORDS = 80
PANELS_MAX_WORDS = 90
PANEL_WORDS = 6
MAX_PANELS = 4
MAX_PANEL_LINES = 4
MAX_FOOTER = 3
LINE_LIMIT = 96
# Uppercase PRC: Tesseract reads lowercase "prc" in small footer text as "pre",
# so the disclosure uses capitals the OCR reads reliably. The gate still accepts
# "pre" for older drawings (see _match).
DISCLOSURE = "Infographic drawn by AI. Words from PRC."
PROFILE = {
    "aspect": "16:9",
    "backend": "auto",
    "language": "en",
    "layout": "structural-breakdown",
    "style": "technical-schematic",
}
PROMPT_RULES = (
    "Show every line exactly once, spelled exactly.",
    "Add no other words, numbers, titles, legends or watermarks than the lines given.",
    "Put each node line alone in its own box.",
    "Join each related pair of node boxes with one straight arrow, source to target.",
    "Draw no other arrows or connector lines between boxes.",
    "Draw removed calls as dashed arrows and every other relation as a solid arrow.",
    "Leave a clear gap of plain canvas between boxes; do not let boxes touch.",
    "Icons are allowed beside text but contain no letters or digits.",
    "Keep icons out of every line that holds a number, so OCR reads numbers exactly.",
    "Draw every line as dark text on a light background.",
    "Keep the disclosure line visible.",
)
PANEL_RULES = (
    "Show every line exactly once, spelled exactly.",
    "Add no other words, numbers, titles or watermarks than the lines given.",
    "Put each panel header and its labels inside that panel.",
    "Draw each panel header on a plain solid header bar with no hatching or pattern behind the text.",
    "Color each panel with its named key color: a pale tint fill, a thick border and a header bar "
    "in that color, and use no other accent colors.",
    "Join each panel to the next with one arrow, left to right, and put no words on it.",
    "Draw no other arrows or connector lines.",
    "Icons are allowed inside panels but contain no letters, digits or digit-like shapes.",
    "Draw every line as dark text on a light background.",
    "Keep the disclosure line visible in the footer bar.",
)
# One meaning per color in Okabe-Ito shades; the video and the page use the same five.
# Each tone: key word, color name, full color, pale tint for fills behind dark text.
TONES: dict[str, tuple[str, str, str, str]] = {
    "problem": ("Problem", "vermillion", "#D55E00", "#FBE3D3"),
    "change": ("Change", "orange", "#E69F00", "#FDF0D2"),
    "part": ("Part", "sky blue", "#56B4E9", "#DDF0FB"),
    "proof": ("Proof", "bluish green", "#009E73", "#D5F1E8"),
    "context": ("Context", "grey", "#8A93A6", "#ECEEF2"),
}
_TONE_WORDS = (
    ("problem", ("before", "problem", "bug", "old", "risk", "gap", "broken", "fail")),
    ("proof", ("proof", "test", "tests", "result", "verified", "evidence")),
    ("change", ("change", "switch", "fix", "new", "after", "now", "how")),
    ("part", ("parts", "pieces", "components", "files", "flow", "map", "where")),
)


def guess_tone(title: str) -> str:
    """The tone a panel title names; a panel can set its own with "tone"."""
    words = set(tokenize(title))
    return next((tone for tone, cues in _TONE_WORDS if words & set(cues)), "context")


LOOK_LABEL = "Look here first"
RISKY_LABEL = "Risky surfaces"
MAX_CALLS = 3
Role = Literal[
    "headline",
    "subtitle",
    "node",
    "legend",
    "label",
    "chip",
    "row",
    "verdict",
    "panel",
    "item",
    "footer",
    "note",
]
Mode = Literal["source", "storyboard-flow", "panels"]
RelationKind = Literal["call", "removed call", "maps", "becomes", "flow"]
LEGEND: dict[str, str] = {
    "call": "Arrows show new calls",
    "removed call": "Dashed arrows show removed calls",
    "flow": "Arrows show the cited storyboard flow",
}
MIXED_CALL_LEGEND = "Arrows into code names show new calls"
IconKind = Literal["lone", "tall"]
Verdict = Literal["pass", "missing", "invented", "flat", "unreadable", "tool"]


@dataclass(frozen=True, slots=True)
class BriefLine:
    role: Role
    text: str


@dataclass(frozen=True, slots=True)
class Relation:
    """An arrow the drawing must show, between two node lines named by their text."""

    source: str
    target: str
    kind: RelationKind


@dataclass(frozen=True, slots=True)
class InfographicBrief:
    title: str
    lines: tuple[BriefLine, ...]
    relations: tuple[Relation, ...] = ()
    mode: Mode = "source"
    tones: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrWord:
    text: str
    conf: float
    box: Box | None = None


@dataclass(frozen=True, slots=True)
class OcrRead:
    mode: str
    words: tuple[OcrWord, ...]


@dataclass(frozen=True, slots=True)
class GateDecision:
    verdict: Verdict
    missing: tuple[tuple[str, tuple[str, ...]], ...]
    invented: tuple[tuple[str, float], ...]
    detail: dict[str, Any]


_SPLIT = re.compile(r"[^a-z0-9]+")
_CODE_WORD = re.compile(r"[._/:][A-Za-z0-9]|[a-z][A-Z]")
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# The "up2x" read runs Tesseract on a doubled image: small panel text that reads as
# low-confidence garbage at native resolution ("mapped" as "auppeth") reads cleanly
# with more pixels. _read_mode doubles the PNG with ffmpeg for this marker.
READS = (("3", ""), ("11", ""), ("3", "150"), ("11", "150"), ("3", "up2x"))


def tokenize(text: str) -> list[str]:
    bare = unicodedata.normalize("NFKD", text)
    flat = "".join(ch for ch in bare if not unicodedata.combining(ch))
    return [tok for tok in _SPLIT.split(flat.casefold()) if tok]


def _has_digit(token: str) -> bool:
    return any(ch.isdigit() for ch in token)


def _fold(token: str) -> str:
    return token.replace("l", "i")


def _match(word: str, tok: str, code: frozenset[str] = frozenset()) -> bool:
    if word == tok:
        return True
    if word not in code and _mixed(word):
        if _mixed(tok):
            return _ones(word) == _ones(tok)
        return "0" in word and word.replace("0", "o") == tok
    if word in code or _has_digit(word) or _has_digit(tok):
        return False
    if {word, tok} == {"prc", "pre"}:
        # Tesseract reads the footer "prc" as "pre" in most panels drawings.
        return True
    return _fold(word) == _fold(tok)


def _mixed(token: str) -> bool:
    return _has_digit(token) and any(ch.isalpha() for ch in token)


def _ones(token: str) -> str:
    """Fold the glyphs that OCR swaps for the digit one inside a letter-and-digit token."""
    return token.replace("l", "1").replace("i", "1").replace("o", "0")


def _label(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


def _trim_line(text: str) -> str:
    if len(text) <= LINE_LIMIT:
        return text
    cut = text[: LINE_LIMIT - 1].rsplit(" ", 1)[0].rstrip()
    return (cut or text[: LINE_LIMIT - 1]) + "…"


def _word_count(lines: tuple[BriefLine, ...]) -> int:
    return sum(len(tokenize(line.text)) for line in lines)


def _section_rows(kept: list[BriefLine], label: str) -> list[int]:
    try:
        start = next(
            i for i, line in enumerate(kept) if line.role == "label" and line.text == label
        )
    except StopIteration:
        return []
    rows: list[int] = []
    for i in range(start + 1, len(kept)):
        if kept[i].role != "row":
            break
        rows.append(i)
    return rows


def _drop_last_row(kept: list[BriefLine], label: str) -> bool:
    rows = _section_rows(kept, label)
    if not rows:
        return False
    if len(rows) == 1:
        start = next(
            i for i, line in enumerate(kept) if line.role == "label" and line.text == label
        )
        del kept[rows[0]]
        del kept[start]
    else:
        del kept[rows[-1]]
    return True


def _fit_words(lines: tuple[BriefLine, ...]) -> tuple[BriefLine, ...]:
    kept = list(lines)
    while _word_count(tuple(kept)) > MAX_WORDS:
        if _section_rows(kept, RISKY_LABEL):
            _drop_last_row(kept, RISKY_LABEL)
        elif _section_rows(kept, LOOK_LABEL):
            _drop_last_row(kept, LOOK_LABEL)
        elif (
            any(line.role == "node" for line in kept)
            and sum(line.role == "chip" for line in kept) > 1
        ):
            del kept[max(i for i, line in enumerate(kept) if line.role == "chip")]
        else:
            head = next(i for i, line in enumerate(kept) if line.role == "headline")
            room = MAX_WORDS - _word_count(tuple(line for i, line in enumerate(kept) if i != head))
            if room > 0:
                words = kept[head].text.split()
                while len(tokenize(" ".join(words))) > room:
                    words.pop()
                kept[head] = BriefLine("headline", " ".join(words).rstrip("…") + "…")
            else:
                chips = [i for i, line in enumerate(kept) if line.role == "chip"]
                if not chips:
                    raise ValueError("infographic verdict and disclosure exceed the word budget")
                del kept[chips[-1]]
    for label in (LOOK_LABEL, RISKY_LABEL):
        if not _section_rows(kept, label):
            kept = [line for line in kept if not (line.role == "label" and line.text == label)]
    return tuple(kept)


def _calls(m: dict[str, Any], brief: Any) -> list[Relation]:
    """Calls the PR adds or removes from production code, plus one node for its new test calls."""
    tests = facts.test_paths(m, brief)
    sym = {s["id"]: s for s in m.get("symbols", [])}

    def name(sid: str) -> str:
        return _trim_line(str(sym[sid]["qualname"]) if sid in sym else sid.rsplit("::", 1)[-1])

    def is_test(sid: str) -> bool:
        return sid in sym and sym[sid]["path"] in tests

    moved = [
        e
        for e in m.get("edges", [])
        if e.get("status") in ("added", "removed") and e.get("resolution") == "exact"
    ]
    prod = sorted(
        (e for e in moved if e["source"] in sym and not is_test(e["source"])),
        key=lambda e: (e["status"] != "added", e["source"], e["target"]),
    )[:MAX_CALLS]
    found = [
        Relation(
            name(e["source"]),
            name(e["target"]),
            "call" if e["status"] == "added" else "removed call",
        )
        for e in prod
    ]
    shown = {e["source"] for e in prod} | {e["target"] for e in prod}
    callers: dict[str, set[str]] = {}
    for e in moved:
        if e["status"] == "added" and is_test(e["source"]) and e["target"] in shown:
            callers.setdefault(e["target"], set()).add(e["source"])
    if callers:
        target = max(sorted(callers), key=lambda t: len(callers[t]))
        count = len(callers[target])
        found.append(
            Relation(f"{count} new test {_label(count, 'call', 'calls')}", name(target), "call")
        )
    return found


def _mapping(m: dict[str, Any], sources: dict[str, str] | None = None) -> list[Relation]:
    found: list[Relation] = []
    for file in m.get("files", []):
        if not file["path"].endswith(".go") or file["path"].endswith("_test.go"):
            continue
        source = (sources or {}).get(file["path"])
        if source is None:
            continue
        original = source.splitlines()
        rows = [
            line
            for hunk in file.get("hunks", [])
            for line in hunk["lines"]
            if line.get("new") is not None
        ]
        if any(
            not 0 < line["new"] <= len(original) or original[line["new"] - 1] != line["text"]
            for line in rows
        ):
            continue
        added = {line["new"] for line in rows if line.get("old") is None}
        if added:
            clean = "".join(
                "".join("\n" if char == "\n" else " " for char in value)
                if kind in Comment or kind in String
                else value
                for kind, value in lex(source, GoLexer(stripnl=False, ensurenl=False))
            )
            anchored = False
            call: str | None = None
            failure = False
            for number, code in enumerate(clean.splitlines(), 1):
                text = code.strip()
                if text.startswith("func "):
                    anchored = True
                    call, failure = None, False
                    continue
                if not anchored or not text:
                    continue
                match = re.fullmatch(
                    r"(?:[\w, ]+\berr\s*(?::=|=)|if\s+err\s*(?::=|=))\s*([\w.]+)"
                    r"\([^(){};]*\)(;\s*err\s*!=\s*nil\s*\{)?",
                    text,
                )
                if match:
                    call = match[1]
                    failure = match[2] is not None
                elif text == "if err != nil {" and call:
                    failure = True
                else:
                    error = re.fullmatch(r"return nil, &([A-Za-z]\w*Error)\{.*", text)
                    if (
                        error
                        and failure
                        and call
                        and number in added
                        and re.search(r"\bErr\s*:\s*err\b", text)
                    ):
                        found.append(Relation(call.rsplit(".", 1)[-1], error[1], "maps"))
                    call, failure = None, False
    return list(dict.fromkeys(found))[:MAX_CALLS]


def _doc_lines(file: dict[str, Any], side: str, source: str | None) -> dict[int, str]:
    if source is None:
        return {}
    original = source.splitlines()
    rows = [
        line
        for hunk in file.get("hunks", [])
        for line in hunk["lines"]
        if line.get(side) is not None
    ]
    if any(
        not 0 < line[side] <= len(original) or original[line[side] - 1] != line["text"]
        for line in rows
    ):
        return {}
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return {}
    changed = {line[side] for line in rows}
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and first.lineno in changed
        ):
            summary = first.value.value.splitlines()[0].replace("`", "").strip()
            if summary:
                found[node.lineno] = summary.removeprefix("Return the ")
    return found


def _before_after(m: dict[str, Any], sources: dict[str, str] | None = None) -> list[Relation]:
    for file in m.get("files", []):
        if not file["path"].endswith(".py"):
            continue
        source = sources or {}
        old = _doc_lines(file, "old", source.get("base:" + file["path"]))
        new = _doc_lines(file, "new", source.get(file["path"]))
        for symbol in m.get("symbols", []):
            if symbol["path"] != file["path"] or symbol["status"] != "modified":
                continue
            base, head = symbol.get("base_span"), symbol.get("span")
            if not base or not head:
                continue
            was, now = old.get(base[0]), new.get(head[0])
            if was and now and was != now:
                return [
                    Relation(
                        _trim_line(f"Before docs: {was}"),
                        _trim_line(f"After docs: {now}"),
                        "becomes",
                    )
                ]
    return []


def structure(
    m: dict[str, Any],
    brief: Any,
    board: dict[str, Any] | None,
    sources: dict[str, str] | None = None,
) -> tuple[Relation, ...]:
    found = _calls(m, brief) or _mapping(m, sources)
    found += _before_after(m, sources)
    return tuple(dict.fromkeys(r for r in found if r.source != r.target))


def _nodes(relations: tuple[Relation, ...]) -> list[str]:
    return list(dict.fromkeys(t for r in relations for t in (r.source, r.target)))


def _short(text: Any, limit: int = LINE_LIMIT) -> TypeGuard[str]:
    return isinstance(text, str) and bool(text.strip()) and len(text) <= limit


def _panels(selection: dict[str, Any]) -> InfographicBrief:
    """A titled-panel brief: exactly the authored headline, subtitle, panel lines and footer.

    The panels read left to right, so the arrows join panel i to panel i + 1 and no other pair.
    """
    head, sub = selection.get("headline"), selection.get("subtitle", "")
    panels, footer = selection.get("panels"), selection.get("footer", [])
    if not _short(head):
        raise ValueError("panels infographic needs a headline within the line limit")
    if not isinstance(sub, str) or len(sub) > LINE_LIMIT:
        raise ValueError("panels infographic subtitle needs text within the line limit")
    if not isinstance(panels, list) or not 2 <= len(panels) <= MAX_PANELS:
        raise ValueError(f"panels infographic needs 2 to {MAX_PANELS} panels")
    if (
        not isinstance(footer, list)
        or len(footer) > MAX_FOOTER
        or not all(_short(text) for text in footer)
    ):
        raise ValueError(f"panels infographic takes 0 to {MAX_FOOTER} footer items of short text")
    lines = [BriefLine("headline", head.strip())]
    if sub.strip():
        lines.append(BriefLine("subtitle", sub.strip()))
    headers: list[str] = []
    tones: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for n, panel in enumerate(panels, 1):
        title = panel.get("title") if isinstance(panel, dict) else None
        items = panel.get("lines") if isinstance(panel, dict) else None
        if not _short(title):
            raise ValueError(f"panel {n} needs a title")
        tone = panel.get("tone") or guess_tone(title)
        if tone not in TONES:
            raise ValueError(f"panel {n}: tone {tone!r} is not one of {', '.join(TONES)}")
        tones.append(tone)
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_PANEL_LINES:
            raise ValueError(f"panel {n} needs 1 to {MAX_PANEL_LINES} lines")
        for text in (title, *items):
            if not _short(text) or len(text.split()) > PANEL_WORDS:
                raise ValueError(f"panel {n}: {text!r} needs text of at most {PANEL_WORDS} words")
        title = title.strip()
        number = f"{n}."
        header = title if title.startswith(number + " ") else f"{number} {title}"
        identity = tuple(tokenize(header.removeprefix(number)))
        if identity in seen:
            raise ValueError("panels infographic needs unique panel titles")
        seen.add(identity)
        headers.append(header)
        lines.append(BriefLine("panel", header))
        lines += [BriefLine("item", text.strip()) for text in items]
    lines += [BriefLine("footer", text.strip()) for text in footer]
    lines += [BriefLine("legend", TONES[tone][0]) for tone in dict.fromkeys(tones)]
    lines.append(BriefLine("note", DISCLOSURE))
    words = _word_count(tuple(lines))
    if words > PANELS_MAX_WORDS:
        raise ValueError(
            f"panels infographic has {words} words with the disclosure; "
            f"use at most {PANELS_MAX_WORDS} words"
        )
    relations = tuple(Relation(one, other, "flow") for one, other in pairwise(headers))
    return InfographicBrief(head.strip(), tuple(lines), relations, "panels", tuple(tones))


def _story_flow(m: dict[str, Any], board: dict[str, Any]) -> tuple[Relation, ...]:
    from prc.explainer.check import verify_board

    selection = board["infographic"]
    if not isinstance(selection, dict) or selection.get("mode") != "storyboard-flow":
        raise ValueError("infographic mode must be storyboard-flow")
    index = selection.get("scene")
    scenes = board.get("scenes", [])
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(scenes):
        raise ValueError("infographic scene must name an existing groups scene")
    scene = scenes[index]
    if scene.get("type") != "groups":
        raise ValueError("infographic scene must be a groups scene")
    verify_board(copy.deepcopy(board), m)
    endpoints: dict[str, str] = {}
    owners: dict[str, str] = {}
    titles: set[tuple[str, ...]] = set()
    for group in scene["groups"]:
        title = group.get("title")
        if not isinstance(title, str) or not title.strip() or len(title) > LINE_LIMIT:
            raise ValueError("infographic group titles need nonempty text within the line limit")
        identity = tuple(tokenize(title))
        if not identity or identity in titles:
            raise ValueError("infographic groups need unique group titles after text normalization")
        titles.add(identity)
        owners[group["id"]] = title
        for item in group["items"]:
            if item["id"] in endpoints:
                raise ValueError("infographic groups need unique item IDs")
            endpoints[item["id"]] = title
    links: list[Relation] = []
    for cue in scene.get("cues", []):
        if cue.get("do") not in ("fly", "arrow"):
            continue
        ends = endpoints | owners if cue["do"] == "arrow" else endpoints
        source, target = ends.get(cue.get("from")), ends.get(cue.get("to"))
        if source is None or target is None or source == target:
            raise ValueError(
                "infographic fly and arrow cues must connect boxes in distinct named groups"
            )
        links.append(Relation(source, target, "flow"))
    unique = tuple(dict.fromkeys(links))
    if not unique or len(unique) > MAX_CALLS:
        raise ValueError(f"infographic scene needs 1 to {MAX_CALLS} distinct flow relationships")
    return unique


def infobrief(
    m: dict[str, Any],
    brief: Any,
    board: dict[str, Any] | None,
    sources: dict[str, str] | None = None,
) -> InfographicBrief:
    selection = board.get("infographic") if board is not None else None
    if isinstance(selection, dict) and selection.get("mode") == "panels":
        return _panels(selection)
    title = card.headline(m, board)
    found = facts.compute_facts(m, brief)
    story = board is not None and "infographic" in board
    links = (
        _story_flow(m, board)
        if board is not None and story
        else structure(m, brief, board, sources)
    )
    head: list[BriefLine] = [BriefLine("headline", title)]
    taken = {title}
    if story and any(r.source in taken or r.target in taken for r in links):
        raise ValueError("infographic headline must differ from its group titles")
    links = tuple(r for r in links if r.source not in taken and r.target not in taken)
    head += [BriefLine("node", text) for text in _nodes(links)]
    kinds = {r.kind for r in links}
    legend = dict(LEGEND)
    if kinds - {"call", "removed call"}:
        legend["call"] = MIXED_CALL_LEGEND
    head += [BriefLine("legend", text) for kind, text in legend.items() if kind in kinds]
    look = [] if story else list(card.look_first(m, brief, 3, board))
    if look:
        head.append(BriefLine("label", LOOK_LABEL))
        head += [BriefLine("row", f"{e.name} in {e.path}") for e in look]
    head.append(BriefLine("verdict", found.test_verdict))
    head.append(BriefLine("note", DISCLOSURE))
    trimmed = tuple(BriefLine(line.role, _trim_line(line.text)) for line in head)
    fitted = _fit_words(trimmed)
    if story and any(
        tokenize(line.text) == tokenize(fitted[0].text) for line in fitted if line.role == "node"
    ):
        raise ValueError("infographic headline must differ from its group titles after fitting")
    return InfographicBrief(fitted[0].text, fitted, links, "storyboard-flow" if story else "source")


def allowed_words(br: InfographicBrief) -> set[str]:
    words: set[str] = set()
    for line in br.lines:
        words.update(tokenize(line.text))
    return words


def joined_words(br: InfographicBrief) -> set[str]:
    joins: set[str] = set()
    for text in (line.text for line in br.lines):
        toks = tokenize(text)
        joins.update(
            one + other
            for one, other in pairwise(toks)
            if not (_has_digit(one) and _has_digit(other))
        )
    return joins


def code_words(br: InfographicBrief) -> frozenset[str]:
    found: set[str] = set()
    for text in (line.text for line in br.lines):
        for word in text.split():
            if _CODE_WORD.search(word.rstrip(".,;:")):
                found.update(tok for tok in tokenize(word) if not tok.isdigit())
    return frozenset(found)


def gate_constants() -> dict[str, Any]:
    return {
        "CONF_FLOOR": CONF_FLOOR,
        "CROSSINGS": diagram.CROSSINGS,
        "GAP": diagram.GAP,
        "LINE_RUN": diagram.LINE_RUN,
        "LINE_LIMIT": LINE_LIMIT,
        "MAX_WORDS": MAX_WORDS,
        "PANELS_MAX_WORDS": PANELS_MAX_WORDS,
        "REACH": diagram.REACH,
        "WINDOW": WINDOW,
    }


def _quoted(texts: list[str]) -> str:
    return ", ".join(f'"{text}"' for text in texts)


def prompt(br: InfographicBrief) -> str:
    """The image prompt for the baoyu-infographic technical profile, built from the brief only."""
    open_line = (
        "Create one landscape 16:9 infographic with the baoyu-infographic profile: "
        "technical-schematic style, structural-breakdown layout."
    )
    if br.mode != "panels":
        rows = [f'- {line.role}: "{line.text}"' for line in br.lines]
        arrows = [f'- "{r.source}" to "{r.target}" ({r.kind})' for r in br.relations]
        return (
            "\n".join(
                [
                    open_line,
                    "",
                    "Text: use only these lines, each exactly once and spelled exactly.",
                    *rows,
                ]
                + (["", "Arrows, source to target:", *arrows] if arrows else [])
                + ["", "Rules:", *(f"- {rule}" for rule in PROMPT_RULES)]
            )
            + "\n"
        )
    by_role = {
        role: [ln.text for ln in br.lines if ln.role == role]
        for role in ("subtitle", "footer", "legend", "note")
    }
    panels: list[tuple[str, list[str]]] = []
    for line in br.lines:
        if line.role == "panel":
            panels.append((line.text, []))
        elif line.role == "item":
            panels[-1][1].append(line.text)
    chain = "; ".join(f'"{r.source}" to "{r.target}"' for r in br.relations)
    text = [f'Headline: "{br.title}"']
    text += [f'Subtitle: "{sub}"' for sub in by_role["subtitle"]]
    tones = list(br.tones) or ["context"] * len(panels)
    for (header, items), tone in zip(panels, tones, strict=True):
        word, name, color, tint = TONES[tone]
        text.append(f'Panel header: "{header}" (color: {name} {color}, tint {tint})')
        text += [f'  - label: "{item}"' for item in items]
    text += [f'Footer: "{item}"' for item in by_role["footer"]]
    key = {TONES[t][0]: TONES[t] for t in tones}
    text += [
        f'Key: "{word}" beside the {key[word][1]} {key[word][2]} swatch'
        for word in by_role["legend"]
    ]
    text += [f'Disclosure: "{note}"' for note in by_role["note"]]
    layout = [
        "Style: a technical-schematic blueprint on pale white grid paper, with thin drafting "
        "lines, dimension ticks and corner marks. Color carries meaning: "
        + ", ".join(
            f"{name} {color} means {word.lower()}" for word, name, color, _ in TONES.values()
        )
        + ". Fill each panel with its pale tint, frame it with a thick border in its full color, "
        "and draw its header bar in a slightly deeper tint of the same color. Draw icons and "
        "arrows in the panel color. Keep every word dark navy on the light tints so it reads "
        "clearly.",
        "",
        "Layout:",
        "- Top: the headline in large bold letters, with the subtitle in smaller letters under it.",
        f"- Middle: {len(panels)} panels in one row, left to right. Each panel has a plain solid "
        "numbered header bar with its panel header, one simple icon with no letters, digits or "
        "digit-like shapes, and its labels as a short list.",
        f"- Between panels: one bold arrow from each panel to the next, left to right ({chain}). "
        "Put no words on the arrows.",
        "- Bottom: a footer bar across the full width that holds the footer items, the key (each "
        "key word beside a small square swatch of its color) and the disclosure.",
    ]
    return (
        "\n".join(
            [
                open_line,
                "",
                *layout,
                "",
                "Text: use only these lines, each exactly once and spelled exactly.",
                *text,
            ]
            + ["", "Rules:", *(f"- {rule}" for rule in PANEL_RULES)]
        )
        + "\n"
    )


def brief_dict(br: InfographicBrief) -> dict[str, Any]:
    return {
        "allowed": sorted(allowed_words(br)),
        "disclosure": DISCLOSURE,
        "gate": gate_constants(),
        "lines": [{"role": line.role, "text": line.text} for line in br.lines],
        "mode": br.mode,
        "profile": dict(PROFILE),
        "prompt": prompt(br),
        "prompt_rules": list(PANEL_RULES if br.mode == "panels" else PROMPT_RULES),
        "relations": [{"from": r.source, "to": r.target, "kind": r.kind} for r in br.relations],
        "title": br.title,
        "tones": list(br.tones),
    }


def write_brief_json(br: InfographicBrief, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(brief_dict(br), indent=2, sort_keys=True)
    path.write_text(payload + "\n")
    path.with_name("prompt.md").write_text(prompt(br))
    return path


def parse_tsv(tsv: str) -> tuple[OcrWord, ...]:
    words: list[OcrWord] = []
    for raw in tsv.splitlines():
        cols = raw.split("\t")
        if len(cols) != 12 or cols[0] != "5":
            continue
        text = cols[11].strip()
        if not text:
            continue
        try:
            conf = float(cols[10])
        except ValueError:
            continue
        try:
            left, top, width, height = (int(col) for col in cols[6:10])
        except ValueError:
            words.append(OcrWord(text, conf))
            continue
        box = (left, top, width, height) if width > 0 and height > 0 else None
        words.append(OcrWord(text, conf, box))
    return tuple(words)


def _same_place(one: Box, other: Box) -> bool:
    """Two boxes cover the same place when they share half of the smaller one."""
    wide = min(one[0] + one[2], other[0] + other[2]) - max(one[0], other[0])
    tall = min(one[1] + one[3], other[1] + other[3]) - max(one[1], other[1])
    if wide <= 0 or tall <= 0:
        return False
    return wide * tall * 2 >= min(one[2] * one[3], other[2] * other[3])


def _text_lines(words: tuple[OcrWord, ...]) -> list[list[OcrWord]]:
    """Words side by side at one height, with gaps no wider than the text is tall."""
    lines: list[list[OcrWord]] = []
    for word in sorted((w for w in words if w.box), key=lambda w: (w.box or (0, 0, 0, 0))[0]):
        box = word.box or (0, 0, 0, 0)
        for line in lines:
            last = line[-1].box or (0, 0, 0, 0)
            shared = min(box[1] + box[3], last[1] + last[3]) - max(box[1], last[1])
            gap = box[0] - (last[0] + last[2])
            tall = max(box[3], last[3])
            if shared * 2 >= min(box[3], last[3]) and -tall / 2 <= gap <= tall * 1.5:
                line.append(word)
                break
        else:
            lines.append([word])
    return lines


def _span(line: list[OcrWord]) -> Box:
    boxes = [w.box for w in line if w.box]
    left = min(b[0] for b in boxes)
    top = min(b[1] for b in boxes)
    right = max(b[0] + b[2] for b in boxes)
    bottom = max(b[1] + b[3] for b in boxes)
    return (left, top, right - left, bottom - top)


def _icon_like(words: tuple[OcrWord, ...]) -> dict[int, IconKind]:
    """Words alone on their text line ("lone"), or much taller than the nearest confident word
    on it ("tall"). Other icon readings on the line do not count as neighbors."""
    found: dict[int, IconKind] = {}
    for line in _text_lines(words):
        for word in line:
            box = word.box or (0, 0, 0, 0)
            rest = [w for w in line if w is not word and w.box]
            if not rest:
                found[id(word)] = "lone"
                continue
            sure = [w for w in rest if w.conf >= CONF_FLOOR and tokenize(w.text)] or rest

            def gap(other: OcrWord, box: Box = box) -> int:
                near = other.box or (0, 0, 0, 0)
                return max(near[0] - (box[0] + box[2]), box[0] - (near[0] + near[2]), 0)

            nearest = min(sure, key=gap).box or (0, 0, 0, 0)
            if box[3] >= ICON_HEIGHT * nearest[3]:
                found[id(word)] = "tall"
    return found


def region_streams(words: tuple[OcrWord, ...]) -> list[list[str]]:
    """Token streams for stacked text lines, so wrapped text in a column reads in order.

    Each text line links to the nearest text line under it that overlaps it sideways and starts
    within one line height. A line takes at most one line above it, so columns stay apart.
    """
    lines = sorted(_text_lines(words), key=lambda line: _span(line)[1])
    spans = [_span(line) for line in lines]
    below: dict[int, int] = {}
    taken: set[int] = set()
    for i, top in enumerate(spans):
        best: tuple[int, int] | None = None
        for j in range(i + 1, len(spans)):
            low = spans[j]
            gap = low[1] - (top[1] + top[3])
            sideways = min(top[0] + top[2], low[0] + low[2]) - max(top[0], low[0])
            if j in taken or sideways <= 0 or not -top[3] / 2 <= gap <= max(top[3], low[3]):
                continue
            if best is None or gap < best[0]:
                best = (gap, j)
        if best is not None:
            below[i] = best[1]
            taken.add(best[1])
    streams: list[list[str]] = []
    for start in (i for i in range(len(lines)) if i not in taken):
        chain: list[str] = []
        at: int | None = start
        while at is not None:
            chain += [tok for w in lines[at] for tok in tokenize(w.text)]
            at = below.get(at)
        streams.append(chain)
    return streams


def _covers(line_toks: list[str], ocr: list[str], code: frozenset[str] = frozenset()) -> bool:
    if not line_toks:
        return True
    dead: set[tuple[int, int]] = set()

    def steps(bi: int, pos: int) -> list[tuple[int, int]]:
        here = line_toks[bi]
        found: list[tuple[int, int]] = []
        if _match(here, ocr[pos], code):
            found.append((1, 1))
        if (
            here not in code
            and not _has_digit(here)
            and pos + 1 < len(ocr)
            and _match(here, ocr[pos] + ocr[pos + 1], code)
        ):
            found.append((1, 2))
        if bi + 1 < len(line_toks) and not (_has_digit(here) and _has_digit(line_toks[bi + 1])):
            next_word = line_toks[bi + 1]
            joined = here + next_word
            exact = here in code or next_word in code
            if joined == ocr[pos] or (not exact and _match(joined, ocr[pos], code)):
                found.append((2, 1))
        return found

    def rec(bi: int, oi: int) -> bool:
        if bi >= len(line_toks):
            return True
        if (bi, oi) in dead:
            return False
        positions = range(oi, len(ocr)) if bi == 0 else range(oi, min(oi + 1, len(ocr)))
        for pos in positions:
            for used, read in steps(bi, pos):
                if rec(bi + used, pos + read):
                    return True
        dead.add((bi, oi))
        return False

    return rec(0, 0)


def _seen_anywhere(token: str, streams: list[list[str]], code: frozenset[str]) -> bool:
    for ocr in streams:
        for i, other in enumerate(ocr):
            if _match(token, other, code):
                return True
            if (
                token not in code
                and not _has_digit(token)
                and i + 1 < len(ocr)
                and _match(token, other + ocr[i + 1], code)
            ):
                return True
    return False


def _allowed_neighbor(token: str, idx: int, ocr: list[str], allowed: set[str]) -> bool:
    left = ocr[idx - 1] + token if idx > 0 else ""
    right = token + ocr[idx + 1] if idx + 1 < len(ocr) else ""
    return _fold(left) in allowed or _fold(right) in allowed


def _rejoined(words: tuple[OcrWord, ...], prose: set[str]) -> set[int]:
    """Ids of words split by a visual break that rejoin to a permitted word.

    A hatched header bar can split CHANGE into "cha" and "nge" with a stray reading
    between them in page order, so stream adjacency misses the split. Words sitting
    side by side on one text line whose edge tokens rejoin to a prose word are the
    two halves of one drawn word.
    """
    found: set[int] = set()
    for line in _text_lines(words):
        for first, second in pairwise(line):
            left = tokenize(first.text)
            right = tokenize(second.text)
            if left and right and _fold(left[-1] + right[0]) in prose:
                found.add(id(first))
                found.add(id(second))
    return found


def _misread(
    token: str,
    box: Box | None,
    read: int,
    reads: tuple[OcrRead, ...],
    known: Callable[[str], bool],
    icon: IconKind | None,
) -> bool:
    """True when the other reads show this token is a misreading of an icon or an allowed word.

    Most other reads see an allowed word at the same place. Or the token is short: one letter
    that looks like an icon (alone on its text line, or much taller than its neighbors), up to
    GLYPH_TOKEN letters in a square box much taller than its neighbors (a gear read as "god"),
    a lone single digit from an icon region (a checkbox grid read as "4"), or a token that
    fewer than STABLE_READS confident reads (all reads, when there are fewer) see there.
    Longer digit codes and tall digit strokes stay invented, as does a digit every read sees.
    """
    if box is None:
        return False
    others = [r for i, r in enumerate(reads) if i != read]

    def at_place(r: OcrRead, floor: float = 0.0) -> list[str]:
        return [
            t
            for w in r.words
            if w.box and w.conf >= floor and _same_place(box, w.box)
            for t in tokenize(w.text)
        ]

    agree = sum(
        1 for r in others if token not in at_place(r) and any(known(t) for t in at_place(r))
    )
    if len(others) >= 2 and agree * 2 > len(others):
        return True
    digit = _has_digit(token)
    if not digit and len(token) >= CLIPPED_PREFIX:
        # One read clips a drawn word ("PROOF" read as "PROO") that another read sees whole.
        whole = (t for r in others for t in at_place(r, CONF_FLOOR))
        if any(t != token and t.startswith(token) and known(t) for t in whole):
            return True
    if digit and (len(token) > 1 or icon == "tall"):
        # Longer codes stay exact, and a tall digit-like icon stroke beside text
        # (the "9" in the square-glyph tests) stays invented: only a lone single
        # digit can be an icon-region reading.
        return False
    seen = 1 + sum(1 for r in others if token in at_place(r, CONF_FLOOR))
    if seen == len(reads):
        return False
    if icon == "tall" and len(token) <= GLYPH_TOKEN and _glyph(box):
        return True
    if len(token) > SHORT_TOKEN:
        return False
    if len(token) == 1 and icon is not None:
        return True
    return seen < min(STABLE_READS, len(reads))


def _glyph(box: Box) -> bool:
    """A box about as wide as it is tall. Printed words of two or more letters are wider."""
    return box[2] <= GLYPH_WIDTH * box[3]


def _bullets(words: tuple[OcrWord, ...], known: Callable[[str], bool]) -> set[int]:
    """Ids of list bullet dots read as one letter (a "●" read as "e" in every mode).

    The dot is the first confident word on its text line, a square box at most
    BULLET_HEIGHT of the height of the word after it, and that word is a brief word.
    """
    found: set[int] = set()
    for line in _text_lines(words):
        sure = [w for w in line if w.conf >= CONF_FLOOR and tokenize(w.text)]
        if len(sure) < 2:
            continue
        dot, item = sure[0], sure[1]
        toks = tokenize(dot.text)
        after = tokenize(item.text)
        if (
            dot.box
            and item.box
            and len(toks) == 1
            and len(toks[0]) == 1
            and not _has_digit(toks[0])
            and _glyph(dot.box)
            and dot.box[3] <= BULLET_HEIGHT * item.box[3]
            and known(after[0])
        ):
            found.add(id(dot))
    return found


def score_ocr(
    reads: tuple[OcrRead, ...], br: InfographicBrief, tesseract: str = ""
) -> GateDecision:
    allowed = allowed_words(br)
    code = code_words(br)
    prose = {_fold(word) for word in allowed if word not in code and not _has_digit(word)}
    joins = joined_words(br)
    pairs = {
        one + other: (one, other)
        for line in br.lines
        for one, other in pairwise(tokenize(line.text))
        if not (_has_digit(one) and _has_digit(other))
    }
    followers: dict[str, set[str]] = {}
    for line in br.lines:
        for left, right in pairwise(tokenize(line.text)):
            followers.setdefault(left, set()).add(right)

    def canonical(tok: str) -> str | None:
        if tok in allowed:
            return tok
        return next((word for word in sorted(allowed) if _match(word, tok, code)), None)

    def joined(tok: str) -> tuple[str, str] | None:
        return next((parts for word, parts in pairs.items() if _match(word, tok, code)), None)

    def known(tok: str) -> bool:
        return tok in joins or canonical(tok) is not None or joined(tok) is not None

    streams: list[list[str]] = []
    scored: list[list[tuple[str, float, Box | None, IconKind | None]]] = []
    owners: list[list[int]] = []
    for read in reads:
        icons = _icon_like(read.words)
        toks: list[str] = []
        confs: list[tuple[str, float, Box | None, IconKind | None]] = []
        held: list[int] = []
        for word in read.words:
            for tok in tokenize(word.text):
                toks.append(tok)
                confs.append((tok, word.conf, word.box, icons.get(id(word))))
                held.append(id(word))
        streams.append(toks)
        scored.append(confs)
        owners.append(held)
    rejoined = [_rejoined(read.words, prose) for read in reads]
    bullets = [_bullets(read.words, known) for read in reads]
    detail: dict[str, Any] = {
        "allowed": len(allowed),
        "brief_lines": len(br.lines),
        "constants": gate_constants(),
        "modes": {read.mode: len(streams[i]) for i, read in enumerate(reads)},
        "failed_modes": [],
        "tesseract": tesseract,
    }
    if not any(conf >= CONF_FLOOR for stream in scored for _, conf, _, _ in stream):
        return GateDecision("unreadable", (), (), detail)
    invented: dict[str, float] = {}
    for idx, stream in enumerate(scored):
        ocr = streams[idx]
        for pos, (tok, conf, box, icon) in enumerate(stream):
            if conf < CONF_FLOOR:
                continue
            if known(tok):
                good = True
            elif _has_digit(tok):
                good = False
            else:
                good = _allowed_neighbor(tok, pos, ocr, prose)
            if not good:
                good = owners[idx][pos] in rejoined[idx]
            if not good:
                good = owners[idx][pos] in bullets[idx]
            if not good:
                good = _misread(tok, box, idx, reads, known, icon)
            if not good:
                invented[tok] = max(invented.get(tok, conf), conf)
    expected = Counter(tok for line in br.lines for tok in tokenize(line.text))
    counts: list[Counter[str]] = []
    totals: list[Counter[str]] = []
    places: dict[str, list[Box]] = {}
    confidences: dict[str, float] = {}
    for stream in scored:
        count: Counter[str] = Counter()
        total: Counter[str] = Counter()
        pos = 0
        while pos < len(stream):
            tok, conf, box, _ = stream[pos]
            counted: tuple[str, ...] = ()
            whole = (
                canonical(tok + stream[pos + 1][0])
                if pos + 1 < len(stream) and not _has_digit(tok + stream[pos + 1][0])
                else None
            )
            if whole is not None and (tok, stream[pos + 1][0]) in pairs.values():
                next_token = canonical(stream[pos + 2][0]) if pos + 2 < len(stream) else None
                if next_token not in followers.get(whole, set()):
                    whole = None
            if whole is not None:
                counted = (whole,)
                conf = min(conf, stream[pos + 1][1])
                pos += 1
            elif (match := canonical(tok)) is not None:
                counted = (match,)
            elif parts := joined(tok):
                counted = parts
            total.update(counted)
            if box is not None:
                for token in counted:
                    seen = places.setdefault(token, [])
                    if not any(_same_place(box, other) for other in seen):
                        seen.append(box)
            if conf >= CONF_FLOOR:
                count.update(counted)
                for token in counted:
                    confidences[token] = max(confidences.get(token, conf), conf)
            pos += 1
        counts.append(count)
        totals.append(total)
    for tok, limit in expected.items():
        surplus = sum(count[tok] > limit for count in counts)
        if surplus >= min(STABLE_READS, len(reads)):
            invented[tok] = confidences[tok]
    covered: list[list[str]] = []
    regions: list[list[str]] = []
    for idx, reading in enumerate(reads):
        kept = []
        pos = 0
        for word in reading.words:
            toks = tokenize(word.text)
            if any(
                known(tok)
                or _allowed_neighbor(tok, pos + offset, streams[idx], prose)
                or id(word) in rejoined[idx]
                or (
                    word.conf >= CONF_FLOOR and not _misread(tok, word.box, idx, reads, known, None)
                )
                for offset, tok in enumerate(toks)
            ):
                kept.append(word)
            pos += len(toks)
        covered.append([tok for word in kept for tok in tokenize(word.text)])
        regions.extend(region_streams(tuple(kept)))
    missing: list[tuple[str, tuple[str, ...]]] = []
    for line in br.lines:
        ltoks = tokenize(line.text)
        enough = all(
            max(len(places.get(tok, [])), max((count[tok] for count in totals), default=0))
            >= expected[tok]
            for tok in ltoks
            if expected[tok] > 1
        )
        if enough and any(_covers(ltoks, ocr, code) for ocr in (*covered, *regions)):
            continue
        lost = tuple(t for t in ltoks if not _seen_anywhere(t, streams, code))
        missing.append((line.text, lost if lost else tuple(ltoks)))
    if invented:
        return GateDecision("invented", tuple(missing), tuple(sorted(invented.items())), detail)
    if missing:
        return GateDecision("missing", tuple(missing), (), detail)
    return GateDecision("pass", (), (), detail)


def tesseract_version() -> str:
    if shutil.which("tesseract") is None:
        return ""
    try:
        done = subprocess.run(
            ["tesseract", "--version"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return ""
    if done.returncode != 0:
        return ""
    return done.stdout.splitlines()[0].strip() if done.stdout else ""


def tool_decision(
    tesseract: str = "", failed_modes: list[str] | None = None, reads: tuple[OcrRead, ...] = ()
) -> GateDecision:
    detail: dict[str, Any] = {
        "allowed": 0,
        "brief_lines": 0,
        "constants": gate_constants(),
        "modes": {read.mode: len(read.words) for read in reads},
        "failed_modes": failed_modes or [],
        "tesseract": tesseract,
    }
    return GateDecision("tool", (), (), detail)


def _doubled_png(png: Path) -> Path | None:
    """A doubled copy of the image for the up2x read, or None without ffmpeg."""
    if shutil.which("ffmpeg") is None:
        return None
    fd, tmp = tempfile.mkstemp(prefix="prc-up2x-", suffix=".png")
    os.close(fd)
    try:
        done = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(png), "-vf", "scale=iw*2:ih*2", tmp],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        Path(tmp).unlink(missing_ok=True)
        return None
    if done.returncode != 0:
        Path(tmp).unlink(missing_ok=True)
        return None
    return Path(tmp)


def _read_mode(png: Path, psm: str, dpi: str) -> tuple[OcrWord, ...] | None:
    if dpi == "up2x":
        doubled = _doubled_png(png)
        if doubled is None:
            return None
        try:
            words = _read_mode(doubled, psm, "")
        finally:
            doubled.unlink(missing_ok=True)
        if words is None:
            return None
        # All gate geometry (places, locate, the ink mask) runs in base-image
        # pixels, so scale the doubled boxes back before returning the read.
        return tuple(
            word if word.box is None else OcrWord(word.text, word.conf, _halve(word.box))
            for word in words
            if word.box is None or _halve(word.box) is not None
        )
    args = ["tesseract", str(png), "stdout", "--psm", psm]
    if dpi:
        args += ["--dpi", dpi]
    try:
        done = subprocess.run([*args, "tsv"], capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None
    if done.returncode != 0:
        return None
    return parse_tsv(done.stdout)


def read_modes(png: Path) -> tuple[tuple[OcrRead, ...], list[str]]:
    """One OCR read per entry in READS, plus the modes that failed to read."""
    reads: list[OcrRead] = []
    failed: list[str] = []
    for psm, dpi in READS:
        if dpi == "up2x":
            mode = f"psm-{psm}-up2x"
        elif dpi:
            mode = f"psm-{psm}-dpi-{dpi}"
        else:
            mode = f"psm-{psm}"
        words = _read_mode(png, psm, dpi)
        if words is None:
            failed.append(mode)
        else:
            reads.append(OcrRead(mode, words))
    return tuple(reads), failed


def gate(png: Path, br: InfographicBrief) -> GateDecision:
    version = tesseract_version()
    if not version:
        return tool_decision()
    reads, failed = read_modes(png)
    if failed:
        return tool_decision(version, failed, reads)
    decision = score_ocr(tuple(reads), br, tesseract=version)
    if decision.verdict != "pass":
        return decision
    if br.mode == "panels":
        # Panel frames hold many lines each, so the ink test between two text lines is not
        # reliable there; the gate checks the words and a reviewer checks the arrows by eye.
        return decision
    if not br.relations:
        return GateDecision(
            "flat", (), (), decision.detail | {"reason": "no code relationships available"}
        )
    rgb = diagram.decode_rgb(png)
    if rgb is None:
        return tool_decision(version, ["ffmpeg"], tuple(reads))
    return score_drawing(decision, check_relations(rgb, tuple(reads), br))


def locate(text: str, reads: tuple[OcrRead, ...], code: frozenset[str]) -> list[tuple[Box, int]]:
    """Every place a text line, or two stacked text lines, shows the whole line, smallest first.

    Each place is a box and the height of its shortest word.
    """
    toks = tokenize(text)
    hits: list[tuple[Box, int]] = []
    for read in reads:
        lines = _text_lines(tuple(w for w in read.words if _spells(w, toks, code)))
        groups = list(lines)
        for upper in lines:
            top = _span(upper)
            for lower in lines:
                low = _span(lower)
                gap = low[1] - (top[1] + top[3])
                sideways = min(top[0] + top[2], low[0] + low[2]) - max(top[0], low[0])
                if lower is not upper and sideways > 0 and 0 <= gap <= max(top[3], low[3]):
                    groups.append(upper + lower)
        hits += [
            (_span(group), min((w.box or (0, 0, 0, 0))[3] for w in group))
            for group in groups
            if _covers(toks, [t for w in group for t in tokenize(w.text)], code)
        ]
    places: list[tuple[Box, int]] = []
    for hit in sorted(hits, key=lambda hit: hit[0][2] * hit[0][3]):
        if not any(_same_place(hit[0], kept[0]) for kept in places):
            places.append(hit)
    return places


def _spells(word: OcrWord, toks: list[str], code: frozenset[str]) -> bool:
    """A confident word, or a weaker reading whose every token spells a word sought exactly.

    Weak readings get no fuzzy match: a line drawn into a word ("----apply") must not count.
    """
    found = tokenize(word.text)
    if not found:
        return False
    if word.conf >= CONF_FLOOR:
        return True
    return all(
        any(
            tok == want or (_mixed(want) and _mixed(tok) and _ones(want) == _ones(tok))
            for want in toks
        )
        for tok in found
    )


def check_relations(
    rgb: npt.NDArray[np.float32], reads: tuple[OcrRead, ...], br: InfographicBrief
) -> list[dict[str, Any]]:
    """For each relation, whether drawn ink joins the two node lines in separate shapes."""
    code = code_words(br)
    allowed = allowed_words(br)
    text = [
        w.box for read in reads for w in read.words if w.box and _spells(w, sorted(allowed), code)
    ]
    labels = diagram.label(diagram.ink_mask(rgb, text))
    found: list[dict[str, Any]] = []
    for rel in br.relations:
        sources, targets = locate(rel.source, reads, code), locate(rel.target, reads, code)
        row: dict[str, Any] = {"from": rel.source, "to": rel.target, "kind": rel.kind}
        if not sources or not targets:
            found.append({**row, "drawn": False, "located": False})
            continue
        tried = [
            diagram.link(labels, one, other, min(tall, low))
            for one, tall in sources
            for other, low in targets
            if not _same_place(one, other)
        ]
        if not tried:
            found.append({**row, "drawn": False, "located": False})
            continue
        seen = max(tried, key=lambda k: (k.drawn, k.run, k.crossings))
        found.append(
            {
                **row,
                "run": seen.run,
                "crossings": seen.crossings,
                "drawn": seen.drawn,
                "located": True,
                "shared": seen.shared,
            }
        )
    return found


def score_drawing(decision: GateDecision, links: list[dict[str, Any]]) -> GateDecision:
    """A brief with relations passes only when the image draws every one of them."""
    detail = {**decision.detail, "relations": links}
    verdict: Verdict = "pass" if all(link["drawn"] for link in links) else "flat"
    return GateDecision(verdict, decision.missing, decision.invented, detail)


def read_png(path: Path) -> bytes:
    raw = path.read_bytes()
    if not raw.startswith(_PNG_MAGIC):
        raise ValueError(f"infographic must be a PNG: {path}")
    return raw


def _halve(box: Box) -> Box | None:
    """A doubled-read word box back in base-image pixels, or None when it vanishes."""
    left, top, width, height = (part // 2 for part in box)
    if width <= 0 or height <= 0:
        return None
    return (left, top, width, height)
