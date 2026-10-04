"""End to end `prc brief` through the CLI. Leaves a repeatable artifact in artifacts/e2e/briefs/."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "e2e" / "briefs"


def brief_cli(*args: str, cwd: Path = ROOT) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "prc.cli", "brief", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    result: dict[str, Any] = json.loads(completed.stdout)

    return result


def test_claims_fixture_brief_is_computed_safe_and_repeatable(tmp_path: Path) -> None:
    shutil.rmtree(ARTIFACT, ignore_errors=True)
    store, out = str(ARTIFACT / "store"), str(ARTIFACT / "out")
    first = brief_cli("--source", "fixture:claims", "--store", store, "--out", out)

    assert first["source"] == "fixture" and first["live_verified"] is False

    path = Path(first["brief"])
    text = path.read_text()
    data = json.loads((path.parent / "brief.json").read_text())

    assert text.startswith("<!-- prc-brief -->\n")
    assert path.parent.name == first["snapshot_id"].rsplit(":", 1)[-1][:16]
    assert not (ARTIFACT / "store" / "prc.sqlite").exists()

    found = {(m["kind"], tuple(m["subjects"])) for m in data["mismatches"]}

    assert found == {
        ("changed_claim_not_in_diff", ("README.md",)),
        ("tests_claim_no_test_files", ()),
        ("test_claim_vs_ci", ("unit-tests",)),
    }
    assert first["mismatches"] == 3

    mismatch_text = json.dumps(data["mismatches"])

    for ignored in ("secret.py", "ghost.py", "hidden.py", "docs/guide.md", "with_retry"):
        assert ignored not in mismatch_text

    files = {f["path"]: f for f in data["files"]}
    unnamed = {p for p, f in files.items() if f["kind"] in ("code", "config") and not f["named"]}

    assert unnamed == {"src/config.py", ".github/workflows/ci.yml", "pyproject.toml"}
    assert files["uv.lock"]["kind"] == "generated"
    assert "uv.lock" not in json.dumps(data["look_first"])
    assert "uv.lock" not in text
    assert set(first["look_first"][:2]) == {".github/workflows/ci.yml", "pyproject.toml"}
    assert first["look_first"][2] == "src/app.py"
    assert "Not named in the description" not in text

    for line in text.splitlines():
        outside = re.sub(r"`[^`]*`", "", line)

        assert "@maintainer" not in outside and "<script" not in outside and "![" not in outside

    assert "![" not in text and "<script" not in text

    again = brief_cli("--source", "fixture:claims", "--store", store, "--out", out)

    assert again == first and path.read_text() == text

    fresh = brief_cli(
        "--source", "fixture:claims", "--store", str(tmp_path / "s"), "--out", str(tmp_path / "o")
    )  # fmt: skip

    assert Path(fresh["brief"]).read_bytes() == path.read_bytes()


def test_default_paths_work_from_any_directory(tmp_path: Path) -> None:
    brief_cli("--source", "fixture:basic", cwd=tmp_path)

    assert any((tmp_path / "artifacts" / "briefs").glob("*/brief.md"))
    assert not (tmp_path / "artifacts" / "store" / "prc.sqlite").exists()
