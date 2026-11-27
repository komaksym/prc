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
from urllib.parse import quote
from zlib import crc32


def blob(head: str, path: PurePosixPath) -> bytes:
    result = subprocess.run(
        ["git", "cat-file", "blob", f"{head}:{path}"], capture_output=True, check=False
    )
    if result.returncode:
        raise ValueError(f"Commit {path} on the pull request branch.")
    return result.stdout


def complete_png(image: bytes) -> bool:
    signature = bytes.fromhex("89504e470d0a1a0a")
    if not image.startswith(signature):
        return False
    offset = len(signature)
    seen_data = False
    while offset + 12 <= len(image):
        length = int.from_bytes(image[offset : offset + 4])
        chunk_type = image[offset + 4 : offset + 8]
        data_end = offset + 8 + length
        end = data_end + 4
        if end > len(image) or crc32(image[offset + 4 : data_end]) != int.from_bytes(
            image[data_end:end]
        ):
            return False
        if offset == len(signature):
            if chunk_type != b"IHDR" or length != 13:
                return False
            header = image[offset + 8 : data_end]
            if not int.from_bytes(header[:4]) or not int.from_bytes(header[4:8]):
                return False
        elif chunk_type == b"IHDR":
            return False
        if chunk_type == b"IDAT" and length:
            seen_data = True
        if chunk_type == b"IEND":
            return seen_data and length == 0 and end == len(image)
        offset = end
    return False


def verify(pull_request: dict[str, Any]) -> None:
    head = pull_request["head"]
    sha = head["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("The pull request head is not a Git commit SHA.")
    ref = quote(head["ref"], safe="/")
    prefix = f"https://github.com/{head['repo']['full_name']}/blob/{ref}/"
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
    if not complete_png(image_bytes):
        raise ValueError("infographic.png must contain a complete PNG with valid chunk checksums.")
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
