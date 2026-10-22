<!-- Replace every TODO with evidence from the final diff. Use one validation status. -->

## Summary
- What changed:
- Why it changed:
- Actual diff:
- Reviewer focus:

## Validation
- Overall status: TODO (replace with PASS, FAIL, or NOT RUN)
- Command:
- Result:
- Evidence:
- Limitations:

Finish the intended commit before the final check. Then run the repository gate:

```sh
bash scripts/verify-release.sh
```

The script runs the hygiene guard, lint, format, strict type checks, tests, build, clean-wheel installation, browser checks, and output checks. On exit 0, record the proof path from `artifacts/release/verify/latest-success.txt`. On a nonzero exit, record the failure and exit status. If this invocation wrote `latest-attempt.txt`, include its result and logs. If the gate failed before writing that pointer, cite the captured failure output and exit status. Do not cite an older attempt pointer or `latest-success.txt` as proof for the current commit. For a narrower check, name the exact command and its observed result. State any part of the change that the check does not exercise.

## Risks / Notes
- Migrations, configuration changes, rollout concerns, follow-up work, or limitations:

## Breaking changes
- None, or describe the break and its migration path:

## Visual summary
- Add a visual only when it helps a reviewer understand the problem, change, or effect.
- Prefer Mermaid for a small change.
- For a generated raster image, run `uv run prc explain --source <PR URL> --board <board.json> --voice none --out "$PWD/artifacts/pr-visual"` and attach its `card.png` to this PR. Use the hosted URL that GitHub returns, and name the board or provenance path.
- Do not put a local filesystem path in place of a hosted image URL.
