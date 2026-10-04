import pytest

from prc.evaluation.protocol import Condition
from prc.evaluation.scoring import (
    FailureReason,
    ItemKind,
    OutcomeState,
    ProductAttempt,
    deliver_baseline,
    deliver_product,
    read_timer,
    score_item,
    scored_result,
    snapshot_accuracy,
    unknown_result,
)


def test_item_scores_follow_rubric_anchors() -> None:
    assert score_item(ItemKind.MULTIPLE_CHOICE, 1) == 1.0
    assert score_item(ItemKind.SHORT, 0.5) == 0.5
    assert score_item(ItemKind.SHORT, None) == 0.0

    with pytest.raises(ValueError):
        score_item(ItemKind.MULTIPLE_CHOICE, 0.5)


def test_timeout_fallback_scores_normally_and_elapsed_includes_generation_seconds() -> None:
    delivery = deliver_product(
        "snap-a",
        ProductAttempt(seconds=300.0, failure_reason=FailureReason.TIMEOUT),
        fallback_view_id="baseline-view",
        response_seconds=400.0,
    )
    result = scored_result(delivery, [1, 0.5, 1])

    assert delivery.assigned is Condition.PRODUCT
    assert delivery.exposed is Condition.BASELINE
    assert delivery.attempt_seconds == 120.0
    assert delivery.elapsed_seconds == 520.0
    assert result.condition is Condition.PRODUCT
    assert result.accuracy == pytest.approx(2.5 / 3)


def test_support_validation_rejection_uses_same_snapshot_baseline_and_keeps_pair() -> None:
    delivery = deliver_product(
        "snap-a",
        ProductAttempt(seconds=8.0, failure_reason=FailureReason.SUPPORT_VALIDATION_REJECTED),
        fallback_view_id="baseline-view-snap-a",
        response_seconds=100.0,
    )

    assert delivery.snapshot_id == "snap-a"
    assert delivery.fallback_view_id == "baseline-view-snap-a"
    assert delivery.assigned is Condition.PRODUCT
    assert delivery.failure_reason is FailureReason.SUPPORT_VALIDATION_REJECTED


def test_successful_product_delivery_records_published_view() -> None:
    delivery = deliver_product(
        "snap-a", ProductAttempt(seconds=5.0, published_view_id="view-9"), "b", 50.0
    )

    assert delivery.exposed is Condition.PRODUCT
    assert delivery.published_view_id == "view-9"
    assert delivery.fallback_view_id is None


def test_abort_after_one_correct_and_two_blanks_is_one_third() -> None:
    delivery = deliver_baseline("snap-b", "view", response_seconds=200.0)
    result = scored_result(delivery, [1, None, None], aborted=True)

    assert result.accuracy == pytest.approx(1 / 3)
    assert result.aborted


def test_fallback_failure_scores_saved_answers_with_zero_blanks() -> None:
    delivery = deliver_product(
        "snap-a",
        ProductAttempt(seconds=120.0, failure_reason=FailureReason.TIMEOUT),
        "b",
        10.0,
        fallback_failed=True,
    )
    result = scored_result(delivery, [None, 1, None])

    assert delivery.fallback_failed
    assert result.accuracy == pytest.approx(1 / 3)


def test_timer_caps_at_deadline_and_flags_censoring() -> None:
    assert read_timer(1199.0).censored is False
    reading = read_timer(5000.0)

    assert reading.elapsed_seconds == 1200.0
    assert reading.censored


def test_unknown_result_has_no_accuracy_and_scored_requires_items() -> None:
    result = unknown_result("snap-x", Condition.BASELINE)

    assert result.state is OutcomeState.UNKNOWN
    assert result.accuracy is None
    assert result.elapsed_seconds is None
    assert snapshot_accuracy((1.0, 1.0, 1.0)) == 1.0
