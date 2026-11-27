from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any

import pytest

from prc import facts
from prc.presentation import card
from prc.presentation import infographic as gate
from prc.presentation.comment import render_comment

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "data" / "infographic"

NOISE: list[tuple[str, float]] = [
    ("ittubonty", 4),
    ("seesteen", 0),
    ("teamtne", 0),
    ("borate", 9),
    ("fae", 0),
    ("present", 24),
    ("second", 28),
    ("x", 68),
]


def sample_map() -> dict[str, Any]:
    return {
        "pr": "o/r#1",
        "url": None,
        "title": "Fix cart totals",
        "author": "ann",
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "brief": {
            "pr": "o/r#1",
            "title": "Fix cart totals",
            "head_sha": "b" * 40,
            "files": [
                {
                    "path": "cart.py",
                    "kind": "code",
                    "added": 3,
                    "removed": 1,
                    "named": True,
                    "sensitive": "external calls",
                },
                {
                    "path": "tests/test_cart.py",
                    "kind": "test",
                    "added": 2,
                    "removed": 0,
                    "named": True,
                },
            ],
            "checks": [{"name": "unit", "state": "passed"}],
            "mismatches": [],
            "look_first": [{"path": "cart.py"}],
        },
        "files": [
            {
                "path": "cart.py",
                "kind": "code",
                "status": "modified",
                "language": "python",
                "sensitive": "external calls",
                "added": 3,
                "removed": 1,
                "hunks": [],
                "symbols": ["cart.py::apply_discount"],
            },
            {
                "path": "tests/test_cart.py",
                "kind": "test",
                "status": "added",
                "language": "python",
                "sensitive": None,
                "added": 2,
                "removed": 0,
                "hunks": [],
                "symbols": ["tests/test_cart.py::test_total"],
            },
        ],
        "symbols": [
            {
                "id": "cart.py::apply_discount",
                "path": "cart.py",
                "qualname": "apply_discount",
                "kind": "function",
                "status": "modified",
                "span": [10, 20],
                "base_span": [10, 18],
                "added": 3,
                "removed": 1,
                "hunks": [],
                "call_sites": 2,
            },
            {
                "id": "tests/test_cart.py::test_total",
                "path": "tests/test_cart.py",
                "qualname": "test_total",
                "kind": "function",
                "status": "added",
                "span": [1, 9],
                "base_span": None,
                "added": 2,
                "removed": 0,
                "hunks": [],
                "call_sites": 0,
            },
        ],
        "edges": [
            {
                "source": "tests/test_cart.py::test_total",
                "target": "cart.py::apply_discount",
                "status": "kept",
                "resolution": "exact",
            }
        ],
        "tour": [],
    }


def tsv(words: list[tuple[str, float]]) -> str:
    """One text line of words laid out left to right, 40 px wide with 10 px gaps."""
    head = ["level", "page", "block", "par", "line", "word", "l", "t", "w", "h", "conf", "text"]
    rows = [chr(9).join(head)]
    for i, (word, conf) in enumerate(words):
        rows.append(
            chr(9).join(
                ["5", "1", "1", "1", "1", str(i + 1), str(i * 50), "0", "40", "20", str(conf), word]
            )
        )
    return chr(10).join(rows)


def tiny_brief() -> gate.InfographicBrief:
    return gate.InfographicBrief(
        "Cart totals",
        (
            gate.BriefLine("headline", "Cart totals"),
            gate.BriefLine("chip", "2 files"),
            gate.BriefLine("note", gate.DISCLOSURE),
        ),
    )


def read(text: str, mode: str, conf: float = 90.0) -> gate.OcrRead:
    return gate.OcrRead(mode, gate.parse_tsv(tsv([(w, conf) for w in text.split()])))


def test_infobrief_words_are_checked() -> None:
    m = sample_map()
    brief = gate.infobrief(m, m["brief"], None)
    found = facts.compute_facts(m, m["brief"])
    stats = found.stats
    look = card.look_first(m, m["brief"], 3, None)
    surfaces = card.risky(m, m["brief"])
    assert brief.title == card.headline(m, None)
    assert brief.title == "Fix cart totals"
    expected: list[tuple[str, str]] = [("headline", "Fix cart totals")]
    expected += [
        ("chip", "2 files"),
        ("chip", "2 parsed symbols changed"),
        ("chip", "2 resolved call sites"),
        ("chip", "1 test file touched"),
        ("chip", "CI 1/1 passed"),
        ("chip", "0 parsed code without test evidence"),
    ]
    assert stats.files == 2 and stats.tests_touched == 1
    assert found.ci_state == "passed"
    expected.append(("label", gate.LOOK_LABEL))
    expected += [("row", f"{e.name} in {e.path}") for e in look]
    assert [e.name for e in look] == ["apply_discount"]
    expected.append(("label", gate.RISKY_LABEL))
    expected += [("row", f"{r.path}: {r.reason}") for r in surfaces]
    assert [(r.path, r.reason) for r in surfaces] == [("cart.py", "external calls")]
    expected.append(("verdict", found.test_verdict))
    expected.append(("note", gate.DISCLOSURE))
    assert [(line.role, line.text) for line in brief.lines] == expected
    assert gate.LOOK_LABEL in render_comment(m, m["brief"], None)
    assert gate.RISKY_LABEL in render_comment(m, m["brief"], None)
    assert "cart" in gate.allowed_words(brief)


def test_infobrief_deterministic(tmp_path: Path) -> None:
    m = sample_map()
    first = gate.write_brief_json(gate.infobrief(m, m["brief"], None), tmp_path / "a.json")
    second = gate.write_brief_json(gate.infobrief(m, m["brief"], None), tmp_path / "b.json")
    assert first.read_bytes() == second.read_bytes()
    payload = json.loads(first.read_text())
    assert list(payload) == sorted(payload)


