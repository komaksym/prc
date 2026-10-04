from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from prc.gitutil import run_git, unified_diff

ZERO = "0" * 40
MARK = "\\ No newline at end of file\n"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    return tmp_path


def blob(repo: Path, data: bytes) -> str:
    return run_git(repo, "hash-object", "-w", "--stdin", input_bytes=data).decode().strip()


def test_missing_final_newline_is_marked_like_git(repo: Path) -> None:
    diff = unified_diff(repo, blob(repo, b"a\nx"), blob(repo, b"a\ny\n"))

    assert diff == f"--- a\n+++ b\n@@ -1,2 +1,2 @@\n a\n-x\n{MARK}+y\n"


def test_both_sides_without_final_newline(repo: Path) -> None:
    diff = unified_diff(repo, blob(repo, b"x"), blob(repo, b"y"))

    assert diff == f"--- a\n+++ b\n@@ -1 +1 @@\n-x\n{MARK}+y\n{MARK}"


def test_added_file_without_final_newline(repo: Path) -> None:
    assert unified_diff(repo, ZERO, blob(repo, b"x\ny")).endswith(f"+x\n+y\n{MARK}")


@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b"\r", b"\x0c", b"\x1c", b"\xe2\x80\xa8"])
def test_any_line_terminator_counts_as_a_final_newline(repo: Path, ending: bytes) -> None:
    diff = unified_diff(repo, blob(repo, b"x" + ending), blob(repo, b"y" + ending))

    assert MARK not in diff
    assert diff.splitlines()[-2:] == ["-x", "+y"]
