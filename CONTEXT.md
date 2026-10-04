# Agent Change Comprehension

This context describes the human review of AI-generated code changes. Its purpose is to make the language around reviewer understanding, evidence, and decisions precise.

## Language

**Reviewer**:
A developer deciding whether an AI-generated pull request should be approved, rejected, or sent back for changes.
_Avoid_: User, approver, operator

**Review Decision**:
The reviewer's human judgment to approve, reject, or request changes after understanding the material change and its risks.
_Avoid_: Agent decision, automated approval

**Ready for Review**:
A pull request state indicating that the coding work is ready for a human review decision. This is the default point at which the comprehension experience begins, with manual invocation also allowed.
_Avoid_: Agent finished, work complete

**Repository Evidence**:
Inspectable information from the codebase or its verification results that can support a factual claim about the change. Evidence used by a published review is pinned to an immutable identity, such as a blob/commit identity or a specific verification run and attempt.
_Avoid_: Agent reasoning, model opinion

**Code Comparison Identity**:
The immutable identity of the code comparison itself: repository and pull-request identity, head commit, observed target-base tip SHA, and the exact comparison or merge-base SHA used to derive the change. It is constructed before selecting verification evidence and contains no check-specific execution subject or result.
_Avoid_: Review snapshot, live PR state

**Verification Evidence Identity**:
The identity of one captured check result, including provider, run and attempt, actual execution commit or tree, check scope, exact consumed payload hashes, and eligibility decision. Head-only checks bind to the pinned head. Merged-behavior checks require evidence that their execution subject corresponds to the pinned head and target base. Missing or conflicting provenance becomes an explicit verification gap. Each check retains its own subject; selecting it never changes Code Comparison Identity.
_Avoid_: PR number as provenance, one merge subject shared by all checks

**Semantic Input Manifest**:
A content-addressed manifest of every normalized record exposed to semantic computation for one review, including consumed mutable PR metadata, repository evidence records, archived verification payloads, and any supplied agent trace. If semantic computation can observe it, its content identity is in the manifest before analysis begins.
_Avoid_: Inputs inferred after generation, run IDs without consumed content

**Source Snapshot**:
The immutable ReviewSnapshotIdentity used by one review revision: Source Basis Identity, Change Surface Inventory identity, Semantic Input Manifest identity, plus comprehension and validation-policy versions. A snapshot is a reproducible bundle of pinned content and timed provider observations. It does not claim that every mutable provider resource existed in that combination at one atomic instant.
_Avoid_: Current PR state, head SHA alone

**Source Basis Identity**:
The content identity of the complete source-and-evidence basis: Code Comparison Identity, consumed PR metadata, complete in-scope verification evidence identities and eligibility states, supplied trace content, and source selection and freshness-policy versions. Observation timestamps are recorded separately. Reobserving identical content in the same eligibility state preserves the identity; a rerun, consumed metadata change, required result expiry, missing required result, or policy change can change it without any code change.
_Avoid_: Code-current as evidence-current, observation time as content identity

**Snapshot Acquisition**:
Trusted collection of pinned source and evidence records with per-resource observation times and an acquisition interval. The controller enumerates the required resource set, captures it, then rereads its membership, identities, and versions. Detected drift restarts collection up to three total attempts. Incomplete enumeration, unavailable provenance, or exhausted retries yields unknown consistency with explicit gaps. Matching reads establish observational stability only, not an atomic provider transaction. Scored evaluation admits only complete, observationally stable bundles; both conditions consume that same bundle.
_Avoid_: Immutable means atomic, retry forever

**Change Surface Inventory**:
An exhaustive mechanical inventory derived before semantic comprehension from the complete immutable Git tree delta between the pinned comparison commits, independent of GitHub rendered-diff limits. It represents additions, deletions, modifications, mode changes, symlinks, submodule pointers, and binary/LFS identities; surfaces that cannot be semantically inspected remain explicit opaque items rather than disappearing. Inventory items may be subdivided as needed for semantic coverage.
_Avoid_: Model-discovered surface list, behavioral-concept list

**Agent Report**:
A statement from the coding agent about its intent, reasoning, or actions. It can explain what the agent believed or attempted, but does not by itself establish that a claim about the codebase is true.
_Avoid_: Evidence, verified fact

**Material Claim**:
A factual statement that could affect the reviewer's decision. It must be supported by repository evidence or explicitly presented as an inference or agent report.
_Avoid_: Summary sentence, generated fact

