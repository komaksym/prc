# Scoreboard: 2026-10-08-release-check

gates passed: 96/96 across 12 PRs

## Per-PR receipts and video durations

| PR | receipts | video duration |
|----|---|---|
| pr10 | 41 | 60.8s |
| pr11 | 16 | 59.0s |
| pr12 | 30 | 65.4s |
| pr13 | 26 | 62.5s |
| pr14 | 20 | 65.0s |
| pr15 | 19 | 55.5s |
| pr16 | 19 | 51.7s |
| pr17 | 64 | 89.0s |
| pr19 | 35 | 49.5s |
| pr5 | 22 | 56.1s |
| pr7 | 22 | 56.0s |
| pr8 | 22 | 50.0s |

## Comprehension by condition

Final grades complete: 480/480 unique PR/condition/question entries. Sources: [grades/reviewer-c1.json](grades/reviewer-c1.json), [grades/reviewer-c2.json](grades/reviewer-c2.json), [grades/reviewer-c3.json](grades/reviewer-c3.json), [grades/reviewer-c4.json](grades/reviewer-c4.json), [grades/reviewer-c5.json](grades/reviewer-c5.json).

| condition | correct / partial / wrong / cannot-tell |
|---|---|
| C0 | not scored |
| C1 | correct 35.4% (34/96) / partial 18.8% (18/96) / wrong 2.1% (2/96) / cannot_tell 43.8% (42/96) |
| C2 | correct 35.4% (34/96) / partial 24.0% (23/96) / wrong 3.1% (3/96) / cannot_tell 37.5% (36/96) |
| C3 | correct 38.5% (37/96) / partial 18.8% (18/96) / wrong 19.8% (19/96) / cannot_tell 22.9% (22/96) |
| C4 | correct 46.9% (45/96) / partial 34.4% (33/96) / wrong 8.3% (8/96) / cannot_tell 10.4% (10/96) |
| C5 | correct 13.5% (13/96) / partial 15.6% (15/96) / wrong 3.1% (3/96) / cannot_tell 67.7% (65/96) |

misleading answers (wrong from C1-C5): 35

## C0 baseline beside it (2026-10-06-baseline)

C0 this run: not scored; frozen baseline C0 overall: 32.3% (31/96).

## Frozen targets

Targets remain frozen in the [baseline scoreboard](../2026-10-06-baseline/scoreboard.md).

| condition | absolute target | +30pt target | result |
|---|---|---|---|
| C1 | 35.0% | 62.3% | C1 absolute target passed; C1 +30pt target failed |
| C2 | 60.0% | 62.3% | C2 absolute target failed; C2 +30pt target failed |
| C3 | 70.0% | 62.3% | C3 absolute target failed; C3 +30pt target failed |
| C4 | 85.0% | 62.3% | C4 absolute target failed; C4 +30pt target failed |
| C5 | not specified | 62.3% | C5 +30pt target failed |

## Evidence status

Grounding audit files: 0. Recorded confirmed verdicts: 0. These files have no artifact hashes. Current-output validity is unverified.
missing grounding audit evidence.
missing judge evidence for this run. Target: at least 2 of 3 planted false statements detected.
OCR evidence recorded in [results.json](results.json): `{"hits": 25, "pass": false, "protocol": "Original fixed scene offsets, frames from actual MP4; exact OCR matches.", "source": "../../../artifacts/release/ocr-20261008/results.json", "total": 31, "width": 800}`. Validity is unverified.
arrow evidence recorded in [results.json](results.json): `{"coverage": "28/28", "pass": true, "rate": 0.9966101694915255, "scope": "28 captured public PR maps; see artifact hashes in arrows/results-20261008.json", "supported": 882, "total": 885}`. Validity is unverified.
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

- C1 +30pt target failed
- C2 absolute target failed
- C2 +30pt target failed
- C3 absolute target failed
- C3 +30pt target failed
- C4 absolute target failed
- C4 +30pt target failed
- C5 +30pt target failed
- misleading answers target failed: 35 wrong; target 0
- missing grounding audit evidence.
- missing judge evidence for this run. Target: at least 2 of 3 planted false statements detected.
- missing human evidence for this run. Target: adoption on at least 2 of 3 PRs and grader agreement at least 8/10.
- Grounding audit validity is unverified without current artifact binding and a valid judge check.
