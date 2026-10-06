# Scoreboard: 2026-10-06-baseline (C0 only)

First scored run. No product outputs exist yet, so only the C0 baseline
(title + description) is measured. Reader: single agent answering strictly
from the packet, `CANNOT TELL` when absent. Exact types graded by
`scripts/eval/grade.py`; free text graded by hand against key facts.

## C0 baseline (all 12 PRs, 8 questions each)

| PR | correct | partial | wrong | cannot-tell |
|----|---|---|---|---|
| 19 | 25.0% (2) | 37.5% (3) | 0 | 37.5% (3) |
| 17 | 37.5% (3) | 25.0% (2) | 0 | 37.5% (3) |
| 16 | 37.5% (3) | 25.0% (2) | 0 | 37.5% (3) |
| 15 | 37.5% (3) | 37.5% (3) | 0 | 25.0% (2) |
| 14 | 37.5% (3) | 25.0% (2) | 0 | 37.5% (3) |
| 13 | 37.5% (3) | 25.0% (2) | 0 | 37.5% (3) |
| 12 | 25.0% (2) | 37.5% (3) | 0 | 37.5% (3) |
| 11 | 12.5% (1) | 37.5% (3) | 0 | 50.0% (4) |
| 10 | 37.5% (3) | 37.5% (3) | 0 | 25.0% (2) |
| 8 | 37.5% (3) | 25.0% (2) | 0 | 37.5% (3) |
| 7 | 37.5% (3) | 25.0% (2) | 0 | 37.5% (3) |
| 5 | 25.0% (2) | 50.0% (4) | 0 | 25.0% (2) |
| **overall** | **32.3% (31/96)** | **32.3% (31/96)** | **0** | **35.4% (34/96)** |

C0 pattern: q1/q5/q8 are answerable from the PR text (behaviour, scope,
blast radius). q2/q3/q6-names are never in the description (all
`cannot_tell`). q4/q7 give partial credit (packets name test files and the
start-at path, never the full set or the function).

Check 5 (EVAL.md): no PR above 60% C0 (max 37.5%). The questions are not
too easy. Frozen as `test(eval): freeze comprehension questions v1`.

## Targets (EVAL.md part C, committed before any product condition is scored)

| Condition | Target correct | Must beat C0 by |
|---|---|---|
| C4 doc | >= 85% | +30 pts (C0 32.3%) |
| C3 video | >= 70% | +30 pts |
| C2 comment | >= 60% | +30 pts |
| C1 card | >= 35% | +30 pts |
| misleading answers (wrong from C1-C5) | 0 | — |

## Failures

None in C0 (baseline only; wrong = 0 everywhere by construction of honest
`CANNOT TELL` answering).
