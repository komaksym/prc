"""Narrow hygiene guard for tracked caches, pyc, eval run logs, private."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tracked_files_via_git() -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    sep = bytes([0])
    return [os.fsdecode(c) for c in proc.stdout.split(sep) if c]


def is_forbidden(path: str) -> bool:
    if path.endswith(".pyc"):
        return True
    parts = Path(path).parts
    if "__pycache__" in parts:
        return True
    if parts and parts[0] in {".mypy_cache", ".ruff_cache", ".pytest_cache", ".venv", "dist"}:
        return True
    if parts and parts[0] == ".private":
        return True
    if "/.private/" in ("/" + path + "/"):
        return True
    return len(parts) >= 4 and parts[0] == "eval" and parts[1] == "runs" and parts[3] == "logs"


def test_hygiene_guard_no_forbidden_tracked_files() -> None:
    tracked = tracked_files_via_git()
    bad = sorted(p for p in tracked if is_forbidden(p))
    assert not bad, "forbidden tracked"
