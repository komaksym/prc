# Step 1 graph converter fixes

## Summary

The converter changes are complete and uncommitted in `/private/tmp/step1-map-fixes` at `a6b0e622cc93bce904f83838cfefde24d7f8ef81`.
Focused verification passed with 25 tests and one deselected lock test.
The parent must validate the refreshed goldens with the pinned schema and update their lock hashes.

## Changed files

- `src/prc/presentation/graphdoc.py` replaces repeated selection with a bounded pass in `_select`. Risky nodes reserve at most 12 slots and respect the node budget. Every budget slice clamps at zero. File-only maps preserve risky targets outside the first 256 file indices. Ordinary files use spare slots in plain and grouped maps. `_overview_doc` clamps its budgets. `_finish` names omitted focus in the existing body text. It shows at most two short names and an exact count of further omissions within 140 characters.
- `tests/test_graphdoc.py` adds subprocess probes with five-second timeouts for 300 one-symbol files and 300 risky tour targets. It covers plain and grouped conversion, reduced budgets, file retention, file-only priority, missing and partial focus, long captions, deterministic conversion, index references, and exact drop counts. It replaces the old aggregate requirement with the approved symbol priority.
- `tests/data/graphdoc/shop.json` adds the ordinary README file node.
- `tests/data/graphdoc/em-5756.json` records the fixed converter output for remaining ordinary files.
- `tests/data/graphdoc/grouped.json` adds the dependency manifest and guide file nodes.

The converter generated all three refreshed goldens. Input fixtures and the other goldens did not change.
`Plotted`, the GraphDoc schema, and index-based IDs remain unchanged. No dependency was added.
Laziness Protocol removed the repeated-selection loop. Model the Domain retained the existing index maps for the bounded graph subset.

## Verification

All Python commands used `PYTHONPATH=src` and `/Users/koval/dev/prc/.claude/worktrees/readiness/.venv/bin/python`.
The subprocess probes additionally put this clone's `tests` directory on `PYTHONPATH`.
An explicit assertion confirmed the converter import resolved to `/private/tmp/step1-map-fixes/src/prc/presentation/graphdoc.py`.

- Red command: `python -m pytest -q -p no:cacheprovider tests/test_graphdoc.py`. Result: 11 failed, 16 passed. Saved before converter edits in `/private/tmp/step1-graph-red.log`.
- Green command: `python -m pytest -q -p no:cacheprovider tests/test_graphdoc.py -k 'not prlens_lock_matches_bundle_and_goldens'`. Result: 25 passed, 1 deselected. Saved in `/private/tmp/step1-graph-green.log`.
- Focused lint: `python -m ruff check --no-cache src/prc/presentation/graphdoc.py tests/test_graphdoc.py`. Result: all checks passed. Saved in the green log.
- `git diff --check` passed.

The 300-file timeout probes already passed at the specified base commit because it contains a flood guard. The red failures establish the remaining file-retention, reduced-budget, focus-disclosure, and selection-priority defects. The fix removes the repeated loop entirely.
The checked maps respect 256 nodes, 512 edges, and 12 steps. Reduced-budget regressions also prove risky nodes cannot produce negative selection budgets.
Grouped edges remain a subset. Drop counts equal the exact difference between source symbols or edges and their plotted counterparts.

## Handoff

Patch: `/private/tmp/step1-graph-fixes.patch`.
Red log: `/private/tmp/step1-graph-red.log`.
Green log: `/private/tmp/step1-graph-green.log`.

The lock test was deliberately deselected. Its recorded golden hashes describe the original outputs and need the parent's pinned-schema validation before refresh. The lock and bundle were not edited.
The parent checkout was not edited. No browser tests, full suite, full build, remote writes, staging, or commits ran.
Only the five owned files appear in the clone's Git diff.

Next step: Integrate this patch into the parent's complete step 1 map scope, validate the goldens, and finish UI coverage verification.
