# prc: GitHub PR comprehension MVP

`prc` turns one GitHub pull request into a pinned, evidence-linked review view for a human reviewing an AI-generated change: an overview, behavioural concepts with adjacent evidence, a required infographic, a relation flow diagram, a change-surface table, the agent trace (as reports, not proof), and visible coverage gaps. The reviewer records approve, reject or request changes. Nothing is merged or decided automatically.

The design contracts live in `CONTEXT.md`, `docs/design/` and `docs/adr/` (provenance in `docs/PROVENANCE.md`). The implementation plan is `PLANS.md`.

## What is real and what is a fixture

- All development and the E2E test use deterministic **local fixtures**: real local git repositories plus fixture provider data. Every artifact and page from them is labelled `fixture` / `live_verified: false`.
- The comprehension, support-assessor and closure-falsifier "models" are deterministic **fixture heuristics** behind typed protocols (`prc.comprehension`). No LLM is wired in. Their output is labelled `fixture` in every artifact.
- `prc.github_source.GitHubSource` implements the same `PullRequestSource` contract against the GitHub REST API and `git fetch`. It is covered only by contract tests with canned payloads. **It has not been run against live GitHub.** It reads `GITHUB_TOKEN` from the environment and never writes it to output.

## Usage

```sh
uv sync
uv run prc review --source fixture:basic          # fixtures: basic, hostile, opaque, gaps, advanced, claims
uv run prc status --source fixture:basic          # reconcile freshness: match / stale / unknown + deadline
uv run prc decide --source fixture:basic --expect-snapshot <id> --expect-view <id> \
    --reviewer me --decision request_changes --confidence 70 --note "..."
uv run prc fixture-mutate basic edit-title         # simulate a provider change (fixture only)
uv run prc eval-analyze results.json               # solo pilot analysis
uv run prc review --source github:<owner>/<repo>#<n>   # live adapter, unverified
uv run prc brief --source fixture:claims           # one PR comment from diff, description and CI; no model
```

`review` prints the snapshot, semantic and published-view identities and writes `index.html`, `infographic.svg`, `flow.svg` (when relations exist), `entry.md`, `semantic.json`, `snapshot.json`, `manifest.json` and `view.json`. `decide` refuses (exit 2) when the expected snapshot/view is no longer the current local exposure.

`brief` computes one GitHub comment from the diff, the PR description and CI results, with no model calls and no store writes. It writes `<out>/<snapshot id short>/brief.md` and `brief.json` (default `--out artifacts/briefs`) and prints the paths, the mismatch count and the look-first files. Domain: `prc.brief`; renderer: `prc.presentation.render_brief`, which routes every PR-controlled string through one code-span helper.

## Contract map

| Contract | Code |
|---|---|
| Code Comparison Identity, separate per-check Verification Evidence Identity and eligibility | `model.py`, `verification.py`, `snapshot.build_basis` |
| Source Basis, Semantic Input Manifest, Source Snapshot; extra context ⇒ new snapshot | `snapshot.py` |
| Timed capture, drift reread, ≤3 attempts, unknown consistency | `capture.py` |
| Complete Git-tree inventory with explicit opaque surfaces | `inventory.py`, `gitutil.py` |
| Untrusted generator/validator, deterministic checks, model-assessed basis, scope witnesses | `controller.py`, `validation.py`, `comprehension.py` |
| Many-to-many coverage ledger and independent closure falsification | `coverage.py` |
| Inert presentation, semantic-operator checks, URL policy, output allowlists | `presentation/` |
| PublishedViewIdentity, atomic canonical publication, CAS decisions | `pipeline.render_view`, `store.py` |
| Freshness reconciliation with finite deadline | `freshness.py` |
| Solo evaluation protocol (assignment, scoring, fallback, PCG64 bootstrap, scenarios) | `evaluation/` |

Semantics are recomputed for every snapshot; no cross-snapshot semantic reuse exists.

## Evaluation input format

`eval-analyze` reads `{"pairs": [{"pair_id", "product": R, "baseline": R}]}` with exactly 12 pairs, where `R` is `{"snapshot_id", "state": "scored"|"unknown", "item_scores": [mc, short, short], "aborted", "confidences", "elapsed_seconds", "censored"}`. `tests/data/synthetic_pairs.json` is synthetic test input, not pilot results. No pilot has been run.

## Verify

```sh
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest && uv build
```

The E2E test (`tests/test_e2e_cli.py`) drives the `prc` entry point through review, status, decide, a provider change, a new revision, a refused stale decision and a byte-identical rerun in a fresh store. It leaves its artifact in `artifacts/e2e/`.

## Dependencies

`numpy` is the only production dependency: the evaluation protocol fixes the bootstrap generator as PCG64 with seed 12024.
