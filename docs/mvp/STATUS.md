# PRC product and repository status

Summary. The trustworthy PR explanation milestone passes its machine checks and awaits the user's acceptance of three real PR cases.
Public release acceptance remains incomplete. Repository reconciliation preserves the earlier baseline and evidence.

Updated 2026-10-22. This file is the current status entry point. Historical plans and scoreboards retain their original results.

## Trustworthy PR explanation milestone

The final source is 548d8ab in the readiness worktree. The assessment's defects have passing regressions.
The clean-cache verifier passed lint, formatting, typecheck, 812 tests without skips, build and installed-wheel rendering.
Proof is `artifacts/release/verify/run-uVHho9` in that worktree.

The acceptance package contains librarySync#98, em#5756 and swarm-deploy#116 at pinned base and head revisions.
Every case retains its original diff and five PRC outputs from the final installed wheel.
All 35 local review links passed in background agent-browser with screenshots.
Direct model inspection covers three cards, 21 complete-walkthrough segments and 19 actual video scenes.
Independent model reviews found no remaining correctness findings in the final delta.

The user is the only human reviewer. All three acceptance decisions remain pending.
Open `artifacts/trustworthiness/2026-10-09/acceptance/index.html` in the readiness worktree and complete its `acceptance.md`.
The [milestone record](../launch/TRUSTWORTHY-PR-EXPLANATIONS.md) records exact proof and limits.
This milestone does not certify the frozen release evaluation below. License, package name and publication remain separate.

## Repository baseline

The retained branch implementation is consolidated with pending PRC fixes, tests, grading tools, and the project verification skill. Missing Stage 5, Stage 6, and Stage 7 evidence is retained under [recovered historical evidence](evidence/reconciliation/README.md).

Historical worktrees and their ignored caches remain intact. The branch reconciliation uses reviewed current code, not blind replay of older implementations. Branch ancestry is checked after consolidation.

Before reconciliation, every branch ref was saved in `artifacts/reconciliation/2026-10-08/branches-before.bundle`. All 2,290 pending file identities and contents were saved beside it. Unrelated analyzer, queue, and provider experiments were moved into its `unrelated-experiments` directory with matching hashes. These archives stay local.

