"""Build pinned PRC maps from privately captured GitHub candidates."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prc.fixture_source import FixtureSource
from prc.github_source import GitHubSource
from prc.gitutil import run_git
from prc.identity import to_jsonable
from prc.model import PrRef
from prc.pipeline import run_map
from prc.source import PullRequestSource
from prc.verification import EligibilityPolicy


def lens_page(source: Path, out: Path, render: Callable[[str], str]) -> None:
    if out.exists():
        raise FileExistsError(out)
    comment = json.loads((source / "comment.json").read_text())
    html = render(comment["body"])
    html = re.sub(
        r"https://camo\.githubusercontent\.com/[0-9a-f]+/([0-9a-f]+)",
        lambda match: bytes.fromhex(match.group(1)).decode(),
        html,
    )
    html = re.sub(r'<source media="\(prefers-color-scheme: dark\)"[^>]*>', "", html)
    html = re.sub(r'\sdata-canonical-src="[^"]*"', "", html)

    def local_asset(match: re.Match[str]) -> str:
        name = match.group(1)
        asset = source / "assets" / name
        if not asset.is_file():
            raise ValueError(f"uncaptured Lens render: {name}")
        if asset.stem != hashlib.sha256(asset.read_bytes()).hexdigest()[:32]:
            raise ValueError(f"Lens render bytes do not match its name: {name}")
        return f"assets/{name}"

    html = re.sub(
        r'https://prlens\.dev/api/i/renders/[^\s"<>]+/([^/\s"<>]+\.svg)', local_asset, html
    )

    def text_for_remote(match: re.Match[str]) -> str:
        alt = re.search(r'alt="([^"]*)"', match.group(0))
        return f"<span>{alt.group(1) if alt else ''}</span>"

    html = re.sub(r'<img\b[^>]*\bsrc="https?://[^"]*"[^>]*>', text_for_remote, html)
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Captured PR Lens CI output</title><style>"
        ":root{color-scheme:light}body{font:16px/1.6 system-ui;background:#fff;color:#172033;"
        "max-width:1100px;margin:24px auto;padding:0 24px}img{max-width:100%;height:auto}"
        "a{color:#125dc3}details{margin:12px 0}pre{overflow:auto}code{overflow-wrap:anywhere}"
        "</style><body><p>Captured PR Lens CI comment. The interactive canvas opens the live provider page.</p>"
        + html
        + "</body></html>"
    )
    shutil.copytree(source, out)
    (out / "index.html").write_text(page)


def capture(source: PullRequestSource, ref: PrRef, head: str, out: Path) -> None:
    if out.exists():
        raise FileExistsError(out)
    resources = {key: source.fetch(ref, key) for key in source.enumerate(ref)}
    metadata = json.loads(resources["pr"])
    if metadata["head_sha"] != head:
        raise ValueError("candidate head changed; recapture and readjudicate before sealing")
    repo = source.repo_path(ref)
    pinned = FixtureSource(repo, resources, label="github-pinned", live_verified=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=".paired-", dir=out.parent) as directory:
        work = Path(directory) / "packet"
        result = run_map(pinned, ref, time.time, EligibilityPolicy(), work / "capture")
        url = f"https://github.com/{ref.owner}/{ref.repo}/pull/{ref.number}"
        data = to_jsonable(dataclasses.replace(result.map, url=url))
        if data["head_sha"] != head:
            raise ValueError("map head differs from captured source")
        original = run_git(
            repo,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--binary",
            data["base_sha"],
            head,
        )
        (work / "map.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        (work / "original.diff").write_bytes(original)
        (work / "provider-resources.json").write_text(
            json.dumps({key: value.decode() for key, value in resources.items()}, indent=2) + "\n"
        )
        record = {
            "pr_identity": f"{ref.owner}/{ref.repo}#{ref.number}",
            "base_sha": data["base_sha"],
            "head_sha": head,
            "original_diff_sha256": hashlib.sha256(original).hexdigest(),
            "map_sha256": hashlib.sha256((work / "map.json").read_bytes()).hexdigest(),
            "git_dir": str(repo.resolve()),
            "captured_at": datetime.now(UTC).isoformat(),
            "map_generation_seconds": time.monotonic() - started,
            "source_note": "Pinned captured provider resources; live GitHub page remains mutable.",
        }
        (work / "provenance.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        if out.exists():
            raise FileExistsError(out)
        work.rename(out)


def gh_transport(url: str) -> tuple[Any, str | None]:
    result = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", url], capture_output=True, check=True
    )
    pages = json.loads(result.stdout)
    if len(pages) == 1:
        return pages[0], None
    if all(isinstance(page, dict) and "check_runs" in page for page in pages):
        return {"check_runs": [run for page in pages for run in page["check_runs"]]}, None
    raise ValueError("unsupported paginated resource")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads((args.candidate / "pr.json").read_text())
    owner, repo = raw["base"]["repo"]["full_name"].split("/")
    ref = PrRef(owner, repo, raw["number"])
    capture(GitHubSource(args.cache, transport=gh_transport), ref, raw["head"]["sha"], args.out)
    print(json.dumps({"packet": str(args.out.resolve()), "head_verified": True}))


if __name__ == "__main__":
    main()
