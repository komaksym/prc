#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
bad=$(git -C "$root" ls-files | grep -E "(__pycache__|[.]pyc$|[.]mypy_cache|[.]ruff_cache|[.]pytest_cache|[.]venv/|eval/runs/.*/logs/|[.]private)" || true)
if [ -n "$bad" ]; then
echo "forbidden tracked paths:"
echo "$bad"
exit 1
fi
echo "hygiene ok"
