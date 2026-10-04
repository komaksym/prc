"""Contract test with canned payloads. This is NOT a live GitHub verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prc.github_source import API, GitHubSource
from prc.model import PrRef
from prc.source import SourceError

HEAD = "b" * 40
PULL = {
    "head": {"sha": HEAD},
    "base": {"sha": "a" * 40, "ref": "main"},
    "title": "t",
    "body": None,
    "user": {"login": "bot"},
    "labels": [{"name": "agent-authored"}],
    "draft": False,
}


def run(page: int) -> dict[str, Any]:
    return {
        "id": page,
        "name": f"check-{page}",
        "head_sha": HEAD,
        "conclusion": "success",
        "app": {"slug": "actions"},
        "output": {"title": "ok", "summary": "s", "text": None},
    }


def transport(url: str) -> tuple[Any, str | None]:
    if url.endswith("/pulls/7"):
        return PULL, None

    if "check-runs" in url and "page=2" not in url:
        return {
            "check_runs": [run(1)]
        }, f"{API}/repos/o/r/commits/{HEAD}/check-runs?per_page=100&page=2"

    if "page=2" in url:
        return {"check_runs": [run(2)]}, None

    raise AssertionError(url)


def test_enumerates_pr_and_all_check_pages(tmp_path: Path) -> None:
    source = GitHubSource(
        tmp_path, transport=transport, fetch_objects=lambda ref, cache, base: None
    )
    ref = PrRef("o", "r", 7)
    versions = source.enumerate(ref)
    checks = json.loads(source.fetch(ref, "checks"))

    assert set(versions) == {"pr", "checks", "check:1:1", "check:2:1"}
    assert [c["scope"] for c in checks] == ["head_only", "head_only"]
    assert json.loads(source.fetch(ref, "pr"))["agent_authored"] is True


def test_rejects_invalid_names_and_unenumerated_keys(tmp_path: Path) -> None:
    source = GitHubSource(
        tmp_path, transport=transport, fetch_objects=lambda ref, cache, base: None
    )

    with pytest.raises(SourceError):
        source.enumerate(PrRef("o/../x", "r", 7))

    with pytest.raises(SourceError):
        source.fetch(PrRef("o", "r", 7), "trace")


def test_git_auth_header_uses_basic_x_access_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import base64
    import subprocess

    from prc import github_source

    seen: list[dict[str, str]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append(kwargs["env"])

        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    monkeypatch.setattr(subprocess, "run", fake_run)
    github_source.git_fetch(PrRef("o", "r", 1), tmp_path / "c.git", "a" * 40)
    expected = "Authorization: Basic " + base64.b64encode(b"x-access-token:tok123").decode()

    assert all(env["GIT_CONFIG_VALUE_0"] == expected for env in seen)


def test_failed_fetch_is_source_error_without_token_and_is_retried(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import subprocess

    calls: list[list[str]] = []

    def failing_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)

        if "fetch" in args:
            return subprocess.CompletedProcess(args, 128, "", "fatal: auth failed for tok123")

        if "cat-file" in args:
            return subprocess.CompletedProcess(args, 1, "", "")

        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    monkeypatch.setattr(subprocess, "run", failing_run)
    source = GitHubSource(tmp_path, transport=transport)
    ref = PrRef("o", "r", 7)
    source.enumerate(ref)

    with pytest.raises(SourceError) as raised:
        source.repo_path(ref)

    assert "tok123" not in str(raised.value)

    with pytest.raises(SourceError):
        source.repo_path(ref)

    assert sum("fetch" in args for args in calls) == 2


def test_refetches_when_pinned_commits_are_missing(tmp_path: Path) -> None:
    fetched: list[str] = []
    source = GitHubSource(
        tmp_path, transport=transport, fetch_objects=lambda ref, cache, base: fetched.append(base)
    )
    ref = PrRef("o", "r", 7)
    source.enumerate(ref)
    source.repo_path(ref)
    source.repo_path(ref)

    assert fetched == ["a" * 40, "a" * 40]
