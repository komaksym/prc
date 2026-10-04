from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

import pytest

from prc.capture import capture_bundle
from prc.comprehension import FixtureAssessor, FixtureFalsifier, ModelInputs
from prc.controller import ModelSuite, analyze, fixture_suite
from prc.coverage import build_ledger
from prc.fixture_source import FixtureSource
from prc.inventory import InventoryItem
from prc.model import PrRef
from prc.semantics import (
    CandidateAssertion,
    CandidateConcept,
    CandidateCoverage,
    CandidateSemantics,
    EvidenceRef,
    FalsifierFinding,
    MechanicalCheck,
    ValidatedSemanticArtifact,
    Verdict,
)
from prc.snapshot import Acquisition, build_snapshot
from prc.validation import ValidationContext, validate_assertion, validate_semantics
from prc.verification import EligibilityPolicy

from conftest import FakeClock

Make = Callable[[str], tuple[FixtureSource, PrRef]]


def acquire(make: Make, name: str, clock: FakeClock) -> Acquisition:
    source, ref = make(name)
    bundle = capture_bundle(source, ref, clock)

    return build_snapshot(bundle, source.label, False, source.repo, EligibilityPolicy())


def context_of(acquisition: Acquisition) -> ValidationContext:
    return ValidationContext(acquisition.records, acquisition.inventory.items, "validation-v1")


@pytest.fixture
def basic(make_source: Make, clock: FakeClock) -> Acquisition:
    return acquire(make_source, "basic", clock)


def candidate(**fields: object) -> CandidateAssertion:
    base: dict[str, object] = {
        "assertion_id": "x:1",
        "kind": "claim",
        "claimed_state": "supported",
        "text": "retry attempts sleep",
        "evidence": (EvidenceRef("diff:src/app.py"),),
    }
    base.update(fields)

    return CandidateAssertion(**base)  # type: ignore[arg-type]


ASSESSORS = (FixtureAssessor(), FixtureAssessor("strict", "v1", True, 0.8, 0.5))


def test_dangling_and_forged_evidence_never_support(basic: Acquisition) -> None:
    context = context_of(basic)
    dangling = candidate(evidence=(EvidenceRef("head:does/not/exist.py"),))
    forged = candidate(evidence=(EvidenceRef("diff:src/app.py", "line that was never there"),))

    for bad in (dangling, forged):
        result = validate_assertion(bad, context, ASSESSORS, frozenset())

        assert result.state == "gap" and result.basis == "none"


def test_mechanical_check_is_deterministic_and_model_cannot_override(basic: Acquisition) -> None:
    context = context_of(basic)
    wrong = candidate(
        text="src/app.py status M: +999/-0 lines",
        mechanical=MechanicalCheck(
            "path_changed",
            (("path", "src/app.py"), ("status", "M"), ("added", "999"), ("removed", "0")),
        ),
    )
    always_yes = (FixtureAssessor("yes", "v1", True, 0.0, 0.0),)
    result = validate_assertion(wrong, context, always_yes, frozenset())

    assert result.state == "gap" and "mechanical check failed" in (result.downgrade_reason or "")


def test_model_assessed_support_is_labelled_and_never_mechanical(basic: Acquisition) -> None:
    context = context_of(basic)
    quoted = "retry attempts sleep"
    result = validate_assertion(
        candidate(text=f"x: {quoted}", evidence=(EvidenceRef("head:src/retry.py"),)),
        context,
        ASSESSORS,
        frozenset(),
    )

    assert result.state == "supported" and result.basis == "model_assessed"
    assert result.limitations and len(result.assessments) == 2


def test_assessor_disagreement_blocks_supported(basic: Acquisition) -> None:
    context = context_of(basic)
    lenient = FixtureAssessor("lenient", "v1", True, 0.0, 0.0)
    strict = FixtureAssessor("strict", "v1", True, 2.0, 0.0)
    result = validate_assertion(
        candidate(text="x: totally unrelated vocabulary words"),
        context,
        (lenient, strict),
        frozenset(),
    )

    assert result.state == "inference" and result.disagreement and result.basis == "model_assessed"


def test_universal_claim_needs_pinned_scope_witness(basic: Acquisition) -> None:
    context = context_of(basic)
    no_witness = candidate(kind="non_material", text="x: retry attempts sleep", universal=True)
    witness = replace(no_witness, scope_witness="inventory")
    ghost = replace(no_witness, scope_witness="record:not-in-manifest")

    assert validate_assertion(no_witness, context, ASSESSORS, frozenset()).state == "uncertainty"
    assert validate_assertion(ghost, context, ASSESSORS, frozenset()).state == "uncertainty"
    assert validate_assertion(witness, context, ASSESSORS, frozenset()).state != "uncertainty"


