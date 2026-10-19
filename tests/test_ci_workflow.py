"""Validate the stable CI workflow required for PR merge policy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def read_workflow() -> str:
    assert WORKFLOW.is_file(), f"missing stable workflow file: {WORKFLOW}"
    return WORKFLOW.read_text()


def test_ci_workflow_file_exists() -> None:
    assert WORKFLOW.is_file(), f"missing stable workflow file: {WORKFLOW}"


def test_ci_workflow_has_stable_names() -> None:
    text = read_workflow()
    assert "name: ci" in text, "workflow name must stay 'ci' for the ruleset check"
    assert "\n  ci:" in text, "job name must stay 'ci' for the ruleset check"


def test_ci_workflow_triggers_always() -> None:
    text = read_workflow()
    assert "pull_request" in text, "workflow must trigger on pull_request"
    assert "push" in text, "workflow must trigger on push"
    assert "workflow_dispatch" in text, "workflow must trigger on workflow_dispatch"


def test_ci_workflow_runs_verification_steps() -> None:
    text = read_workflow()
    assert "ruff check" in text, "workflow must run ruff check"
    assert "ruff format" in text, "workflow must run ruff format check"
    assert "mypy" in text, "workflow must run mypy"
    assert "pytest" in text, "workflow must run pytest"
    assert "uv build" in text, "workflow must run uv build"


def test_ci_workflow_supports_media_tests() -> None:
    text = read_workflow()
    assert "ffmpeg" in text, "workflow must install ffmpeg for media tests"
    assert "playwright" in text, "workflow must install Playwright browsers"
    assert "chromium" in text, "workflow must install Chromium for media tests"


def test_ci_workflow_runs_real_cli_e2e() -> None:
    text = read_workflow()
    assert "prc explain" in text, "workflow must run a real CLI E2E render"
    assert "fixture:shop" in text, "E2E must use the offline fixture source"
    assert "shop.json" in text, "E2E must use the checked shop board"
    assert "--voice none" in text, "E2E must render silent video without voice downloads"
