"""Live GitHub adapter (REST + git fetch). NOT verified against live GitHub in this repository.

Unit tests drive it through an injected transport with canned payloads; that exercises the
contract only. A real run needs ``GITHUB_TOKEN`` (read from the environment, never logged).
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prc.identity import sha256_hex
from prc.model import PrRef
from prc.source import SourceError

API = "https://api.github.com"
_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')

Transport = Callable[[str], tuple[Any, str | None]]


def urllib_transport(url: str) -> tuple[Any, str | None]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "prc-mvp"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if not url.startswith(API + "/"):
        raise SourceError("refusing non-GitHub API URL")

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed https origin
            match = _NEXT.search(response.headers.get("Link", ""))

            return json.load(response), (match.group(1) if match else None)
    except OSError as error:
        raise SourceError(f"GitHub request failed: {type(error).__name__}") from error


def git_fetch(ref: PrRef, cache: Path, base_sha: str) -> None:
    """Fetch the PR head and base objects into a bare cache. Token travels via env, not argv.

    Git smart HTTP on github.com rejects Bearer for OAuth tokens; it needs Basic x-access-token.
    """

    env = {"PATH": os.environ.get("PATH", ""), "GIT_TERMINAL_PROMPT": "0"}
    token = os.environ.get("GITHUB_TOKEN", "")

    if token:
        credential = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
            GIT_CONFIG_VALUE_0=f"Authorization: Basic {credential}",
        )

    cache.mkdir(parents=True, exist_ok=True)
    commands = [
        ["git", "init", "-q", "--bare", str(cache)],
        [
            "git", "-C", str(cache), "fetch", "-q", "--no-tags", "--no-recurse-submodules",
            f"https://github.com/{ref.owner}/{ref.repo}.git",
            f"+refs/pull/{ref.number}/head:refs/prc/head",
            f"+{base_sha}:refs/prc/base",
        ],
    ]  # fmt: skip

    for command in commands:
        completed = subprocess.run(command, capture_output=True, text=True, env=env, check=False)

        if completed.returncode != 0:
            detail = completed.stderr.strip()[-300:]

            if token:
                detail = detail.replace(token, "<redacted>")

            raise SourceError(
                f"git {command[3] if command[1] == '-C' else command[1]} failed: {detail}"
            )


@dataclass
class GitHubSource:
    cache_root: Path
    transport: Transport = urllib_transport
    fetch_objects: Callable[[PrRef, Path, str], None] = git_fetch
    label: str = "github"
    live_verified: bool = True
    _resources: dict[str, bytes] = field(default_factory=dict)

    def _pages(self, url: str) -> list[Any]:
        items: list[Any] = []
        next_url: str | None = url

        while next_url is not None:
            page, next_url = self.transport(next_url)
            items.append(page)

        return items

    def enumerate(self, ref: PrRef) -> dict[str, str]:
        if not (_NAME.match(ref.owner) and _NAME.match(ref.repo)):
            raise SourceError("invalid repository name")

        base = f"{API}/repos/{ref.owner}/{ref.repo}"
        pull, _ = self.transport(f"{base}/pulls/{ref.number}")
        head_sha = pull["head"]["sha"]
        base_tip = pull["base"]["sha"]
        resources: dict[str, bytes] = {
            "pr": json.dumps(
                {
                    "head_sha": head_sha,
                    "base_ref": pull["base"]["ref"],
                    "base_tip_sha": base_tip,
                    "title": pull.get("title") or "",
                    "body": pull.get("body") or "",
                    "author": (pull.get("user") or {}).get("login", ""),
                    "labels": sorted(label["name"] for label in pull.get("labels", [])),
                    "draft": bool(pull.get("draft")),
                    "agent_authored": any(
                        label["name"] == "agent-authored" for label in pull.get("labels", [])
                    ),
                },
                sort_keys=True,
            ).encode()
        }
        listings = []

        for page in self._pages(f"{base}/commits/{head_sha}/check-runs?per_page=100"):
            for run in dict(page)["check_runs"]:
                listings.append(
                    {
                        "run_id": str(run["id"]),
                        "attempt": 1,
                        "provider": run.get("app", {}).get("slug", "github"),
                        "name": run["name"],
                        "scope": "head_only",
                        "subject_sha": run["head_sha"],
                        "subject_kind": "commit",
                        "conclusion": run.get("conclusion") or "pending",
                        "completed_at": 0.0,
                        "expires_at": None,
                        "required": False,
                    }
                )
                output = run.get("output") or {}
                text = "\n".join(str(output.get(key) or "") for key in ("title", "summary", "text"))
                resources[f"check:{run['id']}:1"] = text.encode()

        resources["checks"] = json.dumps(listings, sort_keys=True).encode()
        self._resources = resources

        return {key: sha256_hex(body)[:16] for key, body in resources.items()}

    def fetch(self, ref: PrRef, key: str) -> bytes:
        try:
            return self._resources[key]
        except KeyError as error:
            raise SourceError(f"resource {key} was not enumerated") from error

    def repo_path(self, ref: PrRef) -> Path:
        """Ensure the pinned head and exact base tip are local; refetch whenever either is missing."""

        cache = self.cache_root / f"{ref.owner}__{ref.repo}__{ref.number}.git"
        pr = json.loads(self._resources.get("pr", b"{}"))
        wanted = [str(pr.get("head_sha", "")), str(pr.get("base_tip_sha", ""))]

        if not all(wanted):
            raise SourceError("enumerate must run before repo_path")

        if not _has_commits(cache, wanted):
            self.fetch_objects(ref, cache, wanted[1])

        return cache


def _has_commits(cache: Path, shas: list[str]) -> bool:
    if not (cache / "HEAD").exists():
        return False

    return all(
        subprocess.run(
            ["git", "-C", str(cache), "cat-file", "-e", f"{sha}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
        for sha in shas
    )
