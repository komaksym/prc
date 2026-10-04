"""Brief domain and renderer failure modes that the E2E cannot reach cheaply."""

from __future__ import annotations

import pytest

from prc.brief import Brief, Check, Delta, Mismatch, brief_of, units_of
from prc.presentation.render_brief import MARKER, render_brief, span


def delta(path: str, diff: str = "", head: str = "", added: int = 1, removed: int = 0) -> Delta:
    return Delta(path, False, added, removed, diff, head)


def make(body: str, *deltas: Delta, title: str = "T", checks: tuple[Check, ...] = ()) -> Brief:
    return brief_of("o/r#1", title, body, "abc", deltas, checks)


def kinds(brief: Brief) -> list[str]:
    return [m.kind for m in brief.mismatches]


def test_units_drop_fences_comments_details_quotes_and_split_sentences() -> None:
    body = (
        "Intro one. Intro two.\n"
        "~~~\nupdate `a.py`\n~~~\n"
        "<!-- updated `b.py`\nstill hidden -->\n"
        "<details>\n<details>nested update `c.py`</details>\nupdate `d.py`\n</details>\n"
        "> update `e.py`\n"
        "- [ ] todo\n- [x] done\n"
    )

    assert [(u.text, u.checked) for u in units_of("Title", body)] == [
        ("Title", None),
        ("Intro one.", None),
        ("Intro two.", None),
        ("todo", False),
        ("done", True),
    ]


def test_unchecked_checkbox_claims_nothing() -> None:
    assert make("- [ ] Updated `README.md`\n- [ ] All tests pass").mismatches == ()


def test_change_verb_with_unmatched_path_is_flagged_but_plain_mention_is_not() -> None:
    flagged = make("Updated `docs/missing.md`", delta("src/a.py"))
    plain = make("See `docs/missing.md` for details", delta("src/a.py"))

    assert kinds(flagged) == ["changed_claim_not_in_diff"]
    assert flagged.mismatches[0].subjects == ("docs/missing.md",)
    assert plain.mismatches == ()


def test_arrow_counts_as_a_change_verb() -> None:
    assert kinds(make("`old.py` -> `new.py`", delta("src/a.py"))) == ["changed_claim_not_in_diff"]


def test_suffix_basename_and_directory_tokens_match() -> None:
    workflow = delta(".github/workflows/release.yml")

    assert make("Update `release.yml`", workflow).mismatches == ()
    assert make("Update `workflows/release.yml`", workflow).mismatches == ()
    assert make("Refactor `src/`", delta("src/pkg/a.py")).mismatches == ()
    assert make("Refactor src/pkg/ internals", delta("src/pkg/a.py")).mismatches == ()
    assert kinds(make("Refactor `lib/`", delta("src/pkg/a.py"))) == ["changed_claim_not_in_diff"]
    assert kinds(make("Update `elease.yml`", workflow)) == ["changed_claim_not_in_diff"]


def test_urls_are_ignored() -> None:
    assert (
        make("Updated the guide at https://example.com/docs/guide.md", delta("a.py")).mismatches
        == ()
    )


@pytest.mark.parametrize(
    ("claim", "present"),
    [
        ("Adds `gifSpec(result)`", "gifSpec"),
        ("Adds `CsRegs::enableZicfiss`", "enableZicfiss"),
        ("Adds `mod.sub.helper`", "helper"),
    ],
)
def test_symbol_claims_check_the_last_segment(claim: str, present: str) -> None:
    assert make(claim, delta("a.py", diff=f"+def {present}(): pass")).mismatches == ()

    missing = make(claim, delta("a.py", diff="+x = 1"))

    assert kinds(missing) == ["symbol_claim_not_found"]
    assert missing.mismatches[0].subjects == (present,)


def test_symbol_can_be_found_in_head_content_or_removed_lines() -> None:
    assert make("Removes `old_name`", delta("a.py", diff="-def old_name(): pass")).mismatches == ()
    assert make("Adds `kept`", delta("a.py", head="kept = 1\n")).mismatches == ()


def test_fix_with_backticked_error_is_not_a_symbol_claim() -> None:
    assert make("Fix `KeyError` in parser", delta("a.py", diff="+x = 1")).mismatches == ()


