"""Validate the stable CI workflow required for PR merge policy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pr.yml"
CODECOV_ACTION = "codecov/codecov-action@0fb7174895f61a3b6b78fc075e0cd60383518dac"


def read_workflow() -> str:
    assert WORKFLOW.is_file(), f"missing stable workflow file: {WORKFLOW}"
    return WORKFLOW.read_text()


def test_ci_workflow_file_exists() -> None:
    assert WORKFLOW.is_file(), f"missing stable workflow file: {WORKFLOW}"


def test_ci_workflow_has_stable_names() -> None:
    text = read_workflow()
    assert "\n  ci:" in text, "the release verification job must stay named 'ci'"
    assert "\n  gate:" in text, "job name must stay 'gate' for the ruleset check"


def test_gate_fails_when_ci_fails_or_is_cancelled() -> None:
    gate = read_workflow().split("\n  gate:", 1)[1]
    assert "if: always()" in gate, "a skipped gate counts as passing, so gate must always run"
    assert "needs: [checks, ci]" in gate, "gate must wait for the shared checks and ci"
    assert "contains(needs.*.result, 'failure')" in gate
    assert "contains(needs.*.result, 'cancelled')" in gate


def test_gate_fails_when_a_prerequisite_is_skipped() -> None:
    gate = read_workflow().split("\n  gate:", 1)[1]
    assert "contains(needs.*.result, 'skipped')" in gate, (
        "a skipped prerequisite leaves the required checks incomplete"
    )


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


def test_ci_uploads_the_existing_release_coverage_with_oidc() -> None:
    text = read_workflow()
    ci = text.split("\n  ci:", 1)[1].split("\n  gate:", 1)[0]
    assert "fetch-depth: 0" in ci, "Codecov needs the base history for patch coverage"
    assert "id-token: write" in ci, "Codecov upload must use short-lived GitHub OIDC"
    assert CODECOV_ACTION in ci, "the upload action must use the reviewed immutable pin"
    assert "use_oidc: true" in ci
    assert "files: artifacts/release/verify/run-*/coverage.xml" in ci
    assert "disable_search: true" in ci, "the upload must name its only accepted report"
    assert "fail_ci_if_error: true" in ci, "a failed upload must fail release verification"
    assert ci.index("bash scripts/verify-release.sh") < ci.index(CODECOV_ACTION), (
        "coverage upload must follow the release verifier that creates the report"
    )
