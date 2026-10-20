# PRC hygiene retention

Removed 24 run log files under eval/runs/2026-10-08-release-check/logs.
Kept docs/mvp/evidence/reconciliation/history/stage6-log.md as useful Markdown.
Full history stays in immutable commit 2587b00, no rewrite.
Curated evidence stays tracked, including docs/mvp/evidence and docs/media.
Guard scripts/check-hygiene.sh and tests/test_hygiene_guard.py reject caches and pyc and logs and private.
See .gitignore for eval runs logs and pyc and private prevention.
