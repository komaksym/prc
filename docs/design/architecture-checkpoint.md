# Agent change comprehension — canonical MVP design

Status: **architecture critical-only review complete: zero verified criticals; implementation not started**.

The [bounded critical-only run](../work/critical-only-loop.md) stopped successfully after one fix cycle. Three fresh reviewers and a separate fresh verifier found zero criticals and closed all six original mechanisms. The [review evidence](../work/critical-only/cycle-1/verifier.md) records the exact frozen revision. The user's implementation checkpoint remains in effect.

## Product

The first user is a developer reviewing an AI-generated GitHub pull request. The product enters when the PR is ready for review, with manual invocation also available.

Its job is to help the reviewer reach a **justified human review decision**: approve, reject, or request changes. The product does not make that decision for them.

The MVP supports GitHub pull requests only. An agent trace is optional context.

## Trust model

The product distinguishes three epistemic states:

1. **Supported claim** — backed by inspectable repository evidence such as code, diff context, tests, or repository context.
2. **Inference** — suggested by evidence but not established as fact; shown with its evidence and uncertainty.
3. **Agent report** — describes what the coding agent says it intended, believed, or did; useful for intent, but not proof that a codebase claim is true.

If the available evidence is insufficient, the product abstains and exposes the coverage gap. It never fills a material gap with an unmarked guess.

Every material claim shown to the reviewer has an adjacent path to the exact evidence supporting it.

Evidence attachment alone is not validation. Every reviewer-meaningful assertion receives an explicit support assessment before publication. This includes relationships, grouping, causal or temporal direction, relevance, uncertainty, priority, and emphasis. Generator and validator outputs both remain untrusted. An independently configured validator receives typed assertions and pinned evidence under controller-owned instructions. The controller deterministically checks assertion, snapshot, and evidence bindings, admissible scope, and result schema. Mechanically checkable assertions require their specified deterministic check. Universal, negative, completeness, and non-material assertions require an explicit pinned scope witness; absent scope cannot be certified from a local snippet. The check records:

- the assertion and its epistemic state,
- the immutable evidence references it depends on,
- the support assessment and the deterministic obligations checked,
- the support basis, either mechanically checked or model assessed, and any disagreement or uncertainty,
- the validation-policy version that made that determination.

A failed or ambiguous support check cannot produce supported semantics. It becomes an explicit inference or uncertainty when the evidence justifies that weaker status, otherwise the system abstains or exposes a coverage gap.

Model assessment is fallible even when independently configured. It cannot certify truth or immunity to instructions embedded in evidence. Every supported claim visibly states whether it is mechanically checked or model assessed, with evidence and limitations. A successful model verdict alone never becomes a mechanically verified fact. Detected disagreement or failed structural checks prevent supported publication. Adversarial source and log fixtures are required before reviewer use; they test known attacks without claiming universal model correctness.

Truthfulness is not enough if the system silently overlooks changed behavior. Before semantic comprehension, the source layer therefore derives an exhaustive **mechanical change-surface inventory** from the complete immutable Git tree delta between the pinned comparison commits, independent of GitHub rendered-diff limits. It represents additions, deletions, modifications, mode changes, symlinks, submodule pointers, and binary/LFS identities. Opaque or semantically uninspectable surfaces stay explicit instead of disappearing.

Coverage over that inventory is many-to-many. One source item may contribute to several material behavioral concepts, so mapping an item to one discovered concept does not close it. For every item the ledger records the validated concepts it contributes to plus an explicit residual/closure state for material consequences not yet accounted for. A separate closure-falsification pass is independent of the candidate semantics and primary comprehension pass. It challenges every inventory obligation and the dependency or context edges needed to interpret it. A non-material determination is itself a semantic assertion that must pass support validation. Any unvalidated non-material determination, opaque unresolved surface, unresolved residual, or plausible material consequence that the falsification pass cannot resolve becomes an explicit coverage gap before publication. The Git-tree inventory can be mechanically complete; semantic closure is a falsification-backed result, not a mechanical proof that every behavioral consequence is known.

The review overview exposes when material coverage is incomplete.

Repository contents, PR text, verification output, and traces cross an explicit **untrusted-input boundary**. Trusted deterministic acquisition and controller code owns policy and permissions. Model stages receive typed snapshot-bound data and return untrusted candidates or assessments. The controller applies the structural and support-basis rules above before publication. Models have no direct mutation, source-control, network, permission-changing, or policy-changing authority. Evidence text cannot supply trusted instructions or executable presentation content. Authority isolation does not eliminate residual semantic model error.

## Inert presentation

