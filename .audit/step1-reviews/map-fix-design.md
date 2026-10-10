# Step 1 map fixes: data-shape sketch

## Alternatives compared

A. Extend the GraphDoc contract with coverage fields. Rejected: the contract is pinned
(schema 0.2.0, renderer 0.3.2, zod goldens, vendor-owned bundle). New required fields risk
safeParse failure and widen the blast radius.

B. Add a new top-level coverage block beside map/graph/steps/dropped. Rejected: it duplicates
data already present (MAP.files, MAP.tour, BLOCK.dropped, BLOCK.steps) and needs new plumbing.

C. Chosen: keep the GraphDoc contract byte-identical; add exactly one nullable key,
layoutError, to the page BLOCK; render all disclosure from data already shipped;
name lost tour focus inside step body text (still within MAX_BODY, still valid);
navigate every changed file from MAP.files, which stays complete.

Deepest/smallest interface: MAP is the complete record; GRAPH is a bounded view
(256 nodes, 512 edges); the page BLOCK is the only seam and gains one key.
No new dependency, no schema change.

## Terminating caps (one pass, no fixpoint loop)

_select becomes: risky file nodes first (capped at 12 and clamped to the node budget),
then changed symbols by churn, then context symbols, then aggregate file nodes fill only
the remaining budget. Every slice is clamped at zero so a negative budget yields nothing.
Total nodes stay within MAX_NODES by construction. _overview_doc clamps the same way.
A 300-file flood and a 300-entry risky tour both terminate with a bounded subset.

## The node cap is not the navigation cap

The drawer already renders any MAP file or symbol by index; centering guards on atlas
presence. The missing piece is UI: a persistent file list over every MAP.files entry,
so README-style files keep diffs in ordinary and grouped maps. Both modes gain the list.

## Honest disclosure

- Dropped symbols/edges: BLOCK.dropped already ships; render it in the summary.
- Omitted tour steps: derive from MAP.tour versus BLOCK.steps, no new key.
- Grouped edges: keep edges between plotted walk symbols only; disclose shown vs total.
- Lost tour focus: keep focus-all fallback but suffix step body with dropped short names.
- Conversion failure: page_data records contract issues in layoutError with graph null;
player shows an error banner for layoutError, the empty card only when MAP is empty,
and the file list stays available. A failed conversion never reads as an empty PR.

## Bundle pin at render time

render_map compares sha256 of installed bundle bytes with prlens.lock.json before
embedding and raises a clear error on mismatch. Re-vendoring stays with vendor agent.

## Regression tests (written first, red saved)

Termination with subprocess timeouts (300 single-symbol files; 300 risky entries);
ordinary-file diffs kept; grouped and plain disclosure; honest conversion failure;
lost focus named; bundle tamper rejected; grouped edge counts disclosed.
Browser cases save screenshots on the real artifact.

Principles read: model-the-domain (MAP-complete vs GRAPH-bounded split chose the seam),
laziness-protocol (one nullable key, no new dependency, no schema edit),
prove-it-works (red log plus screenshots before any done claim).