def test_brief_prompt_allows_icons_and_diagram_layouts() -> None:
    rules = gate.brief_dict(case_brief("librarysync-98"))["prompt_rules"]
    assert "Icons are allowed beside text but contain no letters or digits." in rules
    assert any("arrow" in rule for rule in rules)
    assert not any("Use no icons" in rule or "one text column" in rule for rule in rules)


def test_infobrief_caps_drop_risky_then_look() -> None:
    m = sample_map()
    m["brief"]["files"] = [
        {"path": f"s{i}.py", "kind": "code", "sensitive": "external calls"} for i in range(30)
    ]
    brief = gate.infobrief(m, m["brief"], None)
    total = sum(len(gate.tokenize(line.text)) for line in brief.lines)
    assert total <= gate.MAX_WORDS
    assert any(line.role == "headline" for line in brief.lines)
    assert any(line.role == "note" for line in brief.lines)
    for line in brief.lines:
        assert len(line.text) <= gate.LINE_LIMIT


def test_gate_exact_text_passes() -> None:
    brief = tiny_brief()
    reads = (
        read("Cart totals 2 files Infographic drawn by AI Words from prc", "psm-3"),
        read("Cart totals 2 files Infographic drawn by AI Words from prc", "psm-11"),
    )
    assert gate.score_ocr(reads, brief).verdict == "pass"


def test_gate_missing_word_fails() -> None:
    brief = tiny_brief()
    reads = (
        read("Cart 2 files Infographic drawn by AI Words from prc", "psm-3"),
        read("Cart 2 files Infographic drawn by AI Words from prc", "psm-11"),
    )
    decision = gate.score_ocr(reads, brief)
    assert decision.verdict == "missing"
    assert any("totals" in toks for _, toks in decision.missing)


def test_gate_invented_word_fails() -> None:
    brief = tiny_brief()
    reads = (
        read(
            "Cart totals 2 files watermelon Infographic drawn by AI Words from prc", "psm-3", 90.0
        ),
        read("Cart totals 2 files Infographic drawn by AI Words from prc", "psm-11"),
    )
    decision = gate.score_ocr(reads, brief)
    assert decision.verdict == "invented"
    assert [tok for tok, _ in decision.invented] == ["watermelon"]


def test_gate_wrong_number_fails() -> None:
    brief = tiny_brief()
    reads = (
        read("Cart totals 7 files Infographic drawn by AI Words from prc", "psm-3"),
        read("Cart totals 7 files Infographic drawn by AI Words from prc", "psm-11"),
    )
    decision = gate.score_ocr(reads, brief)
    assert decision.verdict == "invented"
    assert "7" in [tok for tok, _ in decision.invented]


def test_gate_negation_fails() -> None:
    brief = tiny_brief()
    reads = (
        read("Cart totals 2 files not Infographic drawn by AI Words from prc", "psm-3", 90.0),
        read("Cart totals 2 files Infographic drawn by AI Words from prc", "psm-11"),
    )
    assert gate.score_ocr(reads, brief).verdict == "invented"


def test_gate_low_confidence_noise_passes() -> None:
    brief = tiny_brief()
    words = [
        (w, c)
        for w, c in [("Cart", 90.0), ("totals", 90.0), ("2", 88.0), ("files", 90.0)]
        + [
            ("Infographic", 90.0),
            ("drawn", 90.0),
            ("by", 90.0),
            ("AI", 90.0),
            ("Words", 90.0),
            ("from", 90.0),
            ("prc", 90.0),
        ]
    ]
    words += NOISE
    reads = (
        gate.OcrRead("psm-3", gate.parse_tsv(tsv(words))),
        gate.OcrRead("psm-11", gate.parse_tsv(tsv(words))),
    )
    decision = gate.score_ocr(reads, brief)
    assert decision.verdict == "pass", decision


def test_gate_low_confidence_counts_for_coverage() -> None:
    brief = tiny_brief()
    reads = (
        gate.OcrRead(
            "psm-3",
            gate.parse_tsv(
                tsv(
                    [
                        ("Cart", 90.0),
                        ("totals", 90.0),
                        ("2", 88.0),
                        ("files", 20.0),
                        ("Infographic", 90.0),
                        ("drawn", 90.0),
                        ("by", 90.0),
                        ("AI", 90.0),
                        ("Words", 90.0),
                        ("from", 90.0),
                        ("prc", 90.0),
                    ]
                )
            ),
        ),
        gate.OcrRead(
            "psm-11", gate.parse_tsv(tsv([("Cart", 90.0), ("totals", 90.0), ("2", 88.0)]))
        ),
    )
    assert gate.score_ocr(reads, brief).verdict == "pass"


def test_gate_split_word_passes() -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("row", "checkout counter"),))
    reads = (
        read("check out counter", "psm-3"),
        read("check out counter", "psm-11"),
    )
    assert gate.score_ocr(reads, brief).verdict == "pass"


def test_gate_merged_neighbors_pass() -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("row", "PR A then PR B"),))
    reads = (read("PRA then PRB", "psm-3"), read("PRA then PRB", "psm-11"))
    assert gate.score_ocr(reads, brief).verdict == "pass"


def test_gate_merge_of_words_out_of_order_fails() -> None:
    text = "Cart totals 2 files Infographic drawn by AI Words from prc"
    reads = (read(text + " totalscart", "psm-3"), read(text, "psm-11"))
    decision = gate.score_ocr(reads, tiny_brief())
    assert decision.verdict == "invented"
    assert [tok for tok, _ in decision.invented] == ["totalscart"]


def test_gate_lost_short_word_is_missing_even_beside_a_long_one() -> None:
    text = "Cart totals 2 files Infographic drawn by Words from prc"
    decision = gate.score_ocr((read(text, "psm-3"), read(text, "psm-11")), tiny_brief())
    assert decision.verdict == "missing"
    assert decision.missing == ((gate.DISCLOSURE, ("ai",)),)