**Claim Validation**:
The explicit support assessment of every reviewer-meaningful assertion, including relationships, grouping, causal or temporal direction, relevance, uncertainty, priority, and emphasis. Both generator and validator outputs remain untrusted. The controller checks assertion and snapshot bindings, immutable evidence references, admissible scope, and result schema deterministically. Mechanically checkable assertions require their specified deterministic check. Other semantics require independently configured model assessment and a visible model-assessed support basis; that assessment is fallible and is not proof of truth or immunity to hostile evidence. Disagreement, ambiguous support, invalid references, or missing scope witnesses produces inference, uncertainty, or a coverage gap. Every displayed supported claim identifies whether its basis is mechanically checked or model assessed, alongside evidence and policy version.
_Avoid_: Citation presence, evidence attachment

**Source Pull Request**:
The GitHub pull request whose exact code revision is being reviewed. It is the primary source object for the first product scope.
_Avoid_: Patch bundle, generic agent run

**Agent Trace**:
Optional recorded activity from the coding agent, such as tool calls, intermediate reasoning summaries, or execution events, used to add context about intent and process.
_Avoid_: Repository evidence, proof

**Untrusted Input Boundary**:
Repository contents, PR text, verification output, and traces are authority-inert but semantically untrusted data. Trusted deterministic acquisition and controller code owns instructions, policies, and permissions. Model stages receive typed snapshot-bound records and return untrusted candidates and assessments. Structural checks enforce the Claim Validation contract before publication. Models cannot modify trusted policy, privileged state, or evidence identities. Presentation treats repository-derived content as inert text and data, with explicit escaping, sanitization, URL, and resource-loading rules. This prevents authority escalation; residual semantic model error remains visible through its support basis and uncertainty.
_Avoid_: Repository instructions as control policy, trace instructions as tool authority

**Inference**:
A potentially useful conclusion suggested by repository evidence but not established as a verified fact. It must remain visibly marked with its supporting evidence and uncertainty.
_Avoid_: Fact, finding, proven risk

**Comprehension Check**:
A short evaluation prompt used during product validation to measure whether the reviewer formed the correct mental model of a material part of the change after using the review experience.
_Avoid_: Product quiz, merge gate, approval test

**Validation Trial**:
A solo evaluation run over one previously unseen immutable Source Snapshot. The baseline, product, fallback, and instrument consume the same captured evidence bundle. Each snapshot is assigned and reviewed once; a failed product delivery retains product assignment and uses its frozen baseline fallback. Actual answers are scored under the predeclared missing-data policy. The bundle records observational stability rather than claiming one atomic GitHub instant.
_Avoid_: Re-review, same-PR comparison

**Product Treatment Identity**:
An immutable identity frozen before the first scored trial for every configuration that can affect the product experience, including model and inference configuration, prompts, semantic and validation implementation or policy versions, retrieval implementation, renderer and visual-language versions, and UI build. Any treatment-affecting change starts a new experiment or cohort.
_Avoid_: Product label, mutable deployment

**Baseline Treatment Identity**:
An immutable identity frozen before the first scored trial for every configuration that can affect the baseline experience, including the frozen-source rendering procedure, baseline UI build, and any other treatment-affecting version or configuration. Any treatment-affecting change starts a new experiment or cohort.
_Avoid_: GitHub as an unspecified control, live baseline

**Matched Review Pair**:
Two previously unseen pull requests with roughly comparable review difficulty, split between the baseline and product conditions so repeated exposure to the same change cannot contaminate the result.
_Avoid_: Before-and-after review, duplicate PR test

**Evaluation Pull Request**:
A real AI-generated or agent-authored open-source pull request the reviewer has not previously seen, selected because its behavior can be established from inspectable repository evidence and it is suitable for a validation trial. General human-authored PRs may be used for exploratory comprehension testing, but do not validate the target AI-generated-PR use case.
_Avoid_: Familiar PR, arbitrary random PR

**Independent Evaluator**:
A separate evaluation process that derives comprehension questions and expected answers from the frozen Source Snapshot without seeing the product's generated explanation or the later baseline/product condition assignment. Questions and answer keys are frozen before assignment, and expected answers must pass the same evidence-support standard used for product semantics plus an independent adjudication step before reviewer exposure.
_Avoid_: Product self-grading, reviewer-authored answer key

