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
