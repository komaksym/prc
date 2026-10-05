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
