# Work log

Append one entry per stage or session. Newest at the bottom. Label every number measured or estimated.

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
