# PRC verification map

Read this index before choosing a recipe. Use unique `VERIFY_STORE` and `VERIFY_PROOF` paths from [verify](../SKILL.md).
Run `.venv/bin/python -m prc.cli` for commands. Open browser pages in background Playwright with screenshots.
Fixtures need no credentials. Live GitHub entry points require network access and separate evidence.
Capture commands, actions, resulting screens, and stored effects. Keep proof after cleanup.
Report untested entry points explicitly.

- [Explainer](explain.md) covers the required infographic, Kokoro video, clickable page, and stored-source rendering.
- [Board tools](board.md) covers guide, code lookup, coverage, and receipt checks.
- [Review state](review.md) covers local review, freshness, and decisions.
- [Skill installation](install.md) covers disposable Claude and Codex destinations.
- [Paired session hub](paired.md) covers every hub button path with refusal recovery. Hub changes require `scripts/verify_paired_hub.py` PASS and cited proof. Operator-facing handoffs require scripts/handoff_study_hub.py with its supervised record under artifacts/handoff/.
