import copy

from prc.evaluation.protocol import (
    PROTOCOL,
    Pair,
    SealedExperiment,
    assign,
    canonical_json,
    seal_experiment,
    verify_seal,
)


def make_pairs() -> list[Pair]:
    return [Pair(pair_id=n, snapshot_ids=(f"s{n:02d}b", f"s{n:02d}a")) for n in range(1, 13)]


def make_seal(product_treatment_id: str = "prod-1") -> SealedExperiment:
    pairs = make_pairs()
    roster = [snapshot for pair in pairs for snapshot in pair.snapshot_ids]

    return seal_experiment(
        roster=roster,
        pairing=pairs,
        instrument_ids={snapshot: f"inst-{snapshot}" for snapshot in roster},
        product_treatment_id=product_treatment_id,
        baseline_treatment_id="base-1",
        evaluator_versions={"evaluator": "1", "adjudicator": "1", "scorer": "1"},
    )


def test_protocol_constants_are_frozen_values() -> None:
    assert PROTOCOL.pair_count == 12
    assert PROTOCOL.bootstrap_resamples == 20_000
    assert PROTOCOL.bootstrap_seed == 12024
    assert (PROTOCOL.lower_rank, PROTOCOL.upper_rank) == (1000, 19000)
    assert PROTOCOL.session_days == (1, 3, 5, 7)


def test_canonical_json_is_key_order_independent_and_unescaped() -> None:
    assert canonical_json({"b": 1, "a": "é"}) == '{"a":"é","b":1}'


def test_seal_verifies_and_is_stable() -> None:
    assert verify_seal(make_seal())
    assert make_seal().digest == make_seal().digest


def test_mid_experiment_edit_breaks_seal_and_new_experiment_preserves_original() -> None:
    original = make_seal()
    original_digest = original.digest
    tampered_payload = copy.deepcopy(dict(original.payload))
    tampered_payload["evaluator_versions"]["scorer"] = "2"
    tampered = SealedExperiment(payload=tampered_payload, digest=original_digest)

    assert not verify_seal(tampered)
    assert make_seal(product_treatment_id="prod-2").digest != original_digest
    assert verify_seal(original)
    assert original.digest == original_digest


def test_assignment_is_deterministic_and_records_all_draws() -> None:
    first = assign(make_pairs(), seed=7)
    second = assign(make_pairs(), seed=7)

    assert first == second
    assert len(first.assignment_draws) == len(first.exposure_draws) == 12
    assert sorted(first.card_permutation) == list(range(12))


def test_heads_assigns_lexicographically_first_snapshot_to_product() -> None:
    result = assign(make_pairs(), seed=3)

    for pair_assignment in result.pairs:
        expected_product = f"s{pair_assignment.pair_id:02d}" + (
            "a" if pair_assignment.assignment_heads else "b"
        )
        assert pair_assignment.product_snapshot_id == expected_product
        assert pair_assignment.product_first == pair_assignment.exposure_heads


def test_no_randomized_snapshot_is_dropped_and_schedule_covers_all_pairs() -> None:
    result = assign(make_pairs(), seed=11)
    assigned = {p.product_snapshot_id for p in result.pairs} | {
        p.baseline_snapshot_id for p in result.pairs
    }
    scheduled = [pair_id for session in result.sessions for pair_id in session.pair_ids]

    assert len(assigned) == 24
    assert sorted(scheduled) == list(range(1, 13))
    assert [session.day for session in result.sessions] == [1, 3, 5, 7]
    assert all(len(session.pair_ids) == 3 for session in result.sessions)
