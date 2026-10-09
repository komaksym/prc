# Final inspection model reviews

Summary. The five fixes passed independent red and green checks. Model review accepted four fixes and found further caption gaps.
Human acceptance remains pending. These reviews are model reviews.

## Immutable input

Descartes reviewed the saved source and test delta before the final caption work.
The retained file is `trust-inspection-d18-d22.delta.diff`.
Its SHA-256 is `c877f1976de170f296d99ea3b31af531fbe75ddab8c46546ace2982ac4d7eb8d`.

## Descartes, gpt-6.1-sol at high

The verdict was accept with fixes.
The reviewer found no new D18, D20, D21 or D22 issue.
The card title fallback still displayed raw paired backticks. This became D23.
Two public document tests had no backticks and retained the old prose oracle.
The parent added backticks to those fixtures and checked independent expected visible text.
The parent also reproduced dictionary headline text when a title used separate `show` and `speak` fields. This became D24.

## Mendel, inherited parent model

The no-comments review deleted one redundant formatter docstring. The parent accepted that deletion.
The reviewer flagged the duplicated Python and JavaScript caption rule without a parity test.
The new caption design owns the Python rule in core and tests browser parity through real rendered output.
No application-code edit from the comment review was accepted.

## Parent verification

Reverting the five source fixes produced eight predicted failures and one passing partial-coverage control.
Restoring them produced nine passes. The wrapped sign offset changed from 90 pixels to zero.
The complete suite then passed 808 tests in 297.50 seconds, before the further caption regressions.
Evidence is under `artifacts/trustworthiness/2026-10-09/regressions/inspection-d18-d22-*`.
Environment failures from sandboxed cache access and Chromium launch were excluded from product regression evidence.

## Remaining round

Fix D23 and D24. Review the resulting delta independently.
Run clean-cache verification and rebuild all acceptance outputs.
Inspect the cards, walkthroughs and settled video frames. Click all local review links.
