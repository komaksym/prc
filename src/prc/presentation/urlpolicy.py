"""Controller-owned URL policy. Links are built from validated identities, never from source text."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import quote

from prc.presentation.versions import GITHUB_ORIGIN

_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHA = re.compile(r"^[0-9a-f]{40}$")


def anchor_for(record_id: str) -> str:
    """Local, deterministic fragment for an evidence excerpt."""

    return "rec-" + hashlib.sha256(record_id.encode("utf-8")).hexdigest()[:12]


def github_blob_url(repo: str, head_sha: str, path: str) -> str:
    if not _REPO.match(repo) or not _SHA.match(head_sha):
        raise ValueError("repository or commit identity is not a valid pinned identity")

    return f"{GITHUB_ORIGIN}/{repo}/blob/{head_sha}/{quote(path, safe='/')}"


def is_allowed_href(url: str) -> bool:
    """Permit only fragment links and HTTPS links to the configured GitHub origin."""

    if re.fullmatch(r"#rec-[0-9a-f]{12}|#[a-z][a-z0-9-]{0,40}", url):
        return True

    return url.startswith(GITHUB_ORIGIN + "/") and all(ch not in url for ch in "\"'<>\\ \n\t")
