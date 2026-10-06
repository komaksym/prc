# feat(inbox): record private LinkedIn inbox evidence

## Why

Person-level action planning needs private inbox evidence with reliable account identity and message direction.

## What changed

- Validate complete snapshots and exact Unicode profile identities before optional duplicate-safe persistence.
- Preserve attachments, subject, timestamp uncertainty and unknown message/read status; withhold ambiguous threads.

## Scope

Inbox observations only. Action planning is in PR13, and publication is in PR15. Dry-run remains the default; this run performs no live persistence.

## Review order

Depends on [PR5](https://github.com/komaksym/linkedin-mdp/pull/5); its refreshed head is included. Review the client and inbox planner before the synthetic artifacts and visuals. PR10 follows this slice. Start at `src/linkedin_mdp_mcp/inbox_sync.py`; review tests before generated evidence and visuals.

## Blast Radius

Private message evidence may be stored only through explicit apply. Invitation notes cannot silently become verified DMs.

## Verification

- Local `python -m pytest -q` passed 32 tests at `dc3f451`. Scoped Ruff, package-module mypy and source/wheel builds passed.
- [Inbox artifact](https://github.com/komaksym/linkedin-mdp/blob/dc3f451dd61aa01394d5f5f121c9fa2affeb0299/artifacts/inbox-e2e-evidence.json) records 54 cases; [review artifact](https://github.com/komaksym/linkedin-mdp/blob/dc3f451dd61aa01394d5f5f121c9fa2affeb0299/artifacts/inbox-review-e2e-evidence.json) records 15 regressions. Committed inbox provenance is historical; fresh execution is confirmed by current-head CI.
- Run `python -m pytest -q` for both matrices; `tests/e2e_inbox_sync.py` alone runs the 54 inbox cases.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37160967876) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Unicode profile identity](https://raw.githubusercontent.com/komaksym/linkedin-mdp/513138369467fe5f106a1c18cc8c70aceb4bf08c/infographic/unicode-profile-identity/infographic.png)