The entry point, overview, prose, tables, infographic, flow diagrams, evidence excerpts, interactive traces, and exports share one presentation boundary. Repository-derived strings are text values in a typed presentation document. Semantic operators for labels, edges, groups, order, emphasis, and epistemic state reference validated assertion IDs. Unknown IDs, invalid relationships, and lost support or uncertainty markers block publication. Trusted renderers choose geometry and style without adding semantic operators.

Raw source content cannot become HTML, SVG, diagram code, CSS, scripts, event handlers, or renderer configuration. Trusted templates construct those formats and escape embedded text for their output context. Untrusted rich markup is displayed as escaped text; it is not passed through. No template evaluates source strings.

Controller-owned URL policy constructs evidence links from validated repository and pinned-source identities. It permits HTTPS links to the configured GitHub origin and application routes, blocks executable and unsupported schemes, and applies safe external navigation. Artifact rendering makes no source-directed network requests. Images, fonts, and other resources are bundled trusted assets or fetched by trusted acquisition under the same allowlist and captured by content identity. Browser script policy, restricted SVG output, and sandboxed export viewers provide additional enforcement; source-derived active content is never admitted to those formats.

Before hashing and publication, validate the presentation document and renderer output structure against these rules. Implementation acceptance includes hostile markup, SVG, diagram labels, and URLs across every renderer, plus relation direction and epistemic-state preservation. A rendered hash identifies what was shown; it does not itself establish security or semantic correctness.

## What the reviewer sees

The GitHub-facing entry point is small: the key change summary and a link into the richer review experience.

The review page starts with a concise overview and the concepts most relevant to the review decision. The primary unit of explanation is a **behavioral concept** such as an execution path, data flow, behavior change, or important decision. Files and diff hunks are evidence beneath those concepts.

Unchanged surrounding code is included when it is necessary to understand changed behavior. The system does not expand into a whole-subsystem explanation unless the change genuinely requires it.

Claims and concepts are ordered by **decision relevance**, not by line count or file count.

## Explanation artifacts

Every review revision gets an infographic.

The infographic uses a consistent visual language so reviewers learn how to read the product, while its structure adapts to the change. Every semantically meaningful node, relationship, priority, uncertainty marker, grouping, direction, and emphasis must originate from the validated semantic artifact. Generation may choose geometry and non-semantic styling, but it cannot create new meaning through layout.

The system may add other artifacts according to the structure of the change, including:

- flow diagrams for execution or data paths,
- tables for structured comparisons or schema-like changes,
- prose explanations,
- interactive traces where interaction materially helps understanding.

The reviewer may request additional artifact types. Video is explicitly outside the MVP and may be explored later.

Presentation is a projection of semantic truth. A renderer can choose how validated information is expressed, but it cannot introduce new factual claims or implied semantic relationships.

Every concrete reviewer exposure has an immutable **PublishedViewIdentity** derived from the validated semantic-artifact identity, the presentation-policy and renderer versions, and content hashes of the rendered artifacts. Reviewer state records which PublishedViewIdentity the reviewer actually saw. A later rerender of the same semantic artifact is a different exposure if any treatment-affecting presentation input or rendered artifact changes.

## Architecture

```text
GitHub PR + optional agent trace
              │
              ▼
 Trusted Acquisition / Controller
 fixed policy + read-only retrieval
              │
              ▼
   Code Comparison Identity
 repo + PR + head + target-base tip
 exact comparison base / merge result
              │
              ▼
 Change Surface Inventory
 complete immutable Git tree delta
              │
              ▼
   Semantic Input Manifest
 content-addressed consumed records
              │
              ▼
       Source Snapshot
 complete review input identity
              │
              ▼
   Comprehension Engine
 candidate claims + concepts
 coverage mappings + residuals
              │
              ▼
      Claim Validation
 semantic support + epistemic state
              │
              ▼
 Validated Semantic Artifact
              │
              ▼
         Presentation
              │
              ▼
    Published View Identity
              │
       ┌──────┴──────┐
       ▼             ▼
 Reviewer State   Review View
 summary + evidence + infographic + selected artifacts
```

The boundaries are deliberate:

