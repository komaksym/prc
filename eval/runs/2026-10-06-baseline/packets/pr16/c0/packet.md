# feat(sync): record actual LinkedIn activity

## Why

Connection-only sync misses pending manual invitations and verified directional DMs.

## What changed

- Stage complete invitation, connection, inbox and bounded changelog evidence before one duplicate-safe optional event batch.
- Retain explicit dry-run, replay and uncertain-write behavior.
- Restore the later PR14 pagination guard and prove refusal before a second request or database access.

## Scope

Observed actions only. Reports and drafts remain read-only. Invitation-history eligibility, live backfill and scheduling remain separate approval work under issue #6.

## Review order

Depends on [PR13](https://github.com/komaksym/linkedin-mdp/pull/13); its refreshed tip is included. invitation_sync.py is identical to PR7 and client.py is identical to PR14. Keep PR7 open for its invitation-specific workflow; integrate shared code once and preserve both scopes. Start at `src/linkedin_mdp_mcp/actual_action_sync.py`; review tests before generated evidence and visuals.

## Blast Radius

Only explicit --apply writes actual observations. Uncertain inbox evidence does not become verified DMs. No live apply or activation occurs in this run.

## Verification

- Local `python -m pytest -q` passed 35 tests at `df74ac3`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `tests/e2e_actual_action_sync.py` for 57 actual-action HTTP/event-store scenarios.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/df74ac34650a049fd1feb4a081adb3ace5f3e0cf/artifacts/actual-action-sync-e2e-evidence.json) records 57 actual-action HTTP/event-store scenarios.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37160967792) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Actual activity sync](https://raw.githubusercontent.com/komaksym/linkedin-mdp/e055396dfca4f2052a68803278155e264e58d4a9/infographic/actual-action-sync/infographic.png)

