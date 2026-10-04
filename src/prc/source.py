"""The PullRequestSource contract implemented by the live adapter and by fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from prc.model import PrRef


class SourceError(RuntimeError):
    """Enumeration or fetch failed; capture treats it as a failed attempt."""


class PullRequestSource(Protocol):
    """Read-only access to one PR's mutable provider resources.

    Resource keys: ``pr``, ``checks``, ``check:<run_id>:<attempt>`` and optional ``trace``.
    ``enumerate`` returns the complete membership with a per-resource version token.
    """

    label: str
    live_verified: bool

    def enumerate(self, ref: PrRef) -> dict[str, str]: ...

    def fetch(self, ref: PrRef, key: str) -> bytes: ...

    def repo_path(self, ref: PrRef) -> Path:
        """Local object database holding the pinned commits."""
        ...
