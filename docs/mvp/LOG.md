# Work log

Append one entry per stage or session. Newest at the bottom. Label every number measured or estimated.

## 2026-10-22. Verification cleanup

Added annotations to the explainer test helpers. Strict mypy now reports no issues in 120 files.
Applied existing Ruff formatting without changing assertions or runtime behavior.
The release copy now initializes Git before validation, so Ruff preserves the source ignore rules.
The new regression failed on the old script and passes with ignored experiments and failing source cases.
Final acceptance runs the isolated release command after the cleanup commit.
Its evidence remains under `artifacts/release/verify/`, with the latest passing run in `latest-success.txt`.

## 2026-10-06 01:00 CEST. Handoff (Opus)

- Moved the project from `~/dev/Codex/2026-10-04/pr-comprehension-implementation` to `~/dev/prc`. The old path is a symlink to the new one, so old absolute paths still work. Repaired the git worktrees.
- Fast-forwarded `main` from `8c6374e` to `visual-map` (`c54b960`), the branch that merges every map branch.
- Verify on `main` at the new path: ruff ok, format ok, mypy ok, 320 passed, build ok, 2 min 44 s (measured).
- Explainer prototype from the new path: `check.py` on mdp12 gives 30 receipts verified, the join tests give 25/25, and `spike/run12.py` gives 287 lines with 0 mismatches (measured).
- `prc map` live on open PR 19: 14 s, 311 changed symbols, 639 calls (measured). The first screen is unreadable (`evidence/pr19-map-before.png`). This led to Stage 6.
- Diff scene frame QA baseline: mdp12 5/5, mdp17b 2/4 (measured, `prototypes/explainer/eval/baseline/RESULT.md`).
- Copied the 2026-10-05 session scratchpad, which lives in a temp folder that a reboot would delete, to `prototypes/scratch-2026-10-05/`. Copied the public agent PR corpus to `eval/corpus/public_agent_prs.json`.
- A fresh Opus reviewer checked the handoff against the code and reported 15 findings. The three blockers were checked by hand and confirmed: Kokoro needs Python below 3.13 while `.venv` runs 3.13.5; with the gutter, the mdp12 font formula gives 36, not 38; and the bakeoff's `cutTokens` throws on a blank row. All 15 findings are fixed in the docs. The main changes:
  - the dev venv moves to Python 3.12;
  - the voice downloads and the `~/.claude` writes are on the ask-first list;
  - tests copy their data into `tests/data/`;
  - the card is a new template with defined stats;
  - Mermaid labels have full escaping;
  - `--voice none` uses character-share timing;
  - the engine refactors to `mount()` for the doc;
  - `--map` covers stored heads.

## 2026-10-06 02:25 CEST. Stage 0 start (full MVP run, poteto-mode)

- Throughput checkpoint: blocking first steps are Stage 0 verify, then Stage 1 questions and Stage 2 diff scene in parallel. Independent workstreams are (a) eval questions plus C0 baseline in main repo and (b) diff scene in prototypes/explainer (own git repo, no shared files except LOG.md). Smallest safe decomposition is one owner per stage. Stages 4 to 7 fan out after Stage 3 merges.
- Verify at `458f61b` on main: ruff ok, format ok, mypy ok (64 files, measured). pytest running in background at start. Tools measured: ffmpeg 8.1 present, Playwright Chromium 1232 and 1234 cached, explainer `.kvenv` Python 3.12.7 with tree-sitter plus Pygments plus Playwright.
- Launched two background delegates: Stage 1 eval questions and C0 baseline, Stage 2 diff scene per docs/mvp/diff-scene.md.

## 2026-10-06 11:00-13:00 CEST. Stage 1 questions and C0 baseline (eval-questions branch)

