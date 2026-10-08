TL;DR: ISSUES. Four concrete defects remain in the scoped pending changes. The narrow checks passed.

Review completed on 2026-10-08 at 17:25 UTC. HEAD was `1576650eabb4224e9b2bb1c8cf56b0029907ee52`.
This review covers the uncommitted diff, including the untracked round grader and related tests.
It is a source review, not a release-verifier result.

## Findings

### [P1] Stored-map reconciliation gives the published outputs different facts

Changed code: [pipeline.py:401](/Users/koval/dev/prc/src/prc/pipeline.py:401), `_change_map_from_stored`.
Related changed code: [pipeline.py:430](/Users/koval/dev/prc/src/prc/pipeline.py:430).

The new reconstruction reclassifies stored files, including `e2e_*` files, and publishes those classifications.
However, `load_map_dict` still returns the original dictionary as both `used` and `live_dict` at line 489.
`run_explain` checks the board against `used` at line 571.
It also renders the video and document from `used` at lines 585 and 596.
The published map, card, and comment use `rebuilt` at lines 552–554, 600, and 609.

An older stored map can classify `diagnostics/e2e_probe.py` as code.
Give it one added symbol, `test_probe`, and one added line, `def test_probe(): pass`.
The current reconstruction classifies that same file as a test.
An in-memory probe produced these results:

| Fact or output | Original dictionary used for board/video/document | Rebuilt published map |
| --- | --- | --- |
| File kind | `code` | `test` |
| `changed` | `1` | `0` |
| `tests_added` | `0` | `1` |
| Board assertion `changed == 1` | Passes | Fails with `narration says changed = 1, the map says 0` |
| Receipt for `test_probe` | `CODE, NO TEST` | `NOT FOUND IN THE CODE` |

Both `build_card_html(rebuilt, board=board)` and `render_comment(rebuilt, board=board)` returned `No production symbols changed.`
Thus a successful checked explanation can contradict its published map and summary outputs.
This divergence follows from the new reclassification, even though the split caller path already existed.

The new `test_stored_map_reclassifies_end_to_end_checks_consistently` checks file kinds and pointers only.
It does not compare board facts or receipt verdicts with the published map.
Use one reconciled dictionary for checking and all renderers.
Add a stored-map entry-point regression that checks those facts across the outputs.

### [P2] Top-level receipts lose their file entry when another symbol changed in the same file

Changed code: [card.py:237](/Users/koval/dev/prc/src/prc/presentation/card.py:237), `_file_fallbacks`.
Affected callers: `build_card_html` and `render_comment`.
Published promise: [README.md:119](/Users/koval/dev/prc/README.md:119).

`with_symbols` records whole paths that have any changed symbol.
Line 244 then excludes every such path from the file fallback.
It never checks whether a quoted line belongs to those symbols.

Probe input: `src/a.py` has changed symbols spanning lines 10–20 and 30–40.
The board displays its added top-level line 1, `API = 2`.
`verify_board` accepts this diff scene with its step cue.
`look_first` returns `src/a.py::context` and `src/a.py::displayed`.
It returns no `file:src/a.py` entry for the actual displayed change.

This contradicts the documented fallback for quoted changes outside parsed symbols.
The added fallback tests cover files without changed symbols, so they miss this case.
Determine fallback eligibility from unmatched quoted lines, not from the existence of any changed symbol in their file.

### [P2] Supported symbol receipts do not affect card or comment ranking

Changed code: [card.py:138](/Users/koval/dev/prc/src/prc/presentation/card.py:138), `_receipt_refs`.
Related changed code: [card.py:210](/Users/koval/dev/prc/src/prc/presentation/card.py:210), `cited_symbol_ids`.

The checker supports receipt rows containing `symbol` or `edge` at `check.py` lines 382–385.
The new board ranking extracts only receipt rows containing `line`.
It therefore ignores a direct symbol receipt, even after the checker accepts that receipt.

Probe input: `src/a.py::busy` has 100 changed lines, and `src/a.py::displayed` has one.
A receipt scene cites `src/a.py::displayed` through its `symbol` field and has a valid `rows` cue.
`verify_board` accepts it.
`look_first` nevertheless returns `busy` before `displayed`.
With three larger uncited symbols, the cited symbol disappears from the three-entry summary.