def test_gate_reads_capital_i_as_lowercase_l() -> None:
    brief = gate.InfographicBrief(
        "t", (gate.BriefLine("chip", "CI 4/4 passed"), gate.BriefLine("note", gate.DISCLOSURE))
    )
    text = "Cl 4/4 passed Infographic drawn by Al. Words from prc."
    assert gate.score_ocr((read(text, "psm-3"), read(text, "psm-11")), brief).verdict == "pass"


def test_gate_code_name_must_be_spelled_exactly() -> None:
    brief = gate.InfographicBrief(
        "t", (gate.BriefLine("row", "noteCommand.multicursor.onComplete in src/commands/note.ts"),)
    )
    drawn = "noteCommand.multicursor.onCComplete in src/commands/note.ts"
    decision = gate.score_ocr((read(drawn, "psm-3"), read(drawn, "psm-11")), brief)
    assert decision.verdict == "invented"
    assert [tok for tok, _ in decision.invented] == ["onccomplete"]


def test_gate_stable_prose_misspelling_is_rejected() -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("verdict", "No direct test evidence"),))
    drawn = "No direct test evidcnce"
    decision = gate.score_ocr((read(drawn, "psm-3"), read(drawn, "psm-11")), brief)
    assert decision.verdict == "invented"


def blank_png(path: Path) -> Path:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(b"\x00" + b"\x00" * 192 for _ in range(64))))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    return path


def test_gate_unreadable(tmp_path: Path) -> None:
    decision = gate.gate(blank_png(tmp_path / "blank.png"), tiny_brief())
    assert decision.verdict == "unreadable"


def test_gate_without_tesseract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil as _shutil

    monkeypatch.setattr(_shutil, "which", lambda _name: None)
    png = blank_png(tmp_path / "blank.png")
    assert gate.gate(png, tiny_brief()).verdict == "tool"
    assert gate.tool_decision().verdict == "tool"


def session_brief(slug: str) -> gate.InfographicBrief:
    spec = json.loads((DATA / slug / "lines.json").read_text())
    title = str(spec["title"])
    lines = tuple(gate.BriefLine("row", str(text)) for text in spec["lines"])
    return gate.InfographicBrief(title, lines)


SESSION = (
    "comparator-split",
    "matched-pair-flow",
    "next-steps-roadmap",
    "pr-infographic-flow",
    "review-bias-2026-10-10",
)


def session_reads(slug: str) -> tuple[gate.OcrRead, ...]:
    return tuple(
        gate.OcrRead(name, gate.parse_tsv((DATA / slug / f"{name}.tsv").read_text()))
        for name in ("psm3", "psm11", "psm3-dpi150", "psm11-dpi150")
    )


REJECTED = {
    "comparator-split": (
        "missing",
        ("You", "Agents give the broad ranking. You judge the interactive tools."),
    ),
    "next-steps-roadmap": (
        "missing",
        (
            "1",
            "2",
            "3",
            "4",
            "3 practice PRs",
            "Seal",
            "Everything frozen",
            "Agents: 4 options, same PRs",
            "Change the product before the seal. After it, any change starts a new study.",
        ),
    ),
    "review-bias-2026-10-10": ("missing", ("Mixed result",)),
}


def test_gate_session_images_record_false_rejections() -> None:
    """Icon reads ("ak", "j", "se", "al") no longer reject; no read finds the lines still missing."""
    for slug in SESSION:
        decision = gate.score_ocr(session_reads(slug), session_brief(slug))
        found = (
            decision.verdict,
            tuple(tok for tok, _ in decision.invented)
            or tuple(text for text, _ in decision.missing),
        )
        assert found == REJECTED.get(slug, ("pass", ())), slug


@pytest.mark.parametrize("word", ["guaranteed", "37", "not"])
def test_gate_session_images_with_a_clear_extra_word_fail(word: str) -> None:
    for slug in SESSION:
        first, *rest = session_reads(slug)
        planted = gate.OcrRead(first.mode, (gate.OcrWord(word, 90.0), *first.words))
        decision = gate.score_ocr((planted, *rest), session_brief(slug))
        assert decision.verdict == "invented", slug
        assert word in [tok for tok, _ in decision.invented], slug


CANDIDATES = {
    "v2-librarysync-98-candidate-02": ("pass", ()),
    "v2-em-5756-candidate-01": ("pass", ()),
    "v2-swarm-116-candidate-01": ("invented", ("9",)),
    "v2-swarm-116-candidate-02": ("pass", ()),
    "librarysync-98-candidate-01": ("missing", ("Infographic drawn by AI. Words from prc.",)),
    "librarysync-98-candidate-02": ("pass", ()),
    "librarysync-98-candidate-03": ("pass", ()),
    "em-5756-candidate-01": ("invented", ("onccomplete",)),
    "em-5756-candidate-02": ("pass", ()),
    "em-5756-candidate-03": ("pass", ()),
    "swarm-116-candidate-01": ("pass", ()),
}


@pytest.mark.parametrize("slug", sorted(CANDIDATES))
def test_gate_judges_drawn_candidates_by_what_they_show(slug: str) -> None:
    """Defect: icons read as "q", "j", "en", one read saw "42" for "12", and column layouts broke
    page order, so correct diagrams failed. Two candidates really misspell: "pnc" and
    "onCComplete"."""
    decision = gate.score_ocr(
        session_reads(f"candidates/{slug}"), session_brief(f"candidates/{slug}")
    )
    found = (
        decision.verdict,
        tuple(tok for tok, _ in decision.invented) or tuple(text for text, _ in decision.missing),
    )
    assert found == CANDIDATES[slug]


@pytest.mark.parametrize("word", ["if", "37", "not", "guaranteed"])
@pytest.mark.parametrize("slug", [s for s, (v, _) in sorted(CANDIDATES.items()) if v == "pass"])
def test_gate_word_every_read_sees_in_one_place_fails(slug: str, word: str) -> None:
    path = f"candidates/{slug}"
    reads = tuple(
        gate.OcrRead(r.mode, (*r.words, gate.OcrWord(word, 90.0, (1500, 2, 80, 30))))
        for r in session_reads(path)
    )
    decision = gate.score_ocr(reads, session_brief(path))
    assert decision.verdict == "invented"
    assert word in dict(decision.invented)


