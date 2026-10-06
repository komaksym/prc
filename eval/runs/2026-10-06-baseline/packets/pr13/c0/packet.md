# feat(report): plan DM actions

## Why

The owner needs researched first-DM drafts and manual reply or follow-up reminders based on verified message evidence.

## What changed

- Add offline DM planning with exact identity, directional source evidence and conservative uncertainty handling.
- Apply connection freshness only to first-DM eligibility; preserve provider calendar-day precision.
- Integrate current PR12 qualification and hashing fixes that the prior branch omitted.

## Scope

Private report planning only. The owner writes replies and follow-ups and sends every message manually. No provider requests or database writes occur during report generation.

## Review order

Depends on [PR12](https://github.com/komaksym/linkedin-mdp/pull/12); its exact refreshed tip is now included. PR15 composes reports and PR16 persists actual observed actions above this slice. PR17 is independent employer accounting. Start at `src/linkedin_mdp_mcp/dm_actions.py`; review tests before generated evidence and visuals.

## Blast Radius

Anonymous or ambiguous evidence can withhold actions. Unknown read status stays unknown.

## Verification

- Local `python -m pytest -q` passed 34 tests at `f59b09a`. Scoped Ruff, package-module mypy and source/wheel builds passed.
- [DM artifact](https://github.com/komaksym/linkedin-mdp/blob/f59b09a1eb2e7d91a3abb0c0eaf72ca2bd016439/artifacts/private-dm-actions-e2e-evidence.json) records 88 DM cases; [uncertainty artifact](https://github.com/komaksym/linkedin-mdp/blob/f59b09a1eb2e7d91a3abb0c0eaf72ca2bd016439/artifacts/dm-uncertainty-scope-e2e-evidence.json) records six; [invitation artifact](https://github.com/komaksym/linkedin-mdp/blob/f59b09a1eb2e7d91a3abb0c0eaf72ca2bd016439/artifacts/invitation-shortlist-e2e-evidence.json) records 97.
- Run `python -m pytest -q` for all three matrices; `tests/e2e_private_dm_actions.py` alone runs the 88 DM cases.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37160967578) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Private DM action flow](https://raw.githubusercontent.com/komaksym/linkedin-mdp/9bdd8bac04b130929ab5fd233e97009831fb94c3/infographic/private-dm-actions/infographic.png)

