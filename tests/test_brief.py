from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from prc.brief import Brief, Check, Delta, Mismatch, brief_of, path_tokens, units_of
from prc.gitutil import list_paths
from prc.presentation.render_brief import MARKER, render_brief, span


def delta(path: str, diff: str = "", head: str = "", added: int = 1, removed: int = 0) -> Delta:
    return Delta(path, False, added, removed, diff, head)


def make(
    body: str,
    *deltas: Delta,
    title: str = "T",
    checks: tuple[Check, ...] = (),
    known: tuple[str, ...] = (),
) -> Brief:
    tree = frozenset(known) | {d.path for d in deltas}

    return brief_of("o/r#1", title, body, "abc", deltas, checks, tree)


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
    flagged = make("Updated `docs/missing.md`", delta("src/a.py"), known=("docs/missing.md",))
    plain = make("See `docs/missing.md` for details", delta("src/a.py"), known=("docs/missing.md",))

    assert kinds(flagged) == ["changed_claim_not_in_diff"]
    assert flagged.mismatches[0].subjects == ("docs/missing.md",)
    assert plain.mismatches == ()


def test_arrow_counts_as_a_change_verb() -> None:
    brief = make("`old.py` -> `new.py`", delta("src/a.py"), known=("old.py", "new.py"))

    assert kinds(brief) == ["changed_claim_not_in_diff"]


def test_suffix_basename_and_directory_tokens_match() -> None:
    workflow = delta(".github/workflows/release.yml")

    assert make("Update `release.yml`", workflow).mismatches == ()
    assert make("Update `workflows/release.yml`", workflow).mismatches == ()
    assert make("Refactor `src/`", delta("src/pkg/a.py")).mismatches == ()
    assert make("Refactor src/pkg/ internals", delta("src/pkg/a.py")).mismatches == ()
    assert kinds(make("Refactor `lib/`", delta("src/pkg/a.py"), known=("lib/x.py",))) == [
        "changed_claim_not_in_diff"
    ]
    assert kinds(make("Update `elease.yml`", workflow, known=("elease.yml",))) == [
        "changed_claim_not_in_diff"
    ]


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

    assert [(p.path, p.reason) for p in brief.look_first] == [
        (".github/workflows/w.yml", "CI workflow; its path is not in the description"),
        ("pyproject.toml", "dependency manifest; its path is not in the description"),
        ("src/named.py", "largest code change (+99 −0)"),
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


def test_path_token_must_exist_in_the_tree_to_be_a_claim() -> None:
    body = "Updated `codex/` and `api/v2/users.py` and `plugins`"

    assert make(body, delta("src/a.py")).mismatches == ()

    flagged = make("Updated `docs/guide.md`", delta("src/a.py"), known=("docs/guide.md",))

    assert flagged.mismatches[0].subjects == ("docs/guide.md",)


@pytest.mark.parametrize(
    ("token", "tree"),
    [
        ("guide.md", "docs/guide.md"),
        ("docs/guide.md", "site/docs/guide.md"),
        ("docs/", "site/docs/guide.md"),
        ("site/docs", "site/docs/guide.md"),
        ("./site/docs/guide.md", "site/docs/guide.md"),
    ],
)
def test_existence_matches_full_path_suffix_and_directory(token: str, tree: str) -> None:
    brief = make(f"Updated `{token}`", delta("src/a.py"), known=(tree,))

    assert kinds(brief) == ["changed_claim_not_in_diff"]


def test_a_file_name_is_not_a_directory_claim() -> None:
    assert make("Updated `guide.md/`", delta("src/a.py"), known=("docs/guide.md",)).mismatches == ()


def test_list_paths_returns_every_file_of_a_commit(tmp_path: Path) -> None:
    def vcs(*args: str) -> str:
        done = subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *args],
            capture_output=True, text=True, check=True,
        )  # fmt: skip

        return done.stdout.strip()

    vcs("init", "-q")
    (tmp_path / "a dir").mkdir()
    (tmp_path / "a dir" / "b.py").write_text("x")
    (tmp_path / "top.md").write_text("x")
    vcs("add", ".")
    vcs("commit", "-qm", "c")

    assert list_paths(tmp_path, vcs("rev-parse", "HEAD")) == ("a dir/b.py", "top.md")


def test_verb_inside_a_code_span_is_not_a_change_verb() -> None:
    quote = (
        "Live on :5173: an invalid POST to `profile?/update` and to `recurring?/togglePaid`"
        " returns 400"
    )

    assert make(quote, delta("src/a.py"), known=("profile/update",)).mismatches == ()


def test_verb_touching_a_hyphen_is_not_a_change_verb() -> None:
    quote = "The add-on's options page lists a plugin bridge as a `mcp-bridge.cjs` file"

    assert make(quote, delta("src/a.py"), known=("mcp-bridge.cjs",)).mismatches == ()
    assert kinds(make("Add `mcp-bridge.cjs`", delta("src/a.py"), known=("mcp-bridge.cjs",)))