def test_gate_lone_letter_is_an_icon_but_a_letter_in_text_is_not() -> None:
    path = "candidates/librarysync-98-candidate-02"
    lone = gate.OcrWord("Y", 90.0, (1500, 2, 30, 30))
    beside = gate.OcrWord("Y", 90.0, (1500, 2, 30, 30))
    text = gate.OcrWord("today", 90.0, (1540, 2, 90, 30))
    alone = tuple(gate.OcrRead(r.mode, (*r.words, lone)) for r in session_reads(path))
    inline = tuple(gate.OcrRead(r.mode, (*r.words, beside, text)) for r in session_reads(path))
    assert "y" in dict(gate.score_ocr(alone, session_brief(path)).invented)
    assert "y" in dict(gate.score_ocr(inline, session_brief(path)).invented)


def wordy(n: int) -> str:
    return " ".join(f"word{i}" for i in range(n))


def test_fit_words_drops_risky_first_and_never_orphans_a_label() -> None:
    head = [gate.BriefLine("headline", wordy(9))]
    head += [gate.BriefLine("chip", wordy(5)) for _ in range(6)]
    look_label = gate.BriefLine("label", gate.LOOK_LABEL)
    risky_label = gate.BriefLine("label", gate.RISKY_LABEL)
    verdict = gate.BriefLine("verdict", wordy(10))
    note = gate.BriefLine("note", wordy(6))

    lines = tuple(
        head
        + [look_label, gate.BriefLine("row", wordy(4))]
        + [risky_label]
        + [gate.BriefLine("row", "risk one two three"), gate.BriefLine("row", wordy(25))]
        + [verdict, note]
    )
    kept = gate._fit_words(lines)
    texts = [line.text for line in kept]
    assert texts.count(risky_label.text) == 1
    assert wordy(25) not in texts
    assert "risk one two three" in texts
    assert wordy(4) in texts

    single = tuple(
        head
        + [look_label, gate.BriefLine("row", wordy(12))]
        + [risky_label]
        + [gate.BriefLine("row", wordy(12))]
        + [verdict, note]
    )
    kept = gate._fit_words(single)
    roles = [(line.role, line.text) for line in kept]
    assert ("label", gate.RISKY_LABEL) not in roles
    assert ("label", gate.LOOK_LABEL) in roles
    assert sum(len(gate.tokenize(line.text)) for line in kept) <= gate.MAX_WORDS

    norisky = tuple(
        head
        + [look_label, gate.BriefLine("row", wordy(4)), gate.BriefLine("row", wordy(25))]
        + [verdict, note]
    )
    kept = gate._fit_words(norisky)
    rows = [line.text for line in kept if line.role == "row"]
    assert rows == [wordy(4)]


def test_em5756_brief_keeps_look_rows_without_orphan_labels() -> None:
    case = ROOT / "tests" / "data" / "trustworthiness" / "em-5756"
    m = json.loads((case / "map.json").read_text())
    board = json.loads((case / "board.json").read_text())
    brief = gate.infobrief(m, m.get("brief"), board)
    assert sum(len(gate.tokenize(line.text)) for line in brief.lines) <= gate.MAX_WORDS
    rows = [line.text for line in brief.lines if line.role == "row"]
    assert rows == [
        "noteCommand.multicursor.onComplete in src/commands/note.ts",
        "openCommandCenterCommand.exec in src/commands/openCommandCenter.ts",
        "CommandCenter in src/components/CommandCenter/CommandCenter.tsx",
    ]
    labels = [line.text for line in brief.lines if line.role == "label"]
    assert labels == [gate.LOOK_LABEL]
    for i, line in enumerate(brief.lines):
        if line.role == "label":
            following = [later.role for later in brief.lines[i + 1 :]]
            assert following and following[0] == "row", line.text


def test_brief_over_max_words_keeps_no_label_without_a_row() -> None:
    head = [gate.BriefLine("headline", wordy(9))]
    head += [gate.BriefLine("chip", wordy(5)) for _ in range(6)]
    lines = tuple(
        head
        + [gate.BriefLine("label", gate.LOOK_LABEL), gate.BriefLine("row", wordy(12))]
        + [gate.BriefLine("label", gate.RISKY_LABEL), gate.BriefLine("row", wordy(12))]
        + [gate.BriefLine("verdict", wordy(10)), gate.BriefLine("note", wordy(6))]
    )
    assert sum(len(gate.tokenize(line.text)) for line in lines) > gate.MAX_WORDS
    kept = gate._fit_words(lines)
    for i, line in enumerate(kept):
        if line.role == "label":
            assert i + 1 < len(kept) and kept[i + 1].role == "row", line.text
    assert ("label", gate.RISKY_LABEL) not in [(line.role, line.text) for line in kept]


@pytest.mark.parametrize("word", ["no", "if", "or", "we", "as", "the", "q", "zx"])
def test_gate_foreign_short_words_and_stopwords_fail(word: str) -> None:
    text = "Cart totals 2 files Infographic drawn by AI Words from prc"
    decision = gate.score_ocr((read(text + " " + word, "psm-3"),), tiny_brief())
    assert decision.verdict == "invented"
    assert word in dict(decision.invented)


@pytest.mark.parametrize("drawn", ["kiii in src/kiii.py", "k ill in src/kill.py"])
def test_gate_code_tokens_cannot_fold_or_split(drawn: str) -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("row", "kill in src/kill.py"),))
    decision = gate.score_ocr((read(drawn, "psm-3"),), brief)
    assert decision.verdict != "pass"
    assert decision.missing


