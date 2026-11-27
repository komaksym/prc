import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "verify-pr-infographic.py"
PREFIX = "https://github.com/example/prc/blob/feature/visual/"
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
        ("wrong-host", "Embed one"),
        ("screenshot-only", "Embed one"),
        ("encoded-ref", ""),
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
    git("add", "visual")
    git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "test")
    if case == "uncommitted-replacement":
        (folder / "infographic.png").write_bytes(IMAGE + b"later")
    url = PREFIX + "visual/infographic.png?raw=true"
    ref = "feature/visual"
    if case == "encoded-ref":
        ref += "#1"
        url = url.replace("feature/visual/", "feature/visual%231/")
    if case == "wrong-host":
        url = "https://example.com/" + url
    body = (
        f"![Overview]({url})"
        if case != "screenshot-only"
        else f"![Page]({PREFIX}page.png?raw=true)"
    )
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "pull_request": {
                    "body": body,
                    "head": {
                        "ref": ref,
                        "sha": git("rev-parse", "HEAD"),
                        "repo": {"full_name": "example/prc"},
                    },
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