def test_relation_direction_and_endpoints_validated(basic: Acquisition) -> None:
    context = context_of(basic)
    concepts = frozenset({"c:a", "c:b"})
    good = candidate(
        kind="relation",
        subject_ids=("c:a", "c:b"),
        relation=("c:a", "c:b"),
        text="x: retry attempts sleep",
        evidence=(EvidenceRef("head:src/retry.py"),),
    )
    ghost = replace(good, subject_ids=("c:a", "c:zzz"), relation=("c:a", "c:zzz"))

    ok = validate_assertion(good, context, ASSESSORS, concepts)

    assert ok.relation == ("c:a", "c:b")
    assert validate_assertion(ghost, context, ASSESSORS, concepts).state == "gap"


def test_agent_report_never_becomes_supported(basic: Acquisition) -> None:
    context = context_of(basic)
    report = candidate(claimed_state="agent_report", evidence=(EvidenceRef("trace"),))
    smuggled = candidate(claimed_state="agent_report", evidence=(EvidenceRef("diff:src/app.py"),))

    assert validate_assertion(report, context, ASSESSORS, frozenset()).state == "agent_report"
    assert validate_assertion(smuggled, context, ASSESSORS, frozenset()).state == "gap"


def test_duplicate_ids_and_unknown_concept_assertions_are_reported(basic: Acquisition) -> None:
    semantics = CandidateSemantics(
        assertions=(candidate(), candidate()),
        concepts=(CandidateConcept("c:a", "A", "s", ("x:1", "x:missing"), 3),),
        coverage=(),
    )
    _, assertions, problems = validate_semantics(semantics, context_of(basic), ASSESSORS)

    assert len(assertions) == 1
    assert any("duplicate" in p for p in problems) and any(
        "unknown assertion" in p for p in problems
    )


def test_basic_scenario_has_full_closure_and_no_gaps(basic: Acquisition) -> None:
    artifact = analyze(basic, fixture_suite())

    assert artifact.gaps == ()
    assert all(entry.residual == "closed" for entry in artifact.ledger)
    assert len(artifact.ledger) == len(basic.inventory.items)


def test_opaque_items_cannot_disappear(make_source: Make, clock: FakeClock) -> None:
    acquisition = acquire(make_source, "opaque", clock)
    artifact = analyze(acquisition, fixture_suite())
    opaque_paths = {item.path for item in acquisition.inventory.items if item.opaque}
    gap_subjects = {gap.subject for gap in artifact.gaps if gap.kind == "opaque"}

    assert opaque_paths == gap_subjects and len(opaque_paths) == 4
    assert {entry.path for entry in artifact.ledger if entry.residual == "open"} >= opaque_paths


def test_coverage_is_many_to_many(basic: Acquisition) -> None:
    artifact = analyze(basic, fixture_suite())
    inputs = ModelInputs("s", basic.records, basic.inventory.items)
    app = next(item for item in basic.inventory.items if item.path == "src/app.py")
    concepts = artifact.concepts[:2]
    ledger, gaps = build_ledger(
        (app,),
        (CandidateCoverage(app.item_id, tuple(c.concept_id for c in concepts), "closed"),),
        artifact.concepts,
        artifact.assertions,
        (FalsifierFinding(app.item_id, "closed", "ok"),),
        frozenset(inputs.records),
    )

    assert len(ledger[0].concept_ids) == 2 and not gaps


def test_falsifier_open_and_unvalidated_nonmaterial_become_gaps(basic: Acquisition) -> None:
    artifact = analyze(basic, fixture_suite())
    readme = next(item for item in basic.inventory.items if item.path == "README.md")
    app = next(item for item in basic.inventory.items if item.path == "src/app.py")
    ledger, gaps = build_ledger(
        (readme, app),
        (
            CandidateCoverage(readme.item_id, (), "closed", "a:does-not-exist"),
            CandidateCoverage(app.item_id, ("c:src",), "closed"),
        ),
        artifact.concepts,
        artifact.assertions,
        (
            FalsifierFinding(readme.item_id, "closed", "ok"),
            FalsifierFinding(app.item_id, "open", "plausible uncovered consequence", ("module:x",)),
        ),
        frozenset(basic.records),
    )

    kinds = {gap.kind for gap in gaps}

    assert {"unvalidated_non_material", "falsification_open"} <= kinds
    assert all(entry.residual == "open" for entry in ledger)


