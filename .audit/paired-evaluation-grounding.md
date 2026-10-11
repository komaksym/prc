# Paired-eval how trace — prc readiness worktree

Read-only trace. Worktree: /Users/koval/dev/prc/.claude/worktrees/readiness (HEAD 533e5d5).
Target design: one test = two similar, distinct, unseen PRs; baseline = GitHub + Coldtea PR Lens
CI; treatment = GitHub + PRC. Parent owns local implementation planning. No files changed; no
candidate PRs exposed.

## 1. Protocol (assignment, sealing, schedule)

src/prc/evaluation/protocol.py

- Condition (product/baseline), Protocol frozen constants (line 21): pair_count=12,
  items_per_snapshot=3, 1 MC + 2 short, success_threshold_pp=10.0, bootstrap_resamples=20_000,
  bootstrap_seed=12024, generation_cap_seconds=120, deadline_seconds=1200, pairs_per_session=3,
  session_days=(1,3,5,7). PROTOCOL = Protocol() at module scope.
- Pair (line 51): two snapshot ids; first/second = lexicographic min/max. seal_experiment (81)
  hashes canonical JSON (sorted keys, no spaces); requires pairing to cover the roster exactly,
  the protocol pair count, unique snapshots, one instrument id per snapshot. verify_seal (115)
  rehashes the payload. Payload freezes protocol, roster, pairing, instrument ids, product and
  baseline treatment ids, evaluator versions.
- PairAssignment (122) / ExperimentAssignment (138): assign (148) draws from one PCG64 stream —
  12 assignment coins, 12 exposure coins, 12-card shuffle. heads → lexicographically first
  snapshot to product; product_first = exposure coin. Sessions slice the shuffled pair order into
  day plans (3/3/3/3).
- Constraints: assign requires exactly protocol.pair_count pairs; custom pair counts need a
  consistent Protocol (pair_count/pairs_per_session/session_days) or sessions come out empty by
  slicing; sealing must happen before the first scored trial, and any treatment or protocol change
  needs a new experiment.

## 2. Scoring (items, timers, delivery, fallback)

src/prc/evaluation/scoring.py

- ItemKind (12); ITEM_KINDS = (multiple_choice, short, short). Rubric anchors: MC {0,1},
  short {0,0.5,1}; unsupplied/blank = 0 (score_item, 35). snapshot_accuracy (56) = mean of 3.
  pair_difference (63) = product − baseline.
- TimerReading/read_timer (73): elapsed capped at 1200 s, reaching it sets censored.
- ProductAttempt (83): either failure_reason or published_view_id, never both.
  DeliveryRecord (96) records assigned vs exposed condition, failure reason, view ids, attempt
  seconds, elapsed, censored, fallback_failed.
- deliver_product (109): one attempt capped at 120 s; failure/timeout/rejection → expose the same
  snapshot's baseline as fallback, keep product assignment, elapsed = attempt + response seconds.
  deliver_baseline (142): no attempt, response seconds only.
- SnapshotResult (164) scored/unknown; scored_result (186) requires item scores; unknown_result
  (205) has no accuracy, no elapsed unless a delivery exists. All constraints have direct tests
  (see §5).

## 3. Analysis (bootstrap, scenarios, decision)

src/prc/evaluation/analysis.py

- Scenario (19): primary/adverse/favorable; UNKNOWN_FILL ~30: primary (0,0), adverse product
  unknown 0 / baseline unknown 1, favorable product 1 / baseline 0. Known blanks stay 0.
- pair_differences (65) resolves unknowns per scenario; bootstrap_interval (91) restarts
  PCG64 seed 12024 each call, 20k resamples of the pair vector, sorted; interval_from_sorted (80)
  takes the 1000th and 19000th values (descriptive 90% interval; not coverage).
- decide (107): success only when primary AND adverse estimate ≥ 10pp with lower endpoint > 0;
  no promising signal when every scenario's upper < 10pp; else inconclusive.
- AnalysisReport (152) + analyze (227): three scenario intervals, decision, pair rows, missing by
  condition, failure counts, abort counts, fallback failures, time summary (175), confidence
  summary (197). analyze raises unless len(pairs) == protocol.pair_count (12).

## 4. I/O and CLI

- src/prc/evaluation/io.py load_pairs (33): JSON {"pairs":[{pair_id, product:{snapshot_id,
  state, item_scores, aborted?, confidences?, elapsed_seconds?, censored?}, baseline:{...}}]}.
  Loader only; there is no writer that exports delivery/session records into this format.
- src/prc/cli.py:200 declares `eval-analyze` (argparse); handler at 224-228 loads pairs, runs
  analyze, prints JSON. No CLI entry point exists for seal/assign/scoring/delivery or for
  building run records. README.md:256 labels eval-analyze "the earlier paired evaluation format".

