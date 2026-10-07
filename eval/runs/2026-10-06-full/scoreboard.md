# Scoreboard: 2026-10-06-full

gates passed: 96/96 across 12 PRs

## Per-PR receipts and video durations

| PR | receipts | video duration |
|----|---|---|
| pr10 | 41 | 60.8s |
| pr11 | 16 | 59.1s |
| pr12 | 30 | 65.4s |
| pr13 | 26 | 62.5s |
| pr14 | 20 | 65.0s |
| pr15 | 19 | 55.5s |
| pr16 | 19 | 51.7s |
| pr17 | 64 | 89.7s |
| pr19 | 35 | 49.5s |
| pr5 | 22 | 56.1s |
| pr7 | 22 | 56.0s |
| pr8 | 22 | 50.0s |

## Comprehension by condition

Final grades complete: 480/480 unique PR/condition/question entries. Sources: [grades/reviewer-a.json](grades/reviewer-a.json), [grades/reviewer-b.json](grades/reviewer-b.json), [grades/reviewer-c.json](grades/reviewer-c.json).

| condition | correct / partial / wrong / cannot-tell |
|---|---|
| C0 | not scored |
| C1 | correct 20.8% (20/96) / partial 19.8% (19/96) / wrong 13.5% (13/96) / cannot_tell 45.8% (44/96) |
| C2 | correct 25.0% (24/96) / partial 24.0% (23/96) / wrong 9.4% (9/96) / cannot_tell 41.7% (40/96) |
| C3 | correct 46.9% (45/96) / partial 35.4% (34/96) / wrong 7.3% (7/96) / cannot_tell 10.4% (10/96) |
| C4 | correct 69.8% (67/96) / partial 22.9% (22/96) / wrong 4.2% (4/96) / cannot_tell 3.1% (3/96) |
| C5 | correct 17.7% (17/96) / partial 27.1% (26/96) / wrong 11.5% (11/96) / cannot_tell 43.8% (42/96) |

misleading answers (wrong from C1-C5): 44

## C0 baseline beside it (2026-10-06-baseline)

C0 this run: not scored; frozen baseline C0 overall: 32.3% (31/96).

## Frozen targets

Targets remain frozen in the [baseline scoreboard](../2026-10-06-baseline/scoreboard.md).

| condition | absolute target | +30pt target | result |
|---|---|---|---|
| C1 | 35.0% | 62.3% | C1 absolute target failed; C1 +30pt target failed |
| C2 | 60.0% | 62.3% | C2 absolute target failed; C2 +30pt target failed |
| C3 | 70.0% | 62.3% | C3 absolute target failed; C3 +30pt target failed |
| C4 | 85.0% | 62.3% | C4 absolute target failed; C4 +30pt target passed |
| C5 | not specified | 62.3% | C5 +30pt target failed |

## Evidence status

Grounding audit files: 12. Recorded confirmed verdicts: 6. These files have no artifact hashes. Current-output validity is unverified.
stale audit findings: [pr10](audit/pr10.json) (2 original statements absent from current board); [pr12](audit/pr12.json) (1 original statements absent from current board); [pr13](audit/pr13.json) (3 original statements absent from current board); [pr15](audit/pr15.json) (1 original statements absent from current board); [pr16](audit/pr16.json) (2 original statements absent from current board); [pr19](audit/pr19.json) (2 original statements absent from current board); [pr5](audit/pr5.json) (4 original statements absent from current board); [pr7](audit/pr7.json) (1 original statements absent from current board); [pr8](audit/pr8.json) (1 original statements absent from current board).
Recorded audit failures: 6 confirmed verdicts in [audit files](audit/). These are not a verified count for current outputs.
missing judge evidence for this run. Target: at least 2 of 3 planted false statements detected.
missing OCR evidence for this run. Target: 31/31 at 800 px.
missing arrow evidence for this run. Target: at least 99% on the 28 public PRs.
missing human evidence for this run. Target: adoption on at least 2 of 3 PRs and grader agreement at least 8/10.
Historical OCR 28/31 at 800 px and arrow precision 879/882 are not measurements of this run.
The [human session sheet](../../human/2026-10-07.md) is a template, not completed evidence.

## Previous run beside it (2026-10-06-baseline)

gates: not scored
missing final grades
- C0 prev: correct 32.3% (31/96) / partial 32.3% (31/96) / wrong 0.0% (0/96) / cannot_tell 35.4% (34/96)
- C1 prev: not scored
- C2 prev: not scored
- C3 prev: not scored
- C4 prev: not scored
- C5 prev: not scored

## Failures

- C1 absolute target failed
- C1 +30pt target failed
- C2 absolute target failed
- C2 +30pt target failed
- C3 absolute target failed
- C3 +30pt target failed
- C4 absolute target failed
- C5 +30pt target failed
- misleading answers target failed: 44 wrong; target 0
- stale audit findings: [pr10](audit/pr10.json) (2 original statements absent from current board); [pr12](audit/pr12.json) (1 original statements absent from current board); [pr13](audit/pr13.json) (3 original statements absent from current board); [pr15](audit/pr15.json) (1 original statements absent from current board); [pr16](audit/pr16.json) (2 original statements absent from current board); [pr19](audit/pr19.json) (2 original statements absent from current board); [pr5](audit/pr5.json) (4 original statements absent from current board); [pr7](audit/pr7.json) (1 original statements absent from current board); [pr8](audit/pr8.json) (1 original statements absent from current board).
- Recorded audit failures: 6 confirmed verdicts in [audit files](audit/). These are not a verified count for current outputs.
- missing judge evidence for this run. Target: at least 2 of 3 planted false statements detected.
- missing OCR evidence for this run. Target: 31/31 at 800 px.
- missing arrow evidence for this run. Target: at least 99% on the 28 public PRs.
- missing human evidence for this run. Target: adoption on at least 2 of 3 PRs and grader agreement at least 8/10.
- Grounding audit validity is unverified without current artifact binding and a valid judge check.