- **Trusted acquisition/controller** owns policy and tool authority, canonical GitHub reconciliation, Code Comparison Identity, typed immutable input capture, the mechanical change-surface inventory, and the Semantic Input Manifest.
- **Source Snapshot** owns exactly which immutable source, evidence, trace, and policy identities were analyzed.
- **Comprehension** proposes claims, concepts, risk/relevance judgments, many-to-many coverage mappings, and residual coverage state, using snapshot-bound data only.
- **Validation** independently assesses evidence support and returns untrusted typed results. The controller checks bindings and scope, enforces deterministic checks where specified, and preserves model-assessed support and uncertainty.
- **Archive/publication** owns immutable publication, atomic canonicalization for one exact input identity, and the concrete rendered-artifact hashes that form PublishedViewIdentity.
- **Reviewer state** owns person-specific observations and decisions, bound to the exact SourceSnapshotId and PublishedViewIdentity that the reviewer saw.
- **Presentation** owns inert rendering and semantic-operator validation, preserves support basis and uncertainty, and contributes its policy and renderer versions to PublishedViewIdentity.

Semantic truth, presentation, and reviewer state remain separate.

## Revisions, freshness, and reuse

A review is tied to one exact **Source Snapshot**, not merely a PR head SHA. Identity is layered to avoid circular provenance.

The **Code Comparison Identity** is established first from:

- repository identity and pull-request identity,
- head commit,
- the current target-base tip SHA observed when the comparison is established,
- the exact comparison or merge-base SHA used to derive the change,
- no verification result, check-specific execution subject, or agent trace.

Each **Verification Evidence Identity** records provider, run and attempt, check scope, actual execution commit or tree, consumed payload hashes, and eligibility decision. Head-only checks must match the pinned head. Merged-behavior checks require independently established provenance connecting their actual subject to the pinned head and target base, including a corresponding merge-tree identity when applicable. Missing or conflicting provenance is a visible gap, never evidence of a verified merge. Two checks can have different subjects without changing Code Comparison Identity. Selection depends on the comparison inputs and check provenance, so identity construction is acyclic.

Before publishable semantic computation, the system creates a content-addressed **Semantic Input Manifest** for every record the semantic stages can observe. Context discovery can request pinned records during acquisition. The manifest then freezes consumed PR metadata, repository records, archived verification payloads, and supplied trace. Published analysis reads only manifest records. A later request for absent context expands the manifest, creates a new snapshot, and restarts analysis; it cannot silently read new evidence under the old identity.

The **Source Basis Identity** content-addresses Code Comparison Identity, consumed mutable PR metadata, the complete in-scope verification identities and eligibility states, trace content, and source selection and freshness-policy versions. It changes on required check reruns or expiry, consumed metadata changes, missing required results, and applicable policy changes even when code is unchanged. Observation times are recorded separately, so unchanged repeated observations do not themselves create new identities.

The complete **Source Snapshot / ReviewSnapshotIdentity** then includes:

- the Code Comparison Identity,
- the complete Source Basis Identity,
- the identity of the mechanically derived change-surface inventory,
- the Semantic Input Manifest identity,
- the versioned rule that defines which verification results are in scope and when they are fresh enough to be used,
- the complete set of in-scope verification identities, including each actual execution subject, archived content, provenance, and eligibility state,
- the comprehension and validation-policy versions.

A verification result is never eligible merely because it belongs to the same PR. Its actual subject and scope must match the pinned comparison inputs under the versioned eligibility rule. Acquisition records the complete required set, including failing, missing, stale, or unavailable required results. Unknown verification cannot silently count as passing. Adding, removing, replacing, changing consumed payloads, or expiring a required result changes source basis even if no published claim cited it.

Acquisition records per-resource observation times and an interval. The controller enumerates the required resource membership, captures content and immutable provenance, and rereads membership, identities, and versions after collection, including pagination. Detected drift starts a new attempt, with at most three total attempts. Failed enumeration, missing required observations, unavailable provenance, or repeated drift yields unknown consistency and explicit gaps. Such a bundle can be retained as an incomplete historical observation, but cannot claim observed freshness or enter scored evaluation.

Matching reads establish **observational stability**, not a provider-wide atomic transaction. A Source Snapshot is a reproducible bundle of pinned content and timed observations; it does not assert that every mutable GitHub resource coexisted at one instant. Undetectable intervening changes remain an observation limitation. Baseline, instrument, and product consume this exact captured bundle; evaluation makes no claim of an atomic frozen provider state.

GitHub events accelerate reconciliation. At presentation and decision recording, the controller freshly reconciles the full expected Source Basis Identity and evaluates required-result expiry at that boundary. It records matching, stale, or unknown with observation interval, resource times, and a finite freshness deadline prescribed by the versioned policy. Code identity alone is insufficient. The UI says when the snapshot last matched observed state and stops representing that observation as fresh when its deadline expires or a mismatch or unknown state is detected.

