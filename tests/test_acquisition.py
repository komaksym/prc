from __future__ import annotations

import json
from collections.abc import Callable

from prc.capture import capture_bundle
from prc.fixture_source import FixtureSource
from prc.identity import canonical_json, content_id
from prc.model import PrRef
from prc.snapshot import build_basis, build_snapshot
from prc.verification import EligibilityPolicy

from conftest import FakeClock

Make = Callable[[str], tuple[FixtureSource, PrRef]]
POLICY = EligibilityPolicy()


def acquire(source: FixtureSource, ref: PrRef, clock: FakeClock):  # type: ignore[no-untyped-def]
    bundle = capture_bundle(source, ref, clock)

    return bundle, build_snapshot(bundle, source.label, source.live_verified, source.repo, POLICY)


def test_canonical_json_is_order_independent() -> None:
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1})
    assert content_id("x", {"a": 1}) != content_id("y", {"a": 1})


def test_stable_capture_and_inventory_is_exhaustive(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    bundle, acquisition = acquire(source, ref, clock)

    assert bundle.consistency == "stable" and bundle.attempts == 1
    paths = {item.path for item in acquisition.inventory.items}
    assert paths == {"src/app.py", "src/retry.py", "tests/test_app.py", "README.md"}


def test_opaque_surfaces_stay_explicit(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("opaque")
    _, acquisition = acquire(source, ref, clock)
    by_path = {item.path: item for item in acquisition.inventory.items}

    assert by_path["assets/old.png"].surface == "binary" and by_path["assets/old.png"].opaque
    assert (
        by_path["assets/model.bin"].surface == "lfs_pointer" and by_path["assets/model.bin"].opaque
    )
    assert by_path["vendor/lib"].surface == "submodule" and by_path["vendor/lib"].opaque
    assert by_path["src/big.py"].surface == "oversize" and by_path["src/big.py"].opaque
    assert by_path["bin/tool.sh"].surface == "mode_only" and not by_path["bin/tool.sh"].opaque
    assert by_path["link"].surface == "symlink"
    assert by_path["src/gone.py"].status == "D"
    assert not any(
        f"diff:{item.path}" in acquisition.records for item in by_path.values() if item.opaque
    )


def test_check_change_alters_basis_but_not_comparison(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    first = build_basis(capture_bundle(source, ref, clock), source.repo, POLICY)
    listings = json.loads(source.resources["checks"])
    listings[0]["attempt"] = 2
    source.resources["checks"] = json.dumps(listings).encode()
    source.resources["check:101:2"] = b"rerun\n"
    second = build_basis(capture_bundle(source, ref, clock), source.repo, POLICY)

    assert first.comparison_id == second.comparison_id
    assert first.basis_id != second.basis_id


def test_metadata_change_alters_basis_with_same_code(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    first = build_basis(capture_bundle(source, ref, clock), source.repo, POLICY)
    pr = json.loads(source.resources["pr"])
    pr["title"] = "different title"
    source.resources["pr"] = json.dumps(pr).encode()
    second = build_basis(capture_bundle(source, ref, clock), source.repo, POLICY)

    assert first.comparison_id == second.comparison_id and first.basis_id != second.basis_id


def test_reobserving_identical_content_preserves_identity(
    make_source: Make, clock: FakeClock
) -> None:
    source, ref = make_source("basic")
    _, first = acquire(source, ref, clock)
    _, second = acquire(source, ref, clock)

    assert first.snapshot.snapshot_id == second.snapshot.snapshot_id
    assert first.snapshot.observed_finished_at != second.snapshot.observed_finished_at


def test_verification_eligibility_and_gaps(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    _, ok = acquire(source, ref, clock)

    assert [e.eligibility for _, e in ok.evidence] == ["eligible", "eligible"]
    assert ok.snapshot.verification_gaps == ()

    source, ref = make_source("gaps")
    _, bad = acquire(source, ref, clock)
    states = {e.name: e.eligibility for _, e in bad.evidence}
    gap_names = {gap.name for gap in bad.snapshot.verification_gaps}

    assert states == {"merged-ci": "subject_mismatch", "lint": "expired"}
    assert gap_names == {"unit-tests", "merged-ci"}


def test_conflicting_and_missing_provenance(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    source.resources["check:101:1"] = b"X-Subject: deadbeef\nok\n"
    listings = json.loads(source.resources["checks"])
    listings[1]["subject_sha"] = None
    source.resources["checks"] = json.dumps(listings).encode()
    _, acquisition = acquire(source, ref, clock)
    states = {e.name: e.eligibility for _, e in acquisition.evidence}

    assert states == {"unit-tests": "conflicting_provenance", "merged-ci": "missing_provenance"}
    assert {gap.name for gap in acquisition.snapshot.verification_gaps} == {
        "unit-tests",
        "merged-ci",
    }


def test_drift_retries_then_stabilizes(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")

    def drift(call: int, resources: dict[str, bytes]) -> None:
        if call == 2:
            resources["trace"] = b"[]"

    source.drift = drift
    bundle = capture_bundle(source, ref, clock)

    assert bundle.consistency == "stable" and bundle.attempts == 2


def test_persistent_drift_is_unknown_after_three_attempts(
    make_source: Make, clock: FakeClock
) -> None:
    source, ref = make_source("basic")

    def drift(call: int, resources: dict[str, bytes]) -> None:
        resources["trace"] = str(call).encode()

    source.drift = drift
    bundle = capture_bundle(source, ref, clock)

    assert bundle.consistency == "unknown" and bundle.attempts == 3
    assert len(bundle.gaps) == 3 and source.enumerate_calls == 6


def test_missing_required_or_failed_fetch_is_unknown(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    source.fail_fetch_keys = {"checks"}

    assert capture_bundle(source, ref, clock).consistency == "unknown"

    source, ref = make_source("basic")
    del source.resources["pr"]

    assert capture_bundle(source, ref, clock).consistency == "unknown"


def test_extra_context_creates_new_snapshot(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    bundle = capture_bundle(source, ref, clock)
    first = build_snapshot(bundle, "fixture", False, source.repo, POLICY)
    second = build_snapshot(
        bundle, "fixture", False, source.repo, POLICY, extra_context_paths=("README.md",)
    )

    assert first.snapshot.snapshot_id != second.snapshot.snapshot_id
    assert first.snapshot.manifest_id != second.snapshot.manifest_id
    assert "context:README.md" in second.records and "context:README.md" not in first.records


def test_unrecognized_check_scope_loses_provenance(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    listings = json.loads(source.resources["checks"])
    listings[0]["scope"] = "trust-me"
    source.resources["checks"] = json.dumps(listings).encode()
    _, acquisition = acquire(source, ref, clock)
    states = {e.name: e.eligibility for _, e in acquisition.evidence}

    assert states["unit-tests"] == "missing_provenance"


def test_inventory_is_merge_base_to_head_when_base_advanced(
    make_source: Make, clock: FakeClock
) -> None:
    source, ref = make_source("advanced")
    _, acquisition = acquire(source, ref, clock)
    comparison = acquisition.snapshot.comparison

    assert comparison.merge_base_sha != comparison.base_tip_sha
    assert {item.path for item in acquisition.inventory.items} == {"src/app.py", "src/retry.py"}


def test_required_check_policy_is_part_of_source_basis(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    bundle = capture_bundle(source, ref, clock)
    default = build_basis(bundle, source.repo, POLICY)
    relaxed = build_basis(bundle, source.repo, EligibilityPolicy(required_names=()))

    assert default.comparison_id == relaxed.comparison_id and default.basis_id != relaxed.basis_id
