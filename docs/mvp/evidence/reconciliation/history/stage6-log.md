# Historical Stage 6 log

Recovered from 711504a. These claims describe that historical worktree.


## 2026-10-06 14:55 CEST. Stage 6 large PRs resumed and finished (stage6-large worktree)

- Resumed a stopped run. Verified: 4 prior commits present; one uncommitted box-index fix in
  map.js (folders read box[1..4] like symbols/files) kept and committed.
- First full `uv run pytest` failed at tests/test_explainer_highlight.py::test_real_lines_join:
  4 vendored blobs (pr12/pr17 head+base artifacts/invitation-shortlist-e2e-evidence.json) were
  exported but never committed because the top-level artifacts/ ignore rule matched their
  path segment. Negated the rule for tests/data/**/artifacts/ and added the 4 files (copied
  from the stage4 worktree where they still sat untracked).
- Then 2 Playwright failures, both real, fixed at source:
  - toggleFolder flew the camera to only the expanded group's members, pushing the folder
    card row off-screen (cards at y=-40), so expanding groups one after another was
    impossible. Now fits the union of members and all folder cards.
  - test_dense_map_draws_edges_only_for_the_hovered_symbol opened large_map(60), which now
    opens grouped (0 hoverable sources on screen). Test expands all groups first.
- Lint debt from the stopped run (grade.py Stage 1, map_layout.py, render_map.py, grouping
  test) fixed with ruff --fix/format plus two mypy fixes in the test.
- Readability failure found by the PR 19 OCR check: a 32-char folder label ellipsized
  ("diagnostics/verify_inbox...") and count lines truncated mid-word. Fixed at source: group
  cards width from their label (like chips, capped 360 px), counts wrap. New browser test
  asserts no scrollWidth/Height overflow on any fcard.
- Failure-mode coverage (all in tests/test_map_grouping.py, 413 tests pass total):
  small PR (<=40 changed symbols, boundary tested at exactly 40/41) unchanged; expanding all
  groups leaves [data-edge] count == map.json edges; group counts equal member sums
  (added/modified/deleted/tests); grouped first screen at 1280x800 passes OCR with every
  label found, <=25 cards (4 on PR 19), all cards fully inside the viewport.
- PR 19 (62 files, 311 changed symbols, 639 edges): grouped into 4 cards with 4 summed
  folder edges (43 calls total, max 20 scripts<->mcp). Timing (measured, perf_counter +
  /usr/bin/time): explain wall 5.5 s, map build 4.2 s, layout 18 ms, map.html render 161 ms,
  voice none, no board. The 5-minute guard passes by a wide margin. Command and numbers in
  docs/mvp/evidence/stage6/results.json.
- Evidence: docs/mvp/evidence/stage6/ (before and after PNGs at 1280x800 scale 2, OCR output,
  results.json). Before is the committed docs/mvp/evidence/pr19-map-before.png.
- Verify (uv run ruff check / format --check / mypy / pytest / uv build): all pass on 3.12.7,
  413 tests, 3 min 2 s pytest. Wheel builds.
- Open problems: none for Stage 6. Grouping thresholds (40 symbols, <3 files per folder) are
  the plan's; not tuned elsewhere. PR 19's real heads matched the stored map, so the stored
  map was written out unchanged and map_source is "live".
