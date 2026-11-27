"""Contract test with canned payloads. This is NOT a live GitHub verification."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from email.message import Message
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from prc.github_source import API, GitHubSource, urllib_transport
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


class UnreadBody(BytesIO):
    def read(self, size: int | None = -1) -> bytes:
        raise AssertionError("HTTP error bodies must not be read")


@pytest.mark.parametrize(
    ("status", "remaining", "message"),
    [
        (
            404,
            None,
            "pull request or resource is missing or inaccessible. "
            "Check the repository, PR number, and access permissions.",
        ),
        (
            401,
            None,
            "authentication was rejected. Check GITHUB_TOKEN credentials and repository access.",
        ),
        (
            403,
            None,
            "request forbidden. Check GITHUB_TOKEN credentials and repository permissions.",
        ),
        (
            403,
            "1",
            "request forbidden. Check GITHUB_TOKEN credentials and repository permissions.",
        ),
        (
            403,
            "0",
            "API rate limit exceeded. Wait for the rate limit to reset before retrying.",
        ),
        (
            429,
            None,
            "API rate limit exceeded. Wait for the rate limit to reset before retrying.",
        ),
        (
            500,
            "0",
            "request failed. Check the request and retry if the failure is temporary.",
        ),
    ],
)
def test_http_error_preserves_status_and_safe_actionable_context(
    status: int, remaining: str | None, message: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = Message()
    if remaining is not None:
        headers["x-ratelimit-remaining"] = remaining
    body = UnreadBody(b"untrusted response content")
    error = urllib.error.HTTPError(
        API + "/repos/o/r/pulls/999999", status, "untrusted server reason", headers, body
    )
    open_url = Mock(side_effect=error)
    monkeypatch.setattr(urllib.request, "urlopen", open_url)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-credential")

    with pytest.raises(SourceError) as raised:
        urllib_transport(API + "/repos/o/r/pulls/999999")

    assert str(raised.value) == f"GitHub HTTP {status}: {message}"
    assert raised.value.__cause__ is error
    assert body.tell() == 0
    assert "synthetic-credential" not in str(raised.value)
    assert "untrusted" not in str(raised.value)
    open_url.assert_called_once()


@pytest.mark.parametrize("error", [urllib.error.URLError("untrusted details"), TimeoutError()])
def test_network_error_has_safe_actionable_context(
    error: OSError, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", Mock(side_effect=error))
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-credential")

    with pytest.raises(SourceError) as raised:
        urllib_transport(API + "/repos/o/r/pulls/999999")

    assert str(raised.value) == (
        f"GitHub network request failed: {type(error).__name__}. "
        "Check your network connection and retry."
    )
    assert raised.value.__cause__ is error


def test_non_github_url_is_rejected_before_http_request(monkeypatch: pytest.MonkeyPatch) -> None:
    open_url = Mock(side_effect=AssertionError("an untrusted origin must not be requested"))
    monkeypatch.setattr(urllib.request, "urlopen", open_url)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-credential")

    with pytest.raises(SourceError, match="refusing non-GitHub API URL"):
        urllib_transport("https://example.com/repos/o/r/pulls/999999")

    open_url.assert_not_called()