def test_gate_reports_foreign_words_and_missing_lines_together() -> None:
    decision = gate.score_ocr(
        (read("Cart 2 files watermelon Infographic drawn by AI Words from prc", "psm-3"),),
        tiny_brief(),
    )
    assert decision.verdict == "invented"
    assert "watermelon" in dict(decision.invented)
    assert ("Cart totals", ("totals",)) in decision.missing


def test_gate_requires_every_reading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "tesseract_version", lambda: "tesseract 5")
    text = "Cart totals 2 files Infographic drawn by AI Words from prc"
    words = read(text, "psm-3").words
    monkeypatch.setattr(
        gate, "_read_mode", lambda _png, psm, dpi: words if (psm, dpi) == ("3", "") else None
    )
    decision = gate.gate(blank_png(tmp_path / "partial.png"), tiny_brief())
    assert decision.verdict == "tool"
    assert len(decision.detail["failed_modes"]) == 3
    assert len(decision.detail["modes"]) == 1


def test_infobrief_long_mandatory_content_stays_in_budget() -> None:
    m = sample_map()
    m["title"] = "a " * 48
    m["brief"]["title"] = m["title"]
    brief = gate.infobrief(m, m["brief"], None)
    assert sum(len(gate.tokenize(line.text)) for line in brief.lines) <= gate.MAX_WORDS
    assert brief.title.endswith("…")
    assert any(line.text == gate.DISCLOSURE for line in brief.lines)


def test_doctor_does_not_call_a_broken_tesseract_available(monkeypatch: pytest.MonkeyPatch) -> None:
    from prc.explainer import doctor

    monkeypatch.setattr(gate, "tesseract_version", lambda: "")
    assert "unavailable" in doctor._tesseract()
    assert " ok" not in doctor._tesseract()


CASES = ROOT / "tests" / "data" / "trustworthiness"


def case_brief(slug: str) -> gate.InfographicBrief:
    m = json.loads((CASES / slug / "map.json").read_text())
    board = json.loads((CASES / slug / "board.json").read_text())
    return gate.infobrief(m, m.get("brief"), board, case_sources(slug))


def case_sources(slug: str) -> dict[str, str]:
    if slug == "swarm-116":
        return {"internal/compose/file.go": (CASES / slug / "file.go").read_text()}
    if slug == "librarysync-98":
        path = "backend/src/librarysync/core/next_episode.py"
        return {
            path: (CASES / slug / "head.txt").read_text(),
            "base:" + path: (CASES / slug / "base.txt").read_text(),
        }
    return {}


def links(brief: gate.InfographicBrief) -> set[tuple[str, str, str]]:
    return {(r.source, r.target, r.kind) for r in brief.relations}


def test_structure_librarysync_shows_the_new_call_its_tests_and_the_changed_pick() -> None:
    """Defect: the infographic drew six counts and no structure, so nothing showed how it works."""
    brief = case_brief("librarysync-98")
    assert links(brief) == {
        ("find_next_episodes_bulk", "select_next_episode", "call"),
        ("2 new test calls", "select_next_episode", "call"),
        (
            "Before docs: first episode not in watched_episode_ids.",
            "After docs: next episode after the user's latest watched point.",
            "becomes",
        ),
    }
    legends = [line.text for line in brief.lines if line.role == "legend"]
    assert legends == [gate.MIXED_CALL_LEGEND], "the Before/After arrow is not a call"


def test_structure_keeps_the_headline_whole_by_dropping_look_rows_first() -> None:
    """Defect: the structure brief cut the librarysync headline to '...watched...'."""
    m = json.loads((CASES / "librarysync-98" / "map.json").read_text())
    board = json.loads((CASES / "librarysync-98" / "board.json").read_text())
    brief = case_brief("librarysync-98")
    assert brief.lines[0].text == card.headline(m, board)
    assert not brief.lines[0].text.endswith("…")
    assert gate.LOOK_LABEL not in [line.text for line in brief.lines]


def test_structure_em5756_shows_both_new_calls() -> None:
    assert links(case_brief("em-5756")) == {
        ("noteCommand.multicursor.onComplete", "toggleDropdownActionCreator", "call"),
        ("openCommandCenterCommand.exec", "dismissKeyboardActionCreator", "call"),
    }


def test_structure_without_parsed_calls_uses_grounded_board_groups() -> None:
    """swarm-116 is Go, so the map has no edges; the checked board groups name the mapping."""
    assert links(case_brief("swarm-116")) == {
        ("fileReader", "ReadComposeError", "maps"),
        ("Unmarshal", "ParseComposeError", "maps"),
        ("Decode", "ValidateComposeError", "maps"),
    }


def test_structure_does_not_promote_unchecked_group_titles() -> None:
    m = json.loads((CASES / "swarm-116" / "map.json").read_text())
    board = json.loads((CASES / "swarm-116" / "board.json").read_text())
    for scene in board["scenes"]:
        if scene["type"] == "groups":
            for group in scene["groups"]:
                group["title"] = "Invented relationship"
    assert links(gate.infobrief(m, m.get("brief"), board, case_sources("swarm-116"))) == links(
        case_brief("swarm-116")
    )


def test_before_after_comes_from_code_even_if_board_scenes_are_reversed() -> None:
    m = json.loads((CASES / "librarysync-98" / "map.json").read_text())
    board = json.loads((CASES / "librarysync-98" / "board.json").read_text())
    for scene in board["scenes"]:
        if scene["type"] == "groups":
            for group in scene["groups"]:
                group["title"] = "Invented transition"
                for item in group["items"]:
                    item["text"] = "invented " + item["text"]
    board["scenes"].reverse()
    sources = case_sources("librarysync-98")
    assert any(r.kind == "becomes" for r in gate.structure(m, m.get("brief"), board, sources))
    assert gate.structure(m, m.get("brief"), board, sources) == gate.structure(
        m, m.get("brief"), None, sources
    )