- Subagent spawn blocked (depth limit 1), so all 12 PRs were done directly. Read each PR body plus `gh pr diff` (measured line counts: pr19 8568, pr10 2822, pr8 2140, pr13 1517, pr16 1387, pr5 1111, pr15 993, pr7 998, pr14 495, pr17 453, pr11 340, pr12 357) and head code from `prototypes/mdp/store/git-cache/*.git`.
- Git note: `rev:path` does not resolve in these caches (`cat-file -p <sha>:<path>` prints the commit); used `ls-tree` to get the blob sha then `cat-file -p <blob>`. `validate_questions.py` does the same.
- Committed `test(eval): freeze comprehension questions v1` (`e5c7261`): 12 files, 8 questions q1..q8 each, head_shas 5ec569d (19), 537a16d (17), df74ac3 (16), 1b18345 (15), 66e8fe4 (14), f59b09a (13), 0c54c1a (12), 306ff5a (11), 5498b6c (10), dc3f451 (8), 1f2f010 (7), 5f4440d (5). Every evidence line re-checked against its head blob; exact keys are substrings of evidence lines.
- Harness: `scripts/eval/validate_questions.py` (5 PLAN Stage 1 checks) passes checks 1-4 on all 12 files; `scripts/eval/grade.py` grades exact/set/bool/location after whitespace+quote normalization, free text by hand.
- C0 baseline (title+description packets, honest `CANNOT TELL` answering): overall correct 31/96 = 32.3% (measured), partial 31/96, wrong 0, cannot-tell 34/96. Per-PR correct: 37.5% max (PRs 7,8,10,13,14,15,16,17), 25% (PRs 5,12,19), 12.5% (PR 11). Check 5 holds: no PR above 60%, questions are not too easy. Targets C4>=85, C3>=70, C2>=60, C1>=35, misleading 0 committed in `eval/runs/2026-10-06-baseline/scoreboard.md`.
- Committed `test(eval): add C0 baseline packets, answers and scoreboard` (`7e7aba7`): 40 files (12 packets + prompts, 12 answers, results.json, scoreboard.md, 2 harness scripts).
- Open problems: C0 reader/grader was the question author (no fresh agent available at this depth); mitigated by mechanical exact-match discipline, but Stage 8 should re-run C0 with a fresh reader. `grade.py` set-grading treats a proper subset as partial; free-text q6 has no key_facts (kept as prose keys).

## 2026-10-06 11:45 CEST. Stage 2 diff scene done (poteto-mode delegate, clean restart)

- Six milestones in `prototypes/explainer` (own repo, from `9c3e7fe`), one Conventional Commit each, no push. Section 1 commands pass at every milestone end: `check.py` mdp12 30 receipts verified, jointest 25/25, `spike/run12.py` 287 lines 0 mismatches (all measured).
- Step 1 `highlight.py` + `test_highlight.py` (14 failure modes, measured: 2958 hunk lines over PR 12/17/4/14 join with 0 mismatches; colours match the spike).
- Step 2 build attaches tokens (`--git-dir`, `tokens_s<i>.json` join gate, `.ct textContent` DOM check), engine draws token spans (regex highlighter deleted), ligatures off. Full videos 63.4 s mdp12, 89.6 s mdp17b (measured).
- Step 3 `diffrows.pair_rows` + 8 tests (exact changed-token lists as specified); removed rows stay red, added keep green, word marks, strike deleted.
- Step 4 `wrap_row` + 6 tests; FS cap 40 with width/height bounds and < 28 px lint. DOM FS 38 mdp12 / 34 mdp17b (measured); no `layout:` lines on mdp12/mdp17b/mdp4/mdp14.
- Step 5 gutter `ceil((digits+1)*0.72)` = 4 columns on both boards (measured); DOM FS 36 mdp12 (measured); numbers once per row on the first visual line; no clipping.
- Step 6 OCR on six mdp12 frames (measured): 1920 px 30/31 (baseline 31/31, miss is the note-covered update tail), 800 px 26/31 (baseline 28/31, gutter digits add noise), 341 px 10/31 (baseline 8/31). Frame QA (measured): mdp12 5/5, mdp17b 4/4 (baseline 5/5, 2/4); the two "before" questions are now answerable. Reader-freshness caveat: nested subagents blocked, read done strictly from pixels, needs a fresh-reader confirm. `BOARD.md` diff paragraphs rewritten; `E/HANDOFF-RESULT.md` written with per-milestone numbers, frames, and surprises.

## 2026-10-06 12:00-13:30 CEST. Stage 3 explainer port (explainer-port branch)

