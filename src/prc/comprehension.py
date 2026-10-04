"""Model contracts and the deterministic FIXTURE models used for development.

The fixture models are heuristics, labelled ``fixture`` in every artifact. They are not LLMs and
make no claim about real model behaviour.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from prc.inventory import InventoryItem
from prc.semantics import (
    CandidateAssertion,
    CandidateConcept,
    CandidateCoverage,
    CandidateSemantics,
    EvidenceRef,
    FalsifierFinding,
    MechanicalCheck,
    Verdict,
)


@dataclass(frozen=True, slots=True)
class ModelInputs:
    """Everything a model stage may see: manifest records and the mechanical inventory."""

    snapshot_id: str
    records: Mapping[str, str]
    inventory: tuple[InventoryItem, ...]


class ComprehensionModel(Protocol):
    @property
    def label(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def fixture(self) -> bool: ...

    def propose(self, inputs: ModelInputs) -> CandidateSemantics: ...


class SupportAssessor(Protocol):
    @property
    def label(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def fixture(self) -> bool: ...

    def assess(self, assertion: CandidateAssertion, evidence: Mapping[str, str]) -> Verdict: ...


class ClosureFalsifier(Protocol):
    """Independent of candidate semantics: sees only snapshot inputs."""

    @property
    def label(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def fixture(self) -> bool: ...

    def challenge(self, inputs: ModelInputs) -> tuple[FalsifierFinding, ...]: ...


KEYWORDS = ("http", "timeout", "retry", "auth", "token", "exec", "subprocess", "sleep", "open(")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{4,}")
_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)


def _added_lines(diff: str) -> list[str]:
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++") and line[1:].strip()
    ]


def _concept_key(item: InventoryItem) -> str:
    if item.path.startswith("tests/") or "/tests/" in item.path:
        return "tests"

    if item.path.endswith((".md", ".lock", ".txt")):
        return "docs"

    return item.path.rsplit("/", 1)[0] if "/" in item.path else "root"


def _stem(path: str) -> str:
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


class FixtureComprehension:
    """Heuristic stand-in for a comprehension model. Deterministic, fixture only."""

    label = "fixture-comprehension"
    version = "fixture-comprehension-v1"
    fixture = True

    def propose(self, inputs: ModelInputs) -> CandidateSemantics:
        assertions: list[CandidateAssertion] = []
        concepts: list[CandidateConcept] = []
        coverage: list[CandidateCoverage] = []
        groups: dict[str, list[InventoryItem]] = {}

        for item in inputs.inventory:
            if not item.opaque:
                groups.setdefault(_concept_key(item), []).append(item)

        def add(**fields: object) -> str:
            assertion_id = f"a:{len(assertions) + 1}"
            assertions.append(CandidateAssertion(assertion_id=assertion_id, **fields))  # type: ignore[arg-type]

            return assertion_id

        concept_of_path: dict[str, str] = {}
        terms_of: dict[str, str] = {}

        for key, items in sorted(groups.items()):
            if key == "docs":
                continue

            concept_id = f"c:{key}"
            ids: list[str] = []
            keyword_hits = 0

            for item in items:
                concept_of_path[item.path] = concept_id
                diff = inputs.records[f"diff:{item.path}"]
                added = _added_lines(diff)
                keyword_hits += sum(any(word in line for word in KEYWORDS) for line in added)
                args = (
                    ("path", item.path),
                    ("status", item.status),
                    ("added", str(item.added_lines)),
                    ("removed", str(item.removed_lines)),
                )
                ids.append(
                    add(
                        kind="claim",
                        claimed_state="supported",
                        text=(
                            f"{item.path} status {item.status}: +{item.added_lines}"
                            f"/-{item.removed_lines} lines"
                        ),
                        evidence=(EvidenceRef(f"diff:{item.path}"),),
                        mechanical=MechanicalCheck("path_changed", args),
                    )
                )

                if added and item.status != "D":
                    quote = max(
                        added, key=lambda line: (any(w in line for w in KEYWORDS), len(line))
                    )
                    ids.append(
                        add(
                            kind="claim",
                            claimed_state="supported",
                            text=f"{item.path} now contains the line: {quote.strip()}",
                            evidence=(EvidenceRef(f"head:{item.path}", quote),),
                            mechanical=MechanicalCheck(
                                "quote_present", (("record", f"head:{item.path}"), ("quote", quote))
                            ),
                        )
                    )

            first = items[0]
            terms = " ".join(_added_lines(inputs.records[f"diff:{first.path}"])[:3])
            terms_of[concept_id] = terms
            ids.append(
                add(
                    kind="inference",
                    claimed_state="inference",
                    text=f"Runtime behaviour under {key} may differ for callers: {terms}",
                    evidence=tuple(EvidenceRef(f"diff:{item.path}") for item in items),
                )
            )
            group_id = add(
                kind="grouping",
                claimed_state="supported",
                text=f"Behavioural unit {key} ({', '.join(item.path for item in items)}): {terms}",
                evidence=tuple(EvidenceRef(f"diff:{item.path}") for item in items),
                subject_ids=(concept_id,),
            )
            relevance = 2 if key == "tests" else min(5, 3 + keyword_hits)
            priority_id = add(
                kind="priority",
                claimed_state="supported",
                text=f"Decision relevance {relevance} for {key}: {terms}",
                evidence=tuple(EvidenceRef(f"diff:{item.path}") for item in items),
                subject_ids=(concept_id,),
            )
            ids.extend((group_id, priority_id))
            summary = f"{len(items)} changed file(s) under {key}"
            concepts.append(
                CandidateConcept(
                    concept_id, f"Changes in {key}", summary, tuple(ids), relevance, priority_id
                )
            )

        relation_pairs = set()

        for item in inputs.inventory:
            if item.opaque or item.path not in concept_of_path:
                continue

            text = inputs.records.get(f"head:{item.path}", "")

            for module in _IMPORT.findall(text):
                for other in inputs.inventory:
                    if (
                        other.path != item.path
                        and _stem(other.path) == module
                        and other.path in concept_of_path
                    ):
                        source, target = concept_of_path[item.path], concept_of_path[other.path]

                        if source != target and (source, target) not in relation_pairs:
                            relation_pairs.add((source, target))
                            line = next(ln for ln in text.splitlines() if module in ln)
                            add(
                                kind="relation",
                                claimed_state="supported",
                                text=f"{item.path} imports {other.path}: {line.strip()}",
                                evidence=(EvidenceRef(f"head:{item.path}", line),),
                                subject_ids=(source, target),
                                relation=(source, target),
                            )

        concept_ids = [concept.concept_id for concept in concepts]
        ranked = sorted(concepts, key=lambda concept: (-concept.relevance, concept.concept_id))

        if ranked:
            add(
                kind="emphasis",
                claimed_state="supported",
                text=f"Most decision-relevant concept {ranked[0].title}: {terms_of[ranked[0].concept_id]}",
                evidence=tuple(
                    EvidenceRef(f"diff:{item.path}")
                    for item in groups.get(ranked[0].concept_id[2:], [])
                ),
                subject_ids=(ranked[0].concept_id,),
            )

        verification_ids = self._verification(inputs, add)

        if verification_ids:
            concepts.append(
                CandidateConcept(
                    "c:verification",
                    "Verification evidence",
                    "Archived check results",
                    tuple(verification_ids),
                    3,
                    None,
                )
            )
            concept_ids.append("c:verification")

        for item in inputs.inventory:
            nonmaterial = None

            if not item.opaque and _concept_key(item) == "docs":
                added = _added_lines(inputs.records[f"diff:{item.path}"])
                nonmaterial = add(
                    kind="non_material",
                    claimed_state="supported",
                    text=f"{item.path} changes only prose: {' '.join(added[:2])}",
                    evidence=(EvidenceRef(f"diff:{item.path}"),),
                    universal=True,
                    scope_witness="inventory",
                )

            coverage.append(
                CandidateCoverage(
                    item.item_id,
                    (concept_of_path[item.path],) if item.path in concept_of_path else (),
                    "closed" if not item.opaque else "open",
                    nonmaterial,
                )
            )

        return CandidateSemantics(tuple(assertions), tuple(concepts), tuple(coverage))

    def _verification(self, inputs: ModelInputs, add_fn: Callable[..., str]) -> list[str]:
        ids: list[str] = []
        verification = json.loads(inputs.records["verification"])

        for evidence in verification["evidence"]:
            if evidence["eligibility"] != "eligible":
                continue

            record = f"check:{evidence['run_id']}:{evidence['attempt']}"
            ids.append(
                add_fn(
                    kind="claim",
                    claimed_state="supported",
                    text=f"Check {evidence['name']} concluded {evidence['conclusion']} on its own subject",
                    evidence=(EvidenceRef(record),),
                    mechanical=MechanicalCheck(
                        "check_conclusion",
                        (("name", evidence["name"]), ("conclusion", evidence["conclusion"])),
                    ),
                )
            )

        for gap in verification["gaps"]:
            ids.append(
                add_fn(
                    kind="uncertainty",
                    claimed_state="uncertainty",
                    text=f"Required check {gap['name']} has no usable result: {gap['reason']}",
                    evidence=(EvidenceRef("verification"),),
                )
            )

        trace = inputs.records.get("trace")

        if trace is not None:
            for event in json.loads(trace):
                summary = str(event["summary"])

                if summary.startswith("Agent says:"):
                    ids.append(
                        add_fn(
                            kind="agent_report",
                            claimed_state="agent_report",
                            text=summary,
                            evidence=(EvidenceRef("trace", summary),),
                        )
                    )

        return ids


def _terms(text: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(text)}


@dataclass(frozen=True, slots=True)
class FixtureAssessor:
    """Lexical-overlap stand-in for a support-assessing model. Fallible by construction."""

    label: str = "fixture-assessor-lenient"
    version: str = "fixture-assessor-v1"
    fixture: bool = True
    supported_at: float = 0.6
    inference_at: float = 0.3

    def assess(self, assertion: CandidateAssertion, evidence: Mapping[str, str]) -> Verdict:
        wanted = _terms(assertion.text.split(": ", 1)[-1])
        have = _terms(" ".join(evidence.values()))

        if not wanted or not evidence:
            return Verdict("ambiguous", "no comparable terms")

        overlap = len(wanted & have) / len(wanted)

        if overlap >= self.supported_at:
            return Verdict("supported", f"term overlap {overlap:.2f}")

        if overlap >= self.inference_at:
            return Verdict("inference_only", f"term overlap {overlap:.2f}")

        return Verdict("unsupported", f"term overlap {overlap:.2f}")


class FixtureFalsifier:
    """Closure challenger. Opaque or context-dependent items stay open."""

    label = "fixture-falsifier"
    version = "fixture-falsifier-v1"
    fixture = True

    def challenge(self, inputs: ModelInputs) -> tuple[FalsifierFinding, ...]:
        changed_stems = {_stem(item.path) for item in inputs.inventory}
        context_stems = {_stem(key) for key in inputs.records if key.startswith("context:")}
        findings: list[FalsifierFinding] = []

        for item in inputs.inventory:
            if item.opaque:
                findings.append(FalsifierFinding(item.item_id, "open", f"opaque: {item.note}"))
                continue

            text = inputs.records.get(f"head:{item.path}", "")
            unseen = sorted(
                module
                for module in set(_IMPORT.findall(text))
                if module not in sys.stdlib_module_names
                and module not in changed_stems
                and module not in context_stems
            )

            if unseen:
                findings.append(
                    FalsifierFinding(
                        item.item_id,
                        "open",
                        "imports modules absent from the snapshot",
                        tuple(f"module:{name}" for name in unseen),
                    )
                )
            else:
                findings.append(
                    FalsifierFinding(item.item_id, "closed", "no unresolved edge found")
                )

        return tuple(findings)
