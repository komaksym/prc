"""Typed presentation document: source strings are plain values; semantics reference ids."""

from __future__ import annotations

from dataclasses import dataclass

from prc.semantics import ModelProvenance


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    record_id: str
    quote: str | None
    anchor: str
    url: str | None


@dataclass(frozen=True, slots=True)
class ClaimView:
    assertion_id: str
    kind: str
    text: str
    state: str
    basis: str
    limitations: tuple[str, ...]
    disagreement: bool
    downgrade_reason: str | None
    evidence: tuple[EvidenceLink, ...]


@dataclass(frozen=True, slots=True)
class ConceptView:
    concept_id: str
    title: str
    summary: str
    relevance: int | None
    group_assertion_id: str | None
    group_state: str
    claims: tuple[ClaimView, ...]


@dataclass(frozen=True, slots=True)
class EdgeView:
    assertion_id: str
    source: str
    target: str
    text: str
    state: str


@dataclass(frozen=True, slots=True)
class InfographicNode:
    concept_id: str
    title: str
    relevance: int | None
    emphasized: bool
    group_state: str
    worst_state: str
    claim_count: int


@dataclass(frozen=True, slots=True)
class Infographic:
    nodes: tuple[InfographicNode, ...]
    edges: tuple[EdgeView, ...]
    emphasis_assertion_id: str | None


@dataclass(frozen=True, slots=True)
class InventoryRow:
    path: str
    status: str
    surface: str
    lines: str
    coverage: str


@dataclass(frozen=True, slots=True)
class TraceEvent:
    step: str
    tool: str
    summary: str


@dataclass(frozen=True, slots=True)
class GapView:
    gap_id: str
    kind: str
    subject: str
    reason: str


@dataclass(frozen=True, slots=True)
class Excerpt:
    record_id: str
    anchor: str
    text: str


@dataclass(frozen=True, slots=True)
class PresentationDoc:
    title: str
    pr_key: str
    snapshot_id: str
    semantic_id: str
    source_label: str
    live_verified: bool
    consistency: str
    concepts: tuple[ConceptView, ...]
    infographic: Infographic
    inventory: tuple[InventoryRow, ...]
    trace: tuple[TraceEvent, ...]
    gaps: tuple[GapView, ...]
    excerpts: tuple[Excerpt, ...]
    models: tuple[ModelProvenance, ...]
    prose: tuple[str, ...]
