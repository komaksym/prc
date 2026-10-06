# fix(collector): collect changelog

## Why

The encrypted private source bundle needs complete CHANGELOG evidence and acquisition timestamps for DM planning.

## What changed

- Collect bounded changelog events and validate member identity before encryption.
- Reject pagination endpoint/query drift, including a startTime introduced by a next link when the original request omitted it.

## Scope

Collector and source validation only. The refresh proposal is outside .github/workflows and still requires a reviewed immutable pin and separate activation approval.

## Review order

Depends on [PR11](https://github.com/komaksym/linkedin-mdp/pull/11). Its validation-base landing gate also applies here. PR16 now copies this exact client blob, including the later pagination repair; collector changes remain a separate slice. Start at `diagnostics/action-report-private-source-20261002/collect_private_source.py`; review tests before generated evidence and visuals.

## Blast Radius

Malformed or incomplete evidence produces no ciphertext. No live source acquisition, migration or workflow activation occurs in this run.

## Verification

- Local `python -m pytest -q` passed 21 tests at `66e8fe4`. Scoped Ruff, package-module mypy and source/wheel builds passed. Run `diagnostics/action-report-private-source-20261002/e2e_private_source.py` for 45 synthetic HTTP/CMS verdicts.
- [Repeatable synthetic artifact](https://github.com/komaksym/linkedin-mdp/blob/66e8fe47d8cf70fcde7f87ebd3b43c1ccf22eaf7/diagnostics/action-report-private-source-20261002/e2e-evidence.json) records 45 synthetic HTTP/CMS verdicts.
- [Current-head Report Boundary E2E](https://github.com/komaksym/linkedin-mdp/actions/runs/37114272125) passed. Whole-repository lint and two inherited prospect_report type diagnostics remain outside this slice.

![Private source acquisition](https://raw.githubusercontent.com/komaksym/linkedin-mdp/9218891/infographic/source-changelog/infographic.png)

