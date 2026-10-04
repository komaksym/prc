"""Pair differences, paired bootstrap, missing-data scenarios, decision rule, and report."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import numpy.typing as npt

from prc.evaluation.protocol import PROTOCOL, Condition, Protocol
from prc.evaluation.scoring import OutcomeState, SnapshotResult, pair_difference

FLOAT_TOLERANCE = 1e-9


class Scenario(StrEnum):
    PRIMARY = "primary"
    ADVERSE = "adverse"
    FAVORABLE = "favorable"


class Decision(StrEnum):
    SUCCESS = "success"
    NO_PROMISING_SIGNAL = "no promising signal"
    INCONCLUSIVE = "inconclusive"


# (score for unknown product-side outcome, score for unknown baseline-side outcome)
UNKNOWN_FILL: dict[Scenario, tuple[float, float]] = {
    Scenario.PRIMARY: (0.0, 0.0),
    Scenario.ADVERSE: (0.0, 1.0),
    Scenario.FAVORABLE: (1.0, 0.0),
}


@dataclass(frozen=True)
class PairOutcome:
    pair_id: int
    product: SnapshotResult
    baseline: SnapshotResult

    def __post_init__(self) -> None:
        if self.product.condition is not Condition.PRODUCT:
            raise ValueError("product result must carry product assignment")
        if self.baseline.condition is not Condition.BASELINE:
            raise ValueError("baseline result must carry baseline assignment")


@dataclass(frozen=True)
class IntervalResult:
    estimate_pp: float
    lower_pp: float
    upper_pp: float


def resolved_accuracy(result: SnapshotResult, unknown_fill: float) -> float:
    accuracy = result.accuracy

    return unknown_fill if accuracy is None else accuracy


def pair_differences(pairs: Sequence[PairOutcome], scenario: Scenario) -> npt.NDArray[np.float64]:
    product_fill, baseline_fill = UNKNOWN_FILL[scenario]

    return np.array(
        [
            pair_difference(
                resolved_accuracy(pair.product, product_fill),
                resolved_accuracy(pair.baseline, baseline_fill),
            )
            for pair in pairs
        ],
        dtype=np.float64,
    )


def interval_from_sorted(
    sorted_estimates: npt.NDArray[np.float64], protocol: Protocol = PROTOCOL
) -> tuple[float, float]:
    """Pick the lower_rank-th and upper_rank-th values (1-indexed) of the sorted estimates."""

    return (
        float(sorted_estimates[protocol.lower_rank - 1]),
        float(sorted_estimates[protocol.upper_rank - 1]),
    )


def bootstrap_interval(
    differences: npt.NDArray[np.float64], protocol: Protocol = PROTOCOL
) -> IntervalResult:
    """Paired bootstrap over pair differences; every call restarts the same PCG64 seed."""

    rng = np.random.Generator(np.random.PCG64(protocol.bootstrap_seed))
    pair_count = len(differences)
    resampled_idx = rng.integers(0, pair_count, size=(protocol.bootstrap_resamples, pair_count))
    estimates = np.sort(100.0 * differences[resampled_idx].mean(axis=1))
    lower, upper = interval_from_sorted(estimates, protocol)

    return IntervalResult(
        estimate_pp=float(100.0 * differences.mean()), lower_pp=lower, upper_pp=upper
    )


def decide(results: Mapping[Scenario, IntervalResult], protocol: Protocol = PROTOCOL) -> Decision:
    threshold = protocol.success_threshold_pp

    def clears(result: IntervalResult) -> bool:
        return (
            result.estimate_pp >= threshold - FLOAT_TOLERANCE and result.lower_pp > FLOAT_TOLERANCE
        )

    if clears(results[Scenario.PRIMARY]) and clears(results[Scenario.ADVERSE]):
        return Decision.SUCCESS
    if all(result.upper_pp < threshold - FLOAT_TOLERANCE for result in results.values()):
        return Decision.NO_PROMISING_SIGNAL

    return Decision.INCONCLUSIVE


@dataclass(frozen=True)
class PairRow:
    pair_id: int
    product_snapshot_id: str
    baseline_snapshot_id: str
    product_state: OutcomeState
    baseline_state: OutcomeState
    product_accuracy: float | None
    baseline_accuracy: float | None
    primary_difference: float


@dataclass(frozen=True)
class TimeSummary:
    mean_pair_difference_seconds: float | None
    pairs_with_both_times: int
    missing_time_by_condition: Mapping[str, int]
    censored_by_condition: Mapping[str, int]


@dataclass(frozen=True)
class ConfidenceSummary:
    mean_by_condition: Mapping[str, float | None]
    missing_by_condition: Mapping[str, int]
    mean_when_correct: float | None
    mean_when_not_correct: float | None


@dataclass(frozen=True)
class AnalysisReport:
    scenarios: Mapping[Scenario, IntervalResult]
    decision: Decision
    pair_rows: tuple[PairRow, ...]
    missing_by_condition: Mapping[str, int]
    failure_counts: Mapping[str, int]
    abort_counts: Mapping[str, int]
    fallback_failure_count: int
    time: TimeSummary
    confidence: ConfidenceSummary


def _mean(values: Sequence[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _side_results(pairs: Sequence[PairOutcome]) -> dict[Condition, list[SnapshotResult]]:
    return {
        Condition.PRODUCT: [pair.product for pair in pairs],
        Condition.BASELINE: [pair.baseline for pair in pairs],
    }


def summarize_time(pairs: Sequence[PairOutcome]) -> TimeSummary:
    both_recorded = [
        pair.product.elapsed_seconds - pair.baseline.elapsed_seconds
        for pair in pairs
        if pair.product.elapsed_seconds is not None and pair.baseline.elapsed_seconds is not None
    ]
    sides = _side_results(pairs)

    return TimeSummary(
        mean_pair_difference_seconds=_mean(both_recorded),
        pairs_with_both_times=len(both_recorded),
        missing_time_by_condition={
            side.value: sum(result.elapsed_seconds is None for result in results)
            for side, results in sides.items()
        },
        censored_by_condition={
            side.value: sum(result.censored for result in results)
            for side, results in sides.items()
        },
    )


def summarize_confidence(pairs: Sequence[PairOutcome]) -> ConfidenceSummary:
    sides = _side_results(pairs)
    mean_by_condition: dict[str, float | None] = {}
    missing_by_condition: dict[str, int] = {}
    correct: list[float] = []
    not_correct: list[float] = []

    for side, results in sides.items():
        recorded: list[float] = []
        missing = 0
        for result in results:
            scores = result.item_scores or (None, None, None)
            for confidence, score in zip(result.confidences, scores, strict=True):
                if confidence is None:
                    missing += 1
                    continue
                recorded.append(confidence)
                if score is not None:
                    (correct if score == 1.0 else not_correct).append(confidence)
        mean_by_condition[side.value] = _mean(recorded)
        missing_by_condition[side.value] = missing

    return ConfidenceSummary(
        mean_by_condition=mean_by_condition,
        missing_by_condition=missing_by_condition,
        mean_when_correct=_mean(correct),
        mean_when_not_correct=_mean(not_correct),
    )


def analyze(pairs: Sequence[PairOutcome], protocol: Protocol = PROTOCOL) -> AnalysisReport:
    """Run all three scenarios over every randomized pair and apply the decision rule."""

    if len(pairs) != protocol.pair_count:
        raise ValueError(f"expected {protocol.pair_count} pairs, got {len(pairs)}")

    scenarios = {
        scenario: bootstrap_interval(pair_differences(pairs, scenario), protocol)
        for scenario in Scenario
    }
    primary_differences = pair_differences(pairs, Scenario.PRIMARY)
    sides = _side_results(pairs)
    deliveries = [result.delivery for results in sides.values() for result in results]

    return AnalysisReport(
        scenarios=scenarios,
        decision=decide(scenarios, protocol),
        pair_rows=tuple(
            PairRow(
                pair_id=pair.pair_id,
                product_snapshot_id=pair.product.snapshot_id,
                baseline_snapshot_id=pair.baseline.snapshot_id,
                product_state=pair.product.state,
                baseline_state=pair.baseline.state,
                product_accuracy=pair.product.accuracy,
                baseline_accuracy=pair.baseline.accuracy,
                primary_difference=float(difference),
            )
            for pair, difference in zip(pairs, primary_differences, strict=True)
        ),
        missing_by_condition={
            side.value: sum(result.state is OutcomeState.UNKNOWN for result in results)
            for side, results in sides.items()
        },
        failure_counts=dict(
            Counter(
                delivery.failure_reason.value
                for delivery in deliveries
                if delivery is not None and delivery.failure_reason is not None
            )
        ),
        abort_counts={
            side.value: sum(result.aborted for result in results) for side, results in sides.items()
        },
        fallback_failure_count=sum(
            delivery.fallback_failed for delivery in deliveries if delivery is not None
        ),
        time=summarize_time(pairs),
        confidence=summarize_confidence(pairs),
    )