- Prototype FROZEN at 6bd6507, read-only. 9 commits, no push. Scope note: PLAN allowed
  src/prc/explainer/, tests/test_e2e_explain.py, tests/data/explainer/, tests/data/boards/,
  pyproject.toml, src/prc/cli.py, src/prc/pipeline.py, docs/mvp/LOG.md. Additionally created
  src/prc/explainer/doctor.py (PLAN failure mode requires `prc doctor` to echo the missing-tool
  line), tests/test_explainer_{check,highlight,diffrows,jointest,render}.py (PLAN turns plant.py,
  Stage 2 tests and the 25 jointest cases into pytest), and docs/mvp/evidence/stage3/ (PLAN
  requires the compared frames there). Nothing else touched.
- Test data (committed first): PR 12/14/17/4 map.json, 7 prototype boards, base/head blobs of
  every hunk file with a skip manifest (2.0 MB total), jointest fixtures + synthetic map.
- Check port: behavior-identical, 6-board parity matches prototype receipt/cover counts exactly
  (mdp12 30/2/3, mdp14 20/4/7, mdp17b 64/1/4, mdp4 32/2/49, mdp4high 52/15/49, mdp4zoom 87/14/49;
  all measured). 10 plants fail with their messages.
- highlight/diffrows/jointest ports: jointest verdicts byte-identical to prototype on all 25
  fixtures (measured). --map is required (no absolute prototype default).
- Voice: kokoro lazy, say via /usr/bin/say, none at 14.2 chars/s (measured: 680 caption chars
  over 47.93 s Kokoro af_heart audio in out/mdp12-baseline/, per-sentence 12.9-15.7 median 14.2).
  Voice extra NOT installed in any venv (ask-first): mdp12/mdp17b built with --voice none,
  recorded here as the reason. Dev venv pinned to 3.12 (uv python pin 3.12, uv sync).
- Deps: pygments==2.21.0 added (colours languages tree-sitter does not cover here);
  tree-sitter==0.26.0, python/js==0.25.0, typescript==0.23.2 pinned to .kvenv (measured).
- Shop E2E (--voice none): exit 0, 16 receipts, video 41.29 s vs predicted 41.29 s (exact for
  none; check-formula estimate 37.27 s), 1920x1080 30 fps h264, no layout warnings. Output in
  artifacts/e2e/explain/ (ignored by git). Looked at title/groups/diff/list/outro frames.
- Outro null-url crash fixed: fixture map.json has url null, port writes "pr" (measured in
  player.html). Prototype build.py line 184 would crash.
- Real PRs (live heads match stored heads exactly, so no --map): mdp12 63.39 s in 72 s wall
  (prototype 63.4 s), mdp17b 89.67 s (prototype 89.6 s), both --voice none (Kokoro extra not
  installed). Diff end frames at 800 px match the prototype frames apart from nothing visible:
  same rows, numbers, red/green tints, word marks, wrap, note-over-tail. Frames in
  docs/mvp/evidence/stage3/.
- Verify on 3.12.7: ruff ok, mypy ok (80 files), 396 passed + E2E, build ok (measured).
  Pre-existing drift, not mine: `ruff format --check .` flags scripts/eval/grade.py:70 (Stage 1
  file, untouched on this branch). pytest needed norecursedirs=data (vendored test_*.py blobs)
  plus mypy/ruff excludes for tests/data/.
- Open problems: E2E asserts duration against run.json predicted_seconds (voice-aware; exact
  for none) rather than the check-formula estimate_seconds, which undershoots by ~10 percent
  because it lacks the per-sentence estimator. mdp12/mdp17b videos use none timing, so scene
  starts drift ~0.6 s from the Kokoro prototype; compared at scene-relative times.

## 2026-10-08. Project verification skill

