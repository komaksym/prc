TL;DR: Changes required. Frozen-source probes reproduce render-check disagreement, incorrect line counts, and coverage claims for code that never appears. This is supplemental model review; the user remains the sole human reviewer. Full isolated verification and visual acceptance remain pending.

## Findings

### 1. [critical] The new preflight duplicates an incompatible join contract

**Location**: [preflight.py:203](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:203), `join_preflight`; [render.py:228](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/render.py:228), `join_gate`; `jointest.run` at `jointest.py:155`.

**Finding**: `join_preflight` checks only part of the existing join contract. A successful board check still permits a deterministic render failure. D9 remains open.

**Evidence**: A probe selected an indented added line followed by an unchanged blank context line. `verify_board` passed. `fill` computed `cut=4`, and `join_gate` failed with `[CUT_NOT_SPACES] row 3`. The new preflight skips blank context lines because its blank branch requires `+` or `-`. The subsequent branch requires nonblank text. The actual join gate checks every row and rejects a blank row shorter than the cut. An empty diff scene also passed `verify_board`, then failed `join_gate` with `[INPUT] no expected refs`. These failures occur before browser rendering. See `blank_context_join` and `empty_diff_join` in [probe-results.json](/private/tmp/prc-trust-final-review-a-vk0t88o5/probe-results.json).

**Suggestion**: Prepare canonical transformed rows once and use the existing join validator in both check and render. Add cases for unchanged blank context and empty diff scenes. Remove the second partial contract.

### 2. [warning] Object handler definitions do not participate in call resolution

**Location**: [codegraph.py:363](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/codegraph.py:363), `parse_file`; `Index.__init__` at line 535, `Index.resolve` at line 607, and `Index._lookup` at line 675.

**Finding**: The parser adds dotted object handler names without representing their object namespaces in the existing resolver. Direct calls to those handlers remain unresolved, including explicit imported test calls. The new parser support is only partially integrated.

**Evidence**: The parser records `command.exec` for a named object. A same-file `command.exec()` call returns no resolution because `_scoped(..., "command")` finds no container definition. For an imported object, `Index.exported` excludes `command.exec` because its prefix is not a class definition. `_lookup` then rejects the qualified name. A full fixture acquisition and map build changed that handler and added an imported test caller. The resulting map contained both symbols, zero edges, and zero call sites. Shared facts listed the handler under missing direct test evidence. See `object_calls_same_file`, `object_calls_imported`, and [followup-results.json](/private/tmp/prc-trust-final-review-a-vk0t88o5/followup-results.json). Existing regressions test handler names and outgoing helper calls, but do not test incoming handler calls.

**Suggestion**: Represent object namespaces inside the index and resolve qualified calls through them. Keep non-callable containers separate from function symbols. Test same-file and imported handler calls through the complete map pipeline.

### 3. [warning] The verifier copies unrelated workspace experiments

**Location**: [verify-release.sh:43](/Users/koval/dev/prc/.claude/worktrees/readiness/scripts/verify-release.sh:43), isolated-copy phase; [test_trust_package.py:98](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_trust_package.py:98).

**Finding**: The new collector treats every untracked Python or JSON file as an intended release input. It restores the workspace-contamination problem that isolated verification was meant to prevent.

**Evidence**: The collector adds all matching `git ls-files --others --exclude-standard` results, without an ownership or directory restriction. Its next steps run `ruff check .`, format, typecheck, and pytest over that copy. A synthetic repository contained one tracked `kept.py` and one unrelated untracked `scratch.py`. Running the exact embedded copy program copied both. Ruff then failed on the unrelated experiment's syntax. This probe used only private temporary files. The added regression asserts that the script contains `ls-files --others`; it does not assert exclusion of unrelated experiments. See `untracked_copy` in [probe-results.json](/private/tmp/prc-trust-final-review-a-vk0t88o5/probe-results.json).

**Suggestion**: Use committed or staged release inputs, or an explicit manifest of additional intended files. Preserve unrelated experiments without copying them into the verification input.

### 4. [critical] Git interprets inventory filenames as pathspec expressions

**Location**: [inventory.py:83](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/inventory.py:83), `_line_counts`, especially lines 94-98.

**Finding**: The new numstat command passes a repository filename as a Git pathspec. `--` ends option parsing, but does not make that path literal. Valid filenames can receive another file's counts or stop acquisition with a traceback.