README line 118 promises that cited symbols follow displayed diff symbols.
The new tests cover line receipts, but they do not rank a supported explicit symbol receipt.
Include supported symbol references when building the cited-symbol order.

### [P2] Context citations inside a diff scene rank before its displayed lines

Changed code: [card.py:121](/Users/koval/dev/prc/src/prc/presentation/card.py:121), `_receipt_refs`.

Sorting scenes puts diff scenes first, but each scene's `cite` list is appended before its displayed `lines`.
Consequently, supporting context inside a diff scene can outrank the actual displayed change.

Probe input: one diff scene displays line 30 in `displayed` and cites line 10 in `context`.
Both symbols are changed, and the board has the required step cue.
`verify_board` accepts it.
`look_first` returns `context` before `displayed`.
The expected order is `displayed`, then `context`, as specified in README line 118 and the function contract.

`test_look_first_prioritizes_displayed_change_over_context_receipt` places context in a separate groups scene.
It therefore misses context citations inside the diff scene itself.
Collect displayed diff references before collecting context references across all scenes.

## PASS evidence and limits

These commands completed successfully. Python bytecode and pytest cache writes were disabled.

| Check | Command | Result |
| --- | --- | --- |
| Receipt ranking, checker, and brief tests | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_card_receipts.py tests/test_explainer_check.py tests/test_brief.py -k 'not list_paths'` | 115 passed, 1 deselected |
| In-memory grading tests | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_eval_grade.py -k 'bool_answers or cannot_tell or location_same or location_rejects or set_none or name_or_free or answer_map_rejects'` | 10 passed, 11 deselected |
| Scoped lint | `.venv/bin/python -B -m ruff check` with the Python paths below and `--no-cache` | All checks passed |
| Release-script syntax | `bash -n scripts/verify-release.sh` | Exit 0 |
| Tracked scoped diff whitespace | `git diff --check --` with the tracked reviewed paths | Exit 0 |
| Four failure probes | `.venv/bin/python -B -` with synthetic maps and boards | Observed the four failures above; the cited board scenes passed `verify_board` |

The lint paths were `src/prc/brief.py`, `src/prc/pipeline.py`, `src/prc/explainer/check.py`,
`src/prc/presentation/card.py`, `src/prc/presentation/comment.py`, `scripts/eval/grade.py`,
`scripts/eval/validate_questions.py`, `scripts/eval/grade_round.py`, `tests/test_card_receipts.py`,
`tests/test_eval_grade.py`, `tests/test_eval_questions.py`, `tests/test_brief.py`,
`tests/test_card_comment.py`, `tests/test_e2e_explain.py`, `tests/test_explainer_check.py`, and `tests/test_release_package.py`.

The scoped checks confirm external-call filtering, negative base-line references, overflow escaping, and missing reveal-cue rejection.
Source inspection found no additional concrete release defect in the grading changes or release-copy additions.
The frozen-v1 selection and exclusion of `.v2.json` files from the default question-validation pass agree.
No live cache validation or full evaluation run was performed.

The parent owns the full verifier, build, typecheck, browser checks, and screenshot evidence.
This review did not run those checks or create GUI artifacts.
Passing narrow tests does not clear the four reproduced defects.

## Comment review

Read [no-comments/SKILL.md](/Users/koval/.codex/plugins/cache/pstack-claude/pstack/0.9.78/skills/no-comments/SKILL.md),
its Codex mapping, and [comment-sicko.md](/Users/koval/.codex/plugins/cache/pstack-claude/pstack/0.9.78/skills/poteto-mode/references/agents/comment-sicko.md).
Applied the reference directly because the caller prohibited subagents and implementation edits.
Comment deletion count: 0. Restored comments: 0. Reruns: 0. Architect sketches: 0. Encodings: 0.
No added correctness or safety suppression requires a `MUST KILL` flag.
`grade_round.py` suppresses `E402` for its script import path setup; this is an import-order exception.
Private helper docstrings describe local mechanics. Any style-only deletions were skipped under the report-only instruction.
The inaccurate ordering contract in `_receipt_refs` is covered by the concrete finding above.

Only `.audit/reconciliation-source-review.md` was written for this review.
No implementation edits, subagents, full-suite run, commits, pushes, or PR changes were made.
Unrelated queue and analyzer experiments were not inspected.

Suggested next step: fix the four findings, add their missing regressions, and run the parent's release verifier.
