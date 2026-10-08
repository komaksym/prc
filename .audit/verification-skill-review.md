TL;DR: ISSUES. Four concrete defects remain in `.agents/skills/verify/**` after the parent's latest fixes.

Reviewed on 2026-10-08 at 16:26 CEST. Only this report was written by this reviewer.
Source and tests were read only to check the skill's recipes. No release diff was inspected.
No subagents, real driver runs, full verifier runs, commits, or remote writes were made by this reviewer.
The parent owns real driver execution and full verification.

## Findings

### 1. [P2] Failed browser checks discard the recorded diagnostics

Location: [scripts/map.py:103](/Users/koval/dev/prc/.agents/skills/verify/scripts/map.py:103), `main()`.

`checks.json` is written only after every browser assertion succeeds.
An unexpected HTTP request, page error, failed drawer check, or browser timeout bypasses this write.
Cleanup preserves command output and actions, but loses the collected browser errors and requests.
Package identity, revision, and map hash also disappear from the failed attempt's evidence.
This contradicts the evidence promise in [SKILL.md:58](/Users/koval/dev/prc/.agents/skills/verify/SKILL.md:58).

A read-only, in-memory fault probe injected a page error into `main()`.
The assertion failed, the browser closed, and scratch removal ran.
Screenshots, CLI transcripts, `actions.json`, and `cleanup.json` survived in the virtual filesystem.
`checks.json` did not. The probe made no filesystem writes and launched no browser.

Persist available diagnostics on failure as well as success.
Record the failed action and exception before teardown, without changing a failed run into PASS.

### 2. [P2] The keyboard tour recipe assumes a fresh page after starting playback

Location: [features/map.md:27](/Users/koval/dev/prc/.agents/skills/verify/features/map.md:27).

The updated recipe first clicks Play, then pauses, then presses ArrowRight twice and expects the CI workflow caption.
Pausing does not exit tour mode at [map.js:1050](/Users/koval/dev/prc/src/prc/presentation/map_assets/map.js:1050).
In tour mode, each ArrowRight advances the current step at [map.js:1060](/Users/koval/dev/prc/src/prc/presentation/map_assets/map.js:1060).
If playback was paused during the initial overview, two presses reach the checkout step, beyond the CI workflow step.
The referenced [test_map_browser.py:151](/Users/koval/dev/prc/tests/test_map_browser.py:151) starts with a fresh page.
Its first press enters step zero; its second press reaches the CI workflow step.
The recipe omits that initial-state requirement and can reject correct playback.

Reload the page or press Escape to exit tour mode before the two-arrow recipe.
Wait for the resulting caption and capture its screenshot.
The new Play selectors and label checks are correct; their earlier omission is resolved.

### 3. [P2] Decision persistence points to a test that never reads stored decisions

Location: [features/review.md:25](/Users/koval/dev/prc/.agents/skills/verify/features/review.md:25).

The recipe says to inspect stored decisions as in `tests/test_e2e_cli.py`.
That test only checks the CLI's `recorded` response at [test_e2e_cli.py:73](/Users/koval/dev/prc/tests/test_e2e_cli.py:73).
It does not read a decision row or show how to inspect one.
The recipe therefore has no usable second read for its main mutation.
Removing the scratch store also removes the decision evidence unless the reader invents a preservation step.

The persisted rows live in `VERIFY_STORE/prc.sqlite`.
Their read interface is [Store.decisions():240](/Users/koval/dev/prc/src/prc/store.py:240).
Specify a read-only row query or artifact read after the CLI command.
Assert the snapshot, view, reviewer, decision, and confidence values.
Save that result under `VERIFY_PROOF` before cleanup.

### 4. [P2] Rejected-board verification bypasses the user-facing CLI

Location: [features/board.md:27](/Users/koval/dev/prc/.agents/skills/verify/features/board.md:27).

The recipe delegates rejected references and missing cues to `tests/test_explainer_check.py`.
Those tests call `verify_board()` directly at [test_explainer_check.py:101](/Users/koval/dev/prc/tests/test_explainer_check.py:101).
They establish checker behavior, but cannot establish CLI exit codes or stderr diagnostics.
The CLI catches the checker exception and returns code 2 at [cli.py:362](/Users/koval/dev/prc/src/prc/cli.py:362).
A regression in that command path can escape the documented negative checks.

Use copied invalid boards in scratch storage and invoke `prc board check` through the real entry point.
Require exit code 2 and the exact diagnostic. Preserve the input board and transcripts under `VERIFY_PROOF`.
Keep the unit tests as additional checker evidence.

## Checks that pass

