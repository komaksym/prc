from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from prc.presentation import infographic as gate

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / "tests" / "data" / "infographic" / "panels"
SLUGS = ("v4a", "opus-v4b", "opus-v4c", "deepseek-v4b", "deepseek-v4c", "glm-v4a", "glm-v4b")


def panels_brief(slug: str) -> gate.InfographicBrief:
    payload = json.loads((PANELS / f"{slug}.json").read_text())
    lines = tuple(
        gate.BriefLine(cast(gate.Role, str(line["role"])), str(line["text"]))
        for line in payload["lines"]
    )
    relations = tuple(
        gate.Relation(str(rel["from"]), str(rel["to"]), cast_kind(str(rel["kind"])))
        for rel in payload.get("relations", [])
    )
    mode = cast(gate.Mode, str(payload.get("mode", "panels")))
    return gate.InfographicBrief(str(payload["title"]), lines, relations, mode)


def cast_kind(kind: str) -> gate.RelationKind:
    return cast(gate.RelationKind, kind)


@pytest.mark.parametrize("slug", SLUGS)
def test_panels_drawn_candidates_pass_the_gate(slug: str) -> None:
    decision = gate.gate(PANELS / f"{slug}.png", panels_brief(slug))
    assert decision.verdict == "pass", (decision.verdict, decision.invented)


def test_panels_planted_word_is_invented() -> None:
    reads, failed = gate.read_modes(PANELS / "v4a.png")
    assert not failed
    box: gate.Box = (1500, 2, 80, 30)
    planted = tuple(
        gate.OcrRead(read.mode, (*read.words, gate.OcrWord("blockchain", 90.0, box)))
        for read in reads
    )
    decision = gate.score_ocr(planted, panels_brief("v4a"))
    assert decision.verdict == "invented"
    assert "blockchain" in dict(decision.invented)


def test_panels_missing_line_is_missing() -> None:
    brief = panels_brief("v4a")
    extra = gate.BriefLine("item", "Blockchain audit trail")
    lines = (*brief.lines[:-1], extra, brief.lines[-1])
    extended = gate.InfographicBrief(brief.title, lines, brief.relations, brief.mode)
    decision = gate.gate(PANELS / "v4a.png", extended)
    assert decision.verdict == "missing"
    assert any("Blockchain audit trail" in text for text, _ in decision.missing)


def line_read(text: str, mode: str) -> gate.OcrRead:
    words = []
    x = 0
    for part in text.split():
        words.append(gate.OcrWord(part, 90.0, (x, 0, 40, 20)))
        x += 50
    return gate.OcrRead(mode, tuple(words))


def disclosure_brief() -> gate.InfographicBrief:
    return gate.InfographicBrief(
        "Cart totals",
        (gate.BriefLine("headline", "Cart totals"), gate.BriefLine("note", gate.DISCLOSURE)),
    )


def test_gate_footer_prc_read_as_pre_passes() -> None:
    brief = disclosure_brief()
    drawn = "Cart totals Infographic drawn by AI Words from pre"
    reads = tuple(line_read(drawn, str(mode)) for mode in range(4))
    assert gate.score_ocr(reads, brief).verdict == "pass"


def test_gate_uppercase_disclosure_passes() -> None:
    brief = disclosure_brief()
    drawn = "Cart totals Infographic drawn by AI Words from PRC"
    reads = tuple(line_read(drawn, str(mode)) for mode in range(4))
    assert gate.score_ocr(reads, brief).verdict == "pass"


def boxed(parts: list[tuple[str, float, gate.Box]]) -> tuple[gate.OcrWord, ...]:
    return tuple(gate.OcrWord(text, conf, box) for text, conf, box in parts)


def test_gate_split_header_word_with_stray_reading_passes() -> None:
    brief = gate.InfographicBrief(
        "t", (gate.BriefLine("panel", "1. BEFORE"), gate.BriefLine("panel", "2. CHANGE"))
    )
    plain = [("1.", 95.0, (0, 0, 20, 20)), ("BEFORE", 96.0, (30, 0, 70, 20))]
    plain += [("2.", 95.0, (0, 40, 20, 20)), ("CHA", 96.0, (30, 40, 40, 20))]
    plain += [("NGE", 93.0, (75, 40, 40, 20))]
    stray = ("1", 90.0, (200, 200, 20, 20))
    split = plain[:4] + [stray] + plain[4:]
    reads = tuple(gate.OcrRead(str(mode), boxed(split if mode < 2 else plain)) for mode in range(4))
    assert gate.score_ocr(reads, brief).verdict == "pass"


