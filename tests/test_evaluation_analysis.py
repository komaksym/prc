import numpy as np
import pytest

from prc.evaluation.analysis import (
    Decision,
    IntervalResult,
    PairOutcome,
    Scenario,
    analyze,
    bootstrap_interval,
    decide,
    interval_from_sorted,
    pair_differences,
)
from prc.evaluation.protocol import PROTOCOL, Condition
from prc.evaluation.scoring import (
    ProductAttempt,
    deliver_baseline,
    deliver_product,
    scored_result,
    unknown_result,
)


def pair(
    pair_id: int,
    product_scores: list[float | None] | None,
    baseline_scores: list[float | None] | None,
) -> PairOutcome:
    product_id, baseline_id = f"p{pair_id}", f"b{pair_id}"
    product = (
        unknown_result(product_id, Condition.PRODUCT)
        if product_scores is None
        else scored_result(
            deliver_product(product_id, ProductAttempt(1.0, None, "view"), "b", 100.0),
            product_scores,
        )
    )
    baseline = (
        unknown_result(baseline_id, Condition.BASELINE)
        if baseline_scores is None
        else scored_result(deliver_baseline(baseline_id, "v", 200.0), baseline_scores)
    )
    return PairOutcome(pair_id=pair_id, product=product, baseline=baseline)


def uniform_pairs(
    product_scores: list[float | None], baseline_scores: list[float | None]
) -> list[PairOutcome]:
    return [pair(pair_number, product_scores, baseline_scores) for pair_number in range(1, 13)]


def test_interval_index_convention_is_1000th_and_19000th_values() -> None:
    sorted_estimates = np.arange(1, 20_001, dtype=np.float64)

    assert interval_from_sorted(sorted_estimates) == (1000.0, 19000.0)


def test_interval_index_convention_small_case_by_hand() -> None:
    from prc.evaluation.protocol import Protocol

    twenty_resamples = Protocol(bootstrap_resamples=20)
    sorted_estimates = np.arange(1, 21, dtype=np.float64)

    assert interval_from_sorted(sorted_estimates, twenty_resamples) == (1.0, 19.0)


def test_bootstrap_is_deterministic_and_constant_input_collapses() -> None:
    differences = np.array([0.5, -1 / 6, 1 / 3, 0.0, 1.0, 0.5, 1 / 6, 0.0, 0.5, 1 / 3, 0.5, 0.0])

    assert bootstrap_interval(differences) == bootstrap_interval(differences)

    flat = bootstrap_interval(np.full(12, 0.25))
    assert flat == IntervalResult(25.0, 25.0, 25.0)


def test_clear_gain_succeeds() -> None:
    report = analyze(uniform_pairs([1, 1, 1], [0, 0, 0]))

    assert report.decision is Decision.SUCCESS
    assert report.scenarios[Scenario.PRIMARY].estimate_pp == 100.0


def test_lost_baseline_triggers_both_scenarios_and_pair_remains() -> None:
    pairs = uniform_pairs([1, 1, 1], [0, 0, 0])
    pairs[0] = pair(1, [1, 1, 1], None)
    report = analyze(pairs)

    assert len(report.pair_rows) == 12
    assert report.missing_by_condition == {"product": 0, "baseline": 1}
    assert pair_differences(pairs, Scenario.PRIMARY)[0] == 1.0
    assert pair_differences(pairs, Scenario.ADVERSE)[0] == 0.0
    assert pair_differences(pairs, Scenario.FAVORABLE)[0] == 1.0
    assert report.scenarios[Scenario.ADVERSE].estimate_pp == pytest.approx(100 * 11 / 12)


def test_unknown_product_adverse_zero_favorable_one_and_blanks_stay_zero() -> None:
    pairs = [pair(1, None, [1, 1, 1])] + uniform_pairs([1, None, None], [1, None, None])[1:]

    assert pair_differences(pairs, Scenario.ADVERSE)[0] == -1.0
    assert pair_differences(pairs, Scenario.FAVORABLE)[0] == 0.0
    assert pair_differences(pairs, Scenario.PRIMARY)[0] == -1.0
    assert pair_differences(pairs, Scenario.PRIMARY)[1] == 0.0


def test_decision_rule_branches() -> None:
    def interval(estimate: float, lower: float, upper: float) -> IntervalResult:
        return IntervalResult(estimate, lower, upper)

    good = interval(20, 5, 30)
    weak_lower = interval(20, 0, 30)
    low_upper = interval(2, -5, 9)

    assert decide({s: good for s in Scenario}) is Decision.SUCCESS
    assert (
        decide({Scenario.PRIMARY: good, Scenario.ADVERSE: weak_lower, Scenario.FAVORABLE: good})
        is Decision.INCONCLUSIVE
    )
    assert decide({s: low_upper for s in Scenario}) is Decision.NO_PROMISING_SIGNAL
    assert (
        decide({Scenario.PRIMARY: low_upper, Scenario.ADVERSE: low_upper, Scenario.FAVORABLE: good})
        is Decision.INCONCLUSIVE
    )


def test_no_unknowns_means_scenarios_equal_primary() -> None:
    report = analyze(uniform_pairs([1, 0.5, 0], [0, 0.5, 0]))

    assert report.scenarios[Scenario.ADVERSE] == report.scenarios[Scenario.PRIMARY]
    assert report.scenarios[Scenario.FAVORABLE] == report.scenarios[Scenario.PRIMARY]


def test_report_counts_time_and_requires_every_pair() -> None:
    pairs = uniform_pairs([1, 1, 1], [0, 0, 0])
    pairs[0] = pair(1, [1, 1, 1], None)
    report = analyze(pairs)

    assert report.time.pairs_with_both_times == 11
    assert report.time.missing_time_by_condition == {"product": 0, "baseline": 1}
    assert report.time.mean_pair_difference_seconds == pytest.approx(-99.0)
    assert report.confidence.missing_by_condition["product"] == 36

    with pytest.raises(ValueError):
        analyze(pairs[:11])
    assert PROTOCOL.pair_count == len(report.pair_rows)