Decision storage compares and swaps the expected local SourceSnapshotId and PublishedViewIdentity so concurrent replacement cannot misattribute a decision. This local operation does not lock GitHub resources. Every decision retains its exact view and observed freshness. The MVP does not automate merges or promise atomic live-current approval. A later action requiring an atomic provider precondition must use an enforceable provider condition or decline that stronger claim.

When any part of that identity changes:

1. the existing review revision becomes visibly stale,
2. a new review revision is created automatically,
3. the MVP recomputes semantic claims and concepts against the new snapshot,
4. raw immutable extraction may be reused by content identity, but semantic claims are not reused across changed snapshots.

The review view remains visibly pinned to its SourceSnapshotId and PublishedViewIdentity. Reviewer notes, confidence, and decisions bind to the exact view exposure they were made against; they do not silently carry onto a changed review revision or a materially changed rerender.

Publication, rather than model generation, is idempotent. A unique publication key over the complete snapshot identity plus comprehension/validation versions is canonicalized atomically. Because the Semantic Input Manifest covers every record semantic computation can observe, semantically different consumed inputs cannot compete under the same publication key. Concurrent runs may compute different candidates, but only one immutable artifact can become authoritative for that key.

## Reviewer decision and measurement

The product surfaces evidence, risks, uncertainty, and explanations. It does not recommend approve/reject.

Reviewer-specific behavior lives outside the immutable semantic artifact. This lets the system measure review behavior without changing the shared explanation of the code.

Useful product signals include:

- comprehension accuracy,
- time to decision or answer,
- confidence calibration,
- concepts that consume reviewer attention.

Confidence alone is not treated as proof of understanding.

## MVP validation

Comprehension checks are an **evaluation instrument**, not a permanent quiz in the normal review workflow.

A validation trial uses one previously unseen eligible evaluation PR exactly once. The reviewer sees either:

- the normal GitHub review experience, or
- the comprehension product.

The normative [Solo evaluation protocol](../work/critical-only/evaluation-protocol.md) specifies the full decision rule and failure policy. Its defaults use 12 matched pairs, three scored items per snapshot, a 10-percentage-point minimum gain, and a descriptive paired bootstrap interval. These are provisional engineering choices for an exploratory solo pilot, not a power claim. Product failures use a frozen baseline fallback while retaining assignment, actual answers, and attempted-delivery time. Unknown outcomes remain in the analysis with prespecified adverse and favorable sensitivity scenarios. No randomized snapshot is dropped or replaced.

Before the first scored trial, the protocol freezes the sample size, PR eligibility rules, matching dimensions, randomization procedure, timer boundaries, question-generation procedure, answer-key format, evidence-support/adjudication procedure, and free-response scoring rubric. It also freezes an immutable **ProductTreatmentId** and **BaselineTreatmentId**. Together these identities cover every treatment-affecting version or configuration, including model and inference settings, prompts, semantic and validation implementation or policy versions, retrieval implementation, renderer and visual-language versions, baseline rendering procedure, and UI builds. Any treatment-affecting change starts a new cohort or experiment.

Scored validation uses previously unseen AI-generated or agent-authored open-source PRs so the sample matches the product's target use case. Human-authored PRs may be used separately for exploratory comprehension testing but are not counted as target-product validation.

Eligible PRs are first captured as complete, observationally stable Source Snapshots and arranged into matched pairs using observable review-difficulty factors such as change type, changed size, file count, and verification evidence. SourceSnapshotId is the unit of a scored trial. Evaluator, answer key, baseline, product, and fallback consume the same captured bundle. Baseline presents normal GitHub review information from that bundle, not later live content. Every scored exposure records its frozen treatment and concrete view identity; successful product delivery records PublishedViewIdentity. Failed product delivery records the fallback view, failure reason, and original product assignment.

For every candidate snapshot, before condition assignment, an independent evaluator derives the protocol's three questions and expected answers without seeing the product explanation. Expected answers meet the same support standard as product semantics, with their support basis recorded. A second independent adjudication process checks each question, key, and pinned evidence; ambiguous or disputed items are revised or removed before the three-item instrument is frozen. The protocol then randomizes assignment and exposure order. Each snapshot is reviewed once. Questions include multiple choice and short mechanism responses. Scorers use a frozen rubric without seeing condition or delivery-failure status. These processes remain fallible; the endpoint is accuracy on this evidence-adjudicated instrument, not certified complete PR understanding.

Primary metric: **comprehension accuracy**.

Secondary metric: **time**.

Diagnostic metric: **confidence**.

