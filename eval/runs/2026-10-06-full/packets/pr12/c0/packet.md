# feat(report): show date added

## Why

Invitation candidates need their existing Supabase creation date displayed with source provenance.

## What changed

- Add date_added to private JSON and Markdown without changing ranking or eligibility.
- Keep missing, invalid, future or ambiguous creation dates explicitly unknown.

## Scope

Report metadata only. PR11 supplies the collector field; this PR adds no schema or database writes.

## Review order

Depends on [PR10](https://github.com/komaksym/linkedin-mdp/pull/10); its refreshed head is included. PR13 and PR17 now both include this current tip. The collector path through PR11 remains a separate landing prerequisite. Start at `src/linkedin_mdp_mcp/invitation_shortlist.py`; review tests before generated evidence and visuals.

## Blast Radius

Preserves the original timezone-aware timestamp. Unknown values do not acquire an invented date.

## Verification

- Local `python -m pytest -q` passed 33 tests at `0c54c1a`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `tests/e2e_invitation_shortlist.py` for 97 invitation/date scenarios.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/0c54c1ae2f0cc3d652e7a5a84fcefb625178fcb7/artifacts/invitation-shortlist-e2e-evidence.json) records 97 invitation/date scenarios.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37160968230) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Timestamp flow](https://raw.githubusercontent.com/komaksym/linkedin-mdp/feature/prospect-date-added/infographic/prospect-date-added/infographic.png)

