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


def test_ci_workflow_runs_release_verification() -> None:
    text = read_workflow()
    assert "scripts/verify-release.sh" in text, (
        "workflow must run the isolated release verifier that owns "
        "lint, mypy, tests, build, and real CLI E2E"
    )


def test_ci_workflow_supports_media_tests() -> None:
    text = read_workflow()
    assert "ffmpeg" in text, "workflow must install ffmpeg for media tests"
    assert "playwright" in text, "workflow must install Playwright browsers"
    assert "chromium" in text, "workflow must install Chromium for media tests"


def test_ci_workflow_avoids_duplicated_e2e() -> None:
    text = read_workflow()
    assert "prc explain" not in text, (
        "workflow must not duplicate the CLI E2E owned by verify-release.sh"
    )


def test_ci_workflow_has_permissions_timeout_evidence() -> None:
    text = read_workflow()
    assert "permissions:" in text, "workflow must declare minimal permissions"
    assert "contents: read" in text, "workflow must restrict to read contents"
    assert "timeout-minutes" in text, "workflow must bound the job runtime"
    assert "upload-artifact" in text, "workflow must upload verify logs as evidence"


def test_ci_runner_supports_zero_skip_ocr_checks() -> None:
    text = read_workflow()
    assert "runs-on: macos-latest" in text, "release OCR tests require macOS sips"
    assert "brew install ffmpeg tesseract" in text, "release tests require OCR tools"


def test_ci_prepares_locked_wheel_cache_before_offline_verification() -> None:
    text = read_workflow()
    assert "uv export --frozen --extra video" in text
    assert "--no-dev --no-emit-project --no-hashes" in text
    assert "uv pip install --python" in text
    assert "--constraint" in text
    assert text.index("uv pip install --python") < text.index("bash scripts/verify-release.sh")
