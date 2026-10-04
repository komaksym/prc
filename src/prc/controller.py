"""Trusted controller: runs untrusted model stages on a frozen snapshot and publishes semantics."""

from __future__ import annotations

from dataclasses import dataclass

from prc.comprehension import (
    ClosureFalsifier,
    ComprehensionModel,
    FixtureAssessor,
    FixtureComprehension,
    FixtureFalsifier,
    ModelInputs,
    SupportAssessor,
)
from prc.coverage import build_ledger
from prc.identity import SemanticArtifactId, content_id
from prc.semantics import (
    CandidateSemantics,
    CoverageGap,
    ModelProvenance,
    ValidatedConcept,
    ValidatedSemanticArtifact,
)
from prc.snapshot import VALIDATION_VERSION, Acquisition
from prc.validation import ASSESSOR_FAILURE, ValidationContext, validate_semantics


@dataclass(frozen=True)
class ModelSuite:
    comprehension: ComprehensionModel
    assessors: tuple[SupportAssessor, ...]
    falsifier: ClosureFalsifier


def fixture_suite() -> ModelSuite:
    """Two independently configured fixture assessors plus a separate falsifier."""

    return ModelSuite(
        FixtureComprehension(),
        (
            FixtureAssessor(),
            FixtureAssessor("fixture-assessor-strict", "fixture-assessor-v1", True, 0.8, 0.5),
        ),
        FixtureFalsifier(),
    )


def _order(concepts: tuple[ValidatedConcept, ...]) -> tuple[ValidatedConcept, ...]:
    return tuple(
        sorted(
            concepts,
            key=lambda concept: (
                concept.relevance is None,
                -(concept.relevance or 0),
                concept.concept_id,
            ),
        )
    )


def analyze(acquisition: Acquisition, suite: ModelSuite) -> ValidatedSemanticArtifact:
    """Semantics are always recomputed for a snapshot; nothing is reused across snapshots."""

    snapshot = acquisition.snapshot
    inputs = ModelInputs(
        snapshot.snapshot_id, dict(acquisition.records), acquisition.inventory.items
    )
    stage_failures: list[CoverageGap] = []

    try:
        candidates = suite.comprehension.propose(inputs)
    except Exception as error:  # untrusted stage: any failure becomes a visible gap
        candidates = CandidateSemantics((), (), ())
        stage_failures.append(
            CoverageGap("m:comprehension", "model_failure", "comprehension", repr(error)[:200])
        )

    try:
        findings = suite.falsifier.challenge(inputs)
    except Exception as error:
        findings = ()
        stage_failures.append(
            CoverageGap("m:falsifier", "model_failure", "falsifier", repr(error)[:200])
        )

    context = ValidationContext(inputs.records, inputs.inventory, VALIDATION_VERSION)
    concepts, assertions, problems = validate_semantics(candidates, context, suite.assessors)
    ledger, gaps = build_ledger(
        inputs.inventory,
        candidates.coverage,
        concepts,
        assertions,
        findings,
        frozenset(inputs.records),
    )
    controller_gaps = [
        CoverageGap(f"p:{position + 1}", "structural", "model output", problem)
        for position, problem in enumerate(problems)
    ]
    controller_gaps.extend(
        CoverageGap(f"v:{gap.name}", "verification", gap.name, gap.reason)
        for gap in snapshot.verification_gaps
    )

    if any(
        result.verdict.rationale.startswith(ASSESSOR_FAILURE)
        for assertion in assertions
        for result in assertion.assessments
    ):
        stage_failures.append(
            CoverageGap(
                "m:assessor",
                "model_failure",
                "assessor",
                "a support assessor failed or returned malformed output",
            )
        )

    if snapshot.consistency == "unknown":
        controller_gaps.append(
            CoverageGap(
                "capture", "capture_consistency", "acquisition", "; ".join(snapshot.capture_gaps)
            )
        )

    models = (
        ModelProvenance(
            "comprehension",
            suite.comprehension.label,
            suite.comprehension.version,
            suite.comprehension.fixture,
        ),
        *(ModelProvenance("assessor", a.label, a.version, a.fixture) for a in suite.assessors),
        ModelProvenance(
            "falsifier", suite.falsifier.label, suite.falsifier.version, suite.falsifier.fixture
        ),
    )
    body = ValidatedSemanticArtifact(
        snapshot_id=snapshot.snapshot_id,
        validation_version=VALIDATION_VERSION,
        concepts=_order(concepts),
        assertions=assertions,
        ledger=ledger,
        gaps=(*gaps, *stage_failures, *controller_gaps),
        models=models,
    )

    return body


def semantic_artifact_id(artifact: ValidatedSemanticArtifact) -> SemanticArtifactId:
    return SemanticArtifactId(content_id("semantic-artifact", artifact))
