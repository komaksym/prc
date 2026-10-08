# Reader answer formats and grading rules disagree

Type: task
Status: resolved

`artifacts/release/grade-audit.json` records 275 disagreements across 410 mechanically graded answers. Many prose answers do not meet the deterministic input format. Two location grades contradict the substring rule directly. Neither mechanical replay nor these records prove semantic correctness.

Use canonical answer shapes in new packets. Apply deterministic grading to its supported types. Independent graders own free text. Preserve frozen answers and verdicts. A new run must establish trustworthy acceptance evidence.

## Answer

The round grader selects frozen v1 keys, records their hashes, rejects incomplete or duplicate coverage, and preserves independent free-text ownership. The complete historical release-check has 480 final grades, including 410 deterministic grades and 70 independently graded free-text answers. Read-only replay matches the saved deterministic verdicts. Historical rule disagreements remain archived. See `docs/mvp/STATUS.md` and the grading regressions. This does not resolve disputed semantic keys or certify the current product.
