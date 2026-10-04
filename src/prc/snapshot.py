"""Source Basis Identity, Semantic Input Manifest and Source Snapshot construction."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from prc.gitutil import GitError, merge_base, read_blob, run_git, unified_diff
from prc.identity import (
    CodeComparisonId,
    InventoryId,
    ManifestId,
    SnapshotId,
    SourceBasisId,
    VerificationEvidenceId,
    content_id,
    sha256_hex,
    to_jsonable,
)
from prc.inventory import ChangeSurfaceInventory, build_inventory
from prc.model import (
    CodeComparison,
    Consistency,
    ObservationBundle,
    PrMetadata,
    PrRef,
    VerificationEvidence,
    VerificationGap,
)
from prc.verification import EligibilityPolicy, build_verification, parse_listings

SOURCE_POLICY_VERSION = "source-selection-v1"
COMPREHENSION_VERSION = "comprehension-v1"
VALIDATION_VERSION = "validation-v1"


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    record_id: str
    kind: str
    content_hash: str
    size: int


@dataclass(frozen=True, slots=True)
class SemanticInputManifest:
    """Every record semantic stages may observe, content-addressed before analysis."""

    manifest_id: ManifestId
    records: tuple[ManifestRecord, ...]


@dataclass(frozen=True, slots=True)
class BasisParts:
    comparison: CodeComparison
    comparison_id: CodeComparisonId
    metadata: PrMetadata
    evidence: tuple[tuple[VerificationEvidenceId, VerificationEvidence], ...]
    gaps: tuple[VerificationGap, ...]
    trace_hash: str | None
    basis_id: SourceBasisId

    @property
    def components(self) -> dict[str, str]:
        """Per-component digests so freshness can report what changed."""

        return {
            "comparison": self.comparison_id,
            "metadata": content_id("metadata", self.metadata),
            "verification": content_id(
                "verification-set", [[identity for identity, _ in self.evidence], self.gaps]
            ),
            "trace": self.trace_hash or "none",
        }


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """ReviewSnapshotIdentity plus the timed observation record (outside the identity)."""

    snapshot_id: SnapshotId
    comparison: CodeComparison
    comparison_id: CodeComparisonId
    basis_id: SourceBasisId
    inventory_id: InventoryId
    manifest_id: ManifestId
    comprehension_version: str
    validation_version: str
    consistency: Consistency
    observed_started_at: float
    observed_finished_at: float
    capture_attempts: int
    capture_gaps: tuple[str, ...]
    source_label: str
    live_verified: bool
    verification_gaps: tuple[VerificationGap, ...]
    basis_components: tuple[tuple[str, str], ...]
    required_checks: tuple[str, ...]


@dataclass(slots=True)
class Acquisition:
    """A snapshot with the records it froze; `records` holds manifest content by record id."""

    snapshot: SourceSnapshot
    manifest: SemanticInputManifest
    inventory: ChangeSurfaceInventory
    metadata: PrMetadata
    evidence: tuple[tuple[VerificationEvidenceId, VerificationEvidence], ...]
    records: dict[str, str] = field(default_factory=dict)


def _metadata(raw: dict[str, Any]) -> PrMetadata:
    return PrMetadata(
        title=str(raw["title"]),
        body=str(raw["body"]),
        author=str(raw["author"]),
        labels=tuple(str(label) for label in raw.get("labels", [])),
        draft=bool(raw["draft"]),
        agent_authored=bool(raw["agent_authored"]),
    )


def build_basis(
    bundle: ObservationBundle, repo: Path, eligibility: EligibilityPolicy
) -> BasisParts:
    """Pure function of the captured bundle; freshness reconciliation reuses it unchanged."""

    pr = json.loads(bundle.contents["pr"])
    head_sha = str(pr["head_sha"])
    base_tip = str(pr["base_tip_sha"])
    comparison = CodeComparison(
        repo=f"{bundle.ref.owner}/{bundle.ref.repo}",
        pr_number=bundle.ref.number,
        head_sha=head_sha,
        base_tip_sha=base_tip,
        merge_base_sha=merge_base(repo, base_tip, head_sha),
    )
    comparison_id = CodeComparisonId(content_id("code-comparison", comparison))
    metadata = _metadata(pr)
    listings = parse_listings(bundle.contents["checks"])
    evidence, gaps = build_verification(
        repo, comparison, listings, bundle.contents, eligibility, bundle.finished_at
    )
    trace = bundle.contents.get("trace")
    trace_hash = None if trace is None else sha256_hex(trace)
    basis_id = SourceBasisId(
        content_id(
            "source-basis",
            {
                "comparison": comparison_id,
                "metadata": metadata,
                "verification": [identity for identity, _ in evidence],
                "verification_gaps": gaps,
                "trace": trace_hash,
                "source_policy": SOURCE_POLICY_VERSION,
                "eligibility_policy": eligibility.version,
                "required_checks": sorted(eligibility.required_names),
                "freshness_ttl": eligibility.freshness_ttl_seconds,
            },
        )
    )

    return BasisParts(comparison, comparison_id, metadata, evidence, gaps, trace_hash, basis_id)


def _manifest_records(
    bundle: ObservationBundle,
    basis: BasisParts,
    inventory: ChangeSurfaceInventory,
    repo: Path,
    extra_paths: tuple[str, ...],
) -> dict[str, tuple[str, str]]:
    """record_id -> (kind, text). Only these records are visible to semantic stages."""

    records: dict[str, tuple[str, str]] = {
        "pr-metadata": ("metadata", json.dumps(to_jsonable(basis.metadata), sort_keys=True)),
        "inventory": ("inventory", json.dumps(to_jsonable(inventory.items), sort_keys=True)),
        "verification": (
            "verification",
            json.dumps(
                to_jsonable({"evidence": [e for _, e in basis.evidence], "gaps": basis.gaps}),
                sort_keys=True,
            ),
        ),
    }

    for _, evidence in basis.evidence:
        payload = bundle.contents.get(f"check:{evidence.run_id}:{evidence.attempt}", b"")
        records[f"check:{evidence.run_id}:{evidence.attempt}"] = (
            "check-payload",
            payload.decode("utf-8", "replace"),
        )

    if "trace" in bundle.contents:
        records["trace"] = ("trace", bundle.contents["trace"].decode("utf-8", "replace"))

    for item in inventory.items:
        if item.opaque:
            continue

        records[f"diff:{item.path}"] = (
            "diff",
            f"# {item.path}\n" + unified_diff(repo, item.old_oid, item.new_oid),
        )

        if item.status != "D" and item.surface != "mode_only":
            records[f"head:{item.path}"] = (
                "head-file",
                read_blob(repo, item.new_oid).decode("utf-8", "replace"),
            )

    for path in extra_paths:
        records[f"context:{path}"] = ("context", _context_text(repo, basis.comparison, path))

    return records


def _context_text(repo: Path, comparison: CodeComparison, path: str) -> str:
    try:
        return run_git(repo, "show", f"{comparison.head_sha}:{path}").decode("utf-8", "replace")
    except GitError:
        return ""


def _freeze_manifest(records: dict[str, tuple[str, str]]) -> SemanticInputManifest:
    entries = tuple(
        ManifestRecord(record_id, kind, sha256_hex(text.encode("utf-8")), len(text.encode("utf-8")))
        for record_id, (kind, text) in sorted(records.items())
    )

    return SemanticInputManifest(ManifestId(content_id("manifest", entries)), entries)


def build_snapshot(
    bundle: ObservationBundle,
    source_label: str,
    live_verified: bool,
    repo: Path,
    eligibility: EligibilityPolicy,
    extra_context_paths: tuple[str, ...] = (),
) -> Acquisition:
    """Freeze the manifest, then derive the snapshot identity. Extra context ⇒ new snapshot."""

    basis = build_basis(bundle, repo, eligibility)
    inventory = build_inventory(repo, basis.comparison.merge_base_sha, basis.comparison.head_sha)
    records = _manifest_records(bundle, basis, inventory, repo, tuple(sorted(extra_context_paths)))
    manifest = _freeze_manifest(records)
    snapshot_id = SnapshotId(
        content_id(
            "source-snapshot",
            {
                "comparison": basis.comparison_id,
                "basis": basis.basis_id,
                "inventory": inventory.inventory_id,
                "manifest": manifest.manifest_id,
                "comprehension": COMPREHENSION_VERSION,
                "validation": VALIDATION_VERSION,
            },
        )
    )
    snapshot = SourceSnapshot(
        snapshot_id=snapshot_id,
        comparison=basis.comparison,
        comparison_id=basis.comparison_id,
        basis_id=basis.basis_id,
        inventory_id=inventory.inventory_id,
        manifest_id=manifest.manifest_id,
        comprehension_version=COMPREHENSION_VERSION,
        validation_version=VALIDATION_VERSION,
        consistency=bundle.consistency,
        observed_started_at=bundle.started_at,
        observed_finished_at=bundle.finished_at,
        capture_attempts=bundle.attempts,
        capture_gaps=bundle.gaps,
        source_label=source_label,
        live_verified=live_verified,
        verification_gaps=basis.gaps,
        basis_components=tuple(sorted(basis.components.items())),
        required_checks=tuple(sorted(eligibility.required_names)),
    )

    return Acquisition(
        snapshot,
        manifest,
        inventory,
        basis.metadata,
        basis.evidence,
        {record_id: text for record_id, (_, text) in records.items()},
    )


def ref_of(snapshot: SourceSnapshot) -> PrRef:
    owner, repo = snapshot.comparison.repo.split("/", 1)

    return PrRef(owner, repo, snapshot.comparison.pr_number)
