"""JSON loader for recorded pair outcomes. Input format is documented in the README."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prc.evaluation.analysis import PairOutcome
from prc.evaluation.protocol import Condition
from prc.evaluation.scoring import OutcomeState, SnapshotResult


def _result(raw: dict[str, Any], condition: Condition) -> SnapshotResult:
    state = OutcomeState(raw["state"])
    scores = raw.get("item_scores")
    confidences = raw.get("confidences", [None, None, None])

    return SnapshotResult(
        snapshot_id=str(raw["snapshot_id"]),
        condition=condition,
        state=state,
        item_scores=None if scores is None else (scores[0], scores[1], scores[2]),
        aborted=bool(raw.get("aborted", False)),
        confidences=(confidences[0], confidences[1], confidences[2]),
        elapsed_seconds=raw.get("elapsed_seconds"),
        censored=bool(raw.get("censored", False)),
    )


def load_pairs(path: Path) -> list[PairOutcome]:
    raw = json.loads(path.read_text())

    return [
        PairOutcome(
            int(entry["pair_id"]),
            _result(entry["product"], Condition.PRODUCT),
            _result(entry["baseline"], Condition.BASELINE),
        )
        for entry in raw["pairs"]
    ]