def test_emphasis_markers_do_not_glue_sentences_together() -> None:
    body = (
        "No rule or substantive meaning is changed.** This PR reconciles the reviews"
        " (`governance/reviews/X.md`)."
    )
    texts = [u.text for u in units_of("", body)]

    assert texts == [
        "No rule or substantive meaning is changed.",
        "This PR reconciles the reviews (`governance/reviews/X.md`).",
    ]
    assert [u.text for u in units_of("", "A __bold__ move. See `__init__.py`.")] == [
        "A bold move.",
        "See `__init__.py`.",
    ]


def test_table_rows_are_units_and_separator_rows_are_dropped() -> None:
    body = "Results:\n| a | b |\n|---|:-:|\n| `x.py` | updated |\nAfter."

    assert [u.text for u in units_of("", body)] == [
        "Results:",
        "| a | b |",
        "| `x.py` | updated |",
        "After.",
    ]


def test_ticked_path_does_not_leak_bare_fragments() -> None:
    assert path_tokens("Updated `budget/+page.server.ts`") == ("budget/+page.server.ts",)
    assert path_tokens("Updated src/pkg/mod.py and lib/") == ("src/pkg/mod.py", "lib/")


def test_verb_in_code_span_with_a_real_path_is_still_not_a_claim() -> None:
    brief = make(
        "The handler `update/profile.ts` returns 400",
        delta("src/a.py"),
        known=("update/profile.ts",),
    )

    assert brief.mismatches == ()


@pytest.mark.parametrize(
    "quote",
    [
        "pin bumped to 17992/`0xfeb7`",
        "Updated the routes at //",
        "Run the /plugin command after you update it",
        "Update the `@openai/codex` package",
        "Update `jules.google.com/task/` links",
        "Update `profile?/update` handling",
        "Update `a=b/c.py` and `x&y/z.py` and `d#e/f.py`",
    ],
)
def test_non_paths_are_not_path_claims(quote: str) -> None:
    assert path_tokens(quote) == ()


def test_path_token_shape() -> None:
    assert path_tokens("`17992/` `//` `/plugin` `@openai/codex` `jules.google.com/task/`") == ()
    assert path_tokens("`profile?/update` `a b/c.py` `a:b/c.py` `src/(app)/dash/+page.ts`") == (
        "src/(app)/dash/+page.ts",
    )
    assert path_tokens("`/etc/hosts.txt` `docs/a.md`") == ("/etc/hosts.txt", "docs/a.md")
    assert path_tokens("`vendor.io/x.py` `app.dev/y.py` `my.co/z.py`") == ()


def test_symbol_suffixes_are_stripped_from_path_tokens() -> None:
    assert path_tokens("Fixed `heroes/service.py::delete_hero`") == ("heroes/service.py",)
    assert path_tokens("Fixed `heroes/service.py:delete_hero` and `a/b.py#helper`") == (
        "heroes/service.py",
        "a/b.py",
    )
    assert path_tokens("`a/b.py:12` `a/c.py#L10-L20`") == ("a/b.py", "a/c.py")

    brief = make("Fixed `heroes/service.py::delete_hero`", delta("src/heroes/service.py"))

    assert brief.mismatches == ()


@pytest.mark.parametrize(
    "quote",
    [
        "`auth-form-handler.ts` is kept byte-identical, so moving the body out would have created"
        " cross-repo drift.",
        "`budget/+page.server.ts` needed no change; its copy was already removed in #602.",
        "Instead of editing `lib/old.py` we leave it.",
        "Does not modify `lib/old.py`.",
        "We couldn't update `lib/old.py`.",
        "Leaves `lib/old.py` untouched after the rename.",
        "Updating `lib/old.py` could break it.",
        "Removed `gone_fn` without touching `lib/old.py`.",
    ],
)
def test_negated_or_hypothetical_claims_are_skipped(quote: str) -> None:
    brief = make(
        quote,
        delta("src/a.py"),
        known=("auth-form-handler.ts", "budget/+page.server.ts", "lib/old.py"),
    )

    assert brief.mismatches == ()


def test_symbol_claim_is_skipped_when_any_changed_file_is_opaque() -> None:
    opaque = Delta("src/big.ts", True, 0, 0)

    assert make("`deepUnwrap` is removed", delta("src/a.py"), opaque).mismatches == ()
    assert make("Removed `deepUnwrap`", delta("src/a.py"), opaque).mismatches == ()
    assert kinds(make("Removed `deepUnwrap`", delta("src/a.py"))) == ["symbol_claim_not_found"]


@pytest.mark.parametrize(
    "quote",
    [
        "deleting a hero also removes their `pending_drop_choices` rows",
        "Adds support for `with_retry` in the client",
        "Removed the old behaviour of `deepUnwrap`",
    ],
)
def test_backticked_data_is_not_a_symbol_claim(quote: str) -> None:
    assert make(quote, delta("a.py", diff="+x = 1")).mismatches == ()


