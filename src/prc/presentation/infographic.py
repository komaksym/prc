from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

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
CONF_FLOOR = 70
WINDOW = 6
MAX_WORDS = 80
LINE_LIMIT = 96
DISCLOSURE = "Infographic drawn by AI. Words from prc."
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
LOOK_LABEL = "Look here first"
RISKY_LABEL = "Risky surfaces"
MAX_CALLS = 3
Role = Literal["headline", "node", "legend", "label", "chip", "row", "verdict", "note"]
RelationKind = Literal["call", "removed call", "maps", "becomes"]
LEGEND: dict[str, str] = {
    "call": "Arrows show new calls",
    "removed call": "Dashed arrows show removed calls",
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
READS = (("3", ""), ("11", ""), ("3", "150"), ("11", "150"))


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


def infobrief(
    m: dict[str, Any],
    brief: Any,
    board: dict[str, Any] | None,
    sources: dict[str, str] | None = None,
) -> InfographicBrief:
    title = card.headline(m, board)
    found = facts.compute_facts(m, brief)
    stats = found.stats
    ci = "no CI" if found.ci_state == "none" else f"CI {stats.ci_text} {found.ci_state}"
    files = f"{stats.files} {_label(stats.files, 'file', 'files')}"
    changed = (
        f"{stats.symbols_changed} "
        f"{_label(stats.symbols_changed, 'parsed symbol changed', 'parsed symbols changed')}"
    )
    links = structure(m, brief, board, sources)
    chips = (
        [files, changed, ci]
        if links
        else [
            files,
            changed,
            f"{stats.call_sites} "
            f"{_label(stats.call_sites, 'resolved call site', 'resolved call sites')}",
            f"{stats.tests_touched} "
            f"{_label(stats.tests_touched, 'test file touched', 'test files touched')}",
            ci,
            f"{stats.untested_total} parsed code without test evidence",
        ]
    )
    head: list[BriefLine] = [BriefLine("headline", title)]
    taken = {title, *chips}
    links = tuple(r for r in links if r.source not in taken and r.target not in taken)
    head += [BriefLine("node", text) for text in _nodes(links)]
    kinds = {r.kind for r in links}
    legend = dict(LEGEND)
    if kinds - {"call", "removed call"}:
        legend["call"] = MIXED_CALL_LEGEND
    head += [BriefLine("legend", text) for kind, text in legend.items() if kind in kinds]
    head += [BriefLine("chip", text) for text in chips]
    look = list(card.look_first(m, brief, 3, board))
    if look:
        head.append(BriefLine("label", LOOK_LABEL))
        head += [BriefLine("row", f"{e.name} in {e.path}") for e in look]
    surfaces = list(card.risky(m, brief))
    if surfaces:
        head.append(BriefLine("label", RISKY_LABEL))
        head += [BriefLine("row", f"{r.path}: {r.reason}") for r in surfaces]
    head.append(BriefLine("verdict", found.test_verdict))
    head.append(BriefLine("note", DISCLOSURE))
    trimmed = tuple(BriefLine(line.role, _trim_line(line.text)) for line in head)
    fitted = _fit_words(trimmed)
    return InfographicBrief(fitted[0].text, fitted, links)


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
        "REACH": diagram.REACH,
        "WINDOW": WINDOW,
    }


def brief_dict(br: InfographicBrief) -> dict[str, Any]:
    return {
        "allowed": sorted(allowed_words(br)),
        "disclosure": DISCLOSURE,
        "gate": gate_constants(),
        "lines": [{"role": line.role, "text": line.text} for line in br.lines],
        "profile": dict(PROFILE),
        "prompt_rules": list(PROMPT_RULES),
        "relations": [{"from": r.source, "to": r.target, "kind": r.kind} for r in br.relations],
        "title": br.title,
    }


def write_brief_json(br: InfographicBrief, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(brief_dict(br), indent=2, sort_keys=True)
    path.write_text(payload + "\n")
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


def _misread(
    token: str,
    box: Box | None,
    read: int,
    reads: tuple[OcrRead, ...],
    known: Callable[[str], bool],
    icon: IconKind | None,
) -> bool:
    """True when the other reads show this token is a misreading of an icon or an allowed word.

    Most other reads see an allowed word at the same place. Or the token has no digit and is
    short: one letter that looks like an icon (alone on its text line, or much taller than its
    neighbors), up to GLYPH_TOKEN letters in a square box much taller than its neighbors (a gear
    read as "god"), or a token that fewer than STABLE_READS confident reads (all reads, when
    there are fewer) see there.
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
    if _has_digit(token):
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
    for read in reads:
        icons = _icon_like(read.words)
        toks: list[str] = []
        confs: list[tuple[str, float, Box | None, IconKind | None]] = []
        for word in read.words:
            for tok in tokenize(word.text):
                toks.append(tok)
                confs.append((tok, word.conf, word.box, icons.get(id(word))))
        streams.append(toks)
        scored.append(confs)
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


def _read_mode(png: Path, psm: str, dpi: str) -> tuple[OcrWord, ...] | None:
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


def gate(png: Path, br: InfographicBrief) -> GateDecision:
    version = tesseract_version()
    if not version:
        return tool_decision()
    reads: list[OcrRead] = []
    failed: list[str] = []
    for psm, dpi in READS:
        mode = f"psm-{psm}-dpi-{dpi}" if dpi else f"psm-{psm}"
        words = _read_mode(png, psm, dpi)
        if words is None:
            failed.append(mode)
        else:
            reads.append(OcrRead(mode, words))
    if failed:
        return tool_decision(version, failed, tuple(reads))
    decision = score_ocr(tuple(reads), br, tesseract=version)
    if decision.verdict != "pass":
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
