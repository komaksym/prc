from __future__ import annotations

import json
import re
import shutil
import subprocess
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

import numpy as np
import numpy.typing as npt

from prc import facts
from prc.presentation import card, diagram

Box = tuple[int, int, int, int]
"""Left, top, width and height of an OCR word, in image pixels."""
STABLE_READS = 3
SHORT_TOKEN = 2
ICON_HEIGHT = 1.6
CONF_FLOOR = 70
WORD_SIM = 0.80
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
    "Add no other words, numbers, titles, legends or watermarks.",
    "Icons and decorations contain no letters or digits.",
    "Draw every line as plain dark text on a light background.",
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


def _lev(one: str, other: str) -> int:
    if one == other:
        return 0
    prev = list(range(len(other) + 1))
    for i, ca in enumerate(one, 1):
        cur = [i]
        for j, cb in enumerate(other, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _ratio(one: str, other: str) -> float:
    total = len(one) + len(other)
    if total == 0:
        return 1.0
    return (total - _lev(one, other)) / total


def _fold(token: str) -> str:
    return token.replace("l", "i")


def _match(word: str, tok: str, code: frozenset[str] = frozenset()) -> bool:
    if word == tok:
        return True
    if word in code or _has_digit(word) or _has_digit(tok):
        return False
    if _fold(word) == _fold(tok):
        return True
    if len(word) <= 3 or len(tok) <= 3:
        return False
    return _ratio(word, tok) >= WORD_SIM


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

    moved = [e for e in m.get("edges", []) if e.get("status") in ("added", "removed")]
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


def _group_scenes(board: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [s for s in (board or {}).get("scenes", []) if s.get("type") == "groups"]


def _mapping(board: dict[str, Any] | None) -> list[Relation]:
    """Board groups grounded in code: each group's title maps to its item."""
    for scene in _group_scenes(board):
        found = [
            Relation(_trim_line(g["title"]), _trim_line(g["items"][0]["text"]), "maps")
            for g in scene["groups"]
            if g.get("ground") and g.get("items") and g["items"][0]["text"] != g["title"]
        ]
        if found:
            return found[:MAX_CALLS]
    return []


def _before_after(board: dict[str, Any] | None) -> list[Relation]:
    """The first group that changes between two consecutive board group scenes."""
    scenes = _group_scenes(board)
    for old, new in pairwise(scenes):
        before = {g["id"]: g for g in old["groups"]}
        for g in new["groups"]:
            prev = before.get(g["id"])
            if prev is None or prev["title"] != g["title"]:
                continue
            was = " ".join(item["text"] for item in prev["items"])
            now = " ".join(item["text"] for item in g["items"])
            if was != now:
                title = g["title"]
                return [
                    Relation(
                        _trim_line(f"Before: {title} {was}"),
                        _trim_line(f"After: {title} {now}"),
                        "becomes",
                    )
                ]
    return []


def structure(m: dict[str, Any], brief: Any, board: dict[str, Any] | None) -> tuple[Relation, ...]:
    """What the drawing connects: real calls, else grounded board groups, plus a before/after."""
    found = _calls(m, brief) or _mapping(board)
    found += _before_after(board)
    return tuple(dict.fromkeys(r for r in found if r.source != r.target))


def _nodes(relations: tuple[Relation, ...]) -> list[str]:
    return list(dict.fromkeys(t for r in relations for t in (r.source, r.target)))


def infobrief(m: dict[str, Any], brief: Any, board: dict[str, Any] | None) -> InfographicBrief:
    title = card.headline(m, board)
    found = facts.compute_facts(m, brief)
    stats = found.stats
    ci = "no CI" if found.ci_state == "none" else f"CI {stats.ci_text} {found.ci_state}"
    files = f"{stats.files} {_label(stats.files, 'file', 'files')}"
    changed = (
        f"{stats.symbols_changed} "
        f"{_label(stats.symbols_changed, 'parsed symbol changed', 'parsed symbols changed')}"
    )
    links = structure(m, brief, board)
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
        joins.update(one + other for one, other in pairwise(toks))
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
        "WORD_SIM": WORD_SIM,
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


def _icon_like(words: tuple[OcrWord, ...]) -> set[int]:
    """Ids of words alone on their text line or much taller than the other words on it."""
    found: set[int] = set()
    for line in _text_lines(words):
        for word in line:
            rest = sorted((w.box or (0, 0, 0, 0))[3] for w in line if w is not word)
            tall = (word.box or (0, 0, 0, 0))[3]
            if not rest or tall >= ICON_HEIGHT * rest[len(rest) // 2]:
                found.add(id(word))
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
        if bi + 1 < len(line_toks):
            next_word = line_toks[bi + 1]
            joined = here + next_word
            exact = here in code or next_word in code or _has_digit(joined)
            if joined == ocr[pos] or (not exact and _fold(joined) == _fold(ocr[pos])):
                found.append((2, 1))
        return found

    def rec(bi: int, oi: int) -> bool:
        if bi >= len(line_toks):
            return True
        if (bi, oi) in dead:
            return False
        for pos in range(oi, len(ocr)):
            if bi > 0 and pos - oi > WINDOW:
                break
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
    icon: bool,
) -> bool:
    """True when the other reads show this token is a misreading of an icon or an allowed word.

    Most other reads see an allowed word at the same place. Or the token has no digit and is
    short: one letter that looks like an icon (alone on its text line, or much taller than its
    neighbors), or a token that fewer than STABLE_READS confident
    reads (all reads, when there are fewer) see there.
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

    agree = sum(1 for r in others if any(known(t) for t in at_place(r)))
    if len(others) >= 2 and agree * 2 > len(others):
        return True
    if _has_digit(token) or len(token) > SHORT_TOKEN:
        return False
    if len(token) == 1 and icon:
        return True
    seen = 1 + sum(1 for r in others if token in at_place(r, CONF_FLOOR))
    return seen < min(STABLE_READS, len(reads))


def score_ocr(
    reads: tuple[OcrRead, ...], br: InfographicBrief, tesseract: str = ""
) -> GateDecision:
    allowed = allowed_words(br)
    code = code_words(br)
    prose = {_fold(word) for word in allowed if word not in code and not _has_digit(word)}
    joins = joined_words(br)

    def known(tok: str) -> bool:
        return tok in joins or any(_match(word, tok, code) for word in allowed)

    streams: list[list[str]] = []
    scored: list[list[tuple[str, float, Box | None, bool]]] = []
    for read in reads:
        icons = _icon_like(read.words)
        toks: list[str] = []
        confs: list[tuple[str, float, Box | None, bool]] = []
        for word in read.words:
            for tok in tokenize(word.text):
                toks.append(tok)
                confs.append((tok, word.conf, word.box, id(word) in icons))
        streams.append(toks)
        scored.append(confs)
    regions = [stream for read in reads for stream in region_streams(read.words)]
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
    missing: list[tuple[str, tuple[str, ...]]] = []
    for line in br.lines:
        ltoks = tokenize(line.text)
        if any(_covers(ltoks, ocr, code) for ocr in (*streams, *regions)):
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
    if decision.verdict != "pass" or not br.relations:
        return decision
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
        lines = _text_lines(tuple(w for w in read.words if w.conf >= CONF_FLOOR))
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


def check_relations(
    rgb: npt.NDArray[np.float32], reads: tuple[OcrRead, ...], br: InfographicBrief
) -> list[dict[str, Any]]:
    """For each relation, whether drawn ink joins the two node lines in separate shapes."""
    code = code_words(br)
    text = [
        w.box
        for read in reads
        for w in read.words
        if w.box and w.conf >= CONF_FLOOR and tokenize(w.text)
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