@pytest.mark.parametrize(
    "quote",
    [
        "Adds `with_retry`",
        "removed the `deepUnwrap` helper",
        "New `parse_args` function",
        "Add a new `with_retry` method",
    ],
)
def test_symbol_claim_needs_the_name_as_direct_object(quote: str) -> None:
    assert kinds(make(quote, delta("a.py", diff="+x = 1"))) == ["symbol_claim_not_found"]


def named(body: str, *paths: str) -> dict[str, bool]:
    return {f.path: f.named for f in make(body, *(delta(p) for p in paths)).files}


def test_bare_backticked_word_names_a_file_by_basename() -> None:
    got = named("Wires `claude-local` and `coder-local`.", "bin/claude-local", "bin/coder-local.sh")

    assert got == {"bin/claude-local": True, "bin/coder-local.sh": True}


def test_names_compare_without_case_dash_underscore_or_dot() -> None:
    got = named(
        "Adds `MemoryFact` and the check-commit-msg hook.",
        "pkg/memory_fact.go",
        "hooks/check_commit_msg.py",
        "pkg/other_thing.go",
    )

    assert got == {
        "pkg/memory_fact.go": True,
        "hooks/check_commit_msg.py": True,
        "pkg/other_thing.go": False,
    }


def test_every_long_stem_part_in_the_prose_names_the_file() -> None:
    body = "Computes the effective review decisions for a PR."

    assert named(body, "a/effective_review_decision.py") == {"a/effective_review_decision.py": True}
    assert named(body, "a/effective_merge_decision.py") == {"a/effective_merge_decision.py": False}
    assert named("The decision reviews are effective", "a/EffectiveReviewDecision.py") == {
        "a/EffectiveReviewDecision.py": True
    }
    assert named("an effective review", "a/effective_review_decision.py") == {
        "a/effective_review_decision.py": False
    }


def test_generic_stems_are_named_by_their_parent_directory() -> None:
    page = "src/routes/(app)/dashboard/+page.server.ts"

    assert named("Reworks the dashboard.", page, "src/routes/(app)/other/+page.server.ts") == {
        page: True,
        "src/routes/(app)/other/+page.server.ts": False,
    }
    assert named("Reworks the app shell.", "src/(app)/+layout.ts") == {"src/(app)/+layout.ts": True}
    assert named("The page is new.", "src/billing/index.ts") == {"src/billing/index.ts": False}
    assert named("Billing is new.", "src/billing/__init__.py") == {"src/billing/__init__.py": True}


def test_secret_scanner_and_registry_configs_are_sensitive() -> None:
    paths = (".gitleaksignore", ".npmrc", "sub/.yarnrc.yml", ".pypirc")
    reasons = {f.path: f.sensitive for f in make("", *(delta(p) for p in paths)).files}

    assert reasons == {
        ".gitleaksignore": "secret-scanner allowlist",
        ".npmrc": "package registry config",
        "sub/.yarnrc.yml": "package registry config",
        ".pypirc": "package registry config",
    }

    for name in (".gitleaks.toml", ".secrets.baseline", ".gitguardian.yml", ".trufflehogignore"):
        assert make("", delta(name)).files[0].sensitive == "secret-scanner allowlist"


def test_look_first_second_tier_is_named_sensitive_files() -> None:
    brief = make(
        "Edits `pyproject.toml` and `src/big.py`",
        delta("pyproject.toml"),
        delta("src/big.py", added=50),
        delta("src/small.py", added=2),
    )

    assert [(p.path, p.reason) for p in brief.look_first] == [
        ("pyproject.toml", "dependency manifest"),
        ("src/big.py", "largest code change (+50 −0)"),
        ("src/small.py", "largest code change (+2 −0)"),
    ]


def test_render_text_has_no_not_named_section_and_the_new_provenance_line() -> None:
    text = render_brief(make("", delta("src/a.py")))

    assert "Not named in the description" not in text
    assert (
        "Computed from the diff, the PR description and CI results. No model wrote any of this;"
        " quoted lines come from the description.\n"
    ) in text
    assert "could not be inspected" not in text


def test_size_line_counts_files_that_could_not_be_inspected() -> None:
    one = render_brief(make("", delta("src/a.py"), Delta("big.bin", True, 0, 0)))
    two = render_brief(make("", Delta("b.bin", True, 0, 0), Delta("c.bin", True, 0, 0)))

    assert "(1 code, 1 opaque). 1 file could not be inspected." in one
    assert "2 files could not be inspected." in two


@pytest.mark.parametrize(
    "path",
    [
        "testdata/case/want.stdout",
        "pkg/testdata/in.go",
        "src/__mocks__/api.ts",
        "__fixtures__/a.json",
    ],
)
def test_test_data_directories_are_test_files(path: str) -> None:
    brief = make("Adds a regression test", delta(path))

    assert [f.kind for f in brief.files] == ["test"]
    assert brief.mismatches == () and brief.look_first == ()
