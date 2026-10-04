"""Project a validated semantic artifact into a presentation document. No new semantics here."""

from __future__ import annotations

import json
from collections import Counter

from prc.identity import SemanticArtifactId
from prc.presentation.doc import (
    ClaimView,
    ConceptView,
    EdgeView,
    EvidenceLink,
    Excerpt,
    GapView,
    Infographic,
    InfographicNode,
    InventoryRow,
    PresentationDoc,
    TraceEvent,
)
from prc.presentation.urlpolicy import anchor_for, github_blob_url
from prc.semantics import ValidatedAssertion, ValidatedSemanticArtifact
from prc.snapshot import Acquisition

STATE_RANK = {"supported": 0, "agent_report": 1, "inference": 2, "uncertainty": 3, "gap": 4}
LIVE_LABEL = "github"


def _links(
    assertion: ValidatedAssertion, acquisition: Acquisition, live: bool
) -> tuple[EvidenceLink, ...]:
    comparison = acquisition.snapshot.comparison
    paths = {item.path for item in acquisition.inventory.items}
    links: list[EvidenceLink] = []

    for ref in assertion.evidence:
        url = None
        path = ref.record_id.split(":", 1)[-1]

        if live and ref.record_id.startswith(("head:", "diff:")) and path in paths:
            url = github_blob_url(comparison.repo, comparison.head_sha, path)

        links.append(EvidenceLink(ref.record_id, ref.quote, anchor_for(ref.record_id), url))

    return tuple(links)


def _claim(assertion: ValidatedAssertion, acquisition: Acquisition, live: bool) -> ClaimView:
    return ClaimView(
        assertion.assertion_id,
        assertion.kind,
        assertion.text,
        assertion.state,
        assertion.basis,
        assertion.limitations,
        assertion.disagreement,
        assertion.downgrade_reason,
        _links(assertion, acquisition, live),
    )


def build_document(
    acquisition: Acquisition, artifact: ValidatedSemanticArtifact, semantic_id: SemanticArtifactId
) -> PresentationDoc:
    snapshot = acquisition.snapshot
    live = snapshot.source_label == LIVE_LABEL and snapshot.live_verified
    by_id = {assertion.assertion_id: assertion for assertion in artifact.assertions}
    concept_views: list[ConceptView] = []

    for concept in artifact.concepts:
        claims = tuple(_claim(by_id[aid], acquisition, live) for aid in concept.assertion_ids)
        group_state = (
            by_id[concept.group_assertion_id].state if concept.group_assertion_id else "gap"
        )
        concept_views.append(
            ConceptView(
                concept.concept_id,
                concept.title,
                concept.summary,
                concept.relevance,
                concept.group_assertion_id,
                group_state,
                claims,
            )
        )

    emphasis = next(
        (
            a
            for a in artifact.assertions
            if a.kind == "emphasis" and a.state in ("supported", "inference")
        ),
        None,
    )
    emphasized = emphasis.subject_ids[0] if emphasis and emphasis.subject_ids else None
    nodes = tuple(
        InfographicNode(
            view.concept_id,
            view.title,
            view.relevance,
            view.concept_id == emphasized,
            view.group_state,
            max((c.state for c in view.claims), key=lambda s: STATE_RANK[s], default="gap"),
            len(view.claims),
        )
        for view in concept_views
    )
    concept_ids = {view.concept_id for view in concept_views}
    edges = tuple(
        EdgeView(a.assertion_id, a.relation[0], a.relation[1], a.text, a.state)
        for a in artifact.assertions
        if a.kind == "relation"
        and a.relation
        and a.state in ("supported", "inference")
        and a.relation[0] in concept_ids
        and a.relation[1] in concept_ids
    )
    ledger_state = {entry.path: entry for entry in artifact.ledger}
    inventory = tuple(
        InventoryRow(
            item.path,
            item.status,
            item.surface + (" (opaque)" if item.opaque else ""),
            f"+{item.added_lines}/-{item.removed_lines}",
            ledger_state[item.path].closure,
        )
        for item in acquisition.inventory.items
    )
    trace = tuple(
        TraceEvent(str(event["step"]), str(event["tool"]), str(event["summary"]))
        for event in json.loads(acquisition.records.get("trace", "[]"))
    )
    cited = sorted({ref.record_id for a in artifact.assertions for ref in a.evidence})
    excerpts = tuple(
        Excerpt(record_id, anchor_for(record_id), acquisition.records[record_id][:4000])
        for record_id in cited
        if record_id in acquisition.records
    )
    counts = Counter(a.state for a in artifact.assertions)
    prose = (
        f"{len(artifact.concepts)} behavioural concept(s) across "
        f"{len(acquisition.inventory.items)} changed surface(s).",
        f"Assertions: {counts['supported']} supported, {counts['inference']} inference, "
        f"{counts['agent_report']} agent report, {counts['uncertainty']} uncertainty, "
        f"{counts['gap']} gap.",
        "Required checks: "
        + (
            ", ".join(snapshot.required_checks)
            if snapshot.required_checks
            else "none configured; all checks are informational"
        )
        + ".",
        f"{len(artifact.gaps)} coverage gap(s) remain."
        if artifact.gaps
        else "No coverage gaps were recorded; semantic closure remains a falsification-backed claim.",
    )

    return PresentationDoc(
        title=acquisition.metadata.title,
        pr_key=f"{snapshot.comparison.repo}#{snapshot.comparison.pr_number}",
        snapshot_id=snapshot.snapshot_id,
        semantic_id=semantic_id,
        source_label=snapshot.source_label,
        live_verified=snapshot.live_verified,
        consistency=snapshot.consistency,
        concepts=tuple(concept_views),
        infographic=Infographic(nodes, edges, emphasis.assertion_id if emphasis else None),
        inventory=inventory,
        trace=trace,
        gaps=tuple(GapView(g.gap_id, g.kind, g.subject, g.reason) for g in artifact.gaps),
        excerpts=excerpts,
        models=artifact.models,
        prose=prose,
    )
