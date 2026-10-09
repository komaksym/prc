# Delta review synthesis

Summary. Five concrete defect areas need correction after the review of 6dbb336..334e1f8.

## Intent

Keep facts truthful, changed-line coverage literal, rendering reliable and installation repeatable.
The user is the only human reviewer. Model reviews are supplemental.

## Reviewers

- A. Lorentz, gpt-6.1-sol at max, reported two reproduced blockers.
- B. Russell, muse-spark-1.3-contributor at xhigh, reported a parser crash and a label defect.
- C. Pasteur, glm-5.3-flash at max, reported one actionable shape gap and a geometry concern.
  Its other claims lacked a distinct reproduction or referred to code that does not exist.

## Act on

- A1. Keep decoded literal backslashes in bracket property identities. Preserve genuine escaped identifier behavior.
- A2. Make wrapping depend on text and columns. Preserve syntax classes and change markers when mapping line breaks back to tokens.
- B1. Preserve malformed escape matches when the regex supplies no hexadecimal digits. Do not crash indexing.
- B2. Keep terminal bracket property names intact in rendered Mermaid labels.
- C1. Require receipt rows and object entries in the scene collections that use objects.
  Graph nodes and diff line references retain their existing string forms.

## Consider

C2 repeats the earlier milestone C4 concern about conservative note geometry.
It does not establish a new rendering defect. Keep this limit explicit and run the real note-placement browser checks.

## Noted

C's browser runs were unavailable. Its stated test counts do not replace parent artifacts.
No matching cleanup file exists in the worktree.

## Dismissed

C3 refers to nonexistent code and supplies no independent root beyond A2.
C4 reports no discrepancy.

## Agreement map

A and B found four distinct defects. The parent reproduced each before fixing it.
C1 exposed the same general board-shape weakness as the first milestone B3, with new reachable inputs.
The parent reproduced seven additional malformed-collection CLI failures.

## Resolution

All Act on findings have passing focused regressions at b880513.
Mill found a follow-up label-shortening regression, which the parent corrected test-first.
Halley and Heisenberg independently rechecked the final label corrections and reported no new regressions.
The final clean-cache build passed 802 tests with no failures, errors or skips.
The three PR outputs use that installed wheel, with exact revision and wheel hashes. Their rebuild and browser checks passed.
Each original diff matches its pinned base and head. Human acceptance remains pending.