**Abstention**:
An explicit statement that the available evidence is insufficient to support a material claim, together with the missing evidence when that can be identified.
_Avoid_: Best guess, silent omission

**Review Entry Point**:
The small GitHub-facing surface that exposes the key review summary and opens the richer review experience.
_Avoid_: Full generated PR report

**Review Overview**:
The first review surface: a concise summary of the change and its highest-risk concepts, with deeper explanations available on demand.
_Avoid_: Full generated report, annotated diff

**Evidence Link**:
A direct path from a material claim to the exact repository evidence that supports it, such as changed code or a test result.
_Avoid_: Evidence appendix, source list

**Presentation Component**:
A deterministic reviewer-facing representation built from assertions with their validation state and support basis. Labels, edges, groups, order, and emphasis reference validated semantic IDs. Raw repository content cannot supply executable HTML, SVG, diagram syntax, scripts, styles, or resource URLs. Renderers escape text, use trusted templates, and restrict links and resources through controller-owned policy.
_Avoid_: Free-form generated fact, semantic analysis

**Infographic**:
A required visual explanation for each review revision, assembled from validated claims and concepts for faster reviewer comprehension. Its layout and style may vary, but its factual labels and relationships must come from validated material.
_Avoid_: Decorative illustration, source of truth

**Explanation Artifact**:
A reviewer-facing representation of validated material, such as an infographic, flow diagram, table, or interactive trace. The system selects additional artifact types according to the structure of the change, while the reviewer may request others.
_Avoid_: Video, source of truth

**Published View Identity**:
The immutable identity of exactly what the reviewer was shown. It binds the validated semantic-artifact identity, presentation-policy and renderer versions, and content hashes of the concrete rendered artifacts. Reviewer exposure and reviewer state refer to this identity, and scored product trials record the exact PublishedViewIdentity shown.
_Avoid_: Review revision alone, mutable latest view

**Visual Language**:
The consistent visual conventions shared across review artifacts while allowing each artifact's structure to adapt to the change being explained.
_Avoid_: Fixed template, unconstrained visual generation

**Supporting Context**:
Unchanged code or repository information needed to understand the behavior affected by the pull request, included only when it materially clarifies the change.
_Avoid_: Changed lines only, whole-subsystem explanation

**Decision Relevance**:
How strongly a claim or concept could affect the reviewer's approve, reject, or request-changes decision. It determines explanation priority ahead of raw code size.
_Avoid_: Lines changed, file count

**Behavioral Concept**:
A meaningful behavior, execution path, data flow, or decision affected by the pull request and explained as one coherent unit backed by repository evidence.
_Avoid_: File, diff hunk

**Coverage Gap**:
A part of the changed behavior that the analysis cannot support confidently from available evidence and therefore marks explicitly as unknown or incomplete.
_Avoid_: Best guess, hidden omission

**Coverage Ledger**:
An internal completeness record keyed by the independent Change Surface Inventory. Coverage is many-to-many: one inventory item may map to multiple validated behavioral concepts, and each item retains an explicit residual/closure state for material consequences not yet accounted for. A separate closure-falsification pass, independent of the candidate semantics and primary comprehension pass, challenges every inventory obligation and the dependency or context edges needed to interpret it. A non-material determination is itself a validated semantic assertion. Any unvalidated non-material determination, opaque unresolved surface, unresolved residual, or plausible material consequence that the falsification pass cannot resolve becomes a visible coverage gap before publication. Mechanical inventory completeness is provable from the immutable Git-tree delta; semantic closure remains a falsification-backed claim rather than a mechanical proof of complete behavior understanding.
_Avoid_: Reviewer-facing file list, claim count

**Review Revision**:
A review of one exact Source Snapshot. Exact consumed payloads and each check's provenance and execution subject are archived. At presentation or decision recording, the controller reconciles the full Source Basis Identity, including eligibility and expiry at that boundary. It records matching, stale, or unknown together with the observation interval, resource times, and freshness deadline. A code match alone is insufficient. Local compare-and-swap protects the expected SourceSnapshotId and PublishedViewIdentity from concurrent replacement; it is not a transaction over GitHub resources. The UI says when the bundle last matched observed state and never promises timeless currentness or atomic live merge authorization. Changed source basis or analysis policy creates a new review revision and recomputes semantics. Notes on an old revision retain that old identity and observed freshness.
_Avoid_: Mutable review, live PR state
