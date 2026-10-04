# PLANS — hardened GitHub PR comprehension MVP

Run date: 2026-10-04. Authority: `CONTEXT.md`, `docs/design/architecture-checkpoint.md`, `docs/adr/0001-*`, `docs/design/evaluation-protocol.md` (copied with provenance in `docs/PROVENANCE.md`). Those contracts are not reopened here.

## Phase 2 (current): PR brief, the free tier

### Summary

`prc brief` turns one pull request into one GitHub comment. Everything in it is computed from the diff, the PR description and the CI results, so it makes no model calls. It tells a reviewer of an agent-written PR four things in seconds:

- how big the real change is once lockfiles and generated files are set aside;
- whether CI passed on this exact commit;
- where the description and the diff disagree;
- the three places to look first, and why.

It reuses capture, snapshot, inventory and verification as they are. The store, the model pipeline and the HTML view are not involved. Validation means running it on real public agent PRs, then on the user's own repos through a GitHub Action. The 12-pair lab pilot is not part of this phase.

Why this comes first (evidence in `reports/AI code comprehension last three months.md`):

- The AI-written PR description is itself the complaint. Kenton Varda put a moratorium on them. GitHub's own blog calls them "long-yet-shallow". Reddit calls them a slop vector.
- Readers cannot tell a wrong AI assertion from a right one (Kaufman et al. 2026-07-09).
- Maintainers triage in seconds.
- Computed facts cannot hallucinate, cost nothing per PR, and never send code to a vendor.

### Milestones

- **B1.** `prc brief` on a fixture through the CLI, with the E2E test written first. Check: `artifacts/e2e/briefs/<id>/brief.md` is byte-identical on rerun, and verify passes.
- **B2.** Run it read-only on at least 20 public agent PRs (Copilot coding agent, Devin, Claude Code, Codex). Hand-check every flagged item to get precision per check type. Tighten or delete any check below 80% precision. Check: `artifacts/corpus/` holds the briefs and the precision table.
- **B3.** A GitHub Action runs `prc brief` on `pull_request` and creates or updates one comment, found by its marker. It is built and tested locally. Installing it on any repository needs the user's go-ahead.
- **B4.** Install it on the user's own repos, then offer it to maintainers. The signals are installs that stay, and comments saying it caught something. Every external message needs authorization.

Deferred until B4 shows people want it:

- the computed import and call map for the visual view (Python `ast` first);
- the model tier;
- the pilot protocol v2 from the 2026-10-04 interrogate review.

### B1 spec

Data shape. The domain lives in `src/prc/brief.py`. It is pure and reads only `Acquisition`.

- `Brief(pr, title, head_sha, files, checks, mismatches, look_first)`
- `FileChange(path, kind, added, removed, named, sensitive)`
- `Kind`: code, test, docs, config, generated or opaque
- `Mismatch(kind, quote, fact, subjects)`, where kind is `changed_claim_not_in_diff`, `symbol_claim_not_found`, `test_claim_vs_ci` or `tests_claim_no_test_files`. `fact` is our fixed sentence. Anything taken from the PR goes in `subjects`.
- `Pointer(path, reason, lines)`

File kinds and sensitive surfaces are ordered rule tables, not if-chains. The renderer is `src/prc/presentation/render_brief.py`. It sends every untrusted string (path, quote, title, check name) through one code-span helper, so PR content can never produce a mention, link, image or HTML. Output starts with the marker `<!-- prc-brief -->`. `pipeline.run_brief` and `prc brief --source … --out artifacts/briefs` write `<out>/<snapshot short id>/brief.md` and `brief.json`, then print JSON.

Rules:

1. **Kinds.** The first match wins, in this order:
   - opaque inventory item: opaque;
   - lockfiles, snapshots, minified files, `dist/`, `vendor/` and generated code: generated;
   - test paths: test;
   - `.github/`, dependency manifests, Docker, CI files, `*.toml`, `*.ini`, `*.cfg`, YAML, non-lock JSON, `.env*`, `Makefile` and `*.tf`: config;
   - Markdown, rst, txt, `docs/` and LICENSE: docs;
   - anything else: code.
2. **Sensitive surfaces** apply to any kind, and the reason text is ours. They are:
   - secret-scanner allowlists and package registry configs;
   - workflows and other `.github/` files;
   - dependency manifests, shown with up to 3 added lines;
   - Docker and infrastructure;
   - migrations and SQL;
   - paths whose names suggest auth or security;
   - env and secret files;
   - other CI configs.