- Added `.agents/skills/verify/SKILL.md`, five feature recipes, and an executable map driver. The desktop discovers the project skill.
- The driver calls the real fixture CLI, verifies checkout in Chromium, and captures overview, open drawer, and closed drawer screenshots. Unique scratch stores are removed; proof survives.
- Screenshot inspection found both drawer shots captured during animation. A failing geometry assertion reproduced the defect. The helper now waits for each visible transition.
- Independent review found lost failure diagnostics and three incomplete recipes. An injected real browser error reproduced missing checks.json. The helper now retains collected errors, requests, revision, map hash, and failure information while failing the run.
- Final normal proof: `artifacts/verification/map-uy5vvt1z`. Failure proof: `artifacts/verification/map-rrkr_4j_`. Recipe proof: `artifacts/verification/recipes-7ozhtxxa`. Screenshot inspection confirmed readable code and visible keyboard captions.
- Commands: `env PLAYWRIGHT_BROWSERS_PATH=/Users/koval/dev/prc/artifacts/release/browser-cache .venv/bin/python .agents/skills/verify/scripts/map.py` passed. Scoped ruff, strict mypy with MYPYPATH=src, structural checks, reference checks, persisted-decision reads, rejected-board CLI calls, and Play/Pause/keyboard checks passed.
- `bash scripts/verify-release.sh` passed in `artifacts/release/verify/run-yu4NDi`: lint, formatting, mypy (97 source files), 563 tests, sdist, wheel, and installed-wheel rendering outside source. These numbers are measured. Video was 1920x1080 at 30 fps; browser errors were empty.
- Reused Playwright because Vercel agent-browser was unavailable in this session. No production dependency was added. Five recipes were seeded; this task does not prove every recipe or live GitHub acquisition.
- Final independent recheck passed all four findings. Reports: `.audit/verification-skill-review.md` and `.audit/verification-skill-recheck.md`.
- Release evaluation and final human comparison remain open. This skill does not establish release acceptance. No remote is configured; push and PR creation are skipped.

## 2026-10-08. Public release readiness

- Assessed whether prc is ready to release as a useful pull request visualizer. The report is `docs/launch/READINESS-2026-10-08.md`. The decision trail is `.audit/readiness-2026-10-08.tsv`.
- Verdict is not ready (inferred from measured checks). A fresh public clone at `eeaba4b` installs on one Mac and fetches six unseen live pull requests. Output accuracy, usefulness evidence, the fresh-clone test suite, and license and distribution fail.
- Two fresh agents with only the installed instructions finished the board workflow, and each logged many instruction problems. Two defects reproduced. `board check` passes a blank diff row that `explain` rejects, and `layout_warnings` misses a note over code.
- Added `scripts/probe-public.sh`. It reruns the clone, install, offline example and boardless explain path. It starts with an empty uv cache, records the environment, and exits 1 if a step fails.
- Proof, ignored by git, is in `artifacts/readiness/2026-10-08/` (u1 install, u3 live pull requests, u4 trials, u5 frames and repros, u9 report screenshots, tmp-copy). Key images are tracked in `docs/launch/evidence/readiness-2026-10-08/`.
- Verify in the worktree passed. ruff check, ruff format, mypy (97 source files), pytest (572 passed in 259.89 s) and uv build exit 0. The fresh clone fails one release test because its uv cache is cold (D16). shellcheck is not installed; `bash -n` passes on the probe script.
- Accepted six independent review flags. Corrected the baseline conclusion, probe exit status, install evidence, D15 evidence, voice limits and private-path count. The `say` example has non-silent audio; human listening and Kokoro remain untested.
- No push and no PR. START-HERE.md requires the owner's yes.


## Trustworthy facts, 2026-10-09

The domain facts module supplies card, comment, and map totals. Static calls are qualified as evidence, not test coverage.
Regressions include unsupported Go, TypeScript object handlers, browser-test paths, large-text counts, dependency risk, and the original librarySync decorator case.
Proof lives under `artifacts/trustworthiness/2026-10-09/regressions/`. `stats-green.png` shows one test file for two test functions. `dense-green.png` and `dense-member-green.png` show readable groups and member names.
The milestone is still in progress. Rendering, clean-cache installation, and human acceptance remain open.

## Trustworthy PR explanation evidence, 2026-10-09

The implementation and acceptance package pass at b880513. Human acceptance remains pending.
Facts, static-call qualifications and changed-line coverage stay consistent across outputs.
Regression fixes cover the assessment's D1 to D17 and defects found in later browser and model reviews.
Quoted property identities, token-independent wrapping, required reveals and malformed boards have regression cases.

