# prc agent routing

Before spawning a pstack subagent, read the model rows below. Authority lives in
the live override sheet at `/Users/koval/.codex/pstack-models.md`. The rows below
mirror only the sheet rows this repo depends on. Keep every row identical to the
sheet. `check_repo` fails when the mirror drifts. Never substitute the workhorse
model into an investigator role.

<!-- pstack-models:start -->

## pstack model configuration (rows this repo depends on)

why investigators: opencode-go/deepseek-v4.1-flash @max
why synthesizer: opencode-go/muse-spark-1.3-contributor @xhigh

<!-- pstack-models:end -->

## Rule table

| Rule | Enforcement | Limit |
| --- | --- | --- |
| Close every dispatch: call `wait_agent` on a long timeout and integrate each result before ending the turn | `tests/test_dispatch_collection.py` fails when this row is absent | No repo check observes turn-end behavior; the test guards the rule's presence, not compliance |
| why investigators run on the configured flash investigator, never the workhorse model | `check_dispatch` in `src/prc/pstack_models.py` checks dispatches against the live sheet, and `check_repo` fails when the mirror drifts from the sheet naming both files; `tests/test_pstack_models.py` replays the 2026-10-11 omitted-model dispatch, the `gpt-6.1-sol` dispatch, and the stale `@max` mirror against the `@xhigh` sheet as failing fixtures | The guard reads policy text; it cannot intercept a direct host tool call, so call `check_dispatch` with the request before every dispatch. `muse-spark` on this runtime supports low, medium, high, xhigh only; the sheet pins `why synthesizer @xhigh`, so `@xhigh` passes and a stale `@max` mirror fails loudly naming both files instead of enforcing the wrong row. |
| Before any handoff of the paired session hub to the operator, run the button-level end-to-end pass and cite its checks.json and screenshots | `tests/test_verify_paired_hub.py` fails when `.agents/skills/verify/features/paired.md` does not require `scripts/verify_paired_hub.py`; `tests/test_dispatch_collection.py` fails when this row is absent | Fixture API checks alone do not prove the hub buttons work; covers the paired session hub first |
| Before any operator-facing handoff of the hub URL, run the supervised handoff script against the exact handed-off server and cite its artifacts/handoff record (scripts/handoff_study_hub.py, pidfile, screenshot) | `tests/test_verify_paired_hub.py` fails when the recipe or drive section does not require `scripts/handoff_study_hub.py`; `tests/test_dispatch_collection.py` fails when this row is absent | Fixture link pass alone does not prove the handed-off server is live; covers the supervised handoff first |
