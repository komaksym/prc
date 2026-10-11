# Paired evaluation failure cases

Tests precede implementation. Each test exercises the CLI or HTTP boundary and saved records.

1. One PR appears twice, including different commits of one PR. Preparation must fail without output.
2. Any acceptance packet or declared familiar PR enters the roster. Preparation must fail.
3. One pair has different question kinds or missing matching rationale. Preparation must fail.
4. Lens CI output is missing, forged as a PRC renderer, or uses a different head. Preparation must fail.
5. PRC output provenance has a different base or head. Preparation must fail.
6. A question, key, tool artifact, source diff or assignment changes after sealing. Session must refuse it.
7. The browser receives a future PR or answer key. Public state and arbitrary paths must not reveal it.
8. Refresh or process restart resets the clock or drops saved answers. Active reading must resume.
9. A second start, replayed submission or duplicate tab advances more than once. State must stay consistent.
10. Deadline passes. Preserve answers, mark timeout, and refuse further edits.
11. Abort discards saved answers or an unstarted trial disappears. Both stay in analysis with their proper states.
12. Score import accepts wrong IDs, invalid anchors, conditions or omitted pairs. Reject the grading document.
13. A local tool artifact path escapes its tree. Refuse traversal and avoid arbitrary file access.
14. Baseline is silently substituted with GitHub alone. A Lens delivery problem must be visible and retained.
15. Analysis assumes 12 pairs or quietly drops unknown outcomes. Explicit sealed protocol covers all pairs.
16. Browser GUI is broken despite passing unit tests. Drive start, answer, reload, submit, abort, closure and export; save screenshots.