**Evidence**: A complete fixture map added `file[1].py` with three lines and `file1.py` with one line. The inventory reported one added line for `file[1].py`, while its stored hunk contained three added rows. The bracket expression selected multiple paths, and the parser consumed the first numstat record. A file named `:(glob)x.py` similarly received `x.py`'s counts. With only `:(glob)absent.py`, numstat returned no record. `_line_counts` raised `ValueError: not enough values to unpack (expected 3, got 1)`. This occurs inside snapshot inventory construction, before brief and output generation. See `counts_bracket`, `counts_pathspec`, and `pathspec_no_match` in the retained probe results.

**Suggestion**: Read numstat once for the complete comparison and index its NUL-delimited records by literal path. Alternatively, use Git's literal-pathspec mode and require exactly one matching record. Test bracketed paths, pathspec prefixes, and unmatched expressions.

### 5. [critical] Coverage includes replacement code whose reveal starts after the scene ends

**Location**: [preflight.py:84](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:84), `rendered_refs`; [check.py:307](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/check.py:307); [timing.py:165](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/timing.py:165); `engine.js:542` and `engine.js:647`.

**Finding**: Coverage counts selected rows without checking their actual reveal intervals. The new timestamp checks validate the cue itself, while the engine applies additional row delays. A checked, renderable board can claim complete coverage while hiding the replacement code.

**Evidence**: A probe used one removed row and its added replacement at the same step. The scene ended at 2.9697 seconds. Its step cue fired at 2.7197 seconds, so `verify_board` passed and `check_stamped_cues` returned no errors. Coverage reported `changed lines 2/2 on screen`. For replacement steps, the engine delays added rows by 0.55 seconds. This row therefore starts opening at 3.2697 seconds, after the scene ends. Its reveal progress stays zero throughout the visible scene. The scene container also becomes hidden at its end. This conclusion follows from the frozen engine formulas; no browser capture was executed. See `hidden_replacement` in [probe-results.json](/private/tmp/prc-trust-final-review-a-vk0t88o5/probe-results.json).

**Suggestion**: Share effective row reveal timing between validation, coverage, and the engine. Reject steps that leave insufficient visible time after replacement delays and scene fades. Test these cases with silent timing and actual fitted voice timing.

## Check limits

Review comparison: `git diff 24e530088b2380f54c781ab5f8f24c51ed2a601f...63f7f361aefe8bf001bdb26dbbf3b11fe970a7cc`.
All probed package and test files came from the frozen commit into `/private/tmp/prc-trust-final-review-a-vk0t88o5`.
Prior audit reports were treated as leads. Findings above use the frozen code and independent probes.
The shared worktree changed during this review. Later edits were not included in this frozen-commit verdict.

**Executed**: `python -B probe.py` and `python -B probe-followup.py` reproduced the cases above. The existing pure tests passed with this command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/prc-trust-final-review-a-vk0t88o5/src:/private/tmp/prc-trust-final-review-a-vk0t88o5/tests \
/Users/koval/dev/prc/.claude/worktrees/readiness/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
--basetemp=/private/tmp/prc-trust-final-review-a-vk0t88o5/pytest-tmp \
--junitxml=/private/tmp/prc-trust-final-review-a-vk0t88o5/pure-tests.xml \
tests/test_trustworthy_facts.py tests/test_trust_render_preflight.py tests/test_trust_package.py tests/test_acquisition_errors.py \
-k 'not test_preview_keys_only_writes_stills_without_video and not test_preview_em5756_note_is_not_flagged_as_overlap and not test_stacked_clamped_notes_still_flag_overlap'
```

Result: 63 passed, three browser tests deselected. The [JUnit artifact](/private/tmp/prc-trust-final-review-a-vk0t88o5/pure-tests.xml) records this subset.
`git diff ... --check -- src scripts .github tests` passed. The complete diff check reported trailing blank lines in three prior audit files.
`ruff check --no-cache` on the synthetic copied experiment failed as expected; this was not a package lint run.

**Not executed**: Full lint, format, mypy, complete pytest, build, empty-cache installed-wheel verification, and CI execution.
Real browser screenshots, preview captures, video inspection, and audio acceptance were not executed.
The parent owns those pending checks. The pure subset does not establish GUI or release acceptance.
No pending proof was counted as passed. Human acceptance remains the user's decision.

Suggested next step: resolve the remaining fact and preflight contracts, then complete isolated release and visual acceptance.
