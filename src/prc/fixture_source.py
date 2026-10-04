"""Deterministic local fixtures. Everything here is labelled ``fixture``, never live GitHub."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from prc.gitutil import merge_tree
from prc.identity import sha256_hex
from prc.model import PrRef
from prc.source import SourceError

FIXTURE_EPOCH = 1_760_000_000.0
Entry = tuple[str, bytes]  # (mode, content); mode 100644/100755/120000 or "160000" with hex oid
ZERO_DATE = "2026-10-01T00:00:00+0000"


@dataclass
class FixtureSource:
    """PullRequestSource backed by in-memory resources and a real local git repo."""

    repo: Path
    resources: dict[str, bytes]
    label: str = "fixture"
    live_verified: bool = False
    drift: Callable[[int, dict[str, bytes]], None] | None = None
    fail_fetch_keys: set[str] = field(default_factory=set)
    enumerate_calls: int = 0

    def enumerate(self, ref: PrRef) -> dict[str, str]:
        self.enumerate_calls += 1

        if self.drift is not None:
            self.drift(self.enumerate_calls, self.resources)

        return {key: sha256_hex(body)[:16] for key, body in self.resources.items()}

    def fetch(self, ref: PrRef, key: str) -> bytes:
        if key in self.fail_fetch_keys or key not in self.resources:
            raise SourceError(f"fetch failed for {key}")

        return self.resources[key]

    def repo_path(self, ref: PrRef) -> Path:
        return self.repo


def _git(
    repo: Path, *args: str, stdin: bytes | None = None, extra_env: dict[str, str] | None = None
) -> str:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": ZERO_DATE,
        "GIT_COMMITTER_DATE": ZERO_DATE,
        **(extra_env or {}),
    }
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], input=stdin, capture_output=True, env=env, check=True
    )

    return completed.stdout.decode().strip()


def commit_tree(repo: Path, files: dict[str, Entry], parents: list[str]) -> str:
    """Write a commit from in-memory entries using plumbing only (deterministic SHAs)."""

    index_lines: list[bytes] = []

    for path, (mode, content) in sorted(files.items()):
        if mode == "160000":
            oid = content.decode()
        else:
            oid = _git(repo, "hash-object", "-w", "--stdin", stdin=content)

        index_lines.append(f"{mode} {oid}\t{path}\n".encode())

    index_file = repo / "fixture.index"
    index_file.unlink(missing_ok=True)
    env = {"GIT_INDEX_FILE": str(index_file)}

    try:
        _git(
            repo,
            "update-index",
            "--add",
            "--index-info",
            stdin=b"".join(index_lines),
            extra_env=env,
        )
        tree = _git(repo, "write-tree", extra_env=env)
    finally:
        index_file.unlink(missing_ok=True)

    parent_args = [arg for parent in parents for arg in ("-p", parent)]

    return _git(repo, "commit-tree", tree, *parent_args, "-m", "fixture commit")


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)

    if not (path / "HEAD").exists():
        subprocess.run(["git", "init", "-q", "--bare", str(path)], check=True)

    return path


def build_source(
    repo_dir: Path,
    base_files: dict[str, Entry],
    head_files: dict[str, Entry],
    metadata: dict[str, object],
    checks: Callable[[str, str, str, str | None], list[dict[str, object]]],
    check_payloads: dict[str, str],
    trace: list[dict[str, object]] | None,
    advanced_base_files: dict[str, Entry] | None = None,
) -> tuple[FixtureSource, PrRef]:
    """Create a base/head pair in a real bare repo and assemble provider resources."""

    repo = init_repo(repo_dir)
    root = commit_tree(repo, {"README.md": ("100644", b"root\n")}, [])
    branch_point = commit_tree(repo, base_files, [root])
    head = commit_tree(repo, head_files, [branch_point])
    base_tip = (
        branch_point
        if advanced_base_files is None
        else commit_tree(repo, advanced_base_files, [branch_point])
    )
    merged_tree = merge_tree(repo, base_tip, head)
    pr = {
        "head_sha": head,
        "base_ref": "main",
        "base_tip_sha": base_tip,
        **metadata,
    }
    listings = checks(head, base_tip, merged_tree or "", merged_tree)
    resources: dict[str, bytes] = {
        "pr": json.dumps(pr, sort_keys=True).encode(),
        "checks": json.dumps(listings, sort_keys=True).encode(),
    }

    for listing in listings:
        key = f"check:{listing['run_id']}:{listing['attempt']}"
        resources[key] = check_payloads.get(str(listing["name"]), "ok\n").encode()

    if trace is not None:
        resources["trace"] = json.dumps(trace, sort_keys=True).encode()

    return FixtureSource(repo=repo, resources=resources), PrRef("fixture-org", "demo", 1)
