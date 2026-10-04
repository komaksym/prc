"""Snapshot acquisition: enumerate, capture, reread, retry at most three times."""

from __future__ import annotations

from collections.abc import Callable

from prc.identity import sha256_hex
from prc.model import ObservationBundle, PrRef, ResourceObservation
from prc.source import PullRequestSource, SourceError

MAX_ATTEMPTS = 3
REQUIRED_KEYS = ("pr", "checks")

Clock = Callable[[], float]


def capture_bundle(
    source: PullRequestSource, ref: PrRef, clock: Clock, max_attempts: int = MAX_ATTEMPTS
) -> ObservationBundle:
    """Capture the resource set, then reread membership and versions to detect drift.

    A matching reread establishes observational stability only. Missing required
    resources, fetch failures or drift on every attempt yield ``unknown`` consistency.
    """

    started_at = clock()
    gaps: list[str] = []
    contents: dict[str, bytes] = {}
    observations: tuple[ResourceObservation, ...] = ()

    for attempt in range(1, max_attempts + 1):
        try:
            before = source.enumerate(ref)
            missing = [key for key in REQUIRED_KEYS if key not in before]

            if missing:
                gaps.append(f"attempt {attempt}: required resources missing: {missing}")
                continue

            contents = {}
            observed: list[ResourceObservation] = []

            for key in sorted(before):
                body = source.fetch(ref, key)
                contents[key] = body
                observed.append(ResourceObservation(key, before[key], sha256_hex(body), clock()))

            observations = tuple(observed)
            after = source.enumerate(ref)
        except SourceError as error:
            gaps.append(f"attempt {attempt}: {error}")
            continue

        if after == before:
            return ObservationBundle(
                ref, contents, observations, started_at, clock(), attempt, "stable", ()
            )

        drifted = sorted(
            key for key in set(before) | set(after) if before.get(key) != after.get(key)
        )
        gaps.append(f"attempt {attempt}: drift detected in {drifted}")

    return ObservationBundle(
        ref, contents, observations, started_at, clock(), max_attempts, "unknown", tuple(gaps)
    )
