"""Question lint: the four parent review rules for study v3 questions."""

from __future__ import annotations

from typing import Any

import pytest

from prc.evaluation import question_lint


def mc(qid: str, options: list[str], key: str, prompt: str = "prompt") -> dict[str, Any]:
    return {
        "qid": qid,
        "kind": "multiple_choice",
        "prompt": prompt,
        "options": options,
        "key": key,
        "required_elements": [],
        "rubric": {"multiple_choice": [0.0, 1.0], "short": [0.0, 0.5, 1.0]},
        "evidence": "evidence",
    }


def short(qid: str, prompt: str, key: str = "key", evidence: str = "e") -> dict[str, Any]:
    return {
        "qid": qid,
        "kind": "short",
        "prompt": prompt,
        "key": key,
        "required_elements": ["first element", "second element"],
        "rubric": {"multiple_choice": [0.0, 1.0], "short": [0.0, 0.5, 1.0]},
        "evidence": evidence,
    }


EVIDENCE = (
    '[{"path": "scripts/fetch_probe.py", "symbol": "collect_rows",'
    ' "side": "head", "supports": "paged fetch keeps valid rows"}]'
)

TITLE = "Fetch live snapshot rows for the daily report"


def test_option_balance_rejects_unique_longest_key() -> None:
    key = "k" * 232
    options = [key, "b" * 122, "c" * 134, "d" * 116]
    errors = question_lint.check_option_balance(mc("s-q1", options, key))
    assert any("option-balance" in e and "s-q1" in e for e in errors)


def test_option_balance_rejects_unique_shortest_key() -> None:
    key = "k" * 61
    options = ["a" * 164, "b" * 160, key, "d" * 166]
    errors = question_lint.check_option_balance(mc("s-q1", options, key))
    assert any("option-balance" in e and "s-q1" in e for e in errors)


def test_option_balance_rejects_outlier_beyond_quarter_mean() -> None:
    key = "k" * 100
    options = [key, "b" * 102, "c" * 60, "d" * 101]
    errors = question_lint.check_option_balance(mc("s-q1", options, key))
    assert any("option-balance" in e and "s-q1" in e for e in errors)


def test_option_balance_accepts_even_set_with_middle_key() -> None:
    key = "k" * 100
    options = ["a" * 96, key, "c" * 104, "d" * 98]
    assert question_lint.check_option_balance(mc("s-q1", options, key)) == []


def test_option_balance_allows_tied_longest_key() -> None:
    key = "k" * 110
    options = [key, "b" * 110, "c" * 96, "d" * 104]
    assert question_lint.check_option_balance(mc("s-q1", options, key)) == []


def test_prompt_leak_rejects_file_and_symbol_names() -> None:
    q = short(
        "s-q2",
        "Read collect_rows in scripts/fetch_probe.py and describe the risk.",
        evidence=EVIDENCE,
    )
    errors = question_lint.check_prompt_leak(q, TITLE)
    assert any("prompt-leak" in e and "s-q2" in e for e in errors)


def test_prompt_leak_allows_pr_number_and_title_words() -> None:
    q = short(
        "s-q2",
        "PR #7, Fetch live snapshot rows for the daily report. "
        "What rows does the change keep that the base revision skipped?",
        evidence=EVIDENCE,
    )
    assert question_lint.check_prompt_leak(q, TITLE) == []


def test_cross_pair_rejects_option_echoing_another_reading() -> None:
    own = "It pages the live table and keeps valid rows while counting skips."
    other = "A standalone one-click HTML report from a snapshot file."
    options = [
        "It pages the live table and keeps more valid rows than before.",
        "It renders the daily HTML report from an existing snapshot file.",
        "It migrates the table schema to add a new column.",
        "It de-duplicates rows across pages before writing the file.",
    ]
    errors = question_lint.check_cross_pair_leak("s-q1", options, own, {"t": other})
    assert any("cross-pair-leak" in e and "s-q1" in e for e in errors)


