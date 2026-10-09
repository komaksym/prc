**TL;DR: Three concrete malformed-cue errors remain.** The prior join mismatch and late replacement reveal now fail preflight correctly. All 90 selected tests passed with an existing cached headless browser. This supplemental review does not replace the user's human review.

## Scope

Reviewed the final local files under `/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/`: `preflight.py`, `check.py`, `timing.py`, `diffrows.py`, `jointest.py`, `render.py`, and `assets/engine.js`. The checkout has uncommitted changes above HEAD `63f7f361aefe8bf001bdb26dbbf3b11fe970a7cc`. This verdict concerns those local files, not the earlier commit diff.

No source edits, commits, pushes, PRs, or browser installations occurred. This report is the only authored output. Tests generated their normal temporary artifacts outside the checkout.

## Findings

### 1. [P2] A fractional sentence index passes check, then crashes fitting

Location: `check.py:125`, `Checker.when`; `timing.py:37`, `estimated_scene`; `timing.py:245`, `check_stamped_cues`; `timing.py:140`, `at`.

Reproduction: use the existing `replacement()` fixture. Keep its valid step cue. Append `{"at":[0.0,0.2],"do":"note","line":"2","text":"changed"}`.

`verify_board` passes and reports `changed lines 2/2 on screen`. `fit_sentences` then raises `TypeError: list indices must be integers or slices, not float`. This also prevents the real render from reaching its fitted-cue checks.

The checker compares index bounds without checking the index type. The estimator requires an integer and returns a `None` stamp for `0.0`. The stamped-cue checker skips that unresolved stamp. The real fitter uses the float as a list index. Thus valid JSON receives incompatible check and render decisions.

Related probe: `[0,"bad"]` raises an uncaught comparison `TypeError` during check. Validate both components before numeric comparisons. Reject unresolved stamps instead of silently skipping them.

### 2. [P2] A step cue without `n` crashes coverage and suppresses the checker errors

Location: `timing.py:58`, `row_motion`; `check.py:172`, `Checker.diff`; `check.py:457`, `verify_board`.

Reproduction: use `replacement()` and replace its cues with `[{"at":0.1,"do":"step"}]`. `verify_board` raises `KeyError: 'n'`.

`Checker.diff` already records that step 1 lacks a cue and that the unidentified cue moves no lines. However, `verify_board` computes coverage before reporting those failures. Coverage calls `row_motion`, which directly indexes `c["n"]`. That crash replaces the intended receipt diagnostics.

Validate the required step identifier before timing or coverage. Ensure coverage cannot crash on a board the checker has already rejected.

### 3. [P2] A non-finite note end passes both checks and keeps the note invisible

Location: `check.py:127`, `Checker.when`; `timing.py:247` and `timing.py:254`, `check_stamped_cues`; `assets/engine.js:613`, diff note update.

Reproduction: append `{"at":[0,0.2],"do":"note","line":"2","text":"changed","until":NaN}` to `replacement()`.

`NaN` is not standard JSON. However, the actual Python `json.loads` loader accepts it, so a malformed board file reaches this path. The probe used that loader. `verify_board`, `fit_sentences`, and `check_stamped_cues` all accept the board.

A real cached Chromium page contained the `changed` note. At `scene.end - 0.5`, its computed opacity was `0`. No page error occurred. The engine computes a NaN opacity, and CSS retains the note's initial zero opacity. The screenshot was byte-identical to the normal board without that note.

The screenshot SHA-256 was `b4db436fb31a5a5ed36d0512adeaee0a2b7ff95a70d15e32f65dbdb19c780cc2`. Both captures contained 29,452 bytes. These probe screenshots were captured in memory, not saved.

Another probe put NaN in the replacement step's `at`. Check reported `2/2` coverage and fitted validation returned no errors. Both rows remained visible in Chromium, so this probe does **not** establish false line coverage. It does confirm that non-finite motion reaches the engine unchecked.

Reject non-finite authored cue times at the input boundary. Also reject non-finite fitted cue stamps. Preserve any deliberate internal infinity used for uncued motion separately.

## Tests actually run

Environment: `PYTHONDONTWRITEBYTECODE=1`, `UV_CACHE_DIR=/private/tmp/prc-trust-uv-cache`, and local `.venv/bin/python -B`. Probes used `PYTHONPATH=src:tests`. No UV downloads occurred.

Selected pytest command:

```sh
PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/private/tmp/prc-trust-uv-cache PYTHONPATH=src \
.venv/bin/python -B -m pytest -q -p no:cacheprovider \
--basetemp=/private/tmp/prc-trust-final-review-pytest \
tests/test_trust_render_preflight.py tests/test_explainer_check.py \
tests/test_explainer_render.py tests/test_explainer_diffrows.py \
tests/test_explainer_jointest.py
```

The first run had 85 passes and five browser launch failures. Playwright's default browser cache was absent. A second run selected the existing browser but the sandbox blocked macOS Mach port registration. It also had 85 passes and five launch failures. These were environment failures, not reported source defects.

The final run used `pytest.main` with the same five files and an in-memory `BrowserType.launch` wrapper. The wrapper supplied this existing executable:

```text
/Users/koval/.cache/puppeteer/chrome-headless-shell/mac_arm-154.0.8037.57/chrome-headless-shell-mac-arm64/chrome-headless-shell
```

That run executed outside the filesystem sandbox after automatic approval. Result: **90 passed in 10.07 seconds**. It used `--tb=short`, disabled pytest's cache, and set basetemp to `/private/tmp/prc-trust-final-review-pytest-unsandboxed`. Tests included the settled replacement screenshot, keys-only previews, note overlap checks, and the hostile-text video render.

Retained settled-frame artifact: `/private/tmp/prc-trust-final-review-pytest-unsandboxed/test_replacement_is_visible_in0/settled-replacement.png`.

Additional inline probes ran against current source:

- Prior item 1: blank context with common indentation now raises `SystemExit` with `CUT_NOT_SPACES`. Empty diff now raises `SystemExit` with `no expected refs`.
- Prior item 5: a replacement step at `scene.end - 0.25` now raises `SystemExit` for row 2's unfinished reveal.
- Join comparison: 48 text/context combinations passed through preflight and actual `fill` highlighting/wrapping plus `document`/`run`. Results: 32 accepted by both, 16 rejected by both, zero mismatches. Inputs included tabs, blank rows, CRLF remnants, entities, combining Unicode, CJK, non-ASCII indentation, long tokens, and embedded newlines.
- Short fitted voice simulation: a board accepted with step time 1.3 seconds was fitted to a 1.45-second scene. Fitted validation rejected row 2 and coverage dropped to one visible row. This used a deterministic fake backend and patched audible bounds, not speech synthesis.
- Malformed-cue probes reproduced all findings above. Additional null, boolean, string step identifier, and invalid index/fraction probes ran. They are not counted as passing acceptance tests.
- Cached Chromium probes checked normal replacement, NaN step timing, and NaN note expiry. Each captured a screenshot in memory and checked computed row/note styles and page errors.

## Limits

This was one bounded review. It did not run the parent's claimed 114-test selection, the full repository suite, lint, typecheck, package build, or release verification. Actual voice synthesis and human video acceptance were not performed. The simulated voice probe proves the validation branch, not voice-backend integration.

No further join mismatch or false coverage was reproduced for the tested finite, well-formed cues. That statement covers the tested cases only. The user remains the sole human reviewer.

Suggested next step: complete cue validation across check, coverage, and fitting, including these malformed inputs and browser regressions.
