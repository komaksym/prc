# Trust final inspection delta - independent correctness recheck

Date: 2026-10-09. Independent recheck of the immutable delta only.
Delta: /Users/koval/dev/prc/.claude/worktrees/readiness/.audit/trust-final-inspection.diff
Design: .audit/trust-caption-design.md. Regression list: .audit/trust-inspection-regressions.txt.
Code state: worktree HEAD 548d8ab. Production src matches the delta exactly.

## Verdict

**PASS - no correctness findings in the delta.**

All five review axes check out: facts, rendering, HTML escaping, coverage
ordering and labels, and display-vs-speech semantics. The core captions module
is layer-clean, the PR-title fallback escapes correctly, the comment contract
is retained, JS outro fmt parity holds, and no missed sibling bug surfaced in
the reviewed surfaces.

## Checks performed

1. **Core module layering.** src/prc/captions.py imports only `html` and `re`.
   Importers are doc.py and timing.py (explainer) and card.py (presentation).
   A repo grep shows no explainer-to-presentation import and no presentation
   import inside explainer code. No import cycle. Core stays clean.

2. **HTML escaping.** `shown_html` escapes with `html.escape` first, then turns
   paired backticks into `<code>` spans. Entities never contain backticks, so
   pairing is unaffected by escaping. Unpaired backticks and empty pairs stay
   literal. The card HEADLINE token dropped `_escape` and now uses `shown_html`
   only, which avoids double-escaping. Doc prose swaps `html.escape` for
   `shown_html`. The hostile-caption test asserts escaping plus code spans.

3. **PR-title fallback.** `headline(m, None)` returns the PR title; the card
   passes it through `shown_html`, so it is escaped and gets code formatting.
   This matches the design contract for the fallback.

4. **Comment contract.** `render_comment` renders `# {span(headline(...))}`.
   `span` turns every backtick into an apostrophe first and then wraps the
   result in one code span, so interior backticks cannot break the span.
   Headlines now yield the show text, so comments stop printing the speech
   spelling. The delta test asserts the shown text inside the headline code
   span for a spoken caption. Retained contract per the design doc.

5. **Coverage ordering and labels.** `line_coverage` sorts missing refs by
   `(path, removed-first, abs(line))`. Removed lines list ascending by original
   line, then added lines ascending. `_not_covered` builds `(removed)` labels
   with base-sha hrefs from the same list. `boards.coverage` prints the same
   list. The new ordering test passes locally without a browser.

6. **Display vs speech.** Doc captions, `fit_sentences` text, and card
   headlines select the show text through `captions.shown`. `check.spoken`
   keeps speech selection and still drives narration and cue phrases.
   `_validate_shape` requires a `show` string on dict say entries, so the
   `KeyError` in `shown` is unreachable for checked boards. This matches the
   recorded design decision to drop the extra ValueError guard.

7. **JS outro parity.** engine.js `fmt` is `esc` plus the same paired-backtick
   regex as Python. The outro maker now uses `fmt` for l1 and l2. `cmd` keeps
   `esc(s.url)` and `fine` keeps `esc`, as before. The checker validates outro
   l1 and l2 as strings. Python `html.escape` also escapes apostrophes; JS
   `esc` does not. Both render the same text content after parsing, and the
   parity test compares text content and code content only, so no drift.

8. **Sign column.** engine.css sets `align-self: flex-start` on `.drow .sg`,
   so the sign sits on the first visual line of wrapped rows. This matches the
   new wrapped-diff sign test contract. Single-line rows are unchanged.

9. **Facts verdicts.** `missing` (no_direct_test) is a subset of `live_prod` by
   construction, so `missing_ids >= live_ids` means exactly "every live symbol
   lacks evidence". The verdict strings flow from the single source
   `facts.test_verdict` into comment and card. A grep confirms the old "some"
   string exists only in facts.py and its tests.

10. **Tests.** The 15-item list ran in the sandbox: 12 passed. The three
    real-browser tests failed at Chromium launch inside the sandbox
    (`mach_port_rendezvous` bootstrap denied), not on assertions. The parent
    clean-cache verification ran 812 tests including the installed-wheel
    five-output browser proof, so the browser trio is verified externally.
    After the snapshot, the two-line narrative comment removal in
    `test_doc_adds_no_new_claims` was verified as comment-only, and the focused
    test re-ran green (1 passed).

## Concrete findings

None.

Minor notes, recorded as non-defects:

- The comment headline with interior backticks is not covered by a test. Only
  the spoken-caption case is asserted. The span substitution makes the
  behavior deterministic, and the design doc retains the single code span
  contract, so no action is required for this delta.
- `build_card_html` reuses the local name `shown` for a caption fragment after
  the imported `captions.shown` has no remaining calls in that function. Style
  shadowing only; mypy and ruff are clean per the parent verification.
- Dict say entries without `show` raise `KeyError` on direct API calls with an
  unchecked board. Accepted by the design doc; the CLI and pipeline always run
  `verify_board` before rendering surfaces.

## Material limits

- The three browser tests did not execute locally. The sandbox denies
  Chromium mach-port rendezvous, and the escalation attempt could not be
  approved because the automatic approval review failed with an upstream
  provider error (HTTP 400 on its own response-schema validation), not a
  policy decision. The parent 812-test clean-cache run with the installed
  wheel and browser proof covers them.
- The local 12-test pass ran against committed source, not the built wheel.
- Residue: the three failing browser runs regenerated player.html,
  tokens_s0.json, and empty audio/ dirs under
  artifacts/e2e/{wrapped-diff-sign,caption-parity,caption-headlines} at 18:31.
  Rendering is deterministic, so content matches the parent 18:19 proof
  artifacts; the parent screenshots and bounds.json are intact, and the
  parent regenerates these dirs anyway.
- The review is read-only on the delta. No installs, commits, external writes,
  or extra agents. Only this file was written, to /private/tmp.
- The acceptance rebuild was in progress on the parent; acceptance artifacts
  and the modified docs/TSV were outside this review scope.