| Check | Result and evidence |
| --- | --- |
| Helper ROOT | PASS. `Path(__file__).resolve().parents[4]` resolves to `/Users/koval/dev/prc`, not `.agents`. |
| Helper launch | PASS. The helper is executable and its invocation is documented. It uses the active Python interpreter. |
| CLI isolation | PASS. `doctor` and `map` use the real CLI. The subprocess cwd, fixture store, and map output belong to scratch. |
| Package identity | PASS. The helper requires `prc.__file__` beneath this checkout's `src`. |
| CLI arguments | PASS. Fourteen fully written recipe commands parse through the current `build_parser()` without dispatching commands. |
| Fixture expectations | PASS. Counts of 7 changed symbols, 12 edges, and 10 steps match `tests/test_map_cli.py:89`. |
| Explain recipe | PASS. Board, stored-map, fallback, and rejected-board paths match `tests/test_e2e_explain.py`. `.shot` and `window.docReady` exist in the document renderer. |
| Install recipe | PASS after a concurrent correction. `--dest` isolates both installers. The test reference now names the existing `tests/test_skill.py`. |
| Normal cleanup | PASS. Browser closure and scratch removal use `finally`. Evidence is outside scratch. No process-name killing exists. |
| Offline evidence | PASS for the inspected fixture page. The captured requests contain only its `file:` URL. HTTP and HTTPS attempts are aborted and rejected. |
| Comments | PASS. The helper has its executable shebang and one module docstring. No inline prose comments or suppressions exist. |

The final inspected proof is [map-bk2qecrb](/Users/koval/dev/prc/artifacts/verification/map-bk2qecrb).
Its `cleanup.json` reports `scratch_removed: true`; the recorded scratch directory is absent.
All three screenshots and the copied HTML and JSON still exist.
Its `checks.json` records no page errors and no HTTP requests.
The final open and closed screenshots were opened and inspected by this reviewer.
The open drawer is fully inside the viewport, with readable code. The closed screenshot has no visible drawer.
The earlier `map-kt_mlr_k` proof was also inspected and had a clipped open drawer.
The new transform wait resolves that defect in the final proof.
The parent executed this run; this reviewer did not rerun the real driver.
The skill correctly limits offline evidence to the page, rather than all CLI traffic.

## Verification commands

| Command or probe | Result |
| --- | --- |
| `date` | Recorded review start and final source-read time. |
| `.venv/bin/ruff check --no-cache .agents/skills/verify/scripts/map.py` | PASS. |
| `.venv/bin/ruff format --check --no-cache .agents/skills/verify/scripts/map.py` | PASS. |
| `MYPYPATH=src PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy --no-incremental --cache-dir=/dev/null .agents/skills/verify/scripts/map.py` | PASS. One source file. |
| Read-only Python AST, executable-mode, argument-parser, and test-reference probes | PASS after the concurrent install-reference correction. |
| In-memory failure injection through the helper's `main()` | Reproduced finding 1. Browser closure and scratch removal ran; diagnostics were not persisted. |
| Artifact metadata and retained-file inspection | PASS for the named captured proof. |
| Visual inspection of final `drawer.png` and `closed.png` | PASS. Both transition waits now produce usable evidence. |
| Full verifier, real driver, and build | Not run by this reviewer. Assigned to the parent by the user. |

The parent reports that full verification passed 563 tests plus build and wheel checks.
This reviewer did not inspect the release diff or independently run that verifier.

Standalone mypy initially treated `prc` as an untyped installed package.
Adding `MYPYPATH=src` made it resolve this checkout and pass. No code change was required.

Concurrent edits corrected the missing install-test reference and replaced an immediate drawer-position assertion with a wait.
The final wait uses `() => document.querySelector('#drawer').getBoundingClientRect().left >= innerWidth`.
The final helper also waits for the open drawer's computed transform to equal `none`.
All corrections were reread, and helper lint, formatting, and type checking were repeated successfully.
The missing reference, closed-shot transition, open-shot transition, and missing Play selectors are resolved.
The new keyboard recipe's initial-state error remains finding 2.

## Scope and comment audit

Read the requested `poteto-mode`, `create-verification-skill`, `no-comments`, and `comment-sicko.md` references.
Also read the Codex tool mapping and `unslop` writing rules.
Applied the driver-generation standard to recipes and evidence. Applied comment rules within the scoped helper.
The user's read-only and no-subagent instructions override the skills' edit and delegation steps.

Comment deletions: 0. Restored comments: 0. Comment-review reruns: 0. `MUST KILL` comment flags: none.
Architect sketch, code fixes, and encodings: none. Encoding offers and unenforced comment constraints: none.
Open work consists of the four findings above. No production code comments were added.

The helper's final-read SHA-256 is `72b938020f5843e2bfdfdedfcd7eaba2f17137a8b6d69ba932ddfebd6685a244`.
Later concurrent edits require fresh line references and a new review of the affected findings.