The public origin is [komaksym/prc](https://github.com/komaksym/prc), with `main` as the default branch. At this update, the remote and checkout resolved `main` at `99362409a24cee6d6cb2a1254e786b1e72908582`. The GitHub Actions workflow in [`.github/workflows/pr.yml`](../../.github/workflows/pr.yml) runs the isolated release verification on pushes to `main`, pull requests, and manual dispatches. Its `gate` job is the only check the `pr-gate` ruleset requires.

GitHub reports no repository license. The README and [decision D21](DECISIONS.md) leave the license, package publication, and promotional publication to the user. The repository contains operator instructions and drafts for those actions; it contains no record of a PyPI upload or promotional post. A public GitHub origin does not establish any of those decisions.

At reconciliation, no GitHub remote was configured. Discovery at that time found no intended PRC repository.
The current readiness checkout has origin configured as https://github.com/komaksym/prc.git.
No remote write was performed in this milestone. Push and PR creation still require the user's explicit approval.

## Implemented and checked behavior

The CLI supports interactive maps, checked explainer video, walkthroughs, cards, comments, board tools, local review decisions, and board-writing skill installation. The package supports captured maps for offline rendering.

Stored-map reconstruction now supplies one reconciled dictionary to board checks and every renderer. File classifications and checked facts agree across outputs. Receipt ranking uses displayed changes before context. Explicit symbol and edge receipts participate. Quoted lines outside changed symbols receive file entries.

The regression invokes the real explain CLI with an older map classifying an E2E test as production code. Its checked facts and published outputs agree after reconstruction. Browser screenshots and media remain under `artifacts/e2e/explain/stored-reclassified`.

The repository check is `bash scripts/verify-release.sh` with the existing Chromium cache. It requires hygiene, lint, formatting, strict types, tests, build, clean-wheel installation, browser screenshots, and five output files. The 2026-10-08 receipt at `artifacts/release/verify/run-MZ8PLD` reported 572 tests and all required checks. That ignored receipt is historical and absent from a fresh checkout. A later STATUS proposal also pointed to `run-UULFOm`, but neither that receipt nor evidence for a current 572-test count is retained. Run the command again at the final commit; use only its fresh proof path for the current result.

The reconciliation proof is `artifacts/release/verify/run-MZ8PLD`. It passed 572 tests and all required checks at that baseline.
The later trustworthy milestone proof is `artifacts/release/verify/run-uVHho9`, as recorded above.
The full check remains `bash scripts/verify-release.sh` with lint, format, strict types, tests, build and installed-wheel browser checks.

## Verification skill

[The project verify skill](../../.agents/skills/verify/SKILL.md) is committed and discovered by Codex. Its five feature recipes cover maps, explainers, board tools, review decisions, and installation.

Its executable map driver uses the real CLI and background Chromium. It verifies symbol inspection, Escape, offline loading, captured screenshots, and scratch cleanup. Failed attempts retain diagnostics. The 2026-10-08 reconciliation recorded a passing run at `artifacts/verification/map-yhisxmlz`; that ignored artifact is historical, not a fresh proof for this update.

The skill seeds manual recipes for the remaining paths. It does not establish complete product acceptance. The historical session used existing Playwright because Vercel agent-browser was unavailable.

## Acceptance evidence

[The complete historical scored run](../../eval/runs/2026-10-08-release-check/scoreboard.md) contains 60 bound reader packets and 480 final grades. It measures earlier output. Its recorded scores remain unchanged.

| Condition | Correct answers | Recorded result |
| --- | --- | --- |
| Card | 34 of 96 | Absolute target passes; improvement target fails. |
| Comment | 34 of 96 | Absolute and improvement targets fail. |
| Muted video frames | 37 of 96 | Absolute and improvement targets fail. |
| Walkthrough | 45 of 96 | Absolute and improvement targets fail. |
| First map viewport | 13 of 96 | Improvement target fails. |

That run records 35 wrong grades. A wrong grade requires source adjudication before it is attributed to a false product statement. The original baseline's reader also authored the questions, so baseline independence is limited.

The reveal candidate has twelve output sets and zero scored reader packets. The reconciled source has no certified acceptance run. Earlier scores cannot certify it. Four v2 question files remain unverified drafts; grading selects the frozen v1 keys.

Recorded OCR is 25 of 31 required strings at 800 pixels. Eight implemented gates passed 96 historical cells. Those gates do not implement every stronger requirement in EVAL.md. Current output-bound grounding audits remain absent.

The timing archive contains 48 successful samples, including twelve warmups and 36 measurements. These measure the earlier offline pipeline with silent voice. They exclude acquisition, authorship, and speech synthesis. They do not provide exact-current-source or per-step timings.

[Archived run status](../../eval/runs/ARCHIVED.md) distinguishes complete evidence, incomplete attempts, and local rendering checkpoints.

## Remaining release work

1. Generate current-source outputs and packets with fixed treatment identities and artifact bindings.
2. Independently adjudicate disputed question keys and audit all twelve current explanations against source.
3. Meet the frozen comprehension, zero misleading-answer, OCR, and complete gate requirements.
4. Capture correctly scoped current-source measurements.
5. Refresh the human comparison and its audible samples to the accepted output generation.
6. Obtain actual human usefulness, grader agreement, grounding checks, and release approval.
7. Review current content and history for later republication, and decide the license, package name and any promotional publication under D21 before any approved remote write.

The [human comparison sheet](../../eval/human/2026-10-08-comparison.md) covers three captured PRs. Responses remain blank. It compares PRC with the plain diff, CodeRabbit, and available Coldtea PR Lens material. Historical third-party results cannot count as current-head coverage.

The [reconciliation map](../../.scratch/reconciliation/map.md) owns repository decisions. Release acceptance is governed by [EVAL.md](EVAL.md) and [DECISIONS.md](DECISIONS.md).
