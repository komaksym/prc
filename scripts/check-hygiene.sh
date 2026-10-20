#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
python3 - "$root" <<'PY'
import os
from pathlib import PurePosixPath
import subprocess
import sys

cache_dirs = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".venv", ".private"}
tracked = subprocess.check_output(["git", "-C", sys.argv[1], "ls-files", "-z"])
bad = []
for raw in tracked.split(b"\0"):
    if not raw:
        continue
    name = os.fsdecode(raw)
    parts = PurePosixPath(name).parts
    if (cache_dirs.intersection(parts) or name.endswith(".pyc") or parts[0] == "dist"
            or (len(parts) >= 5 and parts[:2] == ("eval", "runs") and parts[3] == "logs")):
        bad.append(name)
if bad:
    print("Forbidden tracked paths:")
    for name in bad:
        print(repr(name))
    sys.exit(1)
print("hygiene ok")
PY
