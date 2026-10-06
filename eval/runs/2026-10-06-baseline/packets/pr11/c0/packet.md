# fix(collector): fetch prospect timestamps

## Why

The private collector omitted prospects.created_at, so exported rows lost their existing creation timestamp.

## What changed

- Select and preserve the existing timestamp through pagination and CMS encryption.
- Require exact negative failure evidence and invalidate stale success artifacts before a new run.

## Scope

Collector correction only. No database column, workflow activation, schedule or live collection is added by this PR.

## Review order

Depends on validation/private-action-source-20261002, whose collector and credentialed workflow are absent from main. Do not retarget this PR alone to main. Review that base as a separate prerequisite or extract a clean collector root before landing. [PR14](https://github.com/komaksym/linkedin-mdp/pull/14) follows this fix; PR12 consumes its exported field. Start at `diagnostics/action-report-private-source-20261002/collect_private_source.py`; review tests before generated evidence and visuals.

## Blast Radius

Retargeting alone would include inherited report and workflow history. Live database timestamp values remain unverified in this run.

## Verification

- Local `python -m pytest -q` passed 21 tests at `306ff5a`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `diagnostics/action-report-private-source-20261002/e2e_private_source.py` for 22 synthetic HTTP/CMS verdicts.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/306ff5a26ca6502173b40eeb723826e9e3eca6cd/diagnostics/action-report-private-source-20261002/e2e-evidence.json) records 22 synthetic HTTP/CMS verdicts.
- No new PR-triggered CI is claimed; collector/invitation checks were rerun locally. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Prospect timestamp collection](https://raw.githubusercontent.com/komaksym/linkedin-mdp/fix/prospect-created-at/infographic/prospect-created-at/infographic.png)

