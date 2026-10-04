# prc map: see what a pull request rewired

Your agent wrote 800 lines. `prc map` shows which functions it changed, which calls it added or removed, and what it left untested, as one interactive page and a 30-second video. Every box and arrow is computed by parsing the base and head code. No model draws anything, so no arrow is made up.

## Try it in 10 seconds

```sh
uv sync
uv run prc map --source fixture:shop                       # offline sample, no network
uv run prc map --source https://github.com/<owner>/<repo>/pull/<n>
open artifacts/maps/*/index.html
```

A public PR needs no token. Set `GITHUB_TOKEN` for private repos or higher rate limits. Add `--video` for `tour.mp4` and `card.png` (see below).

## What you get

- **The map.** Changed functions and classes sit in the middle, layered by call depth. Their unchanged callers sit on the left, their callees on the right, and tests along the bottom. Green dashed arrows are calls the PR added, red ones calls it removed, and grey ones calls it kept. A dotted arrow was matched by name only.
- **The drawer.** Click any card for its diff, callers, callees and the tests that call it.
- **The tour.** Press Play. The camera walks from each entry point through the code it calls, with one caption per step, and ends on a summary card: symbols changed, calls added and removed, call sites affected, changed symbols with no direct test, CI on the head commit.
- **Overlay facts.** CI status on the head commit, and risky files (CI workflows, dependency manifests, auth), flagged when the PR description never mentions them.
- **One offline file.** `index.html` loads nothing from the network, and its strict CSP blocks scripts from the PR's own content.

Python, JavaScript, TypeScript and TSX are parsed with tree-sitter. A call is drawn only when an import, the same file, `self`/`this`, or a receiver named after the target's class or module proves it. On 19 public agent-authored PRs, 879 of 882 drawn arrows have a call of the target on a line of the source. The other 3 are generic calls such as `useReport<T>(...)` or calls through a re-export, and they are correct on inspection.

## The rest of prc

`prc` began as a PR comprehension MVP for a human reviewing an AI-generated change. The commands below remain: an evidence-linked review view (`review`), a freshness check (`status`), a recorded decision (`decide`), and a one-comment text brief (`brief`).

## What is real and what is a fixture

- All development and the E2E test use deterministic **local fixtures**: real local git repositories plus fixture provider data. Every artifact and page from them is labelled `fixture` / `live_verified: false`.
- The comprehension, support-assessor and closure-falsifier "models" are deterministic **fixture heuristics** behind typed protocols (`prc.comprehension`). No LLM is wired in. Their output is labelled `fixture` in every artifact.
- `prc.github_source.GitHubSource` implements the same `PullRequestSource` contract against the GitHub REST API and `git fetch`. It has contract tests with canned payloads, and `brief` and `map` have run it read-only against 19 public PRs. It reads `GITHUB_TOKEN` from the environment and never writes it to output.

## Usage

```sh
uv sync
uv run prc review --source fixture:basic          # fixtures: basic, hostile, opaque, gaps, advanced, claims
uv run prc status --source fixture:basic          # reconcile freshness: match / stale / unknown + deadline
uv run prc decide --source fixture:basic --expect-snapshot <id> --expect-view <id> \
    --reviewer me --decision request_changes --confidence 70 --note "..."
uv run prc fixture-mutate basic edit-title         # simulate a provider change (fixture only)
uv run prc eval-analyze results.json               # solo pilot analysis
uv run prc review --source github:<owner>/<repo>#<n>   # live adapter
uv run prc brief --source fixture:claims           # one PR comment from diff, description and CI; no model
uv run prc map --source https://github.com/<owner>/<repo>/pull/<n>   # interactive map of what the PR rewired; also fixture:shop; add --video for tour.mp4 and card.png
```

`review` prints the snapshot, semantic and published-view identities and writes `index.html`, `infographic.svg`, `flow.svg` (when relations exist), `entry.md`, `semantic.json`, `snapshot.json`, `manifest.json` and `view.json`. `decide` refuses (exit 2) when the expected snapshot/view is no longer the current local exposure.

`map --video` also writes `tour.mp4` (1920x1080, 30 fps) and `card.png` (2400x1260) next to `index.html`. It needs the `video` extra (`uv sync --extra video`, then `playwright install chromium`) and ffmpeg on PATH.

`brief` computes one GitHub comment from the diff, the PR description and CI results, with no model calls and no store writes. It writes `<out>/<snapshot id short>/brief.md` and `brief.json` (default `--out artifacts/briefs`) and prints the `brief.md` path, the mismatch count and the look-first files. Domain: `prc.brief`; renderer: `prc.presentation.render_brief`, which routes every PR-controlled string through one code-span helper.

`map` parses the base and head code and writes `<out>/<snapshot id short>/index.html` and `map.json` (default `--out artifacts/maps`). The page is one offline file: a left-to-right call map of the changed symbols with their callers, callees and tests, a diff drawer per node, and a computed tour exposed as `window.prcTour`. It prints the paths and the symbol, edge and step counts. Layout: `prc.presentation.map_layout`; page: `prc.presentation.render_map` with its CSS and JS in `map_assets/`. `--source` also accepts a GitHub PR URL.

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
