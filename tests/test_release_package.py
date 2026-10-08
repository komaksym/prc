"""Check the published source archive, including untracked local files."""

from __future__ import annotations

import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_failed_release_runs_keep_separate_evidence(tmp_path: Path) -> None:
    import os

    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts/verify-release.sh"
    script.write_bytes((ROOT / "scripts/verify-release.sh").read_bytes())
    test = root / "tests/test_card_receipts.py"
    test.parent.mkdir()
    test.write_text('"""Release regression sentinel."""\n')
    for name in ("eval/runs/2026-10-06-full", "docs/media"):
        (root / name).mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "scripts"], check=True)
    commands = tmp_path / "bin"
    commands.mkdir()
    uv = commands / "uv"
    uv.write_text("#!/bin/sh\necho stopped-before-sync >&2\nexit 17\n")
    uv.chmod(0o755)
    env = {**os.environ, "PATH": f"{commands}:{os.environ['PATH']}"}
    proof = root / "artifacts/release/verify"
    for _ in range(2):
        result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
        assert result.returncode == 17, result.stderr
    logs = list(proof.rglob("sync.log"))
    assert len(logs) == 2, f"expected two preserved run logs, found {logs}"
    assert all("stopped-before-sync" in log.read_text() for log in logs)
    for path in proof.glob("run-*/checkout.txt"):
        checkout = Path(path.read_text().strip())
        assert (checkout / "tests/test_card_receipts.py").read_text() == test.read_text()
    assert not (proof / "latest-success.txt").exists()


def test_generated_eval_audio_stays_out_of_git(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
    paths = [
        "eval/runs/release/outputs/pr12/narration.wav",
        "eval/runs/release/outputs/pr12/audio/0.wav",
    ]
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", *paths],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert set(ignored.stdout.splitlines()) == set(paths), ignored.stdout


def test_installed_video_extra_can_use_the_available_browser(tmp_path: Path) -> None:
    build = subprocess.run(
        ["uv", "build", "--offline", "--wheel", "--out-dir", str(tmp_path / "dist")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    env = tmp_path / "env"
    subprocess.run(["uv", "venv", "--python", sys.executable, str(env)], check=True)
    wheel = next((tmp_path / "dist").glob("prc-*.whl"))
    installed = subprocess.run(
        ["uv", "pip", "install", "--offline", "--python", str(env / "bin/python"),
         f"{wheel}[video]"],
        capture_output=True,
        text=True,
        check=False,
    )  # fmt: skip
    assert installed.returncode == 0, installed.stderr
    doctor = subprocess.run(
        [str(env / "bin/prc"), "doctor"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    proof = ROOT / "artifacts/e2e/wheel"
    proof.mkdir(parents=True, exist_ok=True)
    (proof / "doctor.log").write_text(doctor.stdout + doctor.stderr)
    assert doctor.returncode == 0, doctor.stderr
    assert "chromium ok" in doctor.stdout, doctor.stdout


def test_source_archive_contains_only_release_files(tmp_path: Path) -> None:
    build = subprocess.run(
        ["uv", "build", "--offline", "--sdist", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    archive = next(tmp_path.glob("prc-*.tar.gz"))
    with tarfile.open(archive) as source:
        paths = {
            Path(member.name).relative_to(source.getmembers()[0].name.split("/")[0]).as_posix()
            for member in source.getmembers()
            if member.isfile()
        }
    metadata = {
        "PKG-INFO",
        "pyproject.toml",
        "README.md",
        "uv.lock",
        ".python-version",
        ".gitignore",
    }
    unexpected = {
        path for path in paths if path not in metadata and not path.startswith("src/prc/")
    }
    assert not unexpected, sorted(unexpected)[:20]
    assert {"pyproject.toml", "README.md", "src/prc/cli.py"} <= paths
    assert {
        "src/prc/explainer/assets/engine.js",
        "src/prc/explainer/assets/engine.css",
        "src/prc/explainer/assets/doc.css",
        "src/prc/explainer/assets/BOARD.md",
        "src/prc/presentation/assets/card.html",
        "src/prc/presentation/map_assets/map.js",
        "src/prc/presentation/map_assets/map.css",
        "src/prc/skill/SKILL.md",
    } <= paths
