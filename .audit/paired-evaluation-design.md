# Local service with a private sealed study

## Usage

Prepare a manifest with pairs, comparable question slots, source snapshots, both tool artifacts,
and private answer rubrics. Run `prc eval-prepare manifest.json --out study`.
Run `prc eval-session study`; it serves a light page on loopback and prints its URL.
The reviewer starts one reading, sees GitHub and the assigned tool, answers three questions,
records confidence, then submits or aborts. Refresh resumes the same reading.
After all trials, export answers for blinded scoring. Import awarded anchors with
`prc eval-grade study scores.json --out results.json`; feed results to `prc eval-analyze`.

## Shape

The kit owns the sealed manifest, matching rationale, per-PR questions, rubric, hashes, tool
identities, random assignment, and schedule. Persist the assignment after the manifest is sealed.
The session owns atomic server-side state: pending, active, submitted, aborted, timed_out.
One active PR at a time. No arbitrary static directory serving. Serve only its assigned
artifact tree, never the manifest, keys or other PRs. Block path traversal and cross-origin writes.
An exported answer sheet contains opaque trial IDs, question text, answers, and rubrics only
after the whole study is closed. It excludes condition and timing. Grade import verifies the
exact expected trial and item IDs and score anchors before producing existing PairOutcome JSON.
Analysis loads the explicit sealed protocol rather than assuming 12 pairs.

## Grounding

Reuse Protocol, Pair, seal_experiment, assign, score_item and analyze. Preserve old constants for
historical results; define an explicit new three-pair prebuilt protocol. Legacy analysis remains
available. Questions remain one MC plus two short responses; comparison is accuracy first,
time secondary, exploratory. Capture generation timing separately. No substitution of plain
GitHub for unavailable Lens. Real source requires PR identity plus diff base/head hashes and
authentic Lens job/run or published comment at the same head, not PRC's vendored renderer.

## Alternatives

A static file hub with browser localStorage is simpler to deploy but ships future PRs and
potential keys to the browser, permits peeking through paths and loses responses across origins.
A full React/database app has unnecessary infrastructure. A standard-library HTTPServer and
small vanilla JS page fit local single-reviewer scope and durable response persistence.

## Failure contracts

Reject duplicate PR identities even at different commits, exposed acceptance IDs, missing matching
rationale, incompatible question kinds, stale evidence, missing Lens artifact, any tampered seal,
changed treatment, grading before closure, unknown trial IDs, invalid scores, and advancing
without a terminal record. Refuse accidental overwrite of an existing study.
Save every answer edit before advancing. No score feedback until closure.
Timeout saves answers; blanks score zero. Unstarted trials remain unknown when closing early.
Time includes view loading from start, continues across refresh, and does not pause.

## Rubric for comparing designs

1. Distinct unseen pair invariants and exact two conditions.
2. Immutable source, instrument and tool evidence; honest readiness.
3. Browser privacy, persistent one-reading state, deadline and abort.
4. Existing analysis integration and correct missing outcomes.
5. Minimal dependencies and explicit local ownership.

## Synthesis decision

Use the parent local service as base. The independent Muse cross-judge scored it 9/10
against 4/10 for the static candidate. GLM independently chose a local server. Keep one
session state writer and reuse the existing analysis with the explicit sealed protocol.
Graft GLM's active-artifact allowlist and terminal-state no-reread policy. Graft Muse's
CLI workflow and fixture E2E coverage. Reject static delivery of future identities.
Reject public pair-count overrides during analysis; use the frozen kit's protocol.
Model the Domain shaped the typed study and trial states. Separate Before Serializing
Shared State shaped the exclusive implementation checkout. Prove It Works requires
driving actual start, resume, submit, export and grade behavior in a browser.

The configured Muse max effort is unavailable in this host; its supported xhigh ceiling
was used explicitly for feature and design roles. The DeepSeek investigators run at max.
