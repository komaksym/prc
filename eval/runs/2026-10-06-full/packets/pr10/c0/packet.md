# feat(report): plan invitations from complete history

## Why

Invitation capacity must count all outgoing history, including people outside the CRM, before selecting up to 25 qualified prospects.

## What changed

- Count exact recipients against cited current employers and enforce a three-person lifetime company cap.
- Bind each required qualification citation to the same canonical profile; keep snapshot hashing ASCII-safe.
- Reconcile contaminated legacy CRM baseline invitation rows to canonical LinkedIn identities only when the normalized name is unique across full outgoing MDP history, the baseline event is unique, the provider URL is canonical, and the provider date is the baseline date or exactly one day earlier.
- Keep ambiguous names, profile collisions, malformed or conflicting dates, invalid URLs, unrelated event sources, and multiple baseline events unresolved.

## Scope

Private read-only invitation recommendations. Unknown identity or employer evidence withholds capacity claims. Date metadata is in PR12; concurrent employer sets are in PR17.

## Review order

Depends on [PR8](https://github.com/komaksym/linkedin-mdp/pull/8); its refreshed head is included. Review the planner and its E2E matrix first. PR12 adds date metadata above this slice. Start at `src/linkedin_mdp_mcp/invitation_shortlist.py`; review tests before generated evidence and visuals.

## Blast Radius

This changes recommendation eligibility. It produces no recommendation event plan, database writes or outreach sends.

## Verification

- `tests/e2e_invitation_shortlist.py`: 113 scenarios passed.
- Whole repository: 33 tests passed.
- Scoped Ruff passed for the changed planner and invitation tests.
- Mypy passed for `src/linkedin_mdp_mcp/invitation_shortlist.py`.
- Wheel and sdist build succeeded.
- `git diff --check` passed.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37187351199) passed.
- Full-source mypy still reports two inherited `prospect_report/engine.py` diagnostics outside this slice.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/5498b6c605ecd00941aa9dd34275c821f7c01876/artifacts/invitation-shortlist-e2e-evidence.json) records the 113 invitation scenarios.

![Invitation shortlist system](https://raw.githubusercontent.com/komaksym/linkedin-mdp/9862b07/infographic/invitation-shortlist/infographic.png)

