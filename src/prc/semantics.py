"""Semantic types. Candidates are untrusted model output; validated types are controller output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AssertionKind = Literal[
    "claim",
    "inference",
    "agent_report",
    "relation",
    "grouping",
    "order",
    "emphasis",
    "priority",
    "non_material",
    "uncertainty",
]
CLAIMED_STATES = ("supported", "inference", "agent_report", "uncertainty")
ClaimedState = Literal["supported", "inference", "agent_report", "uncertainty"]
ValidatedState = Literal["supported", "inference", "agent_report", "uncertainty", "gap"]
SupportBasis = Literal["mechanical", "model_assessed", "none"]
MechanicalCheckName = Literal["path_changed", "quote_present", "check_conclusion"]
VerdictName = Literal["supported", "inference_only", "unsupported", "ambiguous"]
SEMANTIC_KINDS: frozenset[str] = frozenset(
    {"relation", "grouping", "order", "emphasis", "priority"}
)


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    record_id: str
    quote: str | None = None


@dataclass(frozen=True, slots=True)
class MechanicalCheck:
    check: MechanicalCheckName
    args: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CandidateAssertion:
    assertion_id: str
    kind: AssertionKind
    claimed_state: ClaimedState
    text: str
    evidence: tuple[EvidenceRef, ...] = ()
    mechanical: MechanicalCheck | None = None
    universal: bool = False
    scope_witness: str | None = None
    subject_ids: tuple[str, ...] = ()
    relation: tuple[str, str] | None = None


@dataclass(frozen=True, slots=True)
class CandidateConcept:
    concept_id: str
    title: str
    summary: str
    assertion_ids: tuple[str, ...]
    relevance: int
    relevance_assertion_id: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateCoverage:
    item_id: str
    concept_ids: tuple[str, ...]
    residual: Literal["closed", "open"]
    nonmaterial_assertion_id: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateSemantics:
    assertions: tuple[CandidateAssertion, ...]
    concepts: tuple[CandidateConcept, ...]
    coverage: tuple[CandidateCoverage, ...]


@dataclass(frozen=True, slots=True)
class Verdict:
    verdict: VerdictName
    rationale: str


@dataclass(frozen=True, slots=True)
class AssessorResult:
    assessor: str
    verdict: Verdict


@dataclass(frozen=True, slots=True)
class ValidatedAssertion:
    assertion_id: str
    kind: AssertionKind
    text: str
    state: ValidatedState
    basis: SupportBasis
    evidence: tuple[EvidenceRef, ...]
    limitations: tuple[str, ...]
    policy_version: str
    assessments: tuple[AssessorResult, ...]
    disagreement: bool
    downgrade_reason: str | None
    subject_ids: tuple[str, ...]
    relation: tuple[str, str] | None


@dataclass(frozen=True, slots=True)
class ValidatedConcept:
    concept_id: str
    title: str
    summary: str
    assertion_ids: tuple[str, ...]
    relevance: int | None
    group_assertion_id: str | None


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    item_id: str
    path: str
    concept_ids: tuple[str, ...]
    residual: Literal["closed", "open"]
    closure: str


@dataclass(frozen=True, slots=True)
class CoverageGap:
    gap_id: str
    kind: str
    subject: str
    reason: str


@dataclass(frozen=True, slots=True)
class FalsifierFinding:
    item_id: str
    verdict: Literal["closed", "open"]
    reason: str
    needed_context: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelProvenance:
    role: str
    label: str
    version: str
    fixture: bool


@dataclass(frozen=True, slots=True)
class ValidatedSemanticArtifact:
    snapshot_id: str
    validation_version: str
    concepts: tuple[ValidatedConcept, ...]
    assertions: tuple[ValidatedAssertion, ...]
    ledger: tuple[LedgerEntry, ...]
    gaps: tuple[CoverageGap, ...]
    models: tuple[ModelProvenance, ...]
