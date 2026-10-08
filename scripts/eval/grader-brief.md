# Free-text grader brief (EVAL part C)

Grade only the assigned free-text rows. Grade exactly the rows that grade_round.py marks NEEDS_HUMAN. The script owns answer-type selection.

Read the assigned answer files under `eval/runs/2026-10-08-release-check/answers/` and the frozen question files under `eval/questions/`. Keys and key facts are visible to graders. Never read other readers answers, other conditions packets, or product source.

Verdicts. `correct` when every key fact appears. `partial` when at least one key fact appears and none is contradicted. `wrong` when the answer contradicts a key fact or asserts a false claim. `cannot_tell` only when the answer itself abstains.

Write one file per assigned condition set as `eval/runs/2026-10-08-release-check/grades/free-<condition>.json`. Each file holds `grades` with one entry per free-text row: `pr`, `condition`, `question`, `verdict`, and `reason`. Record the assigned input hash. Deterministic grades cover the remaining rows. A merge step combines both sources after every row is graded.
