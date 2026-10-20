# PRC hygiene retention

Removed 24 run log files under eval/runs/2026-10-08-release-check/logs.
Kept docs/mvp/evidence/reconciliation/history/stage6-log.md as useful Markdown.
The removed files remain in main's prior commit 7d61740108a0635871a3e131e92f92f0b01a85b8. Git history is unchanged.
Curated evidence stays tracked, including docs/mvp/evidence and docs/media.
The release verifier runs scripts/check-hygiene.sh against the tracked index before building.
The guard rejects exact cache directory names, bytecode, root dist output, eval run logs, and .private directories.
Real Git index tests cover forced additions, names containing newlines, and similarly named Markdown that must remain allowed.
See .gitignore for eval runs logs and pyc and private prevention.