def test_gate_split_pieces_of_a_foreign_word_are_invented() -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("panel", "2. CHANGE"),))
    parts = [("2.", 95.0, (0, 0, 20, 20)), ("CHU", 96.0, (30, 0, 40, 20))]
    parts += [("NGE", 93.0, (75, 0, 40, 20))]
    reads = tuple(gate.OcrRead(str(mode), boxed(parts)) for mode in range(4))
    decision = gate.score_ocr(reads, brief)
    assert decision.verdict == "invented"
    assert {"chu", "nge"} <= set(dict(decision.invented))


def unstable_digit_reads(extra_in: int) -> tuple[gate.OcrRead, ...]:
    base = "Cart totals Infographic drawn by AI Words from prc"
    lone: gate.Box = (1500, 2, 18, 23)
    reads = []
    for mode in range(4):
        words = tuple(
            gate.OcrWord(part, 90.0, (i * 50, 0, 40, 20)) for i, part in enumerate(base.split())
        )
        if mode < extra_in:
            words = (*words, gate.OcrWord("4", 96.0, lone))
        reads.append(gate.OcrRead(str(mode), words))
    return tuple(reads)


def test_gate_lone_unstable_digit_is_an_icon_reading() -> None:
    assert gate.score_ocr(unstable_digit_reads(2), disclosure_brief()).verdict == "pass"


def test_gate_stable_lone_digit_is_invented() -> None:
    decision = gate.score_ocr(unstable_digit_reads(4), disclosure_brief())
    assert decision.verdict == "invented"
    assert "4" in dict(decision.invented)


def item_reads(lead: tuple[str, gate.Box]) -> tuple[gate.OcrRead, ...]:
    """A list item "Rows fetched" drawn 30 px tall, led by one extra reading."""
    words = (
        gate.OcrWord(lead[0], 90.0, lead[1]),
        gate.OcrWord("Rows", 95.0, (40, 0, 60, 30)),
        gate.OcrWord("fetched", 95.0, (110, 0, 100, 30)),
    )
    return tuple(gate.OcrRead(str(mode), words) for mode in range(4))


def item_brief() -> gate.InfographicBrief:
    return gate.InfographicBrief("t", (gate.BriefLine("item", "Rows fetched"),))


def test_gate_bullet_dot_before_a_list_item_passes() -> None:
    # GLM v4-a: every read sees the 12 px bullet dot before "Rows" as "e".
    assert gate.score_ocr(item_reads(("e", (10, 9, 12, 12))), item_brief()).verdict == "pass"


def test_gate_full_height_letter_before_a_list_item_is_invented() -> None:
    decision = gate.score_ocr(item_reads(("x", (10, 0, 24, 30))), item_brief())
    assert decision.verdict == "invented"
    assert "x" in dict(decision.invented)


def proof_reads(other: str) -> tuple[gate.OcrRead, ...]:
    """Read 0 clips "PROOF" to "PROO"; read 1 sees `other` there; reads 2 and 3 see nothing."""
    head = gate.OcrWord("3.", 93.0, (0, 0, 40, 37))
    clipped = gate.OcrWord("PROO", 92.0, (62, 0, 134, 37))
    seen = gate.OcrWord(other, 95.0, (62, 0, 162, 37))
    return (
        gate.OcrRead("0", (head, clipped)),
        gate.OcrRead("1", (head, seen)),
        gate.OcrRead("2", (head,)),
        gate.OcrRead("3", (head,)),
    )


def test_gate_word_clipped_in_one_read_passes_when_another_read_sees_it_whole() -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("panel", "3. PROOF"),))
    assert gate.score_ocr(proof_reads("PROOF"), brief).verdict == "pass"


def test_gate_prefix_no_read_completes_is_invented() -> None:
    brief = gate.InfographicBrief("t", (gate.BriefLine("panel", "3. PROOFS"),))
    decision = gate.score_ocr(proof_reads("PRO"), brief)
    assert decision.verdict == "invented"
    assert "proo" in dict(decision.invented)


def test_panels_prompt_requires_plain_header_bars_and_glyph_free_icons() -> None:
    brief = panels_brief("v4a")
    assert "plain solid" in gate.prompt(brief)
    assert "no letters, digits or digit-like shapes" in gate.prompt(brief)
    assert any("plain solid header bar" in rule for rule in gate.PANEL_RULES)
    assert any("digit-like shapes" in rule for rule in gate.PANEL_RULES)
