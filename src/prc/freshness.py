"""Observed freshness: reconcile the full Source Basis Identity, never promise currentness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prc.capture import Clock, capture_bundle
from prc.model import PrRef
from prc.snapshot import build_basis
from prc.source import PullRequestSource
from prc.verification import EligibilityPolicy

Status = Literal["match", "stale", "unknown"]


@dataclass(frozen=True, slots=True)
class StoredBasis:
    basis_id: str
    components: dict[str, str]


@dataclass(frozen=True, slots=True)
class FreshnessReport:
    """Last observed relation between a pinned snapshot and the provider, with a finite deadline."""

    status: Status
    observed_started_at: float
    observed_finished_at: float
    resource_times: tuple[tuple[str, float], ...]
    deadline: float
    differences: tuple[str, ...]
    detail: str

    def effective(self, now: float) -> str:
        """`match` stops being fresh once its deadline passes."""

        if self.status == "match" and now > self.deadline:
            return "expired"

        return self.status


def reconcile(
    source: PullRequestSource,
    ref: PrRef,
    snapshot: StoredBasis,
    policy: EligibilityPolicy,
    clock: Clock,
) -> FreshnessReport:
    bundle = capture_bundle(source, ref, clock)
    times = tuple((obs.key, obs.observed_at) for obs in bundle.observations)
    deadline = bundle.finished_at + policy.freshness_ttl_seconds

    if bundle.consistency == "unknown":
        return FreshnessReport(
            "unknown",
            bundle.started_at,
            bundle.finished_at,
            times,
            bundle.finished_at,
            (),
            "; ".join(bundle.gaps),
        )

    basis = build_basis(bundle, source.repo_path(ref), policy)
    stored = snapshot.components
    differences = tuple(
        sorted(name for name, digest in basis.components.items() if stored.get(name) != digest)
    )

    if basis.basis_id != snapshot.basis_id or differences:
        return FreshnessReport(
            "stale",
            bundle.started_at,
            bundle.finished_at,
            times,
            bundle.finished_at,
            differences or ("policy",),
            "source basis differs from the pinned snapshot",
        )

    expiries = [
        evidence.expires_at
        for _, evidence in basis.evidence
        if evidence.eligibility == "eligible" and evidence.expires_at is not None
    ]
    deadline = min([deadline, *expiries])

    return FreshnessReport(
        "match",
        bundle.started_at,
        bundle.finished_at,
        times,
        deadline,
        (),
        "full source basis matched at observation; not an atomic provider state",
    )
