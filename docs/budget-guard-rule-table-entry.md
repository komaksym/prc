# Budget guard: rule-table entry (proposal, AGENTS.md untouched)

## Proposed row

Redline metered runs at 5 pct of the 5h budget: checkpoint, sleep with zero new dispatches, resume after reset | policy (95 pct redline, loop, checkpoint convention) owned by the global budget-guard skill; tests/test_budget_guard.py and tests/test_budget_guard_global.py fail when the gate, checkpoint, resume, or single-source rule regresses | the guard reads an injected snapshot or `get_usage_limits`; it cannot see the live meter unless the run wires the provider, so pass the reader once per run.

## Mistake classes (correct)

1. Burn-to-zero dispatch: runs keep dispatching below 5 pct and die mid-flight. Evidence: 2026-10-11 omitted-model dispatch ran without a gate (tests/test_pstack_models.py replays it); repo grep shows no budget owner before this change. Fix at architecture level: one gate on the meter reading. Types alone cannot help because any float comparison compiles.

2. Lost queue on retry: checkpoint formats drift per caller and resume restores nothing. Evidence: release audit hit overwritten run logs and read-only copy failures; PLANS.md notes fresh-proof-dir rework. Fix at architecture level: one atomic checkpoint/resume path with a versioned schema. A lint cannot verify durable bytes; behavior tests do.

3. Silent stale resume: an old checkpoint resumes without a loud failure. Evidence: stale-mirror class where a @max mirror enforced the wrong row (tests/test_pstack_models.py stale fixtures). Fix at type plus behavior level: versioned CHECKPOINT_SCHEMA with a ValueError naming the checkpoint call, plus tests that fail on silent acceptance. Docs alone never fail, so they sit last.

4. Repo-local copy of the guard: a project skill redefines the threshold and the two drift. Evidence: this repo carried `.agents/skills/budget-guard/SKILL.md` beside the global skill. Fix at architecture level: delete the copy; the global skill is the single source of truth and tests/test_budget_guard_global.py fails when a project copy redefines a threshold. Deleting beats a pointer because a pointer still needs reading.
