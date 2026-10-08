# Reconcile PRC into one verified release baseline

Label: wayfinder:map

## Destination

Reconcile local PRC branches, pending changes, and verification into one recoverable baseline. Establish an evidence-backed completeness report and the route to the intended GitHub main.

## Notes

The user explicitly asked for execution on 2026-10-08. This overrides planning-only behavior. This session resolves one execution ticket, plus research tickets where needed. No public publication, license choice, forced rewrite, worktree deletion, or final human acceptance is inferred.

Use wayfinder, domain-modeling, grilling, poteto-mode, figure-it-out, and the project verify skill. Facts come from source, Git, and real artifacts. Existing instructions settle reversible reconciliation choices. Do not fabricate human answers.

Local Markdown is the configured tracker. Claims use Status and Assignee fields. Child dependencies use Blocked by. Historical experiments survive as archived evidence.

## Decisions so far

## Not yet specified

The final code review may expose defects that change the remaining release work.

## Out of scope

Public PyPI publication, promotion, new product features, and final human approval. Unrelated local experiments are preserved rather than shipped as PRC.

## Decisions so far

- [Establish one verified local PRC baseline](issues/01-local-baseline.md): consolidated retained source, tests, docs, and eval evidence into one commit; archived unrelated experiments and historical evidence with hash checks.
- [Identify the intended GitHub destination](issues/02-github-destination.md): no intended repository found in local config or the accessible account inventory; blocked on the human identity decision, no remote created.
- Technical package verification passes (572 tests, lint, format, strict types, build, installed-wheel browser checks); product acceptance stays incomplete per docs/mvp/STATUS.md.
