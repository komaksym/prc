# feat(invitations): reconcile outbound invitation history

## Why

Past outbound invitations need durable history evidence so the CRM can avoid recommending repeat invitations.

## What changed

- Add invitation-specific planning and duplicate-safe reconciliation for existing prospects.
- Keep the manual workflow disabled unless the main-branch opt-in gate is enabled.

## Scope

History ingestion only. Issue #6 remains incomplete because outreach_state() does not recognize invitation-history events. No migration or live backfill is included.

## Review order

Keep this independent PR open. [PR16](https://github.com/komaksym/linkedin-mdp/pull/16) reuses the identical invitation planner but adds broader activity sync. These are distinct scopes; coordinate their shared client before landing. Do not enable this workflow before the approved eligibility change and live replay proof. Start at `src/linkedin_mdp_mcp/invitation_sync.py`; review tests before generated evidence and visuals.

## Blast Radius

Applying ingestion alone does not correct invitation eligibility. The existing approval and workflow gates must remain in place.

## Verification

- Local `python -m pytest -q` passed 50 tests at `1f2f010`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `tests/test_invitation_sync_e2e.py` for 20 invitation HTTP-boundary cases.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/1f2f010c57e12cb3fa58f83fdcd5b46b37349cc4/artifacts/invitation_sync_verification.json) records 20 invitation HTTP-boundary cases.
- No new PR-triggered CI is claimed; collector/invitation checks were rerun locally. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Invitation history reconciliation](https://raw.githubusercontent.com/komaksym/linkedin-mdp/feature/invitations-reconciliation/infographic/invitation-history-reconciliation/infographic.png)

