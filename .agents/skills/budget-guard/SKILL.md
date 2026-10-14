---
name: budget-guard
description: "Redline sleep/wake guard for metered 5h runs. Use when starting metered work, when the meter reads 5 pct or less, or when resuming after a meter reset."
---

# Budget guard

Run metered 5h work through the redline loop so a run never burns to zero mid-flight.

Single source of truth: src/prc/budget_guard.py owns the 5 pct threshold, the checkpoint schema, and the one checkpoint/resume path. This doc never copies those values; it points at them.

## Loop

1. Check the meter through BudgetGuard.snapshot before every dispatch.
2. At or below the redline, checkpoint queued plus done with BudgetGuard.checkpoint, then sleep with no new dispatches.
3. After the meter recovers above the redline (is_reset), restore with BudgetGuard.resume and continue the queued units.

Done means every dispatched unit is accounted for (done, queued, or checkpointed), the checkpoint file validates, zero new dispatches happened after the redline, and the resume restored every queued unit.

## Reference

Redline is the binary meter state at or below 5 pct of the 5h budget left. Name it in prompts and code so the guard, the skill, and the run share one word.

Wire the meter provider once per run: pass a zero-argument reader returning a BudgetSnapshot into BudgetGuard with a checkpoint path under the run scratch dir. Keep ports, profile names, and session ids in env, out of the repo.

Gate every dispatch with BudgetGuard.gate; its error names BudgetGuard.checkpoint and BudgetGuard.resume. Treat a gate error as the next action, and a stale-schema error as a re-checkpoint, never as a silent resume.
