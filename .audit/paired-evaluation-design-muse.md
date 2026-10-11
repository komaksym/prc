# Paired PR evaluation - Muse architect candidate

Effort ceiling: max is unavailable on muse-spark on this runtime; this candidate is authored at xhigh.
Do not use the workhorse model in why-investigator roles. why investigators stay on opencode-go/deepseek-v4.1-flash @max; why synthesizer stays on opencode-go/muse-spark-1.3-contributor @max per prc routing. Call check_dispatch before every dispatch.

Grounding: pstack architect SKILL plus design-red-flags; prc AGENTS.md routing table; worktree paired-evaluation src/prc/evaluation (protocol.py, scoring.py, analysis.py, io.py), src/prc/cli.py eval-analyze path, docs/design/evaluation-protocol.md solo 12-pair protocol, PLANS.md Matched PR evaluation plus paired-evaluation.todo.md done predicate.

## Problem

Run an exploratory paired pilot with three pairs and six PRs by default. Each pair holds two similar but distinct unseen PRs. One PR is read under baseline (GitHub plus genuine Coldtea PR Lens CI output). The other is read under treatment (GitHub plus PRC). Each PR is read once. Both tool outputs are prebuilt and pinned. Preparation time stays outside the 20-minute reading deadline. Each PR carries three frozen questions with private keys. Sessions randomize assignment, exposure order, and pair order. The browser persists answers and timing across refresh, exports responses, and feeds blinded scoring into the existing eval-analyze path. No code is implemented by this candidate.

## Usage

Prepare one sealed kit, run it in one labeled browser tab, export answers, then blind and score. Four thin CLI verbs wrap one kit module; the browser hub is static files only.

  prc eval-paired-prepare --roster roster.json --lens lens/ --prc prc-views/ --questions questions/ --out kits/k1
  prc eval-paired-verify kits/k1
  open kits/k1/hub/index.html in a labeled agent-browser tab, answer, resume after refresh, download responses.json
  prc eval-paired-grade --kit kits/k1 --responses responses.json --out grades/k1 --blind
  prc eval-analyze grades/k1/pairs.json

Call sites: kit builder calls seal_experiment plus assign with Protocol(pair_count=3); hub reader calls verify_kit then renders the assigned view only; grader calls load_pairs then analyze unchanged.

## Shape

New boundary is one module: src/prc/evaluation/paired.py owning kit, hub manifest, session cursor, and response export. Existing protocol, scoring, analysis, and io stay untouched. Presentation reuses frozen review HTML plus captured Lens HTML; no new semantics enter build_document or render paths.

Typed model (frozen dataclasses, not implemented): PairedKit with roster of six SnapshotRef, three PairSpec, InstrumentBundle, Assignment, and SealDigest; HubManifest with per-pair page order and redaction flags; SessionCursor with pair index, slot order, per-PR start timestamp, elapsed, and submitted flag; ResponseRecord with snapshot id, slot, answers triple, confidences, delivery record, and elapsed; BlindedResponse with pseudonym, instrument id, and answers only.

Signatures: build_kit(spec) returns KitReceipt or raises KitRefused; verify_kit(kit) returns receipt or raises; export_session(cursor, answers) returns ResponseRecord list; blind_responses(records, kit) returns BlindedResponse list; to_pair_outcomes(graded, assignment) returns PairOutcome list for load_pairs and analyze.

Validation lives at the kit boundary and trusts types inside. build_kit refuses missing Lens output, revision mismatch between pinned base-head SHAs and rendered artifacts, duplicate snapshot ids, any acceptance-packet or previously exposed PR, instrument without exactly three questions per PR, and any key material inside the hub directory. verify_kit rechecks seal digest, assignment coverage exactly once per snapshot, one baseline plus one treatment per pair, and redaction of future PR identities and keys. Export validation rejects unknown snapshots, duplicate submissions, and dropped pairs.

Lifecycle: collect six unseen matched PRs and pin revisions; capture genuine Lens CI plus frozen PRC views and record provenance; freeze three questions and adjudicated keys per PR into private storage; seal roster, pairing rationale, instruments, treatment ids, and versions; randomize assignment, exposure, and card order from one PCG64 stream; build the static hub; present one assigned view per PR with a monotonic per-PR timer; persist drafts and timing in hub-local storage for resume; export responses; strip to blinded form; score against private keys; run eval-analyze with primary, adverse, and favorable scenarios preserved.

Interface depth: callers learn four verbs plus two JSON schemas. The kit hides matching checks, seal hashing, order draws, redaction, timer math, resume merge, and blind stripping. No transport or wire types leak onto the public API.

## Static offline hub versus local server

Static offline hub: prebuilt index plus one page per assigned slot, vanilla JS, hub-local storage, no backend process, file URL or loopback static server, screenshots and resume are trivial, seal equals directory hash plus assignment payload.

Local server: small Python server with session endpoints, server-side timers, and POST persistence. It adds split ownership of session state, a second way to render views, pass-through endpoints, temporal split across load-validate-serve-grade stages, and port plus process management inside the repo.

Decision: choose the static offline hub. It is the whole shape with the smallest boundary. One state owner (PairedKit plus hub-local cursor), no server clock to reconcile, no ports or secrets in the repo, and no changes to scoring or analysis. The server is rejected for shallow-module behavior: more interface for less hidden policy, leaked session and wire types, and duplicated validation across client and server.

Red-flag screen: no shallow module (four verbs hide sealing, randomization, redaction, timing, blind); no leakage (storage and wire schemas stay private); no temporal decomposition (kit owns its invariants end to end); no pass-through methods; single ownership of kit, cursor, and export each; one way to render, one way to score; no importable internals (hub JS cannot import Python internals); one ordered pair list derives navigation, export order, and grade joins.

## Failure cases

Missing Lens output or SHA mismatch refuses kit build, never falls back silently. Duplicate or exposed PR refuses build. Key bytes found in hub fail verify. Product-view load failure scores saved answers and zeroes blanks under product assignment, mirroring deliver_product fallback semantics. Abort or 20-minute censoring keeps saved answers, zeroes blanks, and marks censored time. Lost or unstarted responses stay unknown so adverse and favorable scenarios still run. Refresh resumes from hub-local cursor without reread of another slot. Export with wrong seal is rejected before grading.

## Tests

E2E first through the real entry point: build a two-pair fixture kit, open the hub in a labeled browser tab, answer one pair, refresh and resume, submit, export, blind, score, run eval-analyze, and assert the repeatable artifact path. Then isolated unit tests, one per failure above: duplicate PR, exposed packet PR, missing Lens, revision mismatch, key leak, invalid assignment, dropped pair, censored timer math, and blind stripping that asserts no assignment, timing, interface, or product artifact survives. Browser checks keep screenshot artifacts and restore the user tab.

## Open questions and risks

With three pairs the bootstrap interval is descriptive only and cannot support power claims; is the 10-point solo success rule the right pilot gate, or should this pilot report estimates only? Should the hub enforce strict forward-only navigation, or allow read-only review of submitted pairs? Assumption: forward-only with read-only review, no answer edits after submit.

## Next implementation step

Write the failing two-pair fixture E2E plus the duplicate, exposed, missing-artifact, and key-leak unit tests before any kit code.
