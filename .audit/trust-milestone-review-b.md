Model: opencode-go/muse-spark-1.3-contributor. Agent: 01a12009-b5ad-7c22-95c5-c8dad640f252.
Scope: 24e5300...6dbb336.

**TL;DR verdict: No critical defects reproduced; the frozen candidate is shippable with three warnings.** The closed prior findings spot-check clean (numstat literal paths, binary classification, blob diff, non-finite cue rejection). The three new findings below are all reproduced against HEAD `6dbb336` and none duplicate the closed reports.

## Findings

### 1. [warning] Comment still references card.png after the card fit fails
**Location**: `src/prc/pipeline.py` (`run_explain` CardError path), `src/prc/presentation/comment.py` (`render_comment`)
**Finding**: When crowded-card fit raises `CardError`, `run_explain` unlinks `work/card.png` and records `"card": None` in `run.json`, but the published `comment.md` still contains `![PR card](card.png)` plus "Upload `card.png` with this comment". The comment artifact points at an image that was never produced. This path is newly routine: commits `013cbcc`/`0476bb8` made fit failure raise instead of silently covering the test-evidence block.
**Evidence**: Reproduced by code read and probe: `render_comment` on a symbol-less map returns `has card.png ref: True, has upload line: True` unconditionally, and `_publish_explain` renames the whole work dir, so the broken reference ships as-is. `run.json` knows the card is missing; `comment.md` does not.
**Suggestion**: Pass card availability into `render_comment` and either omit the image block or replace it with the fit-failure warning text when `card_png is None`.

### 2. [warning] Delete-only change contradicts itself on the card
**Location**: `src/prc/facts.py` (`compute_facts`, `untested`)
**Finding**: `symbols_changed` counts `deleted` symbols via `CHANGED`, but `untested()` only considers `added`/`modified` and the verdict branch treats delete-only as "No live production symbols changed." A deleted production symbol whose callers may now break is simultaneously reported as changed and as not-live.
**Evidence**: Probe `compute_facts` on a map with one deleted `a.py` symbol: `symbols_changed = 1`, `untested = 0`, verdict `"No live production symbols changed."` The same card/comment prints "1 parsed symbol changed" next to that verdict.
**Suggestion**: Either exclude deleted symbols from `symbols_changed` or give them their own verdict line (e.g. deleted symbols listed separately, since their risk sits with remaining callers).

### 3. [warning] Malformed boards crash `verify_board` with tracebacks instead of receipt failures
**Location**: `src/prc/explainer/check.py` (`verify_board`, `Checker`), `src/prc/explainer/timing.py` (`scene_windows`)
**Finding**: Structural defects in an authored board raise raw exceptions rather than failing cleanly via `SystemExit("receipts failed: ...")`. `main()` only converts `SourceError`, so `prc board check` on these inputs traceback.
**Evidence**: Probes against HEAD, all with a minimal valid map: missing `scenes` → `KeyError 'scenes'`; `scenes: None` → `TypeError`; scene `{}` → `KeyError 'type'`; scene `None` → `TypeError`; diff scene without `file` → `KeyError 'file'`; `[0, 0.5]` cue on a say-less scene → `KeyError 'say'`; `hold: "x"` → `ValueError`. (Non-finite numeric `at` now fails cleanly, confirming the earlier cue-value fixes held.)
**Suggestion**: Validate board shape at the `verify_board` boundary (scenes list, per-scene `type`/`say`/`file` presence and `hold` numeric) and route violations through `ck.fail`, matching the already-fixed cue-value validation.

One next step: triage these three warnings against the regenerated acceptance outputs, then hand the milestone to the user for human acceptance.