## 5. Tests that pin the protocol engine

- tests/test_evaluation_protocol.py: frozen constants (12 pairs, 20k, seed 12024, ranks
  1000/19000, days 1,3,5,7); canonical JSON; seal stable + tamper detection; deterministic
  assign; heads→lexicographic first; 24 snapshots assigned; schedule covers all pairs 3/day.
- tests/test_evaluation_scoring.py: rubric anchors; timeout fallback (attempt 300→capped 120,
  elapsed 520, fallback exposed, still product-assigned); validation-rejection fallback keeps the
  pair; successful delivery records the view; abort 1 of 3; fallback-failed blanks; censor at
  1200 s; unknown-state invariants.
- tests/test_evaluation_analysis.py: interval index convention incl. a 20-resample hand case;
  deterministic bootstrap; decision branches; scenario fills and lost-baseline pair retention;
  time/confidence counts; 12-pair requirement.
- tests/test_e2e_cli.py:127 test_eval_analyze_runs_on_synthetic_input uses
  tests/data/synthetic_pairs.json (12 synthetic pairs; "not pilot results").

## 6. Docs and operator state

- docs/design/evaluation-protocol.md (49 lines) is the frozen design: §Sample and freeze (5):
  12 matched pairs, 24 previously unseen AI/agent-authored OSS PRs; eligibility = disclosed agent
  authorship, inspectable code, ≤500 changed lines, ≤10 files, no previous creator exposure; match
  on change type, changed lines, file count, verification surface; seal everything before
  assignment. §Evidence and instrument (13): baseline "reproduces normal GitHub review
  information" from the same captured bundle; 3-item instrument (1 MC + 2 short) by an independent
  evaluator, independent adjudicator, keys frozen; blinded scoring. §Outcomes (21): primary =
  mean pair accuracy difference in pp; one attempt, 120 s cap, fallback; timer from first delivery
  request, 20-min deadline; no dropping or replacement. §Decision (31): 20k bootstrap seed 12024,
  10pp rule, adverse/favorable repeats. §Future implementation acceptance examples (41).
- docs/design/architecture-checkpoint.md:216-239: trial rules — one previously unseen eligible PR
  seen once; paired by observable difficulty; baseline from the captured bundle; instrument
  frozen before assignment; solo experiment scope only.
- CONTEXT.md:84 "Scored Evaluation", :104 instrument author (keys frozen before assignment).
- docs/mvp/EVAL.md: the separate older five-part harness (gates, grounding audit, C0–C5
  comprehension, legibility, human session) with targets and scoreboard; not the pilot engine.
