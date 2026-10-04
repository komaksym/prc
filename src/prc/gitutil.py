"""Read-only plumbing over a local git repository.

Only object-database plumbing is used (no checkout, no worktree), so repository
hooks, attributes and filters never execute on untrusted content.
"""

from __future__ import annotations

import difflib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "LC_ALL": "C",
}


class GitError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TreeChange:
    status: str
    old_mode: str
    new_mode: str
    old_oid: str
    new_oid: str
    path: str


def run_git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_bytes,
        capture_output=True,
        env={"PATH": os.environ.get("PATH", ""), **_ENV},
        check=False,
    )

    if completed.returncode != 0:
        raise GitError(f"git {args[0]} failed: {completed.stderr.decode(errors='replace')[:200]}")

    return completed.stdout


def rev_parse(repo: Path, rev: str) -> str:
    return run_git(repo, "rev-parse", "--verify", "--end-of-options", rev).decode().strip()


def merge_base(repo: Path, left: str, right: str) -> str:
    return run_git(repo, "merge-base", left, right).decode().strip()


def tree_of(repo: Path, rev: str) -> str:
    return rev_parse(repo, f"{rev}^{{tree}}")


def merge_tree(repo: Path, base_tip: str, head: str) -> str | None:
    """Tree of the hypothetical merge of head into base tip, or None on conflict."""

    try:
        return run_git(repo, "merge-tree", "--write-tree", base_tip, head).decode().split()[0]
    except GitError:
        return None


def tree_delta(repo: Path, old_commit: str, new_commit: str) -> list[TreeChange]:
    """Complete recursive tree delta without rename detection or size limits."""

    raw = run_git(
        repo,
        "diff-tree",
        "-r",
        "-z",
        "--raw",
        "--no-renames",
        "--no-abbrev",
        "--root",
        old_commit,
        new_commit,
    )
    fields = raw.split(b"\x00")
    changes: list[TreeChange] = []
    cursor = 0

    while cursor < len(fields) and fields[cursor]:
        header = fields[cursor].decode()
        path = fields[cursor + 1].decode("utf-8", errors="surrogateescape")
        old_mode, new_mode, old_oid, new_oid, status = header.lstrip(":").split(" ")
        changes.append(TreeChange(status[0], old_mode, new_mode, old_oid, new_oid, path))
        cursor += 2

    return changes


def read_blob(repo: Path, oid: str) -> bytes:
    return run_git(repo, "cat-file", "blob", oid)


def blob_size(repo: Path, oid: str) -> int:
    return int(run_git(repo, "cat-file", "-s", oid).decode().strip())


def unified_diff(repo: Path, old_oid: str, new_oid: str) -> str:
    """Text diff between two blob ids; empty ids denote an absent side."""

    zero = "0" * 40
    old_text = "" if old_oid == zero else read_blob(repo, old_oid).decode("utf-8", "replace")
    new_text = "" if new_oid == zero else read_blob(repo, new_oid).decode("utf-8", "replace")

    return "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile="a",
            tofile="b",
            n=3,
        )
    )


def list_paths(repo: Path, commit: str) -> tuple[str, ...]:
    raw = run_git(repo, "ls-tree", "-r", "--name-only", "-z", commit)

    return tuple(
        name.decode("utf-8", errors="surrogateescape") for name in raw.split(b"\x00") if name
    )
