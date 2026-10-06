# feat(report): publish private morning reports to Google Docs

## Why

Connection reconciliation needs a private, repeatable morning report that preserves operator notes.

## What changed

- Publish one revision-guarded, marker-owned Google Docs section after owner-only permission checks.
- Retain fetched snapshot rows when LinkedIn returns its exact known terminal no-data response; preserve genuine failures.

## Scope

Opt-in connection reporting only. Person-level action composition is in PR15. This run does not activate reporting, collect live data, or change schema.

## Review order

Start the report chain here, then review [PR8](https://github.com/komaksym/linkedin-mdp/pull/8), PR10 and PR12. PR13 leads to PR15 and PR16; PR17 is a separate child of PR12. Current main is included. Start at `src/linkedin_mdp_mcp/google_doc_report.py`; review tests before generated evidence and visuals.

## Blast Radius

Changes report publication and snapshot completion. Permission checks, marker bounds and revision preconditions remain enforced.

## Verification

- Local `python -m pytest -q` passed 30 tests at `5f4440d`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `tests/e2e_doc_report.py` for 32 report HTTP-boundary scenarios.
- The report E2E passed all 32 synthetic cases; prior credentialed proof remains pinned to [its original live run](https://github.com/komaksym/linkedin-mdp/actions/runs/36927715805).
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37160967893) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Snapshot exhaustion handling fixed](https://raw.githubusercontent.com/komaksym/linkedin-mdp/529add5ae188cda2fa13b40253d51796acf7b33f/docs/images/pr5-snapshot-exhaustion-fixed.png)

