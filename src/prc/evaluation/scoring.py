"""Item and snapshot scoring, delivery records, and timer semantics."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from prc.evaluation.protocol import PROTOCOL, Condition, Protocol


class ItemKind(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT = "short"


ITEM_KINDS: tuple[ItemKind, ...] = (ItemKind.MULTIPLE_CHOICE, ItemKind.SHORT, ItemKind.SHORT)
_ALLOWED_SCORES: dict[ItemKind, frozenset[float]] = {
    ItemKind.MULTIPLE_CHOICE: frozenset({0.0, 1.0}),
    ItemKind.SHORT: frozenset({0.0, 0.5, 1.0}),
}


class OutcomeState(StrEnum):
    SCORED = "scored"
    UNKNOWN = "unknown"


class FailureReason(StrEnum):
    TIMEOUT = "timeout"
    SUPPORT_VALIDATION_REJECTED = "support_validation_rejected"
    GENERATION_ERROR = "generation_error"


def score_item(kind: ItemKind, awarded: float | None) -> float:
    """Blank or unsupplied (None) scores zero; anything off the rubric anchors is an error."""

    if awarded is None:
        return 0.0
    if awarded not in _ALLOWED_SCORES[kind]:
        raise ValueError(f"{kind.value} item cannot score {awarded}")

    return float(awarded)


def score_snapshot(awarded: Sequence[float | None]) -> tuple[float, float, float]:
    if len(awarded) != len(ITEM_KINDS):
        raise ValueError("a snapshot has exactly three items")
    first, second, third = (
        score_item(kind, value) for kind, value in zip(ITEM_KINDS, awarded, strict=True)
    )

    return first, second, third


def snapshot_accuracy(item_scores: Sequence[float]) -> float:
    if len(item_scores) != len(ITEM_KINDS):
        raise ValueError("a snapshot has exactly three items")

    return sum(item_scores) / len(item_scores)


def pair_difference(product_accuracy: float, baseline_accuracy: float) -> float:
    return product_accuracy - baseline_accuracy


@dataclass(frozen=True)
class TimerReading:
    elapsed_seconds: float
    censored: bool


def read_timer(raw_seconds: float, protocol: Protocol = PROTOCOL) -> TimerReading:
    """Elapsed is capped at the deadline; reaching it flags the reading as censored."""

    return TimerReading(
        elapsed_seconds=min(raw_seconds, protocol.deadline_seconds),
        censored=raw_seconds >= protocol.deadline_seconds,
    )


@dataclass(frozen=True)
class ProductAttempt:
    """Result of the single product generation/validation attempt."""

    seconds: float
    failure_reason: FailureReason | None = None
    published_view_id: str | None = None

    def __post_init__(self) -> None:
        if (self.failure_reason is None) == (self.published_view_id is None):
            raise ValueError("an attempt either fails with a reason or publishes a view")


@dataclass(frozen=True)
class DeliveryRecord:
    snapshot_id: str
    assigned: Condition
    exposed: Condition
    failure_reason: FailureReason | None
    published_view_id: str | None
    fallback_view_id: str | None
    attempt_seconds: float
    elapsed_seconds: float
    censored: bool
    fallback_failed: bool = False


def deliver_product(
    snapshot_id: str,
    attempt: ProductAttempt,
    fallback_view_id: str,
    response_seconds: float,
    fallback_failed: bool = False,
    protocol: Protocol = PROTOCOL,
) -> DeliveryRecord:
    """Product assignment: fall back to the same snapshot's baseline on any attempt failure.

    Assignment stays product; attempt time counts toward elapsed against the original deadline.
    """

    attempt_seconds = min(attempt.seconds, protocol.generation_cap_seconds)
    failed = attempt.failure_reason is not None
    if fallback_failed and not failed:
        raise ValueError("fallback cannot fail when product delivery succeeded")
    timer = read_timer(attempt_seconds + response_seconds, protocol)

    return DeliveryRecord(
        snapshot_id=snapshot_id,
        assigned=Condition.PRODUCT,
        exposed=Condition.BASELINE if failed else Condition.PRODUCT,
        failure_reason=attempt.failure_reason,
        published_view_id=attempt.published_view_id,
        fallback_view_id=fallback_view_id if failed else None,
        attempt_seconds=attempt_seconds,
        elapsed_seconds=timer.elapsed_seconds,
        censored=timer.censored,
        fallback_failed=fallback_failed,
    )


def deliver_baseline(
    snapshot_id: str,
    baseline_view_id: str,
    response_seconds: float,
    protocol: Protocol = PROTOCOL,
) -> DeliveryRecord:
    timer = read_timer(response_seconds, protocol)

    return DeliveryRecord(
        snapshot_id=snapshot_id,
        assigned=Condition.BASELINE,
        exposed=Condition.BASELINE,
        failure_reason=None,
        published_view_id=None,
        fallback_view_id=baseline_view_id,
        attempt_seconds=0.0,
        elapsed_seconds=timer.elapsed_seconds,
        censored=timer.censored,
    )


@dataclass(frozen=True)
class SnapshotResult:
    """One randomized snapshot's outcome: scored, or unknown (lost or unstarted)."""

    snapshot_id: str
    condition: Condition
    state: OutcomeState
    item_scores: tuple[float, float, float] | None = None
    delivery: DeliveryRecord | None = None
    aborted: bool = False
    confidences: tuple[float | None, float | None, float | None] = (None, None, None)
    elapsed_seconds: float | None = None
    censored: bool = False

    def __post_init__(self) -> None:
        if (self.state is OutcomeState.SCORED) != (self.item_scores is not None):
            raise ValueError("scored results need item scores; unknown results must have none")

    @property
    def accuracy(self) -> float | None:
        return None if self.item_scores is None else snapshot_accuracy(self.item_scores)


def scored_result(
    delivery: DeliveryRecord,
    awarded: Sequence[float | None],
    aborted: bool = False,
    confidences: tuple[float | None, float | None, float | None] = (None, None, None),
) -> SnapshotResult:
    return SnapshotResult(
        snapshot_id=delivery.snapshot_id,
        condition=delivery.assigned,
        state=OutcomeState.SCORED,
        item_scores=score_snapshot(awarded),
        delivery=delivery,
        aborted=aborted,
        confidences=confidences,
        elapsed_seconds=delivery.elapsed_seconds,
        censored=delivery.censored,
    )


def unknown_result(
    snapshot_id: str,
    condition: Condition,
    delivery: DeliveryRecord | None = None,
) -> SnapshotResult:
    return SnapshotResult(
        snapshot_id=snapshot_id,
        condition=condition,
        state=OutcomeState.UNKNOWN,
        delivery=delivery,
        elapsed_seconds=None if delivery is None else delivery.elapsed_seconds,
        censored=False if delivery is None else delivery.censored,
    )
