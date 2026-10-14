# v3 question fix round: second read of the changed questions

Date: 2026-10-14. Scope: the 20 questions that differ from 18421af. The 4 unchanged ones (p2a-q2, p3a-q2, p4a-q2, p4b-q2) were PASS in the independent review and are not re-read here.
Method: each key, option, element and grader note was read against the pinned diffs in /tmp/v3-diffs (every changed file, workflows included), plus the p3b head file for the code the compare hunks cut off. The read also checked whether Q1 options can be told apart from the title alone. No subagent was available (the delegate brief forbids spawning), so this is a separate pass by the fixing agent, not an independent reviewer.

## First pass

| qid | verdict | note |
| --- | --- | --- |
| v3-p1a-q1 | PASS | All options keep more rows. The key holds against the diff: role keys use the same case-folded lookup, and an http address is neither https nor a bare host. |
| v3-p1a-q2 | PASS | Exact-key precedence and first-seen fallback match the setdefault map. All three named shapes return empty at head. |
| v3-p1a-q3 | FIX | The prompt asks for verdict and probe only, but the rubric pays for a named risk. |
| v3-p1b-q1 | PASS | The key covers the pinned companion checkout, the suite steps that run before the record step, and the constant statuses. The old key is now distractor C and is false. |
| v3-p1b-q2 | PASS | The constant statuses and the default revision are separate from the checkout ref. The grader note handles the false "PASS after failing suite" claim. |
| v3-p1b-q3 | FIX | Same prompt gap as p1a-q3. |
| v3-p2a-q1 | PASS | The snapshot is git-ignored and no step creates it, so a scheduled run renders nothing and commits nothing. The title points away from the key. |
| v3-p2a-q3 | FIX | Same prompt gap. |
| v3-p2b-q1 | PASS | The printed table has labels, match counts, gates and dates, with no names or addresses. Repository access is read-only and there is no send path. |
| v3-p2b-q2 | PASS | Containment matching; attributes come from rows[0] and events are pooled across matches. Either half counts. |
| v3-p2b-q3 | FIX | Same prompt gap. |
| v3-p3a-q1 | PASS | A failed fetch exits 1, and missing credentials exit 2, before the render step. There is no retry, and the snapshot is never kept between runs. |
| v3-p3a-q3 | FIX | Same prompt gap. |
| v3-p3b-q1 | FIX | Facts are correct (the script warns, then the run's check exits 1 before render), but the key ends in an unclear phrase. |
| v3-p3b-q2 | PASS | The hard block and the duplicated, uncalibrated limits are both in the diff. The false "still publishes" claim is now handled in the anchor and the grader note. |
| v3-p3b-q3 | FIX | Same prompt gap. |
| v3-p4a-q1 | PASS | On 404 the reference returns early with the flag, the comparison and the legacy check are skipped, and the run exits normally. All options mention the flag. |
| v3-p4a-q3 | FIX | Same prompt gap. The risk text also said one flag is the only trace, but the summary's zero reference counts show it too. |
| v3-p4b-q1 | PASS | One check at the shared no-next-link return covers lenient and strict snapshot reads and changelog reads (three tests), and missing counts still return. |
| v3-p4b-q3 | FIX | Same prompt gap. |

## Fixes applied, then re-read

- All eight Q3 prompts now ask for the verdict, the main risk behind it, and one concrete probe. This matches the decision anchors. PASS on re-read.
- p3b-q1 key now ends "a later check then blocks that day's page". PASS on re-read; options are 129/132/129/132 characters.
- p4a-q3 key and element 1 now name the summary fields (not-found flag, zero reference counts) as the only trace. PASS on re-read.

Final: 20 of 20 PASS. Lint, kit and cite pass after the last edit (see check-run.txt).

