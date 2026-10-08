TL;DR: No revision, diff-hash, map-hash, or per-file line-count mismatch was found in the three retained cases. Their core behavior claims match the fixed source revisions, and the Go board states its parsing limits. Two provenance gaps remain in the verifier and displayed merge labels. Human acceptance is pending.

## Fixed revisions and counts

Inputs are under `artifacts/trustworthiness/2026-10-09/acceptance/` in the readiness worktree.
Counts include every changed file, including opaque documentation and lockfiles.

| Case | Base SHA | Head SHA | Files | Added / removed | Test files |
|---|---|---|---:|---:|---:|
| librarysync-98 | e3742c159512078753c40da9226cb5fd72de5444 | d24bcde9cfb3b1bb93dc77147d0d31f7598a264c | 2 | 72 / 7 | 1 |
| em-5756 | 9e2db120d3ea98e1e37fe939972ef364ab4508a9 | 3755cd396c0075e29d3ea6638e0fd2e572f3ed3b | 7 | 109 / 3 | 1 |
| swarm-116 | 3dafc39698bafd42172a7a19230153d4127dc8e1 | 2f7696dda0342ae9d5b2bfdf76bc57d64dc890a5 | 7 | 313 / 16 | 2 |

I regenerated each binary diff and numstat from its recorded local Git objects. Both matched the retained bytes exactly.
Each map matched its recorded SHA-256, provenance revisions, provider head, and fixed comparison base.
Every map file's additions/deletions matched numstat. All 800 mapped base/head line checks matched the corresponding Git blobs.
The retained CI check subjects also matched their case heads.

## Story and Go evidence

`verify_board` passed all three boards, with 50, 43, and 20 receipts respectively.
This verifies receipts and preflight rules; it does not establish runtime test coverage.

LibrarySync's helper now skips episodes through the last watched season/episode position in an ordered list.
The bulk lookup calls that helper. Added tests contain the s2e2-to-s2e3 example and the final-episode gap case.
Dashboard and history callers exist at the recorded head. The outro discloses the omitted no-watched fallback.

Em adds the touch-only Note completion callback, keyboard dismissal, `avoidKeyboard={isOpen}`, and copied patch styles.
At the fixed head, `commands.ts:605` invokes completion after cursor restoration.
`toggleDropdown.ts` clears multicursors when closing the Command Center.
The three added Puppeteer cases assert the narrated outcomes. The board correctly describes the keyboard-padding proxy limitation.
The opaque documentation and lockfile retain +5/-1 and +2/-2 respectively.

Swarm's diff separates read, YAML parse, and decode/link validation errors and preserves underlying causes.
Its board explicitly says Go symbol/call analysis is unsupported in the title and outro.
All seven map files have null language and zero parsed symbols. Recomputed facts identify seven unsupported paths and two test files.
These values describe parsing limits, not absence of changes or tests.

## Verified findings

1. **The final verifier does not bind all reviewed content.** [verify-trustworthy-acceptance.py](/Users/koval/dev/prc/.claude/worktrees/readiness/.audit/verify-trustworthy-acceptance.py:15) checks the original diff hash and output revision fields. It never checks the recorded input-map hash, original numstat, output per-file counts, board identity, or explicit Go limitations. Revision fields alone cannot establish content equality. Add those checks before using its final "verified" verdict. The current inputs passed these independent comparisons.

2. **Merge status lacks retained evidence.** Every board sets `scenes[0].kicker` to "Merged pull request". Their retained provider records contain neither merge status nor a merge timestamp. The capture script does not preserve those fields. This label is unverified, not demonstrated false. Preserve authoritative merge evidence or use a neutral label.

The capture and verification scripts are intentionally ignored; their tracking status is not a defect.
Final installed-wheel rendering and visual checks remain the parent's work. Unfinished videos are not findings.
All three provenance records identify `human_reviewer=user` and `human_acceptance=pending`; no outside reviewer is required.

Suggested next step: strengthen the verifier and complete the three installed-wheel review packets for the user's acceptance.

