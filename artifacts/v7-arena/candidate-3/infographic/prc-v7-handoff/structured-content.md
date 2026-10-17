Title: PRC v7 - Arena candidate 3: two design directions, one handoff

Objectives:
1. Show what the page/clip pair delivers: the three moments of PR 5.
2. Show each direction's fixed colour + type system.
3. Show the clip contract and the verification state.

Sections:
1. Subject. Key concept: one merged PR rendered as two looks. Auditors
   compare the page against the GitHub PR page.
2. Moment 1 - the Doc report. The run and the document agree: Status
   REAL_STATUS with six counts; the doc keeps the outside notes, removes
   "old", writes the report; verified at e2e_doc_report.py:247 and :237.
3. Moment 2 - order of work. Google checks run first; lines 36, 42, 43, 44,
   50, 51, 66 with folds 5/5/14; 44 gives BLOCKED; 51 gives FAILED, or
   BLOCKED if the client never started.
4. Splits, contract, verification. Two directions share the bones; the clip
   contract is fixed; screenshots are the parent's pass.

Exact data points:
- Counts: Fetched rows 4, Matched rows 3, Unique matched connections 2,
  Unmatched rows 1, Newly inserted events 1, Already-present events 1.
- Code lines: 36, 42, 43, 44, 50, 51, 66; folds 5/5/14.
- Doc links: e2e_doc_report.py:247, :237; publish in google_doc_report.py:139.
- Wondering tokens: #FFFCF0, #261312, #7ACEFF, #5BBEA5, #E3B33C, #FF7361.
- Review sheet tokens: #FAFAF8, #17181C, #2E5CE6, #146C43, #8A5300, #B3261E.
- Contract: 1280x720; one moment at a time; one build-up per moment;
  __ready on fonts; __marks after each moment; __clipDone at end; about 13 s.
