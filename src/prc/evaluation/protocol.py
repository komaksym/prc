"""Frozen constants, sealing, and randomized assignment for the solo pilot protocol."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy as np


class Condition(StrEnum):
    PRODUCT = "product"
    BASELINE = "baseline"


@dataclass(frozen=True)
class Protocol:
    pair_count: int = 12
    items_per_snapshot: int = 3
    multiple_choice_items: int = 1
    short_items: int = 2
    success_threshold_pp: float = 10.0
    bootstrap_resamples: int = 20_000
    bootstrap_seed: int = 12024
    generation_cap_seconds: float = 120.0
    deadline_seconds: float = 1200.0
    pairs_per_session: int = 3
    session_days: tuple[int, ...] = (1, 3, 5, 7)

    @property
    def lower_rank(self) -> int:
        """1-indexed rank of the lower endpoint (1,000th of 20,000)."""

        return self.bootstrap_resamples // 20

    @property
    def upper_rank(self) -> int:
        """1-indexed rank of the upper endpoint (19,000th of 20,000)."""

        return self.bootstrap_resamples - self.bootstrap_resamples // 20


PROTOCOL = Protocol()


@dataclass(frozen=True)
class Pair:
    pair_id: int
    snapshot_ids: tuple[str, str]

    @property
    def first_snapshot_id(self) -> str:
        return min(self.snapshot_ids)

    @property
    def second_snapshot_id(self) -> str:
        return max(self.snapshot_ids)


@dataclass(frozen=True)
class SealedExperiment:
    payload: Mapping[str, Any]
    digest: str

    def to_json_dict(self) -> dict[str, Any]:
        return {"payload": dict(self.payload), "digest": self.digest}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def seal_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def seal_experiment(
    roster: Sequence[str],
    pairing: Sequence[Pair],
    instrument_ids: Mapping[str, str],
    product_treatment_id: str,
    baseline_treatment_id: str,
    evaluator_versions: Mapping[str, str],
    protocol: Protocol = PROTOCOL,
) -> SealedExperiment:
    """Freeze everything that must not change after assignment; returns payload plus hash."""

    paired_ids = sorted(snapshot for pair in pairing for snapshot in pair.snapshot_ids)
    if len(pairing) != protocol.pair_count or paired_ids != sorted(roster):
        raise ValueError("pairing must cover the roster exactly once with the protocol pair count")
    if len(set(roster)) != len(roster):
        raise ValueError("roster contains duplicate snapshots")
    if set(instrument_ids) != set(roster):
        raise ValueError("instrument_ids must have exactly one entry per roster snapshot")

    payload: dict[str, Any] = {
        "protocol": asdict(protocol),
        "roster": list(roster),
        "pairing": [
            {"pair_id": pair.pair_id, "snapshot_ids": list(pair.snapshot_ids)} for pair in pairing
        ],
        "instrument_ids": dict(instrument_ids),
        "product_treatment_id": product_treatment_id,
        "baseline_treatment_id": baseline_treatment_id,
        "evaluator_versions": dict(evaluator_versions),
    }

    return SealedExperiment(payload=payload, digest=seal_digest(payload))


def verify_seal(sealed: SealedExperiment) -> bool:
    """True only if the payload still hashes to the digest recorded at sealing."""

    return seal_digest(sealed.payload) == sealed.digest


@dataclass(frozen=True)
class PairAssignment:
    pair_id: int
    product_snapshot_id: str
    baseline_snapshot_id: str
    product_first: bool
    assignment_heads: bool
    exposure_heads: bool


@dataclass(frozen=True)
class SessionPlan:
    day: int
    pair_ids: tuple[int, ...]


@dataclass(frozen=True)
class ExperimentAssignment:
    seed: int
    pairs: tuple[PairAssignment, ...]
    pair_order: tuple[int, ...]
    sessions: tuple[SessionPlan, ...]
    assignment_draws: tuple[int, ...]
    exposure_draws: tuple[int, ...]
    card_permutation: tuple[int, ...]


def assign(pairs: Sequence[Pair], seed: int, protocol: Protocol = PROTOCOL) -> ExperimentAssignment:
    """Draw assignment coins, exposure coins, then the card shuffle, all from one PCG64 stream."""

    if len(pairs) != protocol.pair_count:
        raise ValueError(f"expected {protocol.pair_count} pairs, got {len(pairs)}")

    rng = np.random.Generator(np.random.PCG64(seed))
    assignment_draws = tuple(int(draw) for draw in rng.integers(0, 2, size=len(pairs)))
    exposure_draws = tuple(int(draw) for draw in rng.integers(0, 2, size=len(pairs)))
    card_permutation = tuple(int(card) for card in rng.permutation(len(pairs)))

    pair_assignments: list[PairAssignment] = []
    for pair, assignment_draw, exposure_draw in zip(
        pairs, assignment_draws, exposure_draws, strict=True
    ):
        assignment_heads = assignment_draw == 1
        first, second = pair.first_snapshot_id, pair.second_snapshot_id
        pair_assignments.append(
            PairAssignment(
                pair_id=pair.pair_id,
                product_snapshot_id=first if assignment_heads else second,
                baseline_snapshot_id=second if assignment_heads else first,
                product_first=exposure_draw == 1,
                assignment_heads=assignment_heads,
                exposure_heads=exposure_draw == 1,
            )
        )

    pair_order = tuple(pairs[card].pair_id for card in card_permutation)
    sessions = tuple(
        SessionPlan(
            day=day,
            pair_ids=pair_order[
                session_idx * protocol.pairs_per_session : (session_idx + 1)
                * protocol.pairs_per_session
            ],
        )
        for session_idx, day in enumerate(protocol.session_days)
    )

    return ExperimentAssignment(
        seed=seed,
        pairs=tuple(pair_assignments),
        pair_order=pair_order,
        sessions=sessions,
        assignment_draws=assignment_draws,
        exposure_draws=exposure_draws,
        card_permutation=card_permutation,
    )