3. **Claim units.** These are the bullet lines, checkbox lines, table rows and sentences of the title and body, taken after removing fenced code, HTML comments, `<details>` blocks and blockquotes. Bold and underline markers outside code spans are dropped. An unchecked checkbox claims nothing.
4. **`changed_claim_not_in_diff`.** A unit has a change verb (add, update, modify, change, fix, bump, remove, delete, rename, move, replace, create, edit, rewrite, refactor and their inflections) or an arrow (`→` or `->`) outside its code spans. It names a path-like token, meaning one with a slash or a file extension, that matches no changed path. The token must also exist in the base or head tree, so routes, package names and planned files never fire. A path matches by full path, by a suffix on a segment boundary, or by basename. A directory token matches any changed path under it. URLs, domains, package scopes and slash commands are not paths, and `:12` or `#L5` suffixes are stripped.
5. **`symbol_claim_not_found`.** A unit has a create, remove or rename verb (add, create, introduce, new, remove, delete, rename and their inflections). At most 3 words from a fixed list of articles and code nouns sit between the verb and a backticked identifier. The identifier appears in no diff line and no head content of any changed file. `name(args)` is checked as `name`, and a qualified name by its last segment. The check is skipped when any changed file is opaque.
6. **`test_claim_vs_ci`.** A checked checkbox or a sentence claims that tests, lint, typecheck, the build or CI passed. Either a check on this commit failed (failure, timed_out, cancelled, action_required or startup_failure), or no checks ran.
7. **`tests_claim_no_test_files`.** A unit claims tests were added, written or updated, and no test-kind file changed.
8. **Hedges.** Rules 4 and 5 skip a unit that says not, no, never, without, kept, unchanged, untouched, already, would, could or instead. Rules 6 and 7 skip a unit that negates, defers or reports a failure.
9. **Named.** A changed file counts as named when any description token or prose word matches one of these:
   - its path, a path suffix or its basename;
   - its stem or name in any spelling (case, hyphens and underscores ignored, at least 3 characters);
   - every part of its stem of 3 or more characters, as words, plural allowed;
   - the parent directory instead, when the stem is generic (index, page, route, layout, main, mod, init, server, handler, utils, types);
   - a symbol defined or changed in its diff.

   Named only feeds look-first. The brief no longer lists unnamed files, because run 1 showed that list was mostly semantic misses.
10. **Look first.** At most 3 pointers, in a fixed order:
    1. sensitive files the description doesn't name;
    2. other sensitive files;
    3. the largest code change.
11. **Generated files** are counted in a separate total. They never appear in look-first.
12. **Uninspectable files.** The size line says how many changed files could not be inspected (binary, or over the 64 KB inventory limit).

### B2 results (2026-10-04)

Corpus: 28 recent public PRs from small repos, 7 each from the Copilot coding agent, Devin, Claude Code and Codex. The list and runner live outside the repo. Briefs and `runs.json` are under `artifacts/corpus/` (gitignored). All 28 ran in both rounds. Every flag was checked by hand against the PR.

| Check | Run 1 flags, correct | Run 2 flags, correct |
| --- | --- | --- |
| `changed_claim_not_in_diff` | 13, 0 | 0 |
| `symbol_claim_not_found` | 3, 0 | 0 |
| `test_claim_vs_ci` | 3, 3 | 3, 3 |
| `tests_claim_no_test_files` | 0 | 0 |
| sensitive file not in the description (look-first) | not separated | 4, 4 |

Run 1 false positives came from tokens that are not repository paths (routes, domains, package scopes, number fragments, `file.py::symbol`), table rows and bold markers merged into one unit, data names read as symbols, and negated sentences. Rules 3, 4, 5 and 8 above are the fixes. Run 2 found no real description-vs-diff disagreement, so the recall of rules 4, 5 and 7 is unmeasured.

What held up:

- **Unbacked test claims.** All 3 are Devin PRs that report local test runs as passing while no CI ran on the head commit.
- **Unmentioned risky surfaces.** Three PRs change a CI workflow without mentioning it, and one changes the secret-scanner allowlist (`.gitleaksignore`).

Corpus facts:

- 12 of 28 PRs claim tests, lint or the build passed. CI on the same commit backs 9 of them, none is contradicted, and 3 have no CI.
- 8 of 28 have no CI on the head commit.
- 7 of 28 touch a sensitive surface, and 6 touch CI workflows.
- 9 of 28 contain a file the brief cannot inspect.
- None contain generated files.

Premise finding: these agents did not misstate which files they changed. The brief's value is a quiet, precise card of claims against evidence and risky surfaces, not a lie detector.

## Phase 1 (done): MVP

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
