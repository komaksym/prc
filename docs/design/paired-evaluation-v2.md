# Paired evaluation v2

## Summary

Each test compares two similar, distinct PRs. Read each PR once with its assigned aid.
One PR uses GitHub plus genuine Coldtea PR Lens CI. The other uses GitHub plus PRC.
The planned pilot has three pairs, six readings, and three questions per reading.
This is an exploratory usefulness study. It cannot establish release readiness or remove every source of bias.

Artifact acceptance is separate. Previously exposed acceptance PRs cannot enter the study roster.
No push, PR creation, publication, license, or package naming approval follows from this study.

## Preparation

Choose pairs using source evidence before examining tool explanations.
Record language, change kind, changed lines, changed files, and the matching rationale.
Reject pairs where one PR teaches the other PR's answers.
Record remaining differences, including shared history, authorship, merge status, and size differences.
The question author and adjudicator inspect pinned source independently of the explanation tools.
Freeze questions, keys, evidence, and scoring anchors before generating PRC explanations or assigning conditions.

Both aids must exist at the same pinned revisions before assignment.
Lens evidence requires an authentic successful app check, its captured bot comment, and content-addressed SVG files.
The rendered Lens page is pinned by `lens.page_sha256`, so a rebuilt or edited page cannot enter unnoticed.
PRC evidence requires its actual map to match the snapshot base and head, plus a hashed review page.
Keep all artifact directories inside the manifest directory. Symlinks and escaping paths are refused.

All source identities and answer keys stay in the private preparation directory.
Do not show private study images or PR lists in progress reports.
If an aid was accidentally shown before a reading, record that exposure rather than claiming the PR is unseen.

## Timing and assignment

Prebuild both aids. The former 120-second generation cap does not apply to this pilot.
Record measured generation times separately from reading time.
Use `null` with an explicit reason when total preparation time was not measured.
A captured CI duration does not establish the hosted tool's total preparation time.

`eval-prepare` validates the full manifest, then uses its recorded seed to assign conditions and reading order.
The final seal covers the roster, artifact hashes, questions, keys, pairing rationales, assignment, and order.
Later edits invalidate the study. Do not change the roster after observing scores.
Each reading has a 20-minute server clock that continues across page refreshes and server restarts.

## Reading

1. Launch `prc eval-session study/ --port 0` and open its loopback URL.
2. Select **Prepare next reading**. Report prior familiarity and prior explanation exposure.
3. Start the timed reading only if the PR and its explanations are unfamiliar.
4. Use the GitHub PR's normal review interface and the assigned aid. Read the PR once.
5. Answer its three questions. Record any unassigned explanation encountered on GitHub.
6. Submit, abort, or reach the deadline. Continue with the next distinct PR.
7. Close the study after the readings. Closure freezes answers and enables grading.

The service reveals only the next identity before timing starts.
It reveals the assigned aid and questions after timing starts.
A familiarity report refuses the timed reading and retains that outcome as unknown.
It does not replace the PR. Missing outcomes stay in analysis.

GitHub opens at **Files changed**, but other GitHub review surfaces remain available.
The live page remains mutable even when a head SHA is recorded.
The server verifies the live head and captured Lens comment before each real reading.
A changed revision or failed verification refuses the reading.
External GitHub can expose Lens on a PRC reading. The local service cannot prevent that exposure.
Exposure reports survive grading and appear with the analysis.

## Grading

The frozen instrument has one multiple-choice question and two short answers per PR.
Multiple-choice scores are 0 or 1 and must agree with the exact frozen key.
Short answers use 0, 0.5, or 1, according to the frozen required elements and rubric.
Blank answers receive 0. Confidence is optional and ranges from 0 to 100.

After closure, the session hub shows the condition-blinded grading sheet.
It scores multiple-choice and blank answers automatically.
Grade each nonblank short answer against its displayed frozen required elements and score meanings.
Select **Save grades and analyze** to persist the scores and view the exploratory analysis.
The hub requires every short-answer score before analysis. Reloading preserves the result.
The CLI export and grading commands remain available for an external scoring workflow.

Export after closure:

```sh
prc eval-export study/ --out grading.json
```

The sheet includes opaque trial IDs, submitted answers, keys, required elements, and rubric anchors.
It omits conditions, assignment, timing, repository fields, and artifact URLs.
This is condition blinding. Answer content can still reveal identity to a scorer who knows the corpus.
The user is the sole human reviewer; authoring and adjudication agents are not human reviewers.

Use the following score-file shape. Include exactly the terminal trials and their question IDs.
Do not include unknown readings. Copy the actual digest from the grading sheet.

```json
{
  "study_digest": "COPY_FROM_GRADING_SHEET",
  "scores": {
    "OPAQUE_TRIAL_ID": {"q1": 1, "q2": 0.5, "q3": 0}
  }
}
```

```sh
prc eval-grade study/ scores.json --out results.json
prc eval-analyze results.json
```

The result retains every sealed pair, unknown outcomes, exposure reports, and the study digest.
Compare comprehension first. Report elapsed reading time and confidence separately.
Do not treat a three-pair estimate or a threshold verdict as proof that PRC is ready for release.
Results without an explicit protocol retain compatibility with the original 12-pair analyzer.

## Manifest contract

The executable contract is `src/prc/evaluation/kit.py`.
`tests/paired_builder.py` supplies a complete runnable demonstration manifest.
Its fixture aids are demonstration material and cannot substitute for real study packets.

The manifest contains these fields:

| Field | Requirement |
| --- | --- |
| `schema_version` | `2` |
| `study_mode` | `real` for human evaluation; `fixture` for engine checks |
| `seed` | Recorded non-negative assignment seed |
| `protocol` | Pair count, session count, and session days covering the roster |
| `product_treatment_id` | `github+prc` |
| `baseline_treatment_id` | `github+lens-ci` |
| `packet_policy` | `use_assigned_tool_only` |
| `evaluator_versions` | Question author, adjudicator, and scorer version records |
| `familiar_pr_ids` | Additional exposed identities to exclude |
| `pairs` | Unique pair IDs, matching rationales, and two distinct snapshots each |

Each snapshot records its safe opaque ID, PR identity, base/head SHAs, title, change kind, size,
measured or explicitly unknown preparation times, contamination, and three artifact directories.
It also contains the authentic Lens record, PRC page hash and pins, and the frozen questions.
The size limits are 500 changed lines and 10 changed files per PR.

## Verification and limits

Preparation rejects duplicate or exposed identities, changed source pins, missing pages, and altered seals.
It also rejects any artifact file that names another reading's PR, PR URL, or head commit.
This stops one reading's materials from revealing a different PR in the study.
Trial-bound requests prevent old tabs from saving or submitting a later reading.
An exclusive writer and a serial HTTP service protect the persisted session.
Tests cover immediate submission, failed-save recovery, refresh, abort, closure, and unknown outcomes.
Real packet pages and videos need their own browser and media verification before handoff.
Passing demonstration tests does not establish that real study materials are ready.