def test_before_after_requires_a_function_docstring_and_removes_its_quotes() -> None:
    m = sample_map()
    file = m["files"][0]
    file["hunks"] = [
        {
            "lines": [
                {"old": 10, "new": 10, "text": "def apply_discount():"},
                {"old": 11, "new": None, "text": '    """old docs."""'},
                {"old": None, "new": 11, "text": '    """new docs."""'},
            ]
        }
    ]
    path = file["path"]
    sources = {
        path: "\n" * 9 + 'def apply_discount():\n    """new docs."""',
        "base:" + path: "\n" * 9 + 'def apply_discount():\n    """old docs."""',
    }
    assert gate._before_after(m, sources) == [
        gate.Relation("Before docs: old docs.", "After docs: new docs.", "becomes")
    ]
    file["hunks"][0]["lines"][0]["text"] = "    if enabled:"
    path = file["path"]
    sources = {
        path: "\n" * 9 + 'def apply_discount():\n    """new docs."""',
        "base:" + path: "\n" * 9 + 'def apply_discount():\n    """old docs."""',
    }
    assert gate._before_after(m, sources) == []


@pytest.mark.parametrize("comment", ["/*\n{code}\n*/", "`\n{code}\n`"])
def test_go_mapping_excludes_comment_and_string_contents(comment: str) -> None:
    code = "_, err := imaginary()\nif err != nil {\nreturn nil, &ImaginaryError{Err: err}\n}"
    text = "func load() (*File, error) {\n" + comment.format(code=code) + "\nreturn nil, nil\n}"
    m = {
        "files": [
            {
                "path": "file.go",
                "hunks": [
                    {
                        "lines": [
                            {"new": i, "old": None, "text": line}
                            for i, line in enumerate(text.splitlines(), 1)
                        ]
                    }
                ],
            }
        ]
    }
    assert gate._mapping(m, {"file.go": text}) == []


def test_go_mapping_does_not_escape_the_error_branch() -> None:
    text = "func load() (*File, error) {\n_, err := reader()\nif err != nil {\n}\nreturn nil, &WrongError{Err: err}\n}"
    m = {
        "files": [
            {
                "path": "file.go",
                "hunks": [
                    {
                        "lines": [
                            {"new": i, "old": None, "text": line}
                            for i, line in enumerate(text.splitlines(), 1)
                        ]
                    }
                ],
            }
        ]
    }
    assert gate._mapping(m, {"file.go": text}) == []


def test_structure_does_not_join_an_error_with_an_unrelated_go_call() -> None:
    m: dict[str, Any] = {
        "files": [
            {
                "path": "loader.go",
                "hunks": [
                    {
                        "lines": [
                            {"new": 1, "text": "func load() error {"},
                            {"new": 2, "text": "harmless()"},
                            {"new": 3, "text": "if err != nil {"},
                            {"new": 4, "text": "return nil, &WrongError{Err: err}"},
                            {"new": 5, "text": "}"},
                            {"new": 6, "text": "raw, err := l.fileReader(ctx, path)"},
                            {"new": 7, "text": "if err != nil {"},
                            {"new": 8, "text": "return nil, &ReadComposeError{Err: err}"},
                            {"new": 9, "text": "}"},
                        ]
                    }
                ],
            }
        ]
    }
    source = "\n".join(line["text"] for line in m["files"][0]["hunks"][0]["lines"])
    assert gate._mapping(m, {"loader.go": source}) == [
        gate.Relation("fileReader", "ReadComposeError", "maps")
    ]


def test_go_mapping_uses_full_source_context_and_requires_matching_hunk_lines() -> None:
    source = "/*\nfunc imaginary() (*File, error) {\n_, err := reader()\nif err != nil {\nreturn nil, &ImaginaryError{Err: err}\n}\n}\n*/"
    rows = [{"new": i, "old": None, "text": line} for i, line in enumerate(source.splitlines(), 1)][
        1:-1
    ]
    m: dict[str, Any] = {"files": [{"path": "file.go", "hunks": [{"lines": rows}]}]}
    assert gate._mapping(m) == []
    assert gate._mapping(m, {"file.go": source}) == []
    source = source.replace("/*", "  ").replace("*/", "  ")
    assert gate._mapping(m, {"file.go": source}) == [
        gate.Relation("reader", "ImaginaryError", "maps")
    ]
    m["files"][0]["hunks"][0]["lines"][3]["text"] = "return nil, &WrongError{Err: err}"
    assert gate._mapping(m, {"file.go": source}) == []


def test_structure_excludes_name_only_calls_and_test_call_counts() -> None:
    m = call_map(("checkout", "total", "added"), ("test_a", "total", "added"), tests=("test_a",))
    m["edges"][1]["resolution"] = "name"
    assert links(gate.infobrief(m, m["brief"], None)) == {("checkout", "total", "call")}
    m["edges"][0]["resolution"] = "name"
    assert gate.structure(m, m["brief"], None) == ()


@pytest.mark.parametrize("slug", ["librarysync-98", "em-5756", "swarm-116"])
def test_structure_fits_the_budget_and_every_endpoint_is_a_drawn_line(slug: str) -> None:
    brief = case_brief(slug)
    texts = [line.text for line in brief.lines]
    assert sum(len(gate.tokenize(t)) for t in texts) <= gate.MAX_WORDS
    assert len(texts) == len(set(texts))
    for r in brief.relations:
        assert r.source in texts and r.target in texts
    nodes = {line.text for line in brief.lines if line.role == "node"}
    assert nodes == {r.source for r in brief.relations} | {r.target for r in brief.relations}


def call_map(*edges: tuple[str, str, str], tests: tuple[str, ...] = ()) -> dict[str, Any]:
    m = sample_map()
    names = {name for edge in edges for name in edge[:2]}
    m["symbols"] = [
        {
            "id": f"{'tests/test_cart.py' if n in tests else 'cart.py'}::{n}",
            "path": "tests/test_cart.py" if n in tests else "cart.py",
            "qualname": n,
            "kind": "function",
            "status": "added" if n in tests else "modified",
            "span": [1, 2],
            "base_span": [1, 2],
            "added": 1,
            "removed": 0,
            "hunks": [],
            "call_sites": 0,
        }
        for n in sorted(names)
    ]
    path = {s["qualname"]: s["id"] for s in m["symbols"]}
    m["edges"] = [
        {"source": path[a], "target": path[b], "status": status, "resolution": "exact"}
        for a, b, status in edges
    ]
    return m


