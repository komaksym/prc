"""Acquisition-side domain types. Pure data; no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Consistency = Literal["stable", "unknown"]
CheckScope = Literal["head_only", "merged_behavior"]
SubjectKind = Literal["commit", "tree"]
Eligibility = Literal[
    "eligible",
    "expired",
    "subject_mismatch",
    "missing_provenance",
    "conflicting_provenance",
]


@dataclass(frozen=True, slots=True)
class PrRef:
    owner: str
    repo: str
    number: int

    @property
    def key(self) -> str:
        return f"{self.owner}/{self.repo}#{self.number}"


@dataclass(frozen=True, slots=True)
class CodeComparison:
    """Everything needed to derive the change; contains no check data and no trace."""

    repo: str
    pr_number: int
    head_sha: str
    base_tip_sha: str
    merge_base_sha: str


@dataclass(frozen=True, slots=True)
class PrMetadata:
    title: str
    body: str
    author: str
    labels: tuple[str, ...]
    draft: bool
    agent_authored: bool


@dataclass(frozen=True, slots=True)
class CheckListing:
    """One check run as listed by the provider; its payload is a separate resource."""

    run_id: str
    attempt: int
    provider: str
    name: str
    scope: CheckScope
    subject_sha: str | None
    subject_kind: SubjectKind
    conclusion: str
    completed_at: float
    expires_at: float | None
    required: bool

    @property
    def resource_key(self) -> str:
        return f"check:{self.run_id}:{self.attempt}"


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    """One check result with its own execution subject; never alters CodeComparison."""

    run_id: str
    attempt: int
    provider: str
    name: str
    scope: CheckScope
    subject_sha: str | None
    subject_kind: SubjectKind
    subject_tree: str | None
    conclusion: str
    payload_hash: str
    completed_at: float
    expires_at: float | None
    eligibility: Eligibility
    required: bool


@dataclass(frozen=True, slots=True)
class VerificationGap:
    name: str
    reason: str


@dataclass(frozen=True, slots=True)
class ResourceObservation:
    key: str
    version: str
    content_hash: str
    observed_at: float


@dataclass(frozen=True, slots=True)
class ObservationBundle:
    """Timed observations. Stability is observational, never an atomic provider instant."""

    ref: PrRef
    contents: dict[str, bytes]
    observations: tuple[ResourceObservation, ...]
    started_at: float
    finished_at: float
    attempts: int
    consistency: Consistency
    gaps: tuple[str, ...] = field(default=())
