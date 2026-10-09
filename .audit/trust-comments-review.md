**TL;DR:** Recommend 16 complete comment/docstring deletions, covering 36 physical lines, plus one obsolete clause. Keep 17 complete contract or platform-constraint blocks and the API portion of the clause's docstring. The examined additions introduce no suppressions; the refactor flags below are optional and establish no runtime correctness defect.

Reviewed the trustworthy PR milestone in `/Users/koval/dev/prc/.claude/worktrees/readiness`.
The baseline is `24e530088b2380f54c781ab5f8f24c51ed2a601f`.
Review started at `1040ada10b4f3218525f6dcea8b95ec656b332ba`.
Deletion anchors were checked at `63f7f361aefe8bf001bdb26dbbf3b11fe970a7cc`, including the working tree.
The parent committed concurrently. Source hashes below identify the checked deletion inputs.

Read [comment-sicko.md](/Users/koval/.codex/plugins/cache/pstack-claude/pstack/0.9.79/skills/poteto-mode/references/agents/comment-sicko.md) in full before reviewing the diff.
This is supplemental model review. The user remains the sole human reviewer.

Only this report was written in the worktree.
No proposed deletion was applied. No application code, test code, dependency, Git ref, or other review report was changed.
No commit, push, or PR was created.

## Exact deletion recommendations

All line numbers refer to the checked input, before any deletion.
Each complete block below consists only of introduced comment or docstring lines.
The proposed patch follows the table.

| ID | File | Lines | Symbol | Reason |
| --- | --- | --- | --- | --- |
| D01 | [scripts/verify-release.sh](/Users/koval/dev/prc/.claude/worktrees/readiness/scripts/verify-release.sh:40) | 40-42 | checkout `paths` collection | The Git flags already select untracked fixtures. The T2 narrative explains a local implementation. |
| D02 | [src/prc/explainer/assets/engine.js](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/assets/engine.js:565) | 565 | `MAKERS.diff` note placement | The `clamped`, `below`, and row-height updates express this behavior. |
| D03 | [src/prc/explainer/check.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/check.py:264) | 264 | `verify_board` lazy import | This explains a cycle between PRC modules. It is not a foreign dependency constraint. |
| D04 | [src/prc/explainer/check.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/check.py:293) | 293-294 | `verify_board` outro branch | `s.setdefault("fine", "")` already expresses the default. |
| D05 | [src/prc/explainer/check.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/check.py:303) | 303-305 | `verify_board` numeric cue branch | The scene-duration comparison and failure message express the bound. |
| D06 | [src/prc/explainer/highlight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/highlight.py:243) | 243-247 | `attach_tokens.side_runs` | PRC chooses the lossy join. Keep the guard and per-line fallback. |
| D07 | [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:1) | 1 | module docstring | This is a coordination banner. It defines no input, result, or failure contract. |
| D08 | [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:17) | 17 | `_post` | This private helper directly calls `expandtabs(4).rstrip()`. |
| D09 | [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:22) | 22 | `_order` | This documents a private dictionary shape. A clearer name can express its purpose. |
| D10 | [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:229) | 229 | `_scene_geom` | This labels a private tuple. Named fields can express its structure. |
| D11 | [src/prc/explainer/render.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/render.py:44) | 44 | `check_tools` | The `need_video` guard expresses when FFmpeg tools are required. |
| D12 | [src/prc/skill/__init__.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/skill/__init__.py:16) | 16-17 | `PRODUCT_OUTPUTS` | This is a local duplication assurance. The constant has no consumers under `src`. |
| D13 | [src/prc/skill/__init__.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/skill/__init__.py:27) | 27 | `_canonical_text` | This private helper reads the skill file. Its test-seam rationale is not an API contract. |
| D14 | [tests/test_acquisition_errors.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_acquisition_errors.py:1) | 1-5 | module docstring | The test names and `_check_cli_failure` express the tested behavior and artifact handling. |
| D15 | [tests/test_trust_package.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_trust_package.py:1) | 1-7 | module docstring | This is scope and proof narration. The assertions already express the installer contract. |
| D16 | [tests/test_trust_render_preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_trust_render_preflight.py:1) | 1 | module docstring | This is a defect-number banner, not a public API contract. |
| D17 | [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:263) | 263, clause only | `note_risks` | Delete exactly `: clamped notes cover code`. Keep the API sentence and its final period. |


