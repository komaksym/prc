**TL;DR: All three prior findings are resolved for their reported reproductions.** Five malformed-input probes now produce controlled receipt errors before coverage runs. Seven selected regression tests passed. Full verification and cached Chromium checks remain with the parent.

## Scope and verdict

Rechecked the exact malformed-cue reproductions from `/private/tmp/prc-trust-render-final-review.md` against current local source. Review date: 2026-10-09, Europe/Warsaw.

Checkout: `/Users/koval/dev/prc/.claude/worktrees/readiness`.

No remaining error was reproduced within this requested scope. No source edits, commits, pushes, PRs, browser installs, or new fuzz cases occurred.

## Reproduction results

Each probe used a fresh existing `replacement()` fixture. Cue objects passed through `json.loads`, including its accepted NaN extension.

| Prior reproduction | Current result |
| --- | --- |
| Note with `at: [0.0, 0.2]` | Controlled `SystemExit` with the `[sentence, fraction]` diagnostic. No accepted-check/failed-fit path remains. |
| Note with `at: [0, "bad"]` | Controlled `SystemExit` with the same diagnostic. No comparison `TypeError`. |
| Replace step cues with `[{"at":0.1,"do":"step"}]` | Controlled `SystemExit`: `step cue needs a positive integer n`, plus the missing step 1 diagnostic. No `KeyError`. |
| Note with `at: [0, 0.2]` and `until: NaN` | Controlled `SystemExit` with `cue time nan`. Rejected before fitting or rendering. |
| Replace the step's `at` with NaN | Controlled `SystemExit` with `cue time nan`. Rejected before fitting or rendering. |

For all five probes, an in-memory mock made `check.line_coverage` raise if called. Its call count stayed zero. Thus input failures reach the caller before coverage can suppress their diagnostics.

A valid replacement control still passed `verify_board`, reported `changed lines 2/2 on screen`, and fitted with `NoneBackend`. Its fitted-cue validation returned no errors.

Two targeted fitted-value checks used fresh valid boards. After fitting, replacing `t` with NaN produced `needs a finite fitted timestamp`. Replacing `until` with NaN produced `needs a finite fitted end`.

## Tests actually run

An inline `.venv/bin/python -B` probe ran the five exact malformed inputs, the valid control, and the two fitted-value checks. All assertions passed. In-memory mocks changed no source files.

The following focused pytest command passed **7 tests in 0.02 seconds**:

```sh
PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/private/tmp/prc-trust-uv-cache PYTHONPATH=src \
.venv/bin/python -B -m pytest -q -p no:cacheprovider \
--basetemp=/private/tmp/prc-trust-render-followup-pytest \
'tests/test_trust_render_preflight.py::test_malformed_cue_fails_check_without_traceback[cue0]' \
'tests/test_trust_render_preflight.py::test_malformed_cue_fails_check_without_traceback[cue1]' \
'tests/test_trust_render_preflight.py::test_malformed_cue_fails_check_without_traceback[cue3]' \
'tests/test_trust_render_preflight.py::test_malformed_cue_fails_check_without_traceback[cue4]' \
'tests/test_trust_render_preflight.py::test_malformed_cue_fails_check_without_traceback[cue5]' \
tests/test_trust_render_preflight.py::test_actual_fitted_stamps_must_be_finite
```

Commands ran from the checkout above. The inline probes used `PYTHONPATH=src:tests` and the same bytecode/cache settings. They used `NoneBackend`; no speech synthesis or downloads occurred.

## Limits

This follow-up closes the original findings only for their reported cases. It does not establish broader regression or GUI acceptance. No browser run, screenshot, broad fuzzing, full suite, lint, typecheck, build, or full verifier ran here. The parent's reported 74 pure checks were not independently rerun.

The parent owns the full verifier with cached Chromium. This review remains supplemental; the user is the sole human reviewer.

Suggested next step: complete the final join/reveal acceptance with the parent's full verifier and cached Chromium artifacts.
