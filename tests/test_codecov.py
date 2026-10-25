"""Validate Codecov reporting from the isolated release verification run."""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text())


def test_coverage_is_a_development_dependency_with_product_wide_settings() -> None:
    project = load_toml(ROOT / "pyproject.toml")
    dev = project["dependency-groups"]["dev"]
    assert any(isinstance(item, str) and item.startswith("coverage[toml]") for item in dev), (
        "coverage[toml] must remain development-only"
    )
    assert project["tool"]["coverage"]["run"] == {
        "source": ["src/prc"],
        "relative_files": True,
    }, "coverage must include unimported product modules and emit relative paths"


def test_release_verifier_uses_its_existing_pytest_run_for_one_coverage_report() -> None:
    script = (ROOT / "scripts" / "verify-release.sh").read_text()
    run = 'coverage run -m pytest -q --junitxml="$proof/tests.xml"'
    report = 'coverage xml -o "$proof/coverage.xml"'
    assert script.count("coverage run -m pytest") == 1, "reuse the one full release suite"
    assert script.count("coverage xml") == 1, "write one report for this isolated run"
    assert "uv run --offline pytest" not in script, "do not run a second full suite"
    assert run in script
    assert report in script
    assert script.index(run) < script.index(report)


def test_codecov_policy_keeps_project_informational_and_patch_at_eighty() -> None:
    text = (ROOT / "codecov.yml").read_text()
    assert "    project:\n      default:\n        informational: true\n" in text
    assert (
        "    patch:\n      default:\n        target: 80%\n        threshold: 0%\n"
        "        if_not_found: failure\n"
    ) in text


def test_transient_coverage_files_are_ignored(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
    paths = [".coverage", ".coverage.host.123", "nested/.coverage"]
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", *paths],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert set(ignored.stdout.splitlines()) == set(paths), ignored.stderr


def test_coverage_docs_name_app_baseline_and_required_check_prerequisites() -> None:
    text = (ROOT / "docs" / "coverage.md").read_text()
    assert "Codecov GitHub App" in text
    assert "GitHub OIDC" in text
    assert "artifacts/release/verify/run-*/coverage.xml" in text
    assert "baseline" in text.lower()
    assert "codecov/patch" in text
    assert "80%" in text
    assert "Browser JavaScript and CSS assets are outside the report" in text
