"""Many-to-many coverage ledger over the mechanical inventory, closed by independent falsification."""

from __future__ import annotations

from prc.inventory import InventoryItem
from prc.semantics import (
    CandidateCoverage,
    CoverageGap,
    FalsifierFinding,
    LedgerEntry,
    ValidatedAssertion,
    ValidatedConcept,
)

USABLE = ("supported", "inference", "agent_report")


def build_ledger(
    inventory: tuple[InventoryItem, ...],
    candidates: tuple[CandidateCoverage, ...],
    concepts: tuple[ValidatedConcept, ...],
    assertions: tuple[ValidatedAssertion, ...],
    findings: tuple[FalsifierFinding, ...],
    manifest_records: frozenset[str],
) -> tuple[tuple[LedgerEntry, ...], tuple[CoverageGap, ...]]:
    """Every inventory item gets an entry; anything not provably closed becomes a visible gap."""

    by_item = {candidate.item_id: candidate for candidate in candidates}
    by_assertion = {assertion.assertion_id: assertion for assertion in assertions}
    findings_by_item = {finding.item_id: finding for finding in findings}
    usable_concepts = {
        concept.concept_id
        for concept in concepts
        if any(by_assertion[aid].state in USABLE for aid in concept.assertion_ids)
    }
    entries: list[LedgerEntry] = []
    gaps: list[CoverageGap] = []

    for item in inventory:
        candidate = by_item.get(item.item_id)
        finding = findings_by_item.get(item.item_id)
        item_gaps = _item_gaps(item, candidate, finding, by_assertion, manifest_records)
        mapped = tuple(
            concept_id
            for concept_id in (candidate.concept_ids if candidate else ())
            if concept_id in usable_concepts
        )
        nonmaterial = (
            by_assertion.get(candidate.nonmaterial_assertion_id or "") if candidate else None
        )
        closed_by_nonmaterial = (
            nonmaterial is not None
            and nonmaterial.kind == "non_material"
            and nonmaterial.state == "supported"
        )

        if not mapped and not closed_by_nonmaterial and not item_gaps:
            item_gaps.append(
                ("unmapped", "no validated concept or validated non-material determination")
            )

        gaps.extend(
            CoverageGap(f"g:{len(gaps) + offset + 1}", kind, item.path, reason)
            for offset, (kind, reason) in enumerate(item_gaps)
        )
        entries.append(
            LedgerEntry(
                item.item_id,
                item.path,
                mapped,
                "open" if item_gaps else "closed",
                "residual open: see gaps"
                if item_gaps
                else (
                    "validated non-material"
                    if closed_by_nonmaterial and not mapped
                    else "mapped and falsification-closed"
                ),
            )
        )

    return tuple(entries), tuple(gaps)


def _item_gaps(
    item: InventoryItem,
    candidate: CandidateCoverage | None,
    finding: FalsifierFinding | None,
    by_assertion: dict[str, ValidatedAssertion],
    manifest_records: frozenset[str],
) -> list[tuple[str, str]]:
    gaps: list[tuple[str, str]] = []

    if item.opaque:
        gaps.append(("opaque", item.note))

    if candidate is None:
        gaps.append(("no_coverage_entry", "comprehension supplied no coverage entry"))
    elif candidate.residual == "open" and not item.opaque:
        gaps.append(("residual_open", "comprehension left a residual open"))

    if candidate is not None and candidate.nonmaterial_assertion_id is not None:
        nonmaterial = by_assertion.get(candidate.nonmaterial_assertion_id)

        if (
            nonmaterial is None
            or nonmaterial.kind != "non_material"
            or nonmaterial.state != "supported"
        ):
            gaps.append(("unvalidated_non_material", "non-material determination not validated"))

    if finding is None:
        gaps.append(("not_falsified", "closure falsification returned nothing for this item"))
    elif finding.verdict == "open":
        missing = [name for name in finding.needed_context if name not in manifest_records]
        suffix = f"; needs context {missing} (requires a new snapshot)" if missing else ""

        if not item.opaque:
            gaps.append(("falsification_open", finding.reason + suffix))

    return gaps
