# Solo evaluation protocol

This protocol supplies finding 12's decision and failure policy. Numbers are explicit provisional engineering defaults for this bounded solo pilot, not empirical effects. Results are exploratory creator-only signals, with no power or generalization claims.

## Sample and freeze

Use exactly 12 matched pairs, 24 previously unseen AI-generated or agent-authored open-source PRs. Each immutable SourceSnapshotId is reviewed once. Eligibility requires disclosed agent authorship, inspectable code and evidence, at most 500 changed lines and 10 changed files, and no previous creator exposure. Resolve eligibility and instrument problems before assignment.

Match snapshots on change type, changed lines, file count, and verification surface. Freeze the selected roster and pairing rationale. One fair coin per pair assigns the lexicographically first snapshot to product on heads and baseline on tails. A separate coin chooses exposure order: heads product first, tails baseline first. Uniformly shuffle 12 numbered pair cards for pair order; preserve all draws. Run three pairs per session on days 1, 3, 5, and 7. Close at day 7, retaining unstarted assignments. No optional stopping, replacement, or interim aggregate scoring.

Before assignment and the first scored trial, seal this full protocol, roster, snapshots, instrument, schedule, evaluator/adjudicator/scorer versions, and immutable ProductTreatmentId/BaselineTreatmentId. Identities cover models/inference settings, prompts, retrieval, semantic/support-validation policies and implementations, renderers, visual language, UI builds, and baseline/fallback rendering. Any protocol or treatment change requires a new experiment; preserve this experiment's assigned records.

## Evidence and instrument

The instrument, baseline, product, and fallback consume the same complete, observationally stable captured source/evidence bundle for each snapshot. It is a timed observation bundle, not a claim of one atomic GitHub state. Baseline reproduces normal GitHub review information from that bundle.

An independent evaluator, without the creator or product explanation, prepares three equally weighted questions per snapshot: one multiple-choice and two short mechanism responses. A separate independent adjudicator checks each question/key against pinned evidence using the product's evidence-support standard. Resolve disputes before freezing. Independent model processes may fill these roles; the creator cannot adjudicate their own answers.

Freeze required answer elements and evidence references. Multiple-choice scores are 0 or 1; free responses score 0, 0.5, or 1 against explicit rubric anchors. Score pseudonymous free responses without assignment, interface, failure status, timing, or product artifacts. A second blinded scorer resolves rubric disputes; unresolved disputes receive the lower anchored score. Withhold keys and feedback until all exposures end.

## Outcomes and delivery failures

The primary target is the creator's mean accuracy difference under product assignment, including fallback, compared with baseline assignment across the frozen matched roster and schedule. Only one condition is observed per snapshot. For each PR, accuracy is the sum of its three item scores divided by three. For each pair, subtract baseline accuracy from product-assigned accuracy. The estimate is 100 times the mean of all 12 differences, in percentage points. Weight PRs and pairs equally. This measures performance on the evidence-adjudicated instrument, with residual key and model error acknowledged.

Time is secondary. Start the monotonic timer at the first delivery request, before generation, loading, or validation; stop at submission, explicit abort, or the 20-minute deadline. No pauses. Report each pair's product-minus-baseline time and their mean where both durations are recorded.

Allow one product generation/validation attempt, capped at 120 seconds. On failure, rejection, or timeout, immediately deliver the prebuilt frozen baseline for that same snapshot, using the original deadline. Score actual responses. Keep assignment as product, record failure reason and exposed identities, and include attempted generation, validation, and fallback time. Successful product delivery records PublishedViewIdentity. If fallback also fails, score saved answers and zero the blanks. Never drop or replace randomized snapshots.

Collect 0–100% confidence per answer; report confidence against item scores diagnostically. Confidence and time cannot override accuracy.

## Decision and missing data

After closure, resample all 12 pair differences, including primary missing scores, with replacement 20,000 times, taking 12 pairs per resample. Use PCG64 with seed 12024; freeze its implementation/version before assignment. Sort estimates; the 1,000th and 19,000th values are the descriptive 90% paired bootstrap interval. This small convenience panel cannot establish reliable population coverage.

Pilot success requires a gain of at least 10 percentage points and a lower endpoint strictly above zero in both the primary analysis and adverse missing scenario below. Otherwise, report no promising signal if every scenario's upper endpoint is below 10 points; report inconclusive in all other cases. Success warrants broader evaluation.

Known unanswered items and unsupplied items after abort/deadline score zero; preserve and score saved answers. Unstarted trials or lost response records are unknown outcomes, scored zero in the primary analysis. Retain all three items and all 12 pairs. Missing confidence remains missing. Missing time remains missing; report recorded attempt duration, censoring, and missing-time counts separately.

For unknown outcomes, repeat estimation and bootstrapping twice with the same seed: product unknowns 0 and baseline unknowns 1 is adverse; reversing those scores is favorable. Known blanks stay zero. Without unknowns, scenarios equal the primary analysis. Report assignment versus exposure, all pair outcomes, scores, interval, sensitivity decisions, failure/abort/deviation counts, and missing counts by condition.

## Future implementation acceptance examples

These are future implementation checks; no code or tests accompany this document.

- Generation times out at 120 seconds; fallback answers score normally under product assignment and elapsed time includes those seconds.
- Support validation rejects an explanation; the trial uses the same snapshot's baseline and retains its pair.
- Abort after one correct answer and two blanks yields one-third accuracy.
- A lost baseline response triggers both sensitivity scenarios; its pair remains.
- A mid-experiment prompt or key edit requires a new experiment and preserves the original records.
