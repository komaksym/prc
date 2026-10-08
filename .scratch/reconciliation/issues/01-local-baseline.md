# Establish one verified local PRC baseline

Label: wayfinder:task
Type: task
Mode: AFK
Status: resolved
Assignee: Codex
Parent: ../map.md
Blocked by: none

## Question

Which local changes belong in the current PRC baseline, and can they be reconciled, preserved, independently reviewed, verified, and committed without losing unrelated work?

## Comments

The user authorized local reconciliation and remote synchronization. GitHub destination remains a separate fact. Final human release acceptance remains pending.

Confirmed source defects. [Independent source review](../../../.audit/reconciliation-source-review.md) identifies inconsistent stored-map facts and three receipt-ranking defects. The parent owns a real-CLI stored-map regression. A detached worker owns ranking regressions. These are prerequisites for the baseline, not new product scope.

## Answer

One local baseline committed and local main aligned. Branch audit found stage implementations already retained; 20 missing historical files recovered with matching blob hashes. Unrelated experiments preserved under artifacts/reconciliation. Source review found 1 P1 and 3 P2 defects; all four fixed with real-CLI and checker-accepted regressions. Final independent recheck of those fixes is still pending.
