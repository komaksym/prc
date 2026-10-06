# feat(report): count every present employer

## Why

A recipient with multiple explicitly present jobs must consume invitation capacity at every current employer.

## What changed

- Count each profile once per employer and require capacity at every employer before selecting the person once.
- Withhold capacity claims for incomplete, contradictory or unregistered employer sets.

## Scope

Read-only employer accounting. Flat audit fields remain compatible; actual universal employer coverage is still incomplete.

## Review order

Depends on [PR12](https://github.com/komaksym/linkedin-mdp/pull/12); its refreshed tip is included. This is a sibling of PR13, not a prerequisite for PR15. Preserve sibling PLANS.md additions at integration and rerun combined rendering. Start at `src/linkedin_mdp_mcp/invitation_shortlist.py`; review tests before generated evidence and visuals.

## Blast Radius

Changes shortlist capacity accounting while preserving exact identities, exclusions, ranking and date_added. No database writes or invitations are sent.

## Verification

- Local `python -m pytest -q` passed 33 tests at `537a16d`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `tests/e2e_invitation_shortlist.py` for 107 invitation/employer scenarios.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/537a16de03f9fad8ffe0def188494037991b275a/artifacts/invitation-shortlist-e2e-evidence.json) records 107 invitation/employer scenarios.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37160966926) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Present employer accounting](https://raw.githubusercontent.com/komaksym/linkedin-mdp/7ab28a21a8495f6e6d00444747ceecc5726f7b90/infographic/present-employer-sets/infographic.png)

