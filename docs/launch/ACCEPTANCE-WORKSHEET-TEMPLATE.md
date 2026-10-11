# Review hub methods

Rebuild the local hub and worksheet with:

```sh
python .audit/build-trustworthy-review.py artifacts/trustworthiness/2026-10-09/acceptance
```

The builder owns the review instructions. It writes both instruction sections into
`index.html` and `acceptance.md`. It preserves case findings when it updates an existing
worksheet. Old ratings with answers remain as legacy acceptance notes, excluded from study scores.

## Accept the three exposed packets

Review their facts, omissions, references, rendering, and narration.
Use GitHub for optional fact checks. Original diffs remain optional evidence.
Choose accepted, changes requested, or deferred for each packet.
Record concrete defects. False claims and misleading omissions require changes.
Agent verification precedes human acceptance. Read its scope and limits in
`.audit/step1-requirement-audit.md` and the linked packet evidence.
These exposed packets are excluded from the unseen study pool.

## Prepare the matched PR evaluation

Use two similar, distinct PRs that the reviewer has not seen.
Assign one to GitHub plus genuine Coldtea PR Lens CI output and the other to GitHub plus PRC.
Randomize condition assignment and reading order. Review each PR once in its assigned condition.
Freeze equivalent questions and the answer key before either reading.
Grade against the frozen key. Compare question scores within each pair, then summarize pair differences.
Acceptance notes are not study scores.

Before a scored run, reconcile and freeze the pair count, instrument, timing rules, and comparison arms.
The current comparison has exactly these two conditions. Lens CI output must match the frozen source revision.
Artifact acceptance is independent. It is not a prerequisite for the matched study.
The current hub contains instructions only. It does not provide a sealed study roster or start a scored run.