`bash scripts/verify-release.sh` passed with an empty uv cache in `artifacts/release/verify/run-TnN2MF`.
Ruff, formatting, mypy on 103 source files, wheel and sdist builds passed.
Pytest passed 802 tests with no failures, errors or skips.
The installed wheel produced all five outputs outside the source checkout. Its 1080p video lasts 41.008 seconds.
The source archive comparison matches all source, test and script bytes to b880513.

The acceptance package is `artifacts/trustworthiness/2026-10-09/acceptance/index.html`.
It contains librarySync#98, em#5756 and swarm-deploy#116, their original diffs and their pinned base/head revisions.
Each case includes a map, narrated video, walkthrough, card, comment, provenance and output hashes.
Changed lines on screen are 16/79, 3/112 and 5/329. The package lists omitted lines and unsupported files.
Chromium checks passed for every map, drawer, card, walkthrough and actual MP4 playback.
The parent inspected final browser images and all 19 settled video scenes.
Vercel agent-browser checked 35 local review links, three playing videos and map navigation without browser errors.
Proof is in `acceptance/hub-browser-b880513`. The headless session is closed.

Independent model reviews used GPT, Muse and GLM. Reproduced defects were corrected before final verification.
The final GPT recheck found no new regression. Review reports are in `.audit/trust-*-review*.md`.
DeepSeek checked the final decision trail against the transcript and durable proof. It found no high or medium issues.
Minor evidence gaps are corrected or disclosed in `.audit/trust-milestone-trail-final-review.md`.
The user is the only human reviewer. The worksheet retains three pending decisions.
External project tests and human narration listening remain unverified. Kokoro is not installed.
No push or new PR is approved. License, package-name and publication decisions remain separate.
The full milestone record is `docs/launch/TRUSTWORTHY-PR-EXPLANATIONS.md`.

## Final trustworthy PR inspection, 2026-10-09

The machine work for the trustworthy PR explanation milestone is complete at source 548d8ab.
The user is the only human reviewer. All three acceptance decisions remain pending.
Public release evaluation and publication decisions remain separate.

The earlier entry overstated complete card inspection and 35 hub clicks at b880513.
Those claims are superseded by the final inventory and executed browser records below.
Historical entries and their measured test counts remain unchanged.

`scripts/verify-release.sh` passed from an empty uv cache in `artifacts/release/verify/run-uVHho9`.
It passed lint, formatting, mypy on 104 files, 812 tests without failures, errors or skips, and wheel and source builds.
The source archive matches 237 code, test, script and metadata paths at 548d8ab.
The installed wheel produced all five outputs outside source. Its browser record reports no errors.
The parent inspected its five browser images. Its video is 1920x1080 at 30 fps and lasts 41.008 seconds.

The final wheel rebuilt all three acceptance cases at `artifacts/trustworthiness/2026-10-09/acceptance`.
Its installed-package verifier confirms original diffs, code quotes, per-file totals, revisions, merge evidence and hashes.
All 35 local links passed in background Vercel agent-browser with a screenshot per result. The session is closed.
Proof is `acceptance/verification.json` and `acceptance/hub-browser-548d8ab/checks.json` within that directory.

Direct model inspection covers three cards, 21 complete-walkthrough segments and 19 decoded video scenes.
All 43 image hashes match. Video pixels match each final MP4. The walkthrough segments cover every page without gaps.
Proof is `artifacts/trustworthiness/2026-10-09/inspection-548d8ab/inspection-results.json` and `artifact-bindings.json`.
These checks do not replace human judgment of usefulness or narration.

Tests for D18 to D24 landed at cadf6f9 before fixes at 548d8ab. All 15 final regressions pass.
Independent GLM correctness review found no remaining defect in that delta.
The final comment review requested two narrative removals; both are complete without changing executable test logic.
The focused test, full ruff checks, mypy and git diff checks pass after those removals.
Reports are `.audit/trust-final-inspection-review.md`, `.audit/trust-inspection-comments-review.md` and `.audit/trust-final-inspection-closure.md`.

Next step. The user reviews the three cases and completes `acceptance.md` in the final acceptance directory.

## GitHub browser baseline, 2026-10-09

