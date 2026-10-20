"""Exercise the shipped hygiene command against real Git indexes."""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-hygiene.sh"


@pytest.mark.parametrize(
    "name", ["notes.md", "docs/.private-policy.md", "docs/__pycache__-guide.md", "docs/safe.pyc.md"]
)
def test_accepts_source_and_notes(tmp_path: Path, name: str) -> None:
    run_guard(tmp_path, name, expected=0)


@pytest.mark.parametrize(
    "name",
    [
        ".private/notes.md",
        "pkg/__pycache__/mod.pyc",
        ".mypy_cache/meta.json",
        "pkg/.ruff_cache/cache",
        ".pytest_cache/cache",
        ".venv/bin/python",
        "dist/app.whl",
        "eval/runs/check/logs/job.json",
        "line\nbreak.pyc",
    ],
)
def test_rejects_tracked_generated_and_private_files(tmp_path: Path, name: str) -> None:
    run_guard(tmp_path, name, expected=1)


def run_guard(repo: Path, name: str, expected: int) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "scripts").mkdir()
    shutil.copyfile(SCRIPT, repo / "scripts/check-hygiene.sh")
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("test data\n")
    subprocess.run(["git", "-C", str(repo), "add", "--force", "--", name], check=True)
    result = subprocess.run(
        ["bash", str(repo / "scripts/check-hygiene.sh")], capture_output=True, text=True
    )
    assert result.returncode == expected, result.stdout + result.stderr
