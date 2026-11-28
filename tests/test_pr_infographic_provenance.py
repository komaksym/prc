import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "verify-pr-infographic.py"
IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgAAIAAAUAAXpeqz8AAAAASUVORK5CYII="
)
PROMPT = b"Draw the release workflow."


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("valid", ""),
        ("missing-receipt", "provenance.json"),
        ("wrong-skill", "baoyu-infographic"),
        ("wrong-image-hash", "image_sha256"),
        ("wrong-prompt-hash", "prompt_sha256"),
        ("missing-declaration", "pr-infographic.json"),
        ("inherited-declaration", "PR number 15"),
        ("float-pr-number", "PR number 15"),
        ("invalid-path", "infographic.png"),
        ("edited-description", ""),
        ("different-base", ""),
        ("truncated-png", "complete PNG"),
        ("uncommitted-replacement", "image_sha256"),
    ],
)
def test_pr_infographic_checks_the_committed_artifacts(
    tmp_path: Path, case: str, error: str
) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "base",
        "--allow-empty",
    )
    folder = tmp_path / "visual"
    (folder / "prompts").mkdir(parents=True)
    image = IMAGE[:-12] if case == "truncated-png" else IMAGE
    (folder / "infographic.png").write_bytes(image)
    (folder / "prompts/infographic.md").write_bytes(PROMPT)
    receipt = {
        "skill": "baoyu-infographic",
        "backend": "codex-imagegen",
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "prompt_sha256": hashlib.sha256(PROMPT).hexdigest(),
        "purpose": "Shows how release checks reach the gate.",
        "visual_note": "The image reads Release checks and Gate.",
        "created_at": "2026-11-27T15:00:00Z",
    }
    if case == "wrong-skill":
        receipt["skill"] = "another-skill"
    if case in {"wrong-image-hash", "uncommitted-replacement"}:
        receipt["image_sha256"] = hashlib.sha256(IMAGE + b"later").hexdigest()
    if case == "wrong-prompt-hash":
        receipt["prompt_sha256"] = "0" * 64
    if case != "missing-receipt":
        (folder / "provenance.json").write_text(json.dumps(receipt))
    (tmp_path / ".github").mkdir()
    if case != "missing-declaration":
        declared = (
            "../visual/infographic.png" if case == "invalid-path" else "visual/infographic.png"
        )
        number = {"inherited-declaration": 14, "float-pr-number": 15.0}.get(case, 15)
        (tmp_path / ".github/pr-infographic.json").write_text(
            json.dumps({"number": number, "path": declared})
        )
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "test")
    base = "1" * 40 if case == "different-base" else git("rev-parse", "HEAD^")
    if case == "uncommitted-replacement":
        (folder / "infographic.png").write_bytes(IMAGE + b"later")
    body = "Description changed" if case == "edited-description" else ""
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "pull_request": {
                    "number": 15,
                    "body": body,
                    "head": {"sha": git("rev-parse", "HEAD")},
                    "base": {"sha": base},
                }
            }
        )
    )
    done = subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_EVENT_PATH": str(event)},
        capture_output=True,
        text=True,
        check=False,
    )
    if error:
        assert done.returncode == 1
        assert error in done.stderr
    else:
        assert done.returncode == 0, done.stderr
