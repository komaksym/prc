# Budget guard: rule-table entry (proposal, AGENTS.md untouched)

## Proposed row

Redline metered runs at 5 pct of the 5h budget: checkpoint with BudgetGuard.checkpoint, sleep with zero new dispatches, resume with BudgetGuard.resume after reset | tests/test_budget_guard.py fails when the gate, checkpoint, or resume path regresses; src/prc/budget_guard.py is the single owner | The guard reads an injected snapshot; it cannot see the live meter unless the run wires the provider, so pass the reader once per run.

## Mistake classes (correct)

1. Burn-to-zero dispatch: runs keep dispatching below 5 pct and die mid-flight. Evidence: 2026-10-11 omitted-model dispatch ran without a gate (tests/test_pstack_models.py replays it); repo grep shows no budget owner before this change. Fix at architecture level: BudgetGuard owns the meter reading and check_dispatch_allowed is the one gate. Types alone cannot help because any float comparison compiles.

2. Lost queue on retry: checkpoint formats drift per caller and resume restores nothing. Evidence: release audit hit overwritten run logs and read-only copy failures; PLANS.md notes fresh-proof-dir rework. Fix at architecture level: one atomic checkpoint/resume path with a versioned schema. A lint cannot verify durable bytes; behavior tests do.

3. Silent stale resume: an old checkpoint resumes without a loud failure. Evidence: stale-mirror class where a @max mirror enforced the wrong row (tests/test_pstack_models.py stale fixtures). Fix at type plus behavior level: versioned CHECKPOINT_SCHEMA with a ValueError naming BudgetGuard.checkpoint, plus tests that fail on silent acceptance. Docs alone never fail, so they sit last.
