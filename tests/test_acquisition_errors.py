from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest

from prc.fixture_source import FixtureSource
from prc.github_source import GitHubSource
from prc.model import PrRef
from prc.pipeline import _acquire_brief
from prc.source import SourceError
from prc.verification import EligibilityPolicy

from conftest import FakeClock

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "artifacts" / "trust-acquisition" / "offline"
RATE_LIMIT = "GitHub API rate limit exceeded (HTTP 403)"
NOT_FOUND = "GitHub pull request not found (HTTP 404)"
TIMEOUT = "GitHub request failed: TimeoutError"
Make = Callable[[str], tuple[FixtureSource, PrRef]]


@pytest.mark.parametrize(
    ("stage", "message"),
    [("enumerate", RATE_LIMIT), ("fetch", TIMEOUT), ("reread", NOT_FOUND)],
)
def test_failed_capture_preserves_source_error_before_repo_path(
    stage: str, message: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, clock: FakeClock
) -> None:
    source = GitHubSource(tmp_path)
    versions = {"pr": "v1", "checks": "v1"}
    enumerate_call = Mock(return_value=versions)
    fetch = Mock(side_effect=lambda ref, key: b"{}" if key == "pr" else b"[]")
    if stage == "enumerate":
        enumerate_call.side_effect = SourceError(message)
    elif stage == "fetch":
        fetch.side_effect = SourceError(message)
    else:
        enumerate_call.side_effect = [versions, *[SourceError(message) for _ in range(3)]]
    repo_path = Mock(side_effect=AssertionError("repo_path must not run after capture failure"))
    monkeypatch.setattr(source, "enumerate", enumerate_call)
    monkeypatch.setattr(source, "fetch", fetch)
    monkeypatch.setattr(source, "repo_path", repo_path)

    with pytest.raises(SourceError, match=re.escape(message)):
        _acquire_brief(source, PrRef("o", "r", 999999), clock, EligibilityPolicy())

    repo_path.assert_not_called()
    assert enumerate_call.call_count == (4 if stage == "reread" else 3)


def test_missing_required_resources_stop_before_repo_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, clock: FakeClock
) -> None:
    source = GitHubSource(tmp_path)
    monkeypatch.setattr(source, "enumerate", Mock(return_value={"pr": "v1"}))
    repo_path = Mock(side_effect=AssertionError("repo_path must not run for an incomplete capture"))
    monkeypatch.setattr(source, "repo_path", repo_path)

    with pytest.raises(SourceError, match="required resources missing"):
        _acquire_brief(source, PrRef("o", "r", 999999), clock, EligibilityPolicy())

    repo_path.assert_not_called()


def test_persistent_drift_stops_before_repo_path(
    make_source: Make, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, ref = make_source("basic")

    def drift(call: int, resources: dict[str, bytes]) -> None:
        resources["trace"] = str(call).encode()

    source.drift = drift
    repo_path = Mock(side_effect=AssertionError("repo_path must not run for an unstable capture"))
    monkeypatch.setattr(source, "repo_path", repo_path)

    with pytest.raises(SourceError, match="drift detected"):
        _acquire_brief(source, ref, clock, EligibilityPolicy())

    repo_path.assert_not_called()


def test_transient_source_error_can_recover(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")

    def fail_once(call: int, resources: dict[str, bytes]) -> None:
        if call == 1:
            raise SourceError(RATE_LIMIT)

    source.drift = fail_once
    acquisition, repo, brief = _acquire_brief(source, ref, clock, EligibilityPolicy())

    assert acquisition.snapshot.consistency == "stable"
    assert repo == source.repo
    assert brief.files


@pytest.mark.parametrize("command", ["brief", "explain", "board"])
@pytest.mark.parametrize("message", [RATE_LIMIT, NOT_FOUND, TIMEOUT])
def test_cli_source_error_is_nonzero_without_traceback(
    command: str, message: str, tmp_path: Path
) -> None:
    _check_cli_failure(command, message, tmp_path, "enumerate")


def test_cli_checkout_source_error_is_nonzero_without_traceback(tmp_path: Path) -> None:
    _check_cli_failure("explain", "git fetch failed: remote unavailable", tmp_path, "checkout")


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (
            404,
            "GitHub HTTP 404: pull request or resource is missing or inaccessible. "
            "Check the repository, PR number, and access permissions.",
        ),
        (
            403,
            "GitHub HTTP 403: API rate limit exceeded. "
            "Wait for the rate limit to reset before retrying.",
        ),
    ],
)
def test_cli_http_error_keeps_status_and_context_before_repo_path(
    status: int, message: str, tmp_path: Path
) -> None:
    _check_cli_failure("explain", message, tmp_path, f"http-{status}")


def _check_cli_failure(command: str, message: str, tmp_path: Path, stage: str) -> None:
    args = [command, *(["show"] if command == "board" else [])]
    args += ["--source", "https://github.com/o/r/pull/999999", "--store", str(tmp_path / "store")]
    if command != "board":
        args += ["--out", str(tmp_path / "out")]
    script = """
import runpy
import sys
from email.message import Message
from urllib.error import HTTPError
from unittest.mock import patch
from prc.github_source import GitHubSource
from prc.source import SourceError
stage, message, *args = sys.argv[1:]
sys.argv = ["prc", *args]
with patch("socket.create_connection", side_effect=AssertionError("offline test used the network")):
    if stage == "enumerate":
        with patch.object(GitHubSource, "enumerate", side_effect=SourceError(message)), \\
             patch.object(GitHubSource, "repo_path", side_effect=AssertionError("repo_path called after capture failure")):
            runpy.run_module("prc.cli", run_name="__main__")
    elif stage.startswith("http-"):
        status = int(stage.removeprefix("http-"))
        headers = Message()
        if status == 403:
            headers["x-ratelimit-remaining"] = "0"
        error = HTTPError("https://api.github.com/repos/o/r/pulls/999999", status, "ignored reason", headers, None)
        with patch("urllib.request.urlopen", side_effect=error), \\
             patch.object(GitHubSource, "repo_path", side_effect=AssertionError("repo_path called after capture failure")):
            runpy.run_module("prc.cli", run_name="__main__")
    else:
        with patch.object(GitHubSource, "enumerate", return_value={"pr": "v1", "checks": "v1"}), \\
             patch.object(GitHubSource, "fetch", return_value=b"{}"), \\
             patch.object(GitHubSource, "repo_path", side_effect=SourceError(message)):
            runpy.run_module("prc.cli", run_name="__main__")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, stage, message, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    PROOF.mkdir(parents=True, exist_ok=True)
    case = message.rsplit(":", 1)[-1].strip().replace(" ", "-").replace("(", "").replace(")", "")
    (PROOF / f"{command}-{stage}-{case}.json").write_text(
        json.dumps(
            {
                "mode": "offline injected SourceError",
                "command": command,
                "stage": stage,
                "source_error": message,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert message in completed.stderr
    assert completed.stderr.startswith("prc:")
    assert "Traceback" not in completed.stderr
    assert "repo_path" not in completed.stderr
    assert not (tmp_path / "out").exists()
