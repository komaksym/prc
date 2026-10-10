"""Part A gate tests 1-12: brief sources, determinism, and pure OCR scoring."""

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
    ("Se", 79),
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
    head = ["level", "page", "block", "par", "line", "word", "l", "t", "w", "h", "conf", "text"]
    rows = [chr(9).join(head)]
    for i, (word, conf) in enumerate(words):
        rows.append(
            chr(9).join(
                ["5", "1", "1", "1", "1", str(i + 1), "0", "0", "10", "10", str(conf), word]
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


def test_gate_measured_noise_passes() -> None:
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


def test_gate_prose_word_keeps_ocr_tolerance() -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("verdict", "No direct test evidence"),))
    drawn = "No direct test evidcnce"
    decision = gate.score_ocr((read(drawn, "psm-3"), read(drawn, "psm-11")), brief)
    assert decision.verdict == "pass"


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
    "next-steps-roadmap": ("missing", ("1", "2", "Everything frozen")),
    "review-bias-2026-10-10": ("invented", ("all",)),
}


def test_gate_session_images_reject_only_what_ocr_cannot_confirm() -> None:
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
    monkeypatch.setattr(gate.shutil, "which", lambda _name: "/broken/tesseract")
    assert "unavailable" in doctor._tesseract()
    assert " ok" not in doctor._tesseract()
