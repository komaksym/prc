from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from prc.capture import capture_bundle
from prc.controller import analyze, fixture_suite, semantic_artifact_id
from prc.fixture_source import FixtureSource
from prc.freshness import StoredBasis, reconcile
from prc.model import PrRef
from prc.pipeline import render_view, run_decide, run_review, run_status
from prc.presentation import versions
from prc.scenarios import apply_mutations
from prc.snapshot import build_snapshot
from prc.store import StaleExpectation, Store
from prc.verification import EligibilityPolicy

from conftest import FakeClock

Make = Callable[[str], tuple[FixtureSource, PrRef]]
POLICY = EligibilityPolicy()


def test_concurrent_publication_has_one_canonical_winner(tmp_path: Path) -> None:
    store = Store(tmp_path / "s.sqlite")
    results: list[tuple[str, str, bool]] = []

    def publish(semantic: str) -> None:
        results.append(
            store.publish(
                pr_key="o/r#1",
                snapshot_id="snap",
                snapshot_body={"x": 1},
                publication_key="key",
                semantic_id=semantic,
                semantic_body={"s": semantic},
                view_id=f"view-{semantic}",
                files={"index.html": semantic.encode()},
                supporting={},
            )
        )

    threads = [threading.Thread(target=publish, args=(f"sem-{n}",)) for n in range(8)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    canonical = {canonical for canonical, _, _ in results}
    winners = [result for result in results if result[2]]

    assert len(canonical) == 1 and len(winners) == 1
    assert {view for _, view, _ in results} == {winners[0][1]}
    assert store.current("o/r#1") == ("snap", winners[0][1])


def test_view_identity_binds_renderer_version_and_bytes(
    make_source: Make, clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, ref = make_source("basic")
    acquisition = build_snapshot(
        capture_bundle(source, ref, clock), "fixture", False, source.repo, POLICY
    )
    artifact = analyze(acquisition, fixture_suite())
    semantic_id = semantic_artifact_id(artifact)
    first = render_view(acquisition, artifact, semantic_id)
    again = render_view(acquisition, artifact, semantic_id)
    monkeypatch.setitem(versions.RENDERER_VERSIONS, "html", "html-renderer-v2")
    bumped = render_view(acquisition, artifact, semantic_id)

    assert first.view_id == again.view_id and first.files == again.files
    assert bumped.view_id != first.view_id


def test_freshness_match_stale_unknown_and_deadline(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    acquisition = build_snapshot(
        capture_bundle(source, ref, clock), "fixture", False, source.repo, POLICY
    )
    stored = StoredBasis(acquisition.snapshot.basis_id, dict(acquisition.snapshot.basis_components))
    match = reconcile(source, ref, stored, POLICY, clock)

    assert match.status == "match"
    assert match.deadline == match.observed_finished_at + POLICY.freshness_ttl_seconds
    assert match.effective(match.deadline + 1) == "expired"

    for mutation, component in (("edit-title", "metadata"), ("rerun-check", "verification")):
        changed, changed_ref = make_source("basic")
        apply_mutations(changed, [mutation])
        report = reconcile(changed, changed_ref, stored, POLICY, clock)

        assert report.status == "stale" and component in report.differences

    expired, expired_ref = make_source("basic")
    apply_mutations(expired, ["expire-checks"])

    assert reconcile(expired, expired_ref, stored, POLICY, clock).status == "stale"

    source.drift = lambda call, resources: resources.__setitem__("trace", str(call).encode())

    assert reconcile(source, ref, stored, POLICY, clock).status == "unknown"


def test_deadline_is_capped_by_required_result_expiry(make_source: Make, clock: FakeClock) -> None:
    import json

    source, ref = make_source("basic")
    listings = json.loads(source.resources["checks"])
    listings[0]["expires_at"] = clock.now + 100
    source.resources["checks"] = json.dumps(listings).encode()
    acquisition = build_snapshot(
        capture_bundle(source, ref, clock), "fixture", False, source.repo, POLICY
    )
    stored = StoredBasis(acquisition.snapshot.basis_id, dict(acquisition.snapshot.basis_components))
    report = reconcile(source, ref, stored, POLICY, clock)

    assert report.status == "match" and report.deadline == listings[0]["expires_at"]


def test_decision_cas_binds_exact_snapshot_and_view(
    make_source: Make, clock: FakeClock, tmp_path: Path
) -> None:
    source, ref = make_source("basic")
    store = Store(tmp_path / "s.sqlite")
    first = run_review(source, ref, store, fixture_suite(), clock, POLICY, tmp_path / "out")
    decision_id, report = run_decide(
        source, ref, store, POLICY, clock,
        expected_snapshot_id=first.snapshot_id, expected_view_id=first.view_id,
        reviewer="me", decision="request_changes", confidence=60, note="check backoff",
    )  # fmt: skip

    assert decision_id == 1 and report.status == "match"

    apply_mutations(source, ["edit-title"])
    _, _, stale = run_status(source, ref, store, POLICY, clock)

    assert stale.status == "stale"

    second = run_review(source, ref, store, fixture_suite(), clock, POLICY, tmp_path / "out")

    assert second.snapshot_id != first.snapshot_id

    with pytest.raises(StaleExpectation):
        run_decide(
            source, ref, store, POLICY, clock,
            expected_snapshot_id=first.snapshot_id, expected_view_id=first.view_id,
            reviewer="me", decision="approve", confidence=90, note="",
        )  # fmt: skip

    rows = store.decisions(ref.key)

    assert [(row["snapshot_id"], row["view_id"], row["decision"]) for row in rows] == [
        (first.snapshot_id, first.view_id, "request_changes")
    ]
    assert '"status":"match"' in str(rows[0]["freshness"])


def test_invalid_decision_values_rejected(tmp_path: Path) -> None:
    store = Store(tmp_path / "s.sqlite")

    with pytest.raises(ValueError):
        store.record_decision(
            pr_key="k", expected_snapshot_id="s", expected_view_id="v", reviewer="r",
            decision="merge", confidence=None, note="", freshness={},
        )  # fmt: skip


def test_losing_publication_writes_only_canonical_content(
    make_source: Make, clock: FakeClock, tmp_path: Path
) -> None:
    import json

    from prc.comprehension import FixtureAssessor
    from prc.controller import ModelSuite
    from prc.identity import sha256_hex

    source, ref = make_source("basic")
    store = Store(tmp_path / "s.sqlite")
    winner = run_review(source, ref, store, fixture_suite(), clock, POLICY, tmp_path / "out")
    other_suite = ModelSuite(
        fixture_suite().comprehension, (FixtureAssessor(),), fixture_suite().falsifier
    )
    loser = run_review(source, ref, store, other_suite, clock, POLICY, tmp_path / "out")

    assert loser.snapshot_id == winner.snapshot_id and not loser.won_canonicalization
    assert loser.semantic_id == winner.semantic_id and loser.view_id == winner.view_id

    view = json.loads((loser.out_dir / "view.json").read_text())
    semantic = json.loads((loser.out_dir / "semantic.json").read_text())

    for name, digest in view["artifact_hashes"].items():
        assert sha256_hex((loser.out_dir / name).read_bytes()) == digest

    assert len([m for m in semantic["models"] if m["role"] == "assessor"]) == 2
