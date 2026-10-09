# Milestone review synthesis

Summary. The review of 24e5300...6dbb336 requires correctness fixes before acceptance.

## Intent

Make PR facts consistent, coverage literal, rendering reliable and clean-cache verification repeatable.
The user is the sole human reviewer. Publication is outside this milestone.

## Reviewers

- A. Harvey, gpt-6.1-sol, reported three reproduced findings. Bohr failed with HTTP 429 and supplied no verdict.
- B. Gibbs, muse-spark-1.3-contributor at xhigh, reported three warnings.
- C. Socrates, glm-5.3-flash at max, reported five warnings and four nits.

## Act on

- A1. Quoted property segments collide with nested paths. Separate identities and prohibit false exact test evidence.
- A2 and A3. Coverage and required outro cues omit effective visibility. Reject overflowing code and reveals that cannot finish.
- B1. A failed card leaves an image reference in the comment. Omit references to the missing image.
- B2 and C5. Deleted-only changes use unclear wording beside the changed-symbol count. Name the deletion and retain the count.
- B3. Malformed board structure raises raw exceptions. Validate authored data at the board boundary.
- C3 and C8. The verifier comment and package test docstring describe outdated inputs. Describe the current working-file contract precisely.

## Consider

- C4. Note geometry duplicates renderer calculations. The A2 fix will share diff geometry where needed. Note placement still has a conservative estimate and a real browser check.

## Noted

- C6. Diagnostic coverage fields lack product readers. They remain useful to callers and the acceptance verifier.
- C7. Re-exports preserve existing imports. Consolidating them is optional. Avoid unrelated cleanup.
- C9. CI can run twice for a PR. The empty cache is deliberate for D16. CI cost changes stay outside this milestone.

## Dismissed

- C1. latest-success.txt intentionally names the last successful run. latest-attempt.txt names the current attempt.
  Keeping a previous success after a failure preserves evidence. This milestone checks an explicit run directory and exit status.
- C2. tree_delta receives file entries from Git's recursive diff. It cannot produce a trailing-slash directory entry.
  A synthetic invalid TreeChange does not justify a fallback that could hide count failures.

## Agreement map

B and C both flagged deleted-only wording. A reproduced two distinct visibility defects and a new object identity collision.
B identified the missing-card path and malformed authored boards. No other model independently disproved A's inputs.
The parent will reproduce and test the Act on items before fixing them.

## Resolution

All Act on findings have passing regressions at b880513.
Delta reviews and test-first corrections are recorded in trust-delta-review-synthesis.md and the final recheck reports.
The final clean-cache verifier passed 802 tests with no failures, errors or skips.
The installed-wheel acceptance rebuild and browser checks passed for all three original PRs.
The parent inspected the final screenshots and all settled video scenes. Human acceptance remains pending.
