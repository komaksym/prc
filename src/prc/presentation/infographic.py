"""One AI-drawn infographic per PR, gated by OCR before it is published."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

from prc import facts
from prc.presentation import card

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
Role = Literal["headline", "label", "chip", "row", "verdict", "note"]
Verdict = Literal["pass", "missing", "invented", "unreadable", "tool"]


@dataclass(frozen=True, slots=True)
class BriefLine:
    role: Role
    text: str


@dataclass(frozen=True, slots=True)
class InfographicBrief:
    title: str
    lines: tuple[BriefLine, ...]


@dataclass(frozen=True, slots=True)
class OcrWord:
    text: str
    conf: float


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
        elif len(_section_rows(kept, LOOK_LABEL)) > 1:
            _drop_last_row(kept, LOOK_LABEL)
        else:
            head = next(i for i, line in enumerate(kept) if line.role == "headline")
            room = MAX_WORDS - _word_count(tuple(line for i, line in enumerate(kept) if i != head))
            if room > 0:
                words = kept[head].text.split()
                while len(tokenize(" ".join(words))) > room:
                    words.pop()
                kept[head] = BriefLine("headline", " ".join(words).rstrip("…") + "…")
            elif _drop_last_row(kept, LOOK_LABEL):
                continue
            else:
                chips = [i for i, line in enumerate(kept) if line.role == "chip"]
                if not chips:
                    raise ValueError("infographic verdict and disclosure exceed the word budget")
                del kept[chips[-1]]
    for label in (LOOK_LABEL, RISKY_LABEL):
        if not _section_rows(kept, label):
            kept = [line for line in kept if not (line.role == "label" and line.text == label)]
    return tuple(kept)


def infobrief(m: dict[str, Any], brief: Any, board: dict[str, Any] | None) -> InfographicBrief:
    title = card.headline(m, board)
    found = facts.compute_facts(m, brief)
    stats = found.stats
    ci = "no CI" if found.ci_state == "none" else f"CI {stats.ci_text} {found.ci_state}"
    chips = [
        f"{stats.files} {_label(stats.files, 'file', 'files')}",
        f"{stats.symbols_changed} "
        f"{_label(stats.symbols_changed, 'parsed symbol changed', 'parsed symbols changed')}",
        f"{stats.call_sites} "
        f"{_label(stats.call_sites, 'resolved call site', 'resolved call sites')}",
        f"{stats.tests_touched} "
        f"{_label(stats.tests_touched, 'test file touched', 'test files touched')}",
        ci,
        f"{stats.untested_total} parsed code without test evidence",
    ]
    head: list[BriefLine] = [BriefLine("headline", title)]
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
    return InfographicBrief(fitted[0].text, fitted)


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
        "LINE_LIMIT": LINE_LIMIT,
        "MAX_WORDS": MAX_WORDS,
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
        words.append(OcrWord(text, conf))
    return tuple(words)


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


def score_ocr(
    reads: tuple[OcrRead, ...], br: InfographicBrief, tesseract: str = ""
) -> GateDecision:
    allowed = allowed_words(br)
    code = code_words(br)
    prose = {_fold(word) for word in allowed if word not in code and not _has_digit(word)}
    joins = joined_words(br)
    streams: list[list[str]] = []
    scored: list[list[tuple[str, float]]] = []
    for read in reads:
        toks: list[str] = []
        confs: list[tuple[str, float]] = []
        for word in read.words:
            for tok in tokenize(word.text):
                toks.append(tok)
                confs.append((tok, word.conf))
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
    if not any(conf >= CONF_FLOOR for stream in scored for _, conf in stream):
        return GateDecision("unreadable", (), (), detail)
    invented: dict[str, float] = {}
    for idx, stream in enumerate(scored):
        ocr = streams[idx]
        for pos, (tok, conf) in enumerate(stream):
            if conf < CONF_FLOOR:
                continue
            if tok in joins or any(_match(word, tok, code) for word in allowed):
                good = True
            elif _has_digit(tok):
                good = False
            else:
                good = _allowed_neighbor(tok, pos, ocr, prose)
            if not good:
                invented[tok] = max(invented.get(tok, conf), conf)
    missing: list[tuple[str, tuple[str, ...]]] = []
    for line in br.lines:
        ltoks = tokenize(line.text)
        if any(_covers(ltoks, ocr, code) for ocr in streams):
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
    except (OSError, subprocess.SubprocessError):
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
    except (OSError, subprocess.SubprocessError):
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
    return score_ocr(tuple(reads), br, tesseract=version)


def read_png(path: Path) -> bytes:
    raw = path.read_bytes()
    if not raw.startswith(_PNG_MAGIC):
        raise ValueError(f"infographic must be a PNG: {path}")
    return raw