def test_cross_pair_allows_single_generic_overlap() -> None:
    own = "It pages the live table and keeps valid rows while counting skips."
    other = "A standalone one-click HTML report from a snapshot file."
    options = [
        "It keeps more valid rows from the live table than the base did.",
        "It counts the skipped rows and writes the kept rows to a file.",
        "It retries the fetch twice before it records a failure.",
        "It pages through every offset until the table is exhausted.",
    ]
    assert question_lint.check_cross_pair_leak("s-q1", options, own, {"t": other}) == []


def test_later_change_rejects_followup_ask() -> None:
    q = short(
        "s-q2",
        "What is the main risk, and which later change proves the first "
        "version under-repaired? Read the follow-up PR #22 in the same repo.",
    )
    errors = question_lint.check_later_change(q, own_number="21")
    assert any("later-change" in e and "s-q2" in e for e in errors)


def test_later_change_allows_own_pr_number() -> None:
    q = short("s-q2", "PR #21, Tracer with dispatch workflow. What could break?")
    assert question_lint.check_later_change(q, own_number="21") == []


CUE_TITLE = "Treat a missing oracle reference as not_found"


def test_title_cue_rejects_key_that_alone_echoes_the_title() -> None:
    key = "It records a not_found flag and returns an empty reference set early."
    options = [
        "It retries the lookup twice with backoff and then raises the old error.",
        "It skips only the failed lookup and resumes with the remaining rows.",
        "It marks the run truncated and compares against the partial rows.",
        key,
    ]
    errors = question_lint.check_title_cue(mc("s-q1", options, key), CUE_TITLE)
    assert errors == [
        "title-cue s-q1: only the key shares 2 title words (found, reference); "
        "the best other option shares 0"
    ]


def test_title_cue_allows_options_that_share_the_title_framing() -> None:
    key = "On not_found the run skips the reference comparison and still passes."
    options = [
        "On not_found the run retries the reference page twice and then fails.",
        key,
        "On not_found the run compares against an empty reference and fails.",
        "On not_found the run keeps the partial reference rows it fetched.",
    ]
    assert question_lint.check_title_cue(mc("s-q1", options, key), CUE_TITLE) == []


def test_lint_study_reports_every_rule_with_question_id() -> None:
    key = "k" * 200
    bad_mc = mc(
        "bad-q1",
        [key, "b" * 80, "c" * 82, "d" * 84],
        key,
        prompt="Read collect_rows in scripts/fetch_probe.py. What changed?",
    )
    bad_mc["evidence"] = EVIDENCE
    bad_short = short(
        "bad-q2",
        "What is the risk, and which later change proves it? See follow-up PR #9.",
    )
    other_mc = mc(
        "other-q1",
        [
            "A standalone one-click HTML report from a snapshot file.",
            "It pages the live snapshot table and keeps the valid rows.",
            "A digest message sent to the operator every morning.",
            "A merged file with repeated rows combined into single rows.",
        ],
        "A standalone one-click HTML report from a snapshot file.",
        prompt="PR #8, Standalone one-click HTML report. What changed?",
    )
    questions = {
        "bad": [bad_mc, bad_short, short("bad-q3", "PR #7. Merge?")],
        "other": [
            other_mc,
            short("other-q2", "PR #8. Risk?"),
            short("other-q3", "PR #8. Merge?"),
        ],
    }
    meta = {
        "bad": {"title": TITLE, "pr_identity": "owner/repo#7"},
        "other": {
            "title": "Standalone one-click HTML report",
            "pr_identity": "owner/repo#8",
        },
    }
    errors = question_lint.lint_study(questions, meta)
    joined = "\n".join(errors)
    for rule in ("option-balance", "prompt-leak", "cross-pair-leak", "later-change", "title-cue"):
        assert rule in joined
    assert "bad-q1" in joined and "bad-q2" in joined and "title-cue other-q1" in joined


def test_kit_load_manifest_rejects_uneven_options(make_paired: Any) -> None:
    from prc.evaluation import kit

    fixture = make_paired(pairs=1)
    snap = fixture.data["pairs"][0]["snapshots"][0]
    key = "k" * 200
    snap["questions"][0]["options"] = [key, "b" * 80, "c" * 82, "d" * 84]
    snap["questions"][0]["key"] = key
    fixture.save()
    with pytest.raises(kit.KitError, match="option-balance"):
        kit.load_manifest(fixture.manifest)
