"""Per-check verification evidence with its own subject and eligibility."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from prc.gitutil import GitError, merge_tree, run_git, tree_of
from prc.identity import VerificationEvidenceId, content_id, sha256_hex
from prc.model import (
    CheckListing,
    CodeComparison,
    Eligibility,
    VerificationEvidence,
    VerificationGap,
)


@dataclass(frozen=True, slots=True)
class EligibilityPolicy:
    version: str = "eligibility-v1"
    required_names: tuple[str, ...] = ("unit-tests", "merged-ci")
    freshness_ttl_seconds: float = 900.0


def parse_listings(raw: bytes) -> list[CheckListing]:
    """Parse untrusted provider listings; an unrecognized scope or subject drops provenance."""

    listings: list[CheckListing] = []

    for entry in json.loads(raw):
        scope = entry.get("scope")
        kind = entry.get("subject_kind")
        subject = entry.get("subject_sha")
        recognized = scope in ("head_only", "merged_behavior") and kind in ("commit", "tree")
        listings.append(
            CheckListing(
                run_id=str(entry["run_id"]),
                attempt=int(entry["attempt"]),
                provider=str(entry["provider"]),
                name=str(entry["name"]),
                scope=scope if recognized else "merged_behavior",
                subject_sha=str(subject)
                if recognized and isinstance(subject, str) and subject
                else None,
                subject_kind=kind if recognized else "commit",
                conclusion=str(entry["conclusion"]),
                completed_at=float(entry["completed_at"]),
                expires_at=None if entry.get("expires_at") is None else float(entry["expires_at"]),
                required=bool(entry["required"]),
            )
        )

    return listings


def _subject_tree(repo: Path, listing: CheckListing) -> str | None:
    if listing.subject_sha is None:
        return None

    try:
        if listing.subject_kind == "tree":
            run_git(repo, "cat-file", "-e", listing.subject_sha)
            return listing.subject_sha

        return tree_of(repo, listing.subject_sha)
    except GitError:
        return None


def _declared_payload_subject(payload: bytes) -> str | None:
    for line in payload.decode("utf-8", "replace").splitlines():
        if line.startswith("X-Subject:"):
            return line.split(":", 1)[1].strip()

    return None


def _eligibility(
    repo: Path,
    listing: CheckListing,
    payload: bytes,
    comparison: CodeComparison,
    subject_tree: str | None,
    observed_at: float,
) -> Eligibility:
    declared = _declared_payload_subject(payload)

    if listing.subject_sha is None or subject_tree is None:
        return "missing_provenance"

    if declared is not None and declared != listing.subject_sha:
        return "conflicting_provenance"

    if listing.expires_at is not None and listing.expires_at <= observed_at:
        return "expired"

    if listing.scope == "head_only":
        return (
            "eligible" if subject_tree == tree_of(repo, comparison.head_sha) else "subject_mismatch"
        )

    expected = merge_tree(repo, comparison.base_tip_sha, comparison.head_sha)

    if expected is None:
        return "missing_provenance"

    return "eligible" if subject_tree == expected else "subject_mismatch"


def build_verification(
    repo: Path,
    comparison: CodeComparison,
    listings: list[CheckListing],
    payloads: dict[str, bytes],
    policy: EligibilityPolicy,
    observed_at: float,
) -> tuple[
    tuple[tuple[VerificationEvidenceId, VerificationEvidence], ...], tuple[VerificationGap, ...]
]:
    """Select in-scope evidence and record every required result that is not usable."""

    selected: list[tuple[VerificationEvidenceId, VerificationEvidence]] = []

    for listing in sorted(listings, key=lambda entry: (entry.name, entry.run_id, entry.attempt)):
        payload = payloads.get(listing.resource_key, b"")
        subject_tree = _subject_tree(repo, listing)
        evidence = VerificationEvidence(
            run_id=listing.run_id,
            attempt=listing.attempt,
            provider=listing.provider,
            name=listing.name,
            scope=listing.scope,
            subject_sha=listing.subject_sha,
            subject_kind=listing.subject_kind,
            subject_tree=subject_tree,
            conclusion=listing.conclusion,
            payload_hash=sha256_hex(payload),
            completed_at=listing.completed_at,
            expires_at=listing.expires_at,
            eligibility=_eligibility(repo, listing, payload, comparison, subject_tree, observed_at),
            required=listing.required,
        )
        selected.append((VerificationEvidenceId(content_id("verification", evidence)), evidence))

    gaps: list[VerificationGap] = []

    for name in policy.required_names:
        matching = [evidence for _, evidence in selected if evidence.name == name]

        if not matching:
            gaps.append(VerificationGap(name, "required result missing"))
        elif not any(evidence.eligibility == "eligible" for evidence in matching):
            reasons = sorted({evidence.eligibility for evidence in matching})
            gaps.append(VerificationGap(name, f"no eligible result: {', '.join(reasons)}"))

    return tuple(selected), tuple(gaps)