def test_missing_context_is_open_until_context_record_exists() -> None:
    files = {"head:src/x.py": "import mystery\n"}
    item = InventoryItem(
        "i", "src/x.py", "M", "100644", "100644", "a", "b", "text", False, "", 1, 0
    )
    unseen = FixtureFalsifier().challenge(ModelInputs("s", files, (item,)))
    seen = FixtureFalsifier().challenge(
        ModelInputs("s", {**files, "context:src/mystery.py": "X = 1"}, (item,))
    )

    assert unseen[0].verdict == "open" and unseen[0].needed_context == ("module:mystery",)
    assert seen[0].verdict == "closed"


def test_failing_model_stage_becomes_gap_not_crash(basic: Acquisition) -> None:
    class Boom:
        label, version, fixture = "boom", "v0", True

        def propose(self, inputs: ModelInputs) -> CandidateSemantics:
            raise RuntimeError("model exploded")

    artifact = analyze(basic, ModelSuite(Boom(), ASSESSORS, FixtureFalsifier()))

    assert any(gap.kind == "model_failure" for gap in artifact.gaps)
    assert {gap.subject for gap in artifact.gaps if gap.kind == "no_coverage_entry"} >= {
        "src/app.py"
    }


def test_hostile_text_cannot_change_controller_outcomes(
    make_source: Make, clock: FakeClock
) -> None:
    acquisition = acquire(make_source, "hostile", clock)
    artifact = analyze(acquisition, fixture_suite())
    check_claims = [a for a in artifact.assertions if a.text.startswith("Check unit-tests")]

    assert [a.text for a in check_claims] == [
        "Check unit-tests concluded failure on its own subject"
    ]
    assert {gap.subject for gap in artifact.gaps if gap.kind == "verification"} == {"merged-ci"}
    assert not any(
        a.basis == "mechanical" and a.state == "agent_report" and a.kind == "claim"
        for a in artifact.assertions
    )


def test_unknown_capture_consistency_is_a_visible_gap(make_source: Make, clock: FakeClock) -> None:
    source, ref = make_source("basic")
    source.drift = lambda call, resources: resources.__setitem__("trace", str(call).encode())
    bundle = capture_bundle(source, ref, clock)
    acquisition = build_snapshot(bundle, "fixture", False, source.repo, EligibilityPolicy())
    artifact: ValidatedSemanticArtifact = analyze(
        acquisition, ModelSuite(fixture_suite().comprehension, ASSESSORS, FixtureFalsifier())
    )

    assert any(gap.kind == "capture_consistency" for gap in artifact.gaps)


def test_mechanical_check_cannot_certify_unrelated_text_or_skip_witness(basic: Acquisition) -> None:
    context = context_of(basic)
    readme = next(item for item in basic.inventory.items if item.path == "README.md")
    check = MechanicalCheck(
        "path_changed",
        (
            ("path", "README.md"),
            ("status", "M"),
            ("added", str(readme.added_lines)),
            ("removed", str(readme.removed_lines)),
        ),
    )
    forged = candidate(
        kind="non_material",
        text="Every caller is unaffected; this change cannot alter any behaviour anywhere.",
        evidence=(EvidenceRef("diff:README.md"),),
        mechanical=check,
        universal=True,
    )
    result = validate_assertion(forged, context, ASSESSORS, frozenset())

    assert result.basis != "mechanical" and result.state != "supported"


def test_supported_non_nonmaterial_assertion_cannot_close_coverage(basic: Acquisition) -> None:
    artifact = analyze(basic, fixture_suite())
    readme = next(item for item in basic.inventory.items if item.path == "README.md")
    mechanical_claim = next(
        a for a in artifact.assertions if a.basis == "mechanical" and a.kind == "claim"
    )
    ledger, gaps = build_ledger(
        (readme,),
        (CandidateCoverage(readme.item_id, (), "closed", mechanical_claim.assertion_id),),
        artifact.concepts,
        artifact.assertions,
        (FalsifierFinding(readme.item_id, "closed", "ok"),),
        frozenset(basic.records),
    )

    assert ledger[0].residual == "open" and gaps


def test_crashing_assessor_becomes_visible_gap(basic: Acquisition) -> None:
    class Crash:
        label, version, fixture = "crash", "v0", True

        def assess(self, assertion: CandidateAssertion, evidence: Mapping[str, str]) -> Verdict:
            raise RuntimeError("validator crashed")

    artifact = analyze(
        basic, ModelSuite(fixture_suite().comprehension, (Crash(),), FixtureFalsifier())
    )

    assert any(gap.kind == "model_failure" and gap.subject == "assessor" for gap in artifact.gaps)
    assert not any(
        a.basis == "model_assessed" and a.state == "supported" for a in artifact.assertions
    )