def test_empty_body_has_no_mismatches_and_every_code_and_config_file_is_unnamed() -> None:
    brief = make("", delta("src/a.py"), delta("ci.yml"), delta("README.md"), title="")

    assert brief.mismatches == ()
    assert [f.named for f in brief.files if f.kind in ("code", "config")] == [False, False]


@pytest.mark.parametrize("body", ["All tests pass.", "- [x] All tests pass", "CI is green"])
def test_passing_claim_with_no_checks_says_no_checks_ran(body: str) -> None:
    brief = make(body, delta("a.py"))

    assert kinds(brief) == ["test_claim_vs_ci"]
    assert brief.mismatches[0].fact == "no checks ran on this commit"


def test_passing_claim_is_fine_when_checks_pass_or_pending_and_flagged_when_one_failed() -> None:
    ok = (Check("unit", "passed"),)
    pending = (Check("unit", "pending"),)
    failed = (Check("unit", "passed"), Check("lint", "failed"))

    assert make("All tests pass", delta("a.py"), checks=ok).mismatches == ()
    assert make("All tests pass", delta("a.py"), checks=pending).mismatches == ()
    assert make("All tests pass", delta("a.py"), checks=failed).mismatches[0].subjects == ("lint",)
    assert make("Tests do not pass yet", delta("a.py"), checks=failed).mismatches == ()


def test_tests_claim_is_satisfied_by_any_changed_test_file() -> None:
    assert kinds(make("Adds unit tests", delta("src/a.py"))) == ["tests_claim_no_test_files"]
    assert make("Adds unit tests", delta("src/a.py"), delta("tests/test_a.py")).mismatches == ()
    assert make("No tests added", delta("src/a.py")).mismatches == ()


def test_named_by_path_stem_or_defined_symbol() -> None:
    brief = make(
        "Touches the parser and `frobnicate`.",
        delta("src/parser.py"),
        delta("src/ci.py"),
        delta("src/other.py", diff="+def frobnicate(x):\n+    pass"),
        delta("src/untouched.py"),
    )

    assert {f.path: f.named for f in brief.files} == {
        "src/ci.py": False,
        "src/other.py": True,
        "src/parser.py": True,
        "src/untouched.py": False,
    }


def test_lockfile_only_pr_has_no_pointers_and_no_unnamed_section() -> None:
    brief = make("", delta("uv.lock", added=500, removed=400))
    text = render_brief(brief)

    assert brief.look_first == ()
    assert "Not named in the description" not in text
    assert "Generated files" in text and "+500 −400" in text
    assert "Nothing stands out." in text


def test_manifest_pointer_carries_up_to_three_added_lines() -> None:
    diff = "--- a\n+++ b\n+one\n+two\n+three\n+four\n"
    brief = make("", delta("pyproject.toml", diff=diff))

    assert brief.look_first[0].lines == ("one", "two", "three")


def test_look_first_order_and_cap() -> None:
    brief = make(
        "Named: `named.py`",
        delta("src/named.py", added=99),
        delta("src/big.py", added=50),
        delta("src/small.py", added=2),
        delta(".github/workflows/w.yml", added=1),
        delta("pyproject.toml", added=1),
    )

    assert [p.path for p in brief.look_first] == [
        ".github/workflows/w.yml",
        "pyproject.toml",
        "src/big.py",
    ]


def test_span_neutralizes_backticks_controls_newlines_and_length() -> None:
    assert span("a`b") == "`a'b`"
    assert span("x\n@evil\r\x1b[31m‮") == "`x @evil [31m`"
    assert span("p" * 500) == "`" + "p" * 139 + "…`"


def test_render_never_leaks_pr_strings_outside_code_spans() -> None:
    hostile = "src/a`b.py\n![x](http://e/x.png) @maintainer <script>"
    brief = Brief(
        "o/r#1",
        "t",
        "abc",
        make("", delta("src/ok.py")).files,
        (Check("<b>ci`x</b>", "failed"),),
        (Mismatch("changed_claim_not_in_diff", hostile, "no changed file matches", (hostile,)),),
        make("", delta(hostile)).look_first,
    )
    text = render_brief(brief)

    assert text.startswith(MARKER + "\n")

    for line in text.splitlines():
        assert line.count("`") % 2 == 0
        outside = "".join(line.split("`")[::2])

        for danger in ("@maintainer", "<script", "![", "http", "<b>"):
            assert danger not in outside