D17 corrects a comment claim.
The current `MAKERS.diff` branch moves a clamped note below its row and increases the row height.
Thus, the docstring cannot state that clamped notes necessarily cover code.
This finding does not establish a new layout defect.

The 36 deleted physical lines include two blank lines inside docstrings.
The recommendations affect ten source, script, and test files.
They preserve every executable statement and every suppression.

## Exact keep exceptions

These exceptions apply to the specific blocks listed here.
They do not grant an exception to other comments in the same function or file.

| File | Lines | Exception | Contract or constraint |
| --- | --- | --- | --- |
| [scripts/verify-release.sh](/Users/koval/dev/prc/.claude/worktrees/readiness/scripts/verify-release.sh:2) | 2-5 | CLI contract | Documents the public `--offline` mode and its cache and browser prerequisites. The argument branch and explicit failure messages enforce them. |
| [src/prc/explainer/assets/engine.js](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/assets/engine.js:690) | 690-693 | External platform constraint | CSSOM returns separate fragments for an inline span. One bounding rectangle includes empty space between unequal wrapped lines. |
| [src/prc/explainer/boards.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/boards.py:50) | 50 | Public API contract | `coverage` defines literal changed-line coverage for its callers. |
| [src/prc/explainer/doc.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/doc.py:72) | 72 | Public API contract | `uncovered` defines its files-and-symbols result and its reference semantics. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:33) | 33 | Public API contract | `changed_refs` defines signed base/head line keys and raw-text values. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:46) | 46 | Public API contract | `cited_refs` defines which receipt forms contribute references. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:85) | 85-90 | Public API contract | `rendered_refs` excludes citations and mentions from displayed code. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:119) | 119-125 | Public API contract | `line_coverage` defines the denominator and unavailable-line semantics. This distinction is part of the trustworthy milestone. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:168) | 168 | Public API contract | `coverage_summary` defines a changed-line summary rather than a file count. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:176) | 176 | Public API contract | `silent_estimate` defines seconds and the exact voice-none limit. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:184) | 184 | Public API contract | `join_preflight` defines the render rejection conditions it reports. |
| [src/prc/explainer/preflight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:263) | 263, API portion | Public API contract | Keep the statement that `note_risks` reports notes that cannot fit beside their line. Remove only D17's obsolete clause. |
| [src/prc/explainer/timing.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/timing.py:133) | 133-138 | Public API contract | `scene_windows` defines tuple order, voice-none timing, and the approximation limit for speech backends. |
| [src/prc/explainer/timing.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/timing.py:152) | 152-158 | Public API contract | `check_stamped_cues` defines fitted-time inputs and invalid cue conditions. Its fit-before-check precondition belongs to the contract. |
| [src/prc/facts.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/facts.py:1) | 1 | Public module contract | The module limits static call evidence. Its results do not establish executed test coverage. |
| [src/prc/skill/__init__.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/skill/__init__.py:1) | 1-6 | Public module contract | The installers promise one canonical instruction source and specify the Claude/Codex output transformation. |
| [src/prc/skill/__init__.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/skill/__init__.py:32) | 32 | Public API contract | `codex_body_for` identifies the returned Codex body and its canonical input. |
| [src/prc/skill/__init__.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/skill/__init__.py:65) | 65 | Public API contract | `codex_section` identifies the returned AGENTS.md section and canonical source. |