Results use all 12 assigned pair differences with equal pair weight, the frozen bootstrap procedure, and primary and sensitivity decisions. Individual pairs, missingness, and delivery failures remain visible. The protocol declares success only for its provisional creator-only signal; time and confidence cannot override accuracy.

The initial solo experiment measures whether the product helps its creator understand unseen AI-generated PRs. It does not establish general performance across developers; broader reviewer testing follows only if the solo signal is promising.

## MVP invariants

- Every reviewer-meaningful semantic assertion is evidence-backed, explicitly an inference/uncertainty, or explicitly an agent report where that epistemic state applies.
- Every supported semantic assertion has passed an explicit support-validation step; citation presence alone is insufficient.
- Evidence is inspectable from the claim that depends on it.
- The mechanical change-surface inventory comes from the complete immutable Git tree delta, and opaque/uninspectable surfaces remain explicit.
- Coverage is many-to-many; every inventory item has an explicit residual/closure state, and an independent closure-falsification pass reopens any unresolved plausible material consequence as a visible gap.
- Mechanical change-surface completeness and semantic closure are distinct; the former is derived exhaustively from the immutable Git-tree delta, while the latter remains a falsification-backed claim.
- Repository, PR, verification, and agent-trace contents are authority-inert but semantically untrusted across a structurally enforced boundary; trusted deterministic code owns policy and tool authority.
- Generator and validator outputs remain untrusted. Deterministic publication checks enforce bindings, scope, and mechanical obligations; displayed model-assessed support remains explicitly fallible.
- The human owns the review decision.
- Every review revision has an infographic.
- Additional artifacts are selected from the structure of the change.
- Presentation cannot create semantic facts or semantic relationships through layout.
- Every reviewer exposure has an immutable PublishedViewIdentity over semantic-artifact identity, presentation/renderer versions, and rendered-artifact hashes; reviewer state binds to the exact view shown.
- Review revisions are immutable and tied to exact source-and-evidence identity.
- Code Comparison Identity is established independently before verification evidence is selected.
- Every record exposed to semantic computation is content-identified by the Semantic Input Manifest before analysis.
- Each in-scope verification result retains exact archived content, provenance, actual execution subject, and eligibility under the pinned comparison inputs.
- Any Source Snapshot identity change automatically creates a new review revision.
- Observed freshness reconciles the full Source Basis Identity and required-result expiry, with observation times and a finite deadline. Local compare-and-swap protects exact snapshot and view attribution; it does not lock GitHub state.
- Semantic analysis is recomputed across changed review revisions in the MVP.
- Reviewer observations and decisions are bound to the review revision they were made against.
- GitHub PR is the only first-class source in the MVP.
- Video is outside the MVP.
- Every renderer treats source-derived content as inert data, validates semantic operators, and enforces trusted URL and resource policy before publication.
- Captured snapshots are timed observation bundles. Unknown acquisition consistency prevents observed-fresh claims and admission to scored evaluation.
- Scored trials bind one immutable SourceSnapshotId to the frozen instrument, protocol, treatment identities, assigned condition, and actual exposed view. Product delivery failures remain assigned product and follow the frozen fallback and missing-data policy.

## Accepted tradeoffs

- A richer semantic model is accepted in exchange for evidence traceability across every artifact.
- Recomputing semantics on every changed snapshot is accepted in exchange for simple, trustworthy freshness in the MVP.
- A GitHub-only source is accepted in exchange for avoiding premature integration abstractions.
- A required infographic is accepted even for simple PRs to make the visual experience a consistent, testable part of the product.
- Adaptive artifact selection is accepted in exchange for keeping the review concise and concept-driven.
- Separate reviewer state is accepted in exchange for immutable shared semantic truth and measurable comprehension.
- Possible duplicate computation during concurrent first generation is accepted because publication remains atomically canonicalized.

## Explicitly deferred

- video generation,
- arbitrary patch bundles or non-GitHub source integrations,
- autonomous merge or approval decisions,
- a generic agent-event platform,
- making comprehension checks a permanent merge gate,
- cross-revision semantic reuse,
- broad claims about effectiveness across developers before multi-reviewer validation.

## Implementation checkpoint

No implementation has started. The next implementation design should begin with `CodeComparisonIdentity`, trusted acquisition/controller authority, the complete Git-tree change inventory, `SemanticInputManifest`, and provenance/content-bound verification evidence, then build `SourceSnapshot`, independent semantic validation, closure falsification, `PublishedViewIdentity`, and write-boundary currentness contracts. Evaluation then freezes treatment identities before scored exposure. Every downstream artifact, freshness decision, publication key, reviewer-state record, and scored evaluation trial depends on those boundaries being explicit first.
