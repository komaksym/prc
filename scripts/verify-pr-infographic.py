"""Validate the Baoyu infographic bundle committed at a pull request's head."""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any


def blob(head: str, path: PurePosixPath) -> bytes:
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{head}:{path}"], capture_output=True, check=False
    )
    if result.returncode:
        raise ValueError(f"Commit {path} on the pull request branch.")
    return result.stdout


def verify(pull_request: dict[str, Any]) -> None:
    head = pull_request["head"]
    sha = head["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("The pull request head is not a Git commit SHA.")
    prefix = f"https://github.com/{head['repo']['full_name']}/blob/{head['ref']}/"
    links = re.findall(r"!\[[^\]\n]*\]\(([^\s)]+)\)", pull_request.get("body") or "")
    paths = {
        PurePosixPath(url.removeprefix(prefix).removesuffix("?raw=true"))
        for url in links
        if url.startswith(prefix)
        and re.fullmatch(
            r"(?:[\w.-]+/)*infographic\.png\?raw=true", url.removeprefix(prefix), re.ASCII
        )
    }
    if len(paths) != 1 or ".." in next(iter(paths)).parts:
        raise ValueError("Embed one infographic.png from the pull request branch with ?raw=true.")
    image = paths.pop()
    prompt = image.parent / "prompts/infographic.md"
    receipt = json.loads(blob(sha, image.parent / "provenance.json"))
    if not isinstance(receipt, dict) or receipt.get("skill") != "baoyu-infographic":
        raise ValueError("provenance.json must name the baoyu-infographic skill.")
    fields = ["purpose", "visual_note"]
    backend = receipt.get("backend")
    if backend != "codex-imagegen":
        if not isinstance(backend, str) or not re.fullmatch(r"agent-drawn-[\w-]+", backend):
            raise ValueError("provenance.json must name a supported infographic backend.")
        source = receipt.get("source")
        if source not in ("infographic.html", "infographic.svg"):
            raise ValueError("Record the committed fallback source beside infographic.png.")
        blob(sha, image.parent / source)
        fields.append("user_approval")
    for field in fields:
        value = receipt.get(field)
        if not isinstance(value, str) or len(value.strip()) < 20:
            raise ValueError(f"provenance.json needs a specific {field} of at least 20 characters.")
    created_at = datetime.fromisoformat(receipt.get("created_at", ""))
    if created_at.utcoffset() != timedelta(0):
        raise ValueError("provenance.json must use a UTC created_at timestamp.")
    image_bytes = blob(sha, image)
    if not image_bytes.startswith(bytes.fromhex("89504e470d0a1a0a")):
        raise ValueError("infographic.png must contain PNG data.")
    for field, content in (("image_sha256", image_bytes), ("prompt_sha256", blob(sha, prompt))):
        if receipt.get(field) != hashlib.sha256(content).hexdigest():
            raise ValueError(f"{field} does not match the committed artifact at {sha}.")
    print(f"Baoyu infographic receipt matches {image} and its prompt at {sha}.")


if __name__ == "__main__":
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        verify(event["pull_request"])
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"PR infographic: {error}", file=sys.stderr)
        sys.exit(1)
