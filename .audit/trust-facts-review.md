# Review: implemented trust-facts boundary, read-only

TL;DR. The parent's facts boundary is sound and matches the judge contract: one
domain calculator in `facts.py`, compat re-exports in `card.py`, render-only
page injection, and map.js as a pure consumer. D8 is fixed canonically (Git for
two-sided diffs, difflib only for an absent side), opaque browser test files
count as tests, and object handlers get distinct names through TS `satisfies`.
My runs are green; three verified defects remain: pending/failed CI mislabeled
as "CI passed" in map.js, opaque files reported as parse limits, and
PR-controlled paths injected raw into comment Markdown.

## Verified working (my runs, red-to-green)

- Canonical diff: [gitutil.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/gitutil.py:116) uses real `git diff` when both blobs exist;
  an absent side still difflibs. Tests: `test_large_text_files_keep_exact_line_counts`
  (2500 repeat lines, exact (2,1)), `test_repeated_decorator_does_not_make_unchanged_function_modified`,
  the LibrarySync fixture, and my run `pytest tests/test_changemap.py` = 15 passed.
- Opaque test counting: [brief.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/brief.py:184) returns "test" for opaque deltas on test
  paths, so `tests_touched` counts large opaque browser test files
  (`test_large_browser_test_file_keeps_its_test_classification`).
- Handler names: [codegraph.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/codegraph.py:363) climbs `satisfies_expression`/`as_expression`
  wrappers and pair keys; `first.run`, `command.nested.done` and call scopes
  verified by two new regressions.
- Contract shape: [facts.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/facts.py) owns definitions and evidence; `compute_stats`/
  `untested` re-exported from card.py; [render_map.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/render_map.py:73) injects `summary`
  into the page data block only; `map.json` (pipeline.py:553) stays schema-compatible.
  Evidence rule (exact, added/kept, live targets only) matches regressions.
- Runs: `pytest tests/test_trustworthy_facts.py tests/test_render_map.py` =
  22 passed; `pytest tests/test_card_comment.py` = 28 passed, 1 skipped,
  1 failed (Chromium not installed in this sandbox - environmental).
- Parent evidence present at `artifacts/trustworthiness/2026-10-09/regressions/`:
  `stats-red.png`/`stats-green.png`, `dense-red/-green`, red logs showing the old
  "2tests touched"/"noneCI on head" failures, `browser-green.log` = 1 passed.
  Intermediate logs (`facts-green.log`, `facts-green-attempt.log`) are red-phase
  captures of now-updated assertions, not current state.

## Verified defects, minimal fixes

1. P1, map.js CI labels. [map.js:182](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/map_assets/map.js:182) hardcodes label "CI passed"
   while the value came back to `ci_text` ("0/2"). With `ci_state` "failed" the
   header reads "CI passed" in bad tone; [map.js:942](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/map_assets/map.js:942) shows
   "CI passed on the head commit" when checks are merely pending. Fix: one label
   map `{none: "no CI", failed: "CI failed", pending: "CI pending", passed:
   "CI passed"}[FACTS.ci_state] for the header, and a pending branch for the
   summary cell. Behavior, not schema.
2. P2, opaque files become fake parse limits. [facts.py:105](Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/facts.py:105) re-derives kind via
   `kind_of(Delta(path, False, 0, 0))`, dropping the opaque flag, so the opaque
   rule (`delta.opaque`) never matches and a binary file is classified "code".
   Verified run: map file `('blob.bin','opaque',None)` produces
   `ParseLimit('blob.bin','unsupported language')`. This mislabels opaque skips
   and contradicts "never invent reasons". Fix: trust the serialized kind,
   `kind = file.get("kind") or kind_of(...)`.
3. P2, Markdown injection in comment. [comment.py:202](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/comment.py:202) inserts
   `test_evidence(m, brief)` raw; when a parse limit exists the string embeds
   PR-controlled paths (verified: "analysis is incomplete: pat*h.py (not
   parsed)."). Cards escape; comments must follow the file's own span() rule:
   wrap with `span(test_evidence(m, brief))` or escape paths inside facts.

## Deviations from the judge contract, accepted

`Facts` adds `ci_state` and constant `test_note` (display data, not stored
policy); risky count stays derived in map.js from already-serialized brief data;
`test_evidence` is a function, not a stored string, as decided.

## Environment

My sandbox lacks the Playwright Chromium cache, so browser-dependent assertions
here rely on the parent's green artifacts above; every non-browser assertion
passed locally.

Next step: parent-owned D17, large-map readability, then a one-pass fix sweep
for the three defects with the pending-CI screenshot as the added regression.
