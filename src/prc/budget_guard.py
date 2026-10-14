"""Redline sleep/wake guard for metered 5h budgets.

Single owner for budget state and the one checkpoint/resume path.
Threshold and schema live here; callers point here, never copy them.
The guard reads no policy text; it reads an injected snapshot.
Pass paths in tests, never hardcode a home directory here.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REDLINE_REMAINING: Final[float] = 0.05
WINDOW_SECONDS: Final[int] = 5 * 60 * 60
CHECKPOINT_SCHEMA: Final[str] = "budget-guard/v1"


@dataclass(frozen=True)
class BudgetSnapshot:
    """Point-in-time meter reading. Fractions stay in [0.0, 1.0]."""

    remaining_fraction: float
    reset_at: float | None = None
    window_seconds: int = WINDOW_SECONDS

    def is_redline(self) -> bool:
        """Redline holds at or below 5 pct of the 5h budget left."""
        return self.remaining_fraction <= REDLINE_REMAINING


@dataclass(frozen=True)
class Checkpoint:
    """Durable redline state. Queued units resume after reset."""

    checkpoint_id: str
    remaining_fraction: float
    queued: tuple[str, ...]
    done: tuple[str, ...]


def check_dispatch_allowed(snapshot: BudgetSnapshot) -> list[str]:
    """Gate new dispatches on the redline. Call before every dispatch."""
    if snapshot.is_redline():
        return [
            "redline holds; checkpoint with BudgetGuard.checkpoint, "
            "then resume with BudgetGuard.resume after reset"
        ]
    return []


def is_reset(old: BudgetSnapshot, new: BudgetSnapshot) -> bool:
    """Reset holds when the meter recovered above the redline."""
    return old.is_redline() and not new.is_redline()


class BudgetGuard:
    """Own the meter reading and the checkpoint file for one run."""

    def __init__(
        self, read_snapshot: Callable[[], BudgetSnapshot], checkpoint_path: Path
    ) -> None:
        self._read_snapshot = read_snapshot
        self._checkpoint_path = checkpoint_path

    def snapshot(self) -> BudgetSnapshot:
        """Read the current meter through the injected provider."""
        return self._read_snapshot()

    def is_redline(self) -> bool:
        """Redline holds when the live reading is at or below 5 pct."""
        return self.snapshot().is_redline()

    def can_dispatch(self) -> bool:
        """Allow new work only above the redline."""
        return not self.is_redline()

    def gate(self) -> list[str]:
        """Name the fix when dispatch is blocked. Empty means go."""
        return check_dispatch_allowed(self.snapshot())

    def checkpoint(
        self, queued: tuple[str, ...] | list[str], done: tuple[str, ...] | list[str]
    ) -> Path:
        """Write queued plus done atomically. Return the checkpoint path."""
        snap = self.snapshot()
        payload = {
            "schema": CHECKPOINT_SCHEMA,
            "checkpoint_id": uuid.uuid4().hex[:12],
            "remaining_fraction": snap.remaining_fraction,
            "reset_at": snap.reset_at,
            "recorded_at": time.time(),
            "queued": list(queued),
            "done": list(done),
        }
        tmp = self._checkpoint_path.with_suffix(
            self._checkpoint_path.suffix + ".tmp"
        )
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self._checkpoint_path)
        return self._checkpoint_path

    def load_checkpoint(self) -> Checkpoint:
        """Read the checkpoint. Fail loudly on stale or corrupt state."""
        raw = self._checkpoint_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if data.get("schema") != CHECKPOINT_SCHEMA:
            raise ValueError(
                "stale checkpoint schema; re-checkpoint with BudgetGuard.checkpoint"
            )
        queued = data.get("queued")
        done = data.get("done")
        if not isinstance(queued, list) or not isinstance(done, list):
            raise ValueError("corrupt checkpoint: queued and done must be lists")
        return Checkpoint(
            checkpoint_id=str(data.get("checkpoint_id", "")),
            remaining_fraction=float(data.get("remaining_fraction", 0.0)),
            queued=tuple(str(u) for u in queued),
            done=tuple(str(u) for u in done),
        )

    def resume(self) -> Checkpoint:
        """Restore queued work after reset. Fail while the meter is red."""
        snap = self.snapshot()
        if snap.is_redline():
            raise RuntimeError(
                "meter still red; sleep until reset, then BudgetGuard.resume"
            )
        return self.load_checkpoint()