def test_structure_removed_call_and_kept_calls() -> None:
    m = call_map(("checkout", "apply_discount", "removed"), ("checkout", "total", "kept"))
    brief = gate.infobrief(m, m["brief"], None)
    assert links(brief) == {("checkout", "apply_discount", "removed call")}
    assert ("legend", "Dashed arrows show removed calls") in [
        (line.role, line.text) for line in brief.lines
    ]


def test_structure_counts_distinct_tests_once_for_the_most_tested_target() -> None:
    m = call_map(
        ("checkout", "total", "added"),
        ("test_a", "total", "added"),
        ("test_b", "total", "added"),
        ("test_c", "checkout", "added"),
        ("test_d", "total", "kept"),
        tests=("test_a", "test_b", "test_c", "test_d"),
    )
    brief = gate.infobrief(m, m["brief"], None)
    assert links(brief) == {
        ("checkout", "total", "call"),
        ("2 new test calls", "total", "call"),
    }


def test_structure_caps_production_calls() -> None:
    m = call_map(*[(f"caller{i}", f"callee{i}", "added") for i in range(5)])
    brief = gate.infobrief(m, m["brief"], None)
    assert len(brief.relations) == gate.MAX_CALLS


def test_structure_absent_keeps_all_six_chips_and_no_relations() -> None:
    m = sample_map()
    brief = gate.infobrief(m, m["brief"], None)
    assert brief.relations == ()
    assert [line.role for line in brief.lines].count("chip") == 6


def test_brief_json_records_relations(tmp_path: Path) -> None:
    brief = case_brief("librarysync-98")
    payload = json.loads(gate.write_brief_json(brief, tmp_path / "b.json").read_text())
    assert {"from": "find_next_episodes_bulk", "to": "select_next_episode", "kind": "call"} in (
        payload["relations"]
    )


@pytest.mark.parametrize(
    ("brief", "read", "same"),
    [
        ("s1e1", "sle1", True),
        ("s1e1", "siei", False),
        ("s2e3", "s2e8", False),
        ("12", "l2", False),
        ("12", "42", False),
    ],
)
def test_gate_reads_one_as_l_only_inside_letter_and_digit_tokens(
    brief: str, read: str, same: bool
) -> None:
    """Defect: a drawn "s1e1" read as "sle1" in every read, so a correct line was missing."""
    assert gate._match(brief, read) is same


def test_locate_finds_a_node_box_read_with_low_confidence() -> None:
    """Defect: em-5756's top node read at confidence 60, so only its copy in the Look panel was
    found and the gate missed the arrow drawn from the top box."""
    path = "candidates/v2-em-5756-candidate-01"
    reads = session_reads(path)
    brief = session_brief(path)
    places = gate.locate("noteCommand.multicursor.onComplete", reads, gate.code_words(brief))
    tops = sorted(box[1] for box, _ in places)
    assert len(tops) == 2
    assert tops[0] < 230 < tops[1]


def test_locate_ignores_a_weak_word_that_swallowed_a_drawn_line() -> None:
    line = gate.OcrWord("----Papply", 22.0, (440, 331, 509, 49))
    word = gate.OcrWord("apply", 96.0, (800, 331, 149, 49))
    read = gate.OcrRead("psm-3", (line,))
    assert gate.locate("apply", (read,), frozenset()) == []
    assert gate.locate("apply", (gate.OcrRead("psm-3", (word,)),), frozenset()) != []


def test_gate_square_glyph_taller_than_its_line_is_an_icon_but_a_word_is_not() -> None:
    """Defect: a gear icon beside a code name read as "god" in three reads."""
    path = "candidates/v2-librarysync-98-candidate-02"
    base = session_reads(path)
    text = gate.OcrWord("today", 90.0, (1540, 2, 90, 30))

    def extra(*words: gate.OcrWord) -> gate.GateDecision:
        reads = tuple(
            gate.OcrRead(r.mode, (*r.words, *words)) if i < 3 else r for i, r in enumerate(base)
        )
        return gate.score_ocr(reads, session_brief(path))

    gear = gate.OcrWord("god", 90.0, (1440, 0, 77, 77))
    assert "today" in dict(extra(gear, text).invented)
    assert "god" not in dict(extra(gear, text).invented)
    wide = gate.OcrWord("god", 90.0, (1400, 0, 130, 77))
    assert "god" in dict(extra(wide, text).invented)
    lone = gate.OcrWord("if", 90.0, (1440, 0, 30, 30))
    all_reads = tuple(gate.OcrRead(r.mode, (*r.words, lone)) for r in base)
    assert "if" in dict(gate.score_ocr(all_reads, session_brief(path)).invented)
    digit = gate.OcrWord("9", 90.0, (1440, 0, 77, 77))
    assert "9" in dict(extra(digit, text).invented)


@pytest.mark.parametrize("extra", ["9.files", "no", "X", "god"])
def test_gate_stable_foreign_text_is_not_excused_by_box_geometry(extra: str) -> None:
    brief = gate.InfographicBrief("2 files", (gate.BriefLine("chip", "2 files"),))
    words = (
        gate.OcrWord("2", 95, (0, 0, 15, 20)),
        gate.OcrWord("files", 95, (25, 0, 50, 20)),
        gate.OcrWord(extra, 95, (50, 75, 36, 60)),
        gate.OcrWord("files", 95, (100, 100, 50, 20)),
    )
    reads = tuple(gate.OcrRead(str(i), words) for i in range(4))
    decision = gate.score_ocr(reads, brief)
    assert decision.verdict == "invented"
    assert gate.tokenize(extra)[0] in dict(decision.invented)