The user chose the normal GitHub PR page as the human review baseline.
The packet and worksheet now direct the user to review on GitHub.
The baseline includes description, Files changed, discussion, checks and navigation.
Scores measure the extra help each PRC output adds beyond that baseline, from 1 to 5.
Each case has fields for baseline notes, added help, preferred formats, would-use judgment and correctness findings.
All three human decisions remain pending. Retained raw diffs are optional verification evidence.

Read-only `gh api` checks confirm all three GitHub base/head pairs, file counts and line totals match the captured cases.
The browser check initially lacked the baseline and grading instructions. Both appear after the update.
Background Vercel agent-browser screenshots confirm readable instructions. All 35 local and three GitHub destinations are preserved.
Proof is `.audit/github-review-baseline.json` and `artifacts/trustworthiness/2026-10-09/github-baseline/{before,after}.png`.
Product source and rendered outputs remain unchanged. The frozen agent evaluation keeps its existing protocol.

Next step. The user reviews the three PRs on GitHub and records the extra help from PRC in the worksheet.


## Step 1 machine verification, 2026-10-10

Source be2e7fa passes run-NYgULN from an empty uv package cache. All 855 tests pass with no skips.
Static checks, build, installed-wheel browser interaction and forced Kokoro audio smoke pass. Chromium and model weights were reused.
The three frozen real PRs now include one gated baoyu infographic, the PR Lens map and Kokoro narration.
Original revisions, diffs, counts, quoted code and output hashes match. All 41 local hub links pass.
Independent visual inspection covers 44 inventory images and 39 active-caption samples. Readability limits remain documented.
Full soundtrack transcription and sampled waveform comparison support the machine audio checks. They do not prove listening.
This runtime cannot receive audio input. s2e3, onComplete and ErrNotExist have explicit listening checks in the worksheet.
The goal stays open for direct listening. Human acceptance, public release, push and PR creation remain gated.

Next step. Review the complete three-case package and record the listening and usefulness judgments.

## Game battle review, 2026-10-21

Added Tuxemon/Tuxemon #2370 as one light-mode review with actual before-and-after game screenshots.
The author supplied the screenshots. PRC did not install or run Tuxemon.
The comparison shows overlapping monster sprites before and separate pairs afterward.
Nine storyboard scenes cover representative lines from all four changed Python files.
Sixteen reading entries explain every changed code unit, including supporting combat refactors.

The board passes its receipt check. The focused renderer, transition and UI-evidence checks passed 122 tests.
Independent factual review found a screenshot-description error, which the parent corrected before the final render.
The second native baoyu infographic candidate passed the unchanged text gate.
The full release check and exact-artifact browser, click, vision and listening checks remain required before handoff.
Their records are collected under `/private/tmp/prc-battle-proof/` and the release verification directory.
The final local output is `artifacts/game-review/light/Tuxemon-2370/labsheet/`.
Existing study outputs and application code remain unchanged. Publication still requires the user's approval.

The exact-page browser pass found a callout intercepting a code-line click.
The renderer now lets clicks pass through decorative callouts. A browser regression test fails before this fix and passes after it.
The page verifier scrolls each target into view before clicking it.
The full test suite passes 1126 tests. Source lint and the package build pass.
The repository typecheck still reports 16 existing errors in test_explainer_v6.py and test_transitions.py.
The isolated release check stops on existing lint errors in tracked artifact scripts.

Independent reviewer Leibniz inspected all 17 page shots and the native baoyu infographic.
The parent found three video scenes with delayed added-code reveals and moved those reveals into the first sentence.
Socrates checked the six changed cue anchors against the source board and reran the receipt check.
The rebuilt 102.3-second labsheet video reuses the original narration.
Final click and visual records are under `/private/tmp/prc-battle-proof/final-click/` and `/private/tmp/prc-battle-proof/final-vision/`.
The Prove It Works principle required checking the generated page and video directly.
The Fix Root Causes principle put the click fix in decorative callout hit testing and the timing fix in the source board.

On 2026-10-22, the parent resumed the exact-output handoff check without changing the generated artifacts.
The live page still answers at its existing local URL. Its screenshot pair remains readable.
The rebuilt video's Parakeet check passes with no lost words or identifier gaps.
The final proof set is `/private/tmp/prc-battle-proof/handoff-current/`.
The game example remains a local checkpoint. The existing repository typecheck and release-lint failures remain open.
