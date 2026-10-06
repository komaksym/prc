# feat(report): combine actions

## Why

The private report needs invitation recommendations, researched first-DM drafts and manual reminders in one document.

## What changed

- Compose real upstream planner outputs while preserving evidence, uncertainty and withheld states.
- Publish prepared text through a Google-only command with marker, control-character, UTF-16 and revision safeguards.

## Scope

Offline composition and optional publication only. It does not request LinkedIn data, write Supabase or send outreach. Fresh live coverage and publication are outside this reconciliation run.

## Review order

Depends on [PR13](https://github.com/komaksym/linkedin-mdp/pull/13); its refreshed tip is included. PR17 can land independently after PR12. When combining sibling PR15, PR16 and PR17, preserve each PLANS.md addition and rerun the combined checks. Start at `src/linkedin_mdp_mcp/combined_action_report.py`; review tests before generated evidence and visuals.

## Blast Radius

Invalid or blank text fails before OAuth. Private-write cleanup preserves foreign output files.

## Verification

- Local `python -m pytest -q` passed 35 tests at `1b18345`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `tests/e2e_combined_action_report.py` for 48 combined CLI/Google HTTP scenarios.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/1b183458ae48f7a575ae92d8f310009671767553/artifacts/combined-action-report-e2e-evidence.json) records 48 combined CLI/Google HTTP scenarios.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37160969379) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Combined private report](https://raw.githubusercontent.com/komaksym/linkedin-mdp/9995fbd/infographic/combined-action-report/infographic.png)