@pytest.mark.parametrize(
    "expected,actual", [("untested code", "tested code"), ("2 files removed", "2 files moved")]
)
def test_gate_rejects_stable_words_that_change_meaning(expected: str, actual: str) -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("row", expected),))
    decision = gate.score_ocr(tuple(read(actual, str(i), 95) for i in range(4)), brief)
    assert decision.verdict == "invented"


@pytest.mark.parametrize(
    "actual", ["Tests no passed no CI", "Tests passed no no CI", "Tests passed noci noci"]
)
def test_gate_accounts_for_extra_occurrences_of_allowed_words(actual: str) -> None:
    brief = gate.InfographicBrief(
        "t", (gate.BriefLine("row", "Tests passed"), gate.BriefLine("chip", "no CI"))
    )
    decision = gate.score_ocr(tuple(read(actual, str(i), 95) for i in range(4)), brief)
    assert decision.verdict != "pass"


def test_gate_cannot_publish_a_relation_free_text_card(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("chip", "2 files"),))
    monkeypatch.setattr(gate, "tesseract_version", lambda: "test")
    monkeypatch.setattr(gate, "_read_mode", lambda *args: read("2 files", "test").words)
    assert gate.gate(tmp_path / "card.png", brief).verdict == "flat"


def test_go_mapping_rejects_multiple_assignment_expressions() -> None:
    text = "func load() (*File, error) {\nresult, err := getValue(), fail()\nif err != nil {\nreturn nil, &LoadError{Err: err}\n}\n}"
    m = {
        "files": [
            {
                "path": "file.go",
                "hunks": [
                    {
                        "lines": [
                            {"new": i, "old": None, "text": line}
                            for i, line in enumerate(text.splitlines(), 1)
                        ]
                    }
                ],
            }
        ]
    }
    assert gate._mapping(m, {"file.go": text}) == []


def test_ocr_recombines_split_words_before_counting_individual_tokens() -> None:
    br = gate.InfographicBrief(
        "checkout counter",
        (
            gate.BriefLine("headline", "checkout counter"),
            gate.BriefLine("verdict", "check result"),
        ),
    )
    reads = tuple(read("check out counter check result", str(i)) for i in range(4))
    assert gate.score_ocr(reads, br).verdict == "pass"


def test_ocr_requires_each_duplicate_line_occurrence() -> None:
    br = gate.InfographicBrief(
        "Tests passed",
        (
            gate.BriefLine("headline", "Tests passed"),
            gate.BriefLine("verdict", "Tests passed"),
        ),
    )
    reads = tuple(read("Tests passed", str(i)) for i in range(4))
    assert gate.score_ocr(reads, br).verdict == "missing"


def test_before_after_rejects_function_like_text_inside_a_multiline_string() -> None:
    m = sample_map()
    file = m["files"][0]
    file["hunks"] = [
        {
            "lines": [
                {"old": 10, "new": 10, "text": "def apply_discount():"},
                {"old": 11, "new": None, "text": '    """old docs."""'},
                {"old": None, "new": 11, "text": '    """new docs."""'},
            ]
        }
    ]
    old = (
        "def outer():\n    value = '''\n"
        + "\n" * 7
        + 'def apply_discount():\n    """old docs."""\n'
        + "'''"
    )
    sources = {file["path"]: old.replace("old docs", "new docs"), "base:" + file["path"]: old}
    assert gate._before_after(m, sources) == []


def test_before_after_does_not_pair_an_outer_doc_with_an_inner_doc() -> None:
    m = sample_map()
    old = (
        "\n" * 9
        + 'def apply_discount():\n    """Old outer docs."""\n    def inner():\n        """Inner docs."""\n        pass\n'
    )
    new = old.replace('    """Old outer docs."""\n', "")
    rows = [
        {"old": i, "new": i if i < 11 else i - 1, "text": line}
        for i, line in enumerate(old.splitlines(), 1)
    ]
    rows[10]["new"] = None
    m["files"][0]["hunks"] = [{"lines": rows}]
    path = m["files"][0]["path"]
    assert gate._before_after(m, {path: new, "base:" + path: old}) == []


def test_ocr_split_words_use_their_line_context() -> None:
    br = gate.InfographicBrief(
        "checkout counter",
        (
            gate.BriefLine("headline", "checkout counter"),
            gate.BriefLine("verdict", "check out result"),
        ),
    )
    reads = tuple(read("check out counter check out result", str(i)) for i in range(4))
    assert gate.score_ocr(reads, br).verdict == "pass"


def test_ocr_does_not_merge_numeric_facts() -> None:
    br = gate.InfographicBrief("CI", (gate.BriefLine("chip", "CI 1/1 passed"),))
    reads = tuple(read("CI 11 passed", str(i), 95) for i in range(4))
    assert gate.score_ocr(reads, br).verdict == "invented"


@pytest.mark.parametrize("wrapper_added", [True, False])
def test_go_mapping_preserves_leading_blank_source_lines(wrapper_added: bool) -> None:
    text = "\n\nfunc load() (*File, error) {\nraw, err := reader()\nif err != nil {\nreturn nil, &LoadError{Err: err}\n}\n}"
    rows = [
        {"new": i, "old": None if (i == 6 if wrapper_added else i == 4) else i, "text": line}
        for i, line in enumerate(text.splitlines(), 1)
    ]
    m = {"files": [{"path": "file.go", "hunks": [{"lines": rows}]}]}
    assert gate._mapping(m, {"file.go": text}) == (
        [gate.Relation("reader", "LoadError", "maps")] if wrapper_added else []
    )


def test_ocr_does_not_merge_compact_numeric_facts() -> None:
    br = gate.InfographicBrief("CI", (gate.BriefLine("chip", "CI1/1 passed"),))
    reads = tuple(read("CI11 passed", str(i), 95) for i in range(4))
    assert gate.score_ocr(reads, br).verdict == "invented"
