Model: gpt-6.1-sol. Agent: 01a12028-9fd1-7563-889c-3c5efbaef53f, Harvey, replacing Bohr after HTTP 429.
Scope: 24e5300...6dbb336.

**TL;DR: Changes required.** Three new inputs reproduce false test evidence, false on-screen coverage, and accepted invisible outro content. This is an independent model review of `24e5300...6dbb336`. The user remains the sole human reviewer.

## Findings

### 1. [critical] Quoted property names collide with nested object paths

**Location:** [codegraph.py:391](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/codegraph.py:391), `parse_file`.

**Finding:** Joining property names with dots conflates `"nested.run"` with the actual nested property `nested.run`. The index merges distinct functions and assigns test evidence to the wrong changed function.

**Evidence:** A complete fixture acquisition used this object:

```javascript
export const command = {
  "nested.run": () => 1,
  nested: { run: () => 11 },
};
```

The head changed only the quoted property's return value to `2`. An unchanged test called `command.nested.run()`.

The generated map merged both functions into `command.ts::command.nested.run`, with span `[2,3]`. It assigned an `exact`, `kept` test edge to that modified symbol. Shared facts reported zero symbols without direct test evidence and the verdict:

> Direct test-call evidence found for all live changed production symbols in this map.

Node confirmed distinct behavior. The test's call returned `11`; `command["nested.run"]()` returned `2`. The test never called the changed function.

Reproduction: [probe-collision.py](/private/tmp/prc-bohr-review-OYpmru/probe-collision.py). Results: [collision-results.json](/private/tmp/prc-bohr-review-OYpmru/collision-results.json).

**Suggestion:** Preserve property segment boundaries in symbol identity. A quoted segment containing dots must not resolve as a nested member chain.

### 2. [critical] Coverage counts wrapped rows outside the visible stage

**Location:** [timing.py:80](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/timing.py:80), `visible_rows`; [preflight.py:100](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:100), `rendered_refs`.

**Finding:** Visibility checks consider animation timing but omit layout bounds. A valid board can claim complete coverage while its settled code extends below the clipped stage.

**Evidence:** A complete fixture map added twelve valid Python assignments. Each assignment contained a 190-character string. One diff scene selected all twelve lines, with an early step cue and three seconds of hold.

The real CLI accepted the board and printed `changed lines 12/12 on screen`. `fill`, `join_gate`, and fitted-cue validation also passed. The walkthrough generated:

> 12 of 12 changed lines are on screen.
>
> Everything changed is on screen.

Each source row wrapped into four visual lines. The frozen engine selected its minimum font of 22 pixels. Its calculated block height was 2,016 pixels, starting at 118 pixels. The stage clips at 1,080 pixels.

Executing the actual engine maker with element stubs confirmed 156-pixel row heights and positions below the stage. This reproduces the calculation and false claims. Browser screenshots were not obtained.

Reproduction: [probe-wrapped-real.py](/private/tmp/prc-bohr-review-OYpmru/probe-wrapped-real.py). Results: [wrapped-results.json](/private/tmp/prc-bohr-review-OYpmru/wrapped-results.json).

**Suggestion:** Include wrapped layout bounds in preflight and coverage. Reject scenes whose complete code cannot fit within the visible frame.

### 3. [warning] Required outro cues can pass while never appearing

**Location:** [check.py:326](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/check.py:326); [timing.py:252](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/timing.py:252).

**Finding:** Both checks permit a reveal timestamp exactly at the scene end. The effective reveal needs additional time.

**Evidence:** Starting with the existing valid `tiny_board` fixture, I moved only its required outro `cmd` cue to the scene's duration.

`verify_board` passed. Silent fitting stamped both the command and scene end at `5.939436619718311`. `check_stamped_cues` returned no errors.

The actual outro engine needs 0.5 seconds to reveal the command. Its fine print starts another 0.5 seconds later. Executing that maker throughout the scene produced a maximum command opacity of zero.

Reproduction: [probe-late.py](/private/tmp/prc-bohr-review-OYpmru/probe-late.py). Engine probe: [engine-probe.cjs](/private/tmp/prc-bohr-review-OYpmru/engine-probe.cjs).

**Suggestion:** Validate effective reveal completion for required elements against scene fade and the settled frame.

## Verification and limits

Probes used files archived from frozen commit `6dbb336` into a new temporary directory. No repository files were edited. Nothing was installed, committed, pushed, or published.

- `ruff check --no-cache src scripts tests` passed.
- `ruff format --check src scripts tests` passed for 114 files.
- `python -B -m mypy --cache-dir …` passed for 103 source files.
- Focused pytest passed **144 tests**, with six browser-related tests deselected. [JUnit artifact](/private/tmp/prc-bohr-review-OYpmru/pure-tests.xml).
- `git diff --check 24e5300...6dbb336 -- src scripts tests .github` passed.

I inspected the release script and workflow. I did not run package installation, the full clean-cache verifier, or browser acceptance. Those remain unverified by this reviewer.

Suggested next step: complete the fact-identity and effective-visibility fixes, then rerun frozen release verification before the user's human review.
