"""Claim Validation: controller-enforced bindings, deterministic checks, visible model support.

Generator and assessor outputs are untrusted. The controller alone assigns state and basis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from prc.comprehension import SupportAssessor
from prc.inventory import InventoryItem
from prc.semantics import (
    SEMANTIC_KINDS,
    AssessorResult,
    CandidateAssertion,
    CandidateConcept,
    CandidateSemantics,
    EvidenceRef,
    MechanicalCheck,
    SupportBasis,
    ValidatedAssertion,
    ValidatedConcept,
    ValidatedState,
    Verdict,
)

VERDICTS = ("supported", "inference_only", "unsupported", "ambiguous")

MAX_TEXT = 600
SCOPE_KINDS = frozenset({"non_material"})
MODEL_LIMITATION = "model-assessed support is fallible and not proof of truth"


@dataclass(frozen=True, slots=True)
class ValidationContext:
    records: Mapping[str, str]
    inventory: tuple[InventoryItem, ...]
    policy_version: str


def mechanical_text(check: MechanicalCheck) -> str | None:
    """The only claim text a mechanical check can certify. Owned by the controller, not models."""

    args = dict(check.args)

    if check.check == "path_changed":
        return f"{args.get('path')} status {args.get('status')}: +{args.get('added')}/-{args.get('removed')} lines"

    if check.check == "quote_present":
        record = args.get("record", "")

        if not record.startswith("head:"):
            return None

        return f"{record[len('head:') :]} now contains the line: {args.get('quote', '').strip()}"

    return f"Check {args.get('name')} concluded {args.get('conclusion')} on its own subject"


def _run_mechanical(check: MechanicalCheck, context: ValidationContext) -> str | None:
    """Return None on pass, otherwise the failure reason."""

    args = dict(check.args)

    if check.check == "path_changed":
        for item in context.inventory:
            if (
                item.path == args.get("path")
                and item.status == args.get("status")
                and str(item.added_lines) == args.get("added")
                and str(item.removed_lines) == args.get("removed")
            ):
                return None

        return "inventory has no matching changed path"

    if check.check == "quote_present":
        record = context.records.get(args.get("record", ""))
        quote = args.get("quote", "")

        if record is not None and quote and quote in record:
            return None

        return "quote not found verbatim in record"

    verification = json.loads(context.records.get("verification", '{"evidence": []}'))

    for evidence in verification["evidence"]:
        if (
            evidence["name"] == args.get("name")
            and evidence["conclusion"] == args.get("conclusion")
            and evidence["eligibility"] == "eligible"
        ):
            return None

    return "no eligible archived check with that conclusion"


def _bound_evidence(
    assertion: CandidateAssertion, context: ValidationContext
) -> tuple[tuple[EvidenceRef, ...], list[str]]:
    kept: list[EvidenceRef] = []
    problems: list[str] = []

    for ref in assertion.evidence:
        record = context.records.get(ref.record_id)

        if record is None:
            problems.append(f"evidence record {ref.record_id!r} is not in the manifest")
        elif ref.quote is not None and ref.quote not in record:
            problems.append(f"quote not verbatim in {ref.record_id!r}")
        else:
            kept.append(ref)

    return tuple(kept), problems


def _build(
    candidate: CandidateAssertion,
    state: ValidatedState,
    basis: SupportBasis,
    evidence: tuple[EvidenceRef, ...],
    context: ValidationContext,
    limitations: Sequence[str] = (),
    assessments: tuple[AssessorResult, ...] = (),
    disagreement: bool = False,
    reason: str | None = None,
) -> ValidatedAssertion:
    return ValidatedAssertion(
        assertion_id=candidate.assertion_id,
        kind=candidate.kind,
        text=candidate.text,
        state=state,
        basis=basis,
        evidence=evidence,
        limitations=tuple(limitations),
        policy_version=context.policy_version,
        assessments=assessments,
        disagreement=disagreement,
        downgrade_reason=reason,
        subject_ids=candidate.subject_ids,
        relation=candidate.relation,
    )


def validate_assertion(
    candidate: CandidateAssertion,
    context: ValidationContext,
    assessors: Sequence[SupportAssessor],
    concept_ids: frozenset[str],
) -> ValidatedAssertion:
    evidence, problems = _bound_evidence(candidate, context)

    if len(candidate.text) > MAX_TEXT or not candidate.text.strip():
        return _build(candidate, "gap", "none", (), context, reason="text empty or over length")

    if candidate.claimed_state == "uncertainty":
        return _build(
            candidate, "uncertainty", "none", evidence, context, ("stated as uncertainty",)
        )

    if problems:
        return _build(candidate, "gap", "none", evidence, context, reason="; ".join(problems))

    if candidate.claimed_state == "agent_report":
        cites_trace = bool(evidence) and all(ref.record_id == "trace" for ref in evidence)

        if not cites_trace:
            return _build(
                candidate,
                "gap",
                "none",
                evidence,
                context,
                reason="agent report must cite the trace",
            )

        basis: SupportBasis = "mechanical" if all(ref.quote for ref in evidence) else "none"

        return _build(
            candidate,
            "agent_report",
            basis,
            evidence,
            context,
            ("agent statement; does not establish a codebase fact",),
        )

    if candidate.kind in SEMANTIC_KINDS:
        unknown = [ref for ref in candidate.subject_ids if ref not in concept_ids]

        if unknown or (
            candidate.kind == "relation" and not _valid_relation(candidate, concept_ids)
        ):
            return _build(
                candidate,
                "gap",
                "none",
                evidence,
                context,
                reason=f"unknown or invalid subjects {unknown}",
            )

    if candidate.mechanical is not None:
        applicable = (
            candidate.kind == "claim"
            and not candidate.universal
            and candidate.scope_witness is None
            and candidate.text == mechanical_text(candidate.mechanical)
        )

        if not applicable:
            return _build(
                candidate,
                "gap",
                "none",
                evidence,
                context,
                reason="mechanical check does not certify this assertion's kind or text",
            )

        failure = _run_mechanical(candidate.mechanical, context)

        if failure is not None:
            return _build(
                candidate,
                "gap",
                "none",
                evidence,
                context,
                reason=f"mechanical check failed: {failure}",
            )

        return _build(
            candidate, "supported", "mechanical", evidence, context, ("checks the cited fact only",)
        )

    if not evidence:
        return _build(
            candidate, "uncertainty", "none", evidence, context, reason="no evidence supplied"
        )

    needs_witness = candidate.kind in SCOPE_KINDS or candidate.universal

    if needs_witness and (
        candidate.scope_witness is None or candidate.scope_witness not in context.records
    ):
        return _build(
            candidate,
            "uncertainty",
            "none",
            evidence,
            context,
            reason="universal/negative/non-material claim lacks a pinned scope witness",
        )

    return _assess(candidate, evidence, context, assessors)


def _valid_relation(candidate: CandidateAssertion, concept_ids: frozenset[str]) -> bool:
    return (
        candidate.relation is not None
        and candidate.relation[0] in concept_ids
        and candidate.relation[1] in concept_ids
        and candidate.relation[0] != candidate.relation[1]
    )


ASSESSOR_FAILURE = "assessor failure"


def _safe_assess(
    assessor: SupportAssessor, candidate: CandidateAssertion, texts: Mapping[str, str]
) -> Verdict:
    """Validator output is untrusted too: a crash or malformed verdict counts as ambiguous."""

    try:
        verdict = assessor.assess(candidate, texts)
    except Exception as error:
        return Verdict("ambiguous", f"{ASSESSOR_FAILURE}: {type(error).__name__}")

    if not isinstance(verdict, Verdict) or verdict.verdict not in VERDICTS:
        return Verdict("ambiguous", f"{ASSESSOR_FAILURE}: malformed verdict")

    return verdict


def _assess(
    candidate: CandidateAssertion,
    evidence: tuple[EvidenceRef, ...],
    context: ValidationContext,
    assessors: Sequence[SupportAssessor],
) -> ValidatedAssertion:
    texts = {ref.record_id: context.records[ref.record_id] for ref in evidence}

    if candidate.scope_witness is not None and candidate.scope_witness in context.records:
        texts[candidate.scope_witness] = context.records[candidate.scope_witness]

    results = tuple(
        AssessorResult(assessor.label, _safe_assess(assessor, candidate, texts))
        for assessor in assessors
    )
    verdicts = {result.verdict.verdict for result in results}
    limitations = (MODEL_LIMITATION,)
    disagreement = len(verdicts) > 1

    if not results:
        return _build(
            candidate, "uncertainty", "none", evidence, context, reason="no assessor configured"
        )

    if verdicts == {"supported"} and candidate.claimed_state == "supported":
        return _build(
            candidate, "supported", "model_assessed", evidence, context, limitations, results
        )

    if verdicts <= {"supported", "inference_only"}:
        reason = "assessors disagree" if disagreement else "support limited to inference"

        return _build(
            candidate,
            "inference",
            "model_assessed",
            evidence,
            context,
            limitations,
            results,
            disagreement,
            reason,
        )

    if verdicts == {"unsupported"}:
        return _build(
            candidate,
            "gap",
            "none",
            evidence,
            context,
            limitations,
            results,
            False,
            "assessors found no support",
        )

    return _build(
        candidate,
        "uncertainty",
        "none",
        evidence,
        context,
        limitations,
        results,
        disagreement,
        "assessment ambiguous or in conflict",
    )


def validate_semantics(
    semantics: CandidateSemantics, context: ValidationContext, assessors: Sequence[SupportAssessor]
) -> tuple[tuple[ValidatedConcept, ...], tuple[ValidatedAssertion, ...], list[str]]:
    """Validate every assertion, then concepts. Returns controller-detected structural problems."""

    problems: list[str] = []
    seen: set[str] = set()
    concept_ids = frozenset(concept.concept_id for concept in semantics.concepts)
    validated: list[ValidatedAssertion] = []

    for candidate in semantics.assertions:
        if candidate.assertion_id in seen:
            problems.append(f"duplicate assertion id {candidate.assertion_id}")
            continue

        seen.add(candidate.assertion_id)
        validated.append(validate_assertion(candidate, context, assessors, concept_ids))

    by_id = {assertion.assertion_id: assertion for assertion in validated}
    concepts = tuple(_validate_concept(concept, by_id, problems) for concept in semantics.concepts)

    return concepts, tuple(validated), problems


def _validate_concept(
    concept: CandidateConcept, by_id: dict[str, ValidatedAssertion], problems: list[str]
) -> ValidatedConcept:
    known = tuple(aid for aid in concept.assertion_ids if aid in by_id)
    problems.extend(
        f"concept {concept.concept_id} references unknown assertion {aid}"
        for aid in concept.assertion_ids
        if aid not in by_id
    )
    priority = by_id.get(concept.relevance_assertion_id or "")
    ranked = priority is not None and priority.state in ("supported", "inference")
    group = next(
        (
            aid
            for aid in known
            if by_id[aid].kind == "grouping" and concept.concept_id in by_id[aid].subject_ids
        ),
        None,
    )

    return ValidatedConcept(
        concept.concept_id,
        concept.title,
        concept.summary,
        known,
        concept.relevance if ranked or concept.relevance_assertion_id is None else None,
        group,
    )
