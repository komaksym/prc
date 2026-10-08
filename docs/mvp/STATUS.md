# PRC product and repository status

Summary. PRC's implemented package produces local review outputs. Product acceptance is incomplete. Repository reconciliation preserves earlier work and gives local main one baseline.

Updated 2026-10-08. This file is the current status entry point. Historical plans and scoreboards retain their original results.

## Repository baseline

The retained branch implementation is consolidated with pending PRC fixes, tests, grading tools, and the project verification skill. Missing Stage 5, Stage 6, and Stage 7 evidence is retained under [recovered historical evidence](evidence/reconciliation/README.md).

Historical worktrees and their ignored caches remain intact. The branch reconciliation uses reviewed current code, not blind replay of older implementations. Branch ancestry is checked after consolidation.

Before reconciliation, every branch ref was saved in `artifacts/reconciliation/2026-10-08/branches-before.bundle`. All 2,290 pending file identities and contents were saved beside it. Unrelated analyzer, queue, and provider experiments were moved into its `unrelated-experiments` directory with matching hashes. These archives stay local.

The public repository is https://github.com/komaksym/prc with default branch main. Local main was pushed there and PR 1 (tracker destination record) was merged. No license is selected yet.

## Implemented and checked behavior

The CLI supports interactive maps, checked explainer video, walkthroughs, cards, comments, board tools, local review decisions, and board-writing skill installation. The package supports captured maps for offline rendering.

Stored-map reconstruction now supplies one reconciled dictionary to board checks and every renderer. File classifications and checked facts agree across outputs. Receipt ranking uses displayed changes before context. Explicit symbol and edge receipts participate. Quoted lines outside changed symbols receive file entries.

The regression invokes the real explain CLI with an older map classifying an E2E test as production code. Its checked facts and published outputs agree after reconstruction. Browser screenshots and media remain under `artifacts/e2e/explain/stored-reclassified`.

The full check is `bash scripts/verify-release.sh` with the existing Chromium cache. The final proof is `artifacts/release/verify/run-MZ8PLD`. It passed 572 tests and all required checks. After publication, `artifacts/release/verify/run-UULFOm` repeated the full check on the merged main with the same result. Lint, formatting, strict types, tests, build, clean-wheel installation, browser screenshots, and five output files are required.

## Verification skill

[The project verify skill](../../.agents/skills/verify/SKILL.md) is committed and discovered by Codex. Its five feature recipes cover maps, explainers, board tools, review decisions, and installation.

Its executable map driver uses the real CLI and background Chromium. It verifies symbol inspection, Escape, offline loading, captured screenshots, and scratch cleanup. Failed attempts retain diagnostics. The current reconciliation run passed at `artifacts/verification/map-yhisxmlz`.

The skill seeds manual recipes for the remaining paths. It does not establish complete product acceptance. This session used existing Playwright because Vercel agent-browser was unavailable.

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
7. Establish the intended GitHub URL, content and history review, license, and publication decisions.

The [human comparison sheet](../../eval/human/2026-10-08-comparison.md) covers three captured PRs. Responses remain blank. It compares PRC with the plain diff, CodeRabbit, and available Coldtea PR Lens material. Historical third-party results cannot count as current-head coverage.

The [reconciliation map](../../.scratch/reconciliation/map.md) owns repository decisions. Release acceptance is governed by [EVAL.md](EVAL.md) and [DECISIONS.md](DECISIONS.md).