- Hub instructions (public-facing): docs/launch/ACCEPTANCE-WORKSHEET-TEMPLATE.md ("Review hub
  methods" → "Prepare the matched PR evaluation") states the exact two-PR design: two similar,
  distinct unseen PRs; one normal GitHub browser experience, the other GitHub plus PRC; randomize
  assignment and reading order; freeze equivalent questions and the key before either reading;
  acceptance notes are not study scores. .audit/review-hub-method.md (2026-10-11) records the
  state: acceptance separated from the matched study; "study size, questions, timing rules, and
  comparison arms remain to be reconciled and frozen"; no study roster or scored run exists.
  .audit/build-trustworthy-review.py:45-52 holds the same instruction text; line 52 names the
  requested comparison arms (agent text + Mermaid, Coldtea PR Lens), each with distinct unseen
  PRs and one scored reading per PR. tests/test_review_hub.py pins the "distinct unseen" and
  "excluded from the unseen" wording.
- Sizing tool: .audit/pilot-size-sim.py (tracked) simulates the pass rule for 3–12 pairs using
  the real analysis functions via replace(PROTOCOL, pair_count=n) (line 37) and checks the
  vectorized verdicts against bootstrap_interval/decide. Reusable as-is for study-size choice.

## 7. Reusable pieces for the new test

| Need | Reuse | Pointer |
| --- | --- | --- |
| Pair unit, coins, order, seal | as-is | protocol.py Pair 51, seal_experiment 81, assign 148 |
| One PR per condition, once | as-is (assign covers product_first + pair order) | protocol.py 148 |
| 3-item scoring, timers, fallback, unknowns | as-is | scoring.py 35-215 |
| Bootstrap, scenarios, decision | as-is at 12 pairs; custom Protocol for other counts | analysis.py 91, 107, 227; pilot-size-sim.py:37 |
| Recovery/analysis record | loader exists; format is minimal | io.py 33; cli.py:224 |
| Candidate eligibility signals | PR metadata + agent-authored label; size counts | github_source.py enumerate 140, repo_path 200; inventory.py build_inventory 106 |
| Treatment capture | `prc explain --source github:owner/repo#N` (GITHUB_TOKEN); map/doc/card/comment/video | cli.py explain; pipeline.py run_explain 538, ExplainResult 345 |
| Packet packaging pattern | staging dir + manifest (source/payload SHA-256) + atomic replace + previous backup | scripts/eval/packets.py |
| Deterministic grading primitives | normalization + exact/set/bool/location graders; prose → NEEDS_HUMAN | scripts/eval/grade.py; round pinning via question-hashes.json in grade_round.py |
| Instrument key checks vs pinned evidence | evidence path:line existence, key substring, bool keys | scripts/eval/validate_questions.py (adapt schema; see gap 8) |

## 8. Concrete gaps

1. PR Lens CI baseline has no runner or capture. In-repo PR Lens is only the renderer PRC's map
   uses: src/prc/presentation/map_assets/prlens.bundle.js + prlens.lock.json, maintained by
   scripts/vendor-prlens.mjs and scripts/verify_prlens_vendor.py (pins @coldtea/pr-lens-renderer
   0.3.2, MIT; docs/PROVENANCE.md). The PR Lens product (GitHub App/Action/CLI/agent skill, posts
   an animated diagram as a PR comment) is described only in prose at
   docs/launch/READINESS-2026-10-08.md:187-189. Missing: who runs it on unseen third-party PRs
   (app install requires repo cooperation; CLI availability unverified), commit-coverage check
   (the human sheet eval/human/2026-10-08-comparison.md warns stale "original reviewed commits"
   are not current-head coverage), capture of its comment/diagram into a packet, and a pinned
   baseline treatment identity (app/run id + version + head sha) for sealing.
2. No candidate discovery/screening/matching code. Eligibility signals exist piecemeal
   (agent-authored label, changed-line/file counts), but nothing selects or records candidates,
   enforces ≤500 lines/≤10 files, tracks "no previous creator exposure" (acceptance packets are
   excluded by prose only; .audit/candidate-watch.md is a hand-kept note), or computes the
   similarity match. seal_experiment takes pairing as a manual input.
3. No run recorder/exporter. load_pairs has no writer; DeliveryRecord/SnapshotResult and the
   ExperimentAssignment (draws, sessions) are not persisted into the eval JSON, and nothing at
   eval time binds a recorded file to the seal digest.
4. No packet builder for the new conditions. packets.py materializes C1–C5 (prc outputs alone);
   the study needs "github" (description, Files changed, discussion, checks, navigation per hub
   text) and "github+prc" payloads under the same manifest/hash discipline. Question IDs come from
   the older 8-question eval/questions/pr*.json; the pilot instrument is 3 items with no file
   format, no freeze-hash check, and no writer/adjudicator workflow (the question-hashes.json
   pattern is the model to copy).
5. No scoring bridge. grade.py verdicts (correct/partial/wrong/cannot_tell) do not map to the
   pilot's 0/0.5/1 anchors; free-text scoring by an independent blinded scorer and
   pseudonymous-scoring enforcement are unbuilt.
6. Single-test feasibility. analyze()/eval-analyze require exactly 12 pairs; a one-pair test must
   use custom Protocol values (or a new entry point). With 1 pair the bootstrap interval
   collapses to a point, so a one-test decision is descriptive; use pilot-size-sim.py to choose
   the frozen test count.
7. Timing/exposure runbook. Timer start/stop, 20-min deadline, 120 s generation cap exist only as
   function inputs (scoring.py 73-160); no operator tooling records them; "review each PR once"
   and blinding rules are prose.
8. Docs/scripts to reconcile. docs/design/evaluation-protocol.md §Evidence still defines a
   GitHub-only baseline; adding PR Lens CI changes the baseline into a third-party treatment with
   its own identity and external-account decisions (D21 gates publishing; the hub rules exclude
   exposed PRs from the unseen pool). scripts/eval/validate_questions.py hardcodes the 8-question
   schema and CACHE_DIR prototypes/mdp/store/git-cache, and this worktree has no prototypes/
   directory, so it cannot run here unmodified.

## 9. Frozen constraints to honor

- If the frozen protocol stands: 12 pairs / 24 snapshots; exactly 3 items per snapshot
  (1 MC + 2 short); anchors 0/0.5/1; blanks 0; unknowns primary-all-0, adverse (0,1), favorable
  (1,0); decision ≥10pp with lower >0 in primary and adverse, else no-signal/inconclusive;
  no optional stopping, replacement, or interim scoring; keys withheld until exposures end.
- Freeze evaluator/adjudicator/scorer versions in the seal (protocol.py 81); keep numpy PCG64
  behavior fixed (pyproject pins numpy>=1.26 as a floor only; the design doc asks for a frozen
  implementation/version before assignment).
- D20: questions and keys frozen before outputs (and per hub text, before either reading in the
  pair). D21: push/PR/publication and license choices wait for the user.
- Do not expose candidate PRs; exposed acceptance material is excluded from the unseen pool.

