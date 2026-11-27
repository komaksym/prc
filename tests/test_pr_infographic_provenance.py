import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "verify-pr-infographic.py"
PREFIX = "https://github.com/example/prc/blob/feature/visual/"
IMAGE = bytes.fromhex("89504e470d0a1a0a") + b"image"
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
    (folder / "infographic.png").write_bytes(IMAGE)
    (folder / "prompts/infographic.md").write_bytes(PROMPT)
    receipt = {
        "skill": "baoyu-infographic",
        "backend": "codex-imagegen",
        "image_sha256": hashlib.sha256(IMAGE).hexdigest(),
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
                        "ref": "feature/visual",
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
