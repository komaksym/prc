# PLANS — hardened GitHub PR comprehension MVP

Run date: 2026-10-04. Authority: `CONTEXT.md`, `docs/design/architecture-checkpoint.md`, `docs/adr/0001-*`, `docs/design/evaluation-protocol.md` (copied with provenance in `docs/PROVENANCE.md`). Those contracts are not reopened here.

## TLDR

1. Build the full MVP as a Python 3.12 package `prc` (stdlib + numpy for the protocol's PCG64) with one real entry point, the `prc` CLI, that turns a GitHub PR source into a published, hash-identified review view (overview, required infographic, evidence-adjacent claims, selected table/flow/prose artifacts) plus recorded reviewer decisions.
2. Contracts implemented in code: Code Comparison Identity separate from per-check Verification Evidence Identity; Source Basis / Snapshot identities; Git-tree Change Surface Inventory (real `git`); Semantic Input Manifest; bounded 3-attempt timed capture with unknown-consistency; Claim Validation with mechanical vs model-assessed basis; many-to-many Coverage Ledger with closure falsification; inert presentation with URL/output checks; PublishedViewIdentity; atomic canonical publication; freshness reconciliation + local CAS decisions; solo evaluation protocol engine.
3. Live GitHub: a real REST/`git` adapter implementing the same `PullRequestSource` contract is included but **unverified live** (no credentials were exercised). All development and E2E use clearly labelled deterministic local fixtures (real local git repos, fixture provider data, fixture model). Fixture behaviour is never reported as live verification.
4. Models: the comprehension and validator model clients are protocol-typed. Only deterministic **fixture models** ship; they are labelled `fixture` in every artifact. No real LLM adapter is wired (deferred).
5. Out of scope: video, non-GitHub sources, autonomous merge, permanent quiz/merge gate, cross-revision semantic reuse, running the pilot (no pilot results are claimed), PR publishing/deployment.
6. Deferred follow-ups: live LLM adapters, live GitHub run, web server UI for decisions (CLI + static HTML for MVP), frozen treatment-ID registration for a real cohort.

## High-Level Flow

```text
prc review --source fixture:<name> | github:<owner/repo#N>
  │
  ▼ acquisition/  PullRequestSource.observe()  ──► capture.capture_bundle (≤3 attempts, drift check)
  │                                               └─ ObservationBundle {resources, interval, consistency}
  ▼ identity.py   CodeComparisonIdentity (repo, PR, head, base tip, merge-base)   [no check data]
  ▼ inventory.py  git diff-tree over pinned commits ─► ChangeSurfaceInventory (opaque items kept)
  ▼ verification.py  per-check VerificationEvidenceIdentity + eligibility (gaps for missing/conflicting)
  ▼ manifest.py   SemanticInputManifest (content-addressed records)
  ▼ snapshot.py   SourceBasisIdentity ─► SourceSnapshot (ReviewSnapshotIdentity)
  ▼ comprehension.py  ModelClient.generate (untrusted) ─► candidate concepts/claims/coverage
  ▼ validation.py  deterministic checks + independent assessor ─► ValidatedSemanticArtifact
  ▼ coverage.py   many-to-many ledger + closure falsification ─► gaps
  ▼ presentation/ typed doc ─► html/svg/table/prose renderers ─► output checks ─► hashes
  ▼ publication.py  PublishedViewIdentity; sqlite UNIQUE(publication_key) atomic canonicalize
  ▼ reviewer.py   freshness reconcile ─► CAS decision (snapshot_id, view_id) ─► reviewer state
  ▼ artifacts/<run>/{index.html, infographic.svg, semantic.json, snapshot.json, manifest.json}

evaluation/  protocol.py (assignment, roster seal) → scoring.py → analysis.py (PCG64 bootstrap, scenarios)
```

## Milestones (each ends in a verified state)

- [x] M0 Workspace: docs copied with provenance, uv project, PLANS.md.
- [x] M1 Identity + models core: canonical hashing, branded ids, frozen models. Tests: hash stability/order independence, identity layering (check change ⇒ basis change, comparison unchanged).
- [x] M2 Acquisition: `PullRequestSource` contract, fixture source building real local git repos, GitHub live adapter (unverified), `inventory.py` (add/del/mod/mode/symlink/submodule/binary/LFS/opaque), `capture.py` (drift ≤3 attempts, unknown consistency), verification eligibility + gaps.
- [x] M3 Manifest + Snapshot: manifest, SourceBasis, snapshot identities; late context ⇒ new snapshot.
- [x] M4 Comprehension + Validation + Coverage: model protocols, fixture models, claim validation (mechanical vs model-assessed, scope witnesses, disagreement ⇒ inference/gap), many-to-many ledger, closure falsification, adversarial fixtures.
- [x] M5 Presentation: typed document, inert HTML/SVG/table/prose renderers, URL policy, output validator, infographic always; hostile markup/URL tests per renderer; relation direction + epistemic-state preservation.
- [x] M6 Publication + reviewer state + freshness: PublishedViewIdentity, sqlite atomic canonical key, freshness reconcile (match/stale/unknown + deadline), CAS decisions.
- [x] M7 Evaluation engine: assignment, three-item instrument scoring, fallback, PCG64 bootstrap, adverse/favorable scenarios, decision rule. Acceptance examples from the protocol as tests. (Delegated to a subagent; reviewed by me.)
- [x] M8 CLI + E2E: `prc review|decide|status|eval-analyze`; E2E test through CLI ending in `artifacts/e2e/` repeatable artifact.
- [x] M9 Independent validation by a fresh-context agent (finite: one pass, fix confirmed defects), docs (README), final verify: ruff, mypy --strict, pytest, build.

## Verify command

`uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest && uv build`

## Progress log

- 2026-10-04 00:36 start. 00:45 M0–M4+M7 (6/10), 52 tests. 00:52 M5–M6 (8/10), 93 tests. 00:55 M8 E2E green, full verify green (97 tests, build ok). M9 independent validation running.
- 01:05 Independent validator (fresh context, one finite pass) reported 1 CRITICAL + 2 MAJOR: mechanical checks not bound to claim text/kind and able to close coverage; assessor crash not contained; losing publication overwrote the canonical bundle. All three fixed test-first and re-verified with the validator's own repro scripts. Final verify: ruff, format, mypy strict, 101 tests, build all pass. 10/10.
- Decisions: Python 3.12 + stdlib + numpy (PCG64 fixed by protocol); SQLite for atomic publication/CAS; static HTML/SVG with no script (CSP `default-src 'none'`); fixture models and fixture sources are labelled in every artifact.