The browser exception rests on current source and the [CSSOM View editor's draft](https://drafts.csswg.org/cssom-view/#dom-element-getclientrects).
The standard defines fragment rectangles and a bounding rectangle that encloses their union.
The current `.ct` span is inline. Its renderer inserts explicit line breaks.
Both `render.render` and `doc.render_doc` embed this engine and call `prcMount`.
This establishes an active production path for the external API constraint.

A background browser proof was attempted, but Chromium failed to launch.
No browser pass or screenshot evidence is claimed.
The parent's full verifier must supply runtime GUI evidence.
The failed launch does not contradict the specified rectangle behavior.

The hunk-highlighting comment has a different basis.
PRC builds a list of hunk entries, then chooses `"\\n".join` before `file_runs`.
Joining `["a", ""]` produces `"a\\n"`; `splitlines()` returns only `["a"]`.
The lost entry follows from PRC's representation choice.
A focused `pstack:how` source trace and a standard-library probe confirmed this distinction.
The existing guard and per-line fallback remain intact.

## MUST KILL flags and correctness boundary

These flags identify local design explanations under the reviewer policy.
They are optional refactors, separate from the comment deletions.
They do not block source freezing or imply that these changes are required for correctness.

- **MUST KILL `check.verify_board`, line 264.** The lazy import explains a local module cycle. Shared phrase helpers could remove that cycle.
- **MUST KILL `highlight.attach_tokens.side_runs`, lines 237-251.** A representation that preserves hunk-entry boundaries could remove the fallback explanation. Keep the working fallback during this milestone.
- **MUST KILL `preflight._order`, line 22.** The name hides a hunk-line lookup. A clearer name could replace the private shape explanation.
- **MUST KILL `preflight._scene_geom`, line 229.** Named geometry fields could replace the private tuple explanation.
- **MUST KILL `skill.PRODUCT_OUTPUTS`, lines 16-18.** The production constant duplicates metadata and has no consumers under `src`. Removing or deriving it is an optional cleanup.

The test-module headers are deletion-only recommendations.
Their existing test names and assertions already express the claimed behavior.
No test refactor is requested.

No runtime correctness defect is asserted by this bounded comment review.
D17 concerns comment accuracy. D01-D16 concern comment policy.
API docstrings remain because they define caller-visible semantics.

## Scoped suppressions review

The examined additions contain zero new suppressions.
The scan found 26 existing physical lines, with 28 directive instances.
Two import lines each contain both a type suppression and an import-order suppression.

These are scope skips, not newly approved correctness or dependency exceptions.
No suppression-removal recommendation is made outside the introduced-comment scope.

| File | Existing lines | Directives | Disposition |
| --- | --- | --- | --- |
| [src/prc/brief.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/brief.py:463) | 463, 609 | `fmt: skip` | Pre-existing; skip. |
| [src/prc/cli.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/cli.py:73) | 73, 78; 516 | `type: ignore[no-untyped-def]`, `type: ignore[call-overload]`; `fmt: skip` | Pre-existing; skip. |
| [src/prc/explainer/highlight.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/highlight.py:70) | 70-71; 211 | `type: ignore[import-untyped]` plus `noqa: I001`; `type: ignore[no-any-return]` | Pre-existing; skip. |
| [src/prc/explainer/render.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/render.py:50) | 50; 251, 259, 367; 308 | `noqa: F401`; `fmt: skip`; `noqa: BLE001` | Pre-existing; skip. |
| [src/prc/github_source.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/github_source.py:66) | 66; 105 | `noqa: S310`; `fmt: skip` | Pre-existing; skip. |
| [src/prc/pipeline.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/pipeline.py:301) | 301 | `type: ignore[attr-defined]` | Pre-existing; skip. |
| [src/prc/presentation/card.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/card.py:353) | 353; 364 | `noqa: F401`; `noqa: BLE001` | Pre-existing; skip. |
| [tests/test_card_comment.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_card_comment.py:610) | 610 | `noqa: BLE001` | Pre-existing; skip. |
| [tests/test_explainer_doc.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_explainer_doc.py:297) | 297, 473, 498, 518 | `noqa: BLE001` | Pre-existing; skip. |
| [tests/test_map_browser.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_map_browser.py:92) | 92 | `noqa: BLE001` | Pre-existing; skip. |
| [tests/test_map_grouping.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_map_grouping.py:261) | 261 | `noqa: BLE001` | Pre-existing; skip. |
| [tests/test_release_package.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_release_package.py:101) | 101 | `fmt: skip` | Pre-existing; skip. |

No introduced `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, `prettier-ignore`, `noqa`, or `type: ignore` was found.
No introduced suppression requires a correctness-rule removal or a guilty-symbol flag.

## Other skips

- Existing comments and unchanged docstrings remain outside scope.
- Markdown prose, plans, guides, and other reviewers' reports are not source comments.
- The recorded external source inside `tests/data/trustworthiness/librarysync-decorator.json` is fixture data. Preserve it verbatim.
- HTML section markers and HTML comments inside output strings are functional data. No marker deletion is proposed.
- No introduced legal header or issue/RFC constraint link required classification.
- No broader application, test, release, or dependency review was performed.

## Proposed patch, not applied

This patch changes comment text only.
The shortened `note_risks` docstring retains its API contract.

```diff
--- a/scripts/verify-release.sh
+++ b/scripts/verify-release.sh
@@ -40,3 +39,0 @@
-# Intended but not yet committed .py/.json fixtures (for example new T2
-# regression tests) must also verify; otherwise the isolated run silently
-# skips them until their local commit lands.
--- a/src/prc/explainer/assets/engine.js
+++ b/src/prc/explainer/assets/engine.js
@@ -565,1 +564,0 @@
-      // A clamped note would sit on the code: drop it under its row instead.
--- a/src/prc/explainer/check.py
+++ b/src/prc/explainer/check.py
@@ -264,1 +263,0 @@
-    # Lazy import: timing imports this module for find_phrase/spoken.
@@ -293,2 +291,0 @@
-            # `fine` is optional small print: absent means an empty default,
-            # which the engine already renders as an empty string.
@@ -303,3 +299,0 @@
-                # Absolute seconds from the scene start: a cue stamped after
-                # the scene ends would never show, so its rows would be
-                # counted on screen without ever appearing.
--- a/src/prc/explainer/highlight.py
+++ b/src/prc/explainer/highlight.py
@@ -243,5 +242,0 @@
-                # Hunk text that does not round-trip through whole-text
-                # highlighting (for example trailing blank lines, which
-                # "\n".join ends with a newline that splitlines drops):
-                # tokenize each line on its own so every hunk line keeps
-                # a runs entry instead of crashing on a short list.
--- a/src/prc/explainer/preflight.py
+++ b/src/prc/explainer/preflight.py
@@ -1,1 +0,0 @@
-"""One preflight for board check and render: line coverage, join parity, note fit."""
@@ -17,1 +15,0 @@
-    """The render transform: expand tabs, strip trailing whitespace."""
@@ -22,1 +19,0 @@
-    """(path, ref) -> hunk line, with ref str(new) or -old like boards use."""
@@ -229,1 +225,0 @@
-    """Gutter, wrap columns, per-row wrap map, and engine font size for a diff scene."""
@@ -263,1 +259,1 @@
-    """Diff notes whose box cannot fit beside their line: clamped notes cover code."""
+    """Diff notes whose box cannot fit beside their line."""
--- a/src/prc/explainer/render.py
+++ b/src/prc/explainer/render.py
@@ -44,1 +43,0 @@
-    # Key-only still previews never encode or mix audio, so they need no ffmpeg.
--- a/src/prc/skill/__init__.py
+++ b/src/prc/skill/__init__.py
@@ -16,2 +15,0 @@
-# Canonical metadata mirrored from SKILL.md; the instruction prose itself
-# always comes from the file, never from a second hand-written copy here.
@@ -27,1 +24,0 @@
-    """The canonical instruction text. Separate seam so tests can vary it."""
--- a/tests/test_acquisition_errors.py
+++ b/tests/test_acquisition_errors.py
@@ -1,5 +0,0 @@
-"""Offline acquisition failures: enumeration, fetch, reread, drift, and checkout.
-
-CLI regressions run the real module entry point with injected provider failures.
-They retain exit status and both output streams under artifacts/trust-acquisition.
-"""
--- a/tests/test_trust_package.py
+++ b/tests/test_trust_package.py
@@ -1,7 +0,0 @@
-"""Trust-package regressions: D14 single-source instructions, D16 clean-cache verify.
-
-Scope: src/prc/skill/*, scripts/verify-release.sh, release packaging.
-D14 is proven behaviorally: the Codex body is derived from the canonical
-SKILL.md, so consistency holds by construction instead of by parallel
-string assertions.
-"""
--- a/tests/test_trust_render_preflight.py
+++ b/tests/test_trust_render_preflight.py
@@ -1,1 +0,0 @@
-"""Trust-render regressions: D7 line coverage, D9 join parity, D10 notes, D11 fine, D12 estimate, D13 guide."""
```

## Input hashes and validation

Check these hashes before applying the patch.
If an input changed, match the quoted patch text to the new lines first.

| Proposed file | SHA-256 |
| --- | --- |
| `scripts/verify-release.sh` | `e17f82be5979ca940d25c49ab933fa0c0c57e5e33ed1c1ecdee0bee74d1ada9c` |
| `src/prc/explainer/assets/engine.js` | `1e62c5feae188aac9887c5550ad4f3ba3b9f5e283243c96b7e76bf3c87281f87` |
| `src/prc/explainer/check.py` | `33c622e6934e3af49823a95bb4f9f053effa2465785f6c0499c9c76c5ea9a006` |
| `src/prc/explainer/highlight.py` | `39ca983d84252eacd9c9fb041499216ff165b599214dfe44cba1c7bb9c11188b` |
| `src/prc/explainer/preflight.py` | `75f6413f409ecad823d22a037096fa495aa82c2c2b55c9475511223aecee22d0` |
| `src/prc/explainer/render.py` | `ac7dc04144e141fb9b4dd9cab2b909e0df7570496c1a6327b00866dd9e47b026` |
| `src/prc/skill/__init__.py` | `efb05192eaccee73b9d37691f081744769766977c163c98e808883044068437b` |
| `tests/test_acquisition_errors.py` | `932e15cff95a962fefbf3f717021136eb9364e5a5c7bad557d1a2aac28952754` |
| `tests/test_trust_package.py` | `d19bce3c54a9645dff05aa59d3a07d01daf9491263e57af8f086038fb3e868b5` |
| `tests/test_trust_render_preflight.py` | `38da90bc7f4bff6e937eaad3bea589d8a92bc2ccc8853407f72e8b02ea09811a` |

The read-only proposal validator checked every deleted line against `git diff --unified=0 24e5300`.
Result: all 36 complete-block lines and the D17 line are introduced lines.

Python parsing passed for all eight proposed Python inputs.
After removing docstrings from both syntax trees, every executable AST matched.
The validator used physical newline boundaries, so Unicode separators inside source strings remained intact.

`bash -n` passed on the proposed release-script text through standard input.
The JavaScript deletion contains only a standalone `//` comment.
No source proposal was written to disk.

The embedded patch passed `git apply --check --unidiff-zero`. No deletion was applied.

Lint, typecheck, tests, build, and the clean-cache verifier were not run by this reviewer.
The parent owns those checks after the single accepted deletion pass.

Next step: apply accepted comment deletions once, then complete the trustworthy PR milestone's full clean-cache verification.
