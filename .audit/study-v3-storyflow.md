# Storyboard infographic design

## Summary

The v3 infographic must show system behavior from the same storyboard as its video and clickable page.
The old brief can only show production call edges and selected source docstrings.
It rejects test-only changes as flat, and presents function names where the user asked for a high-level view.

## Usage and candidates

Candidate A selects an existing groups scene through board.infographic = {mode: storyboard-flow, scene: index}.
The selected scene's fly cues define flow direction between grounded group items.
The group titles become high-level node labels. The legend explicitly describes storyboard flow, not inferred calls.
verify_board validates the entire board and each cited endpoint before brief generation.
The artist receives the exact labels and directed relationships already used by the video.
No second storyboard or parallel node list exists.

Candidate B adds an independent overview object with nodes, citations, and typed relationships.
That gives a larger interface, duplicates endpoints and receipts, and can drift from the video scene.
It also needs another validator for equivalent grounding.

## Contract

Existing boards without an infographic selector retain the current source-derived brief.
A selected scene must exist and be a groups scene. Its fly cues must connect distinct grounded groups.
No flow, unknown endpoints, uncited ground, unsupported mode, or invalid scene refuses drawing.
A pure-test PR can have a high-level diagram, without claiming production call evidence.
A storyboard's semantic prose remains authored explanation, supported by source receipts.
The automated checker does not prove every semantic label or causal inference. The author must inspect those against the source.
The gate still checks exact words, connecting ink, and published bytes.
Agent inspection must check actual endpoints, direction, arrowheads, extra connectors, and dash patterns before handoff.

## Evidence

Seven regression cases target the previous implementation. Their failing run was not saved, so this record cannot prove they failed first.
The first returns [] where the two cited group titles and a flow relation are expected.
The other six fail DID NOT RAISE for invalid authored flows.
The earlier GLM report did not provide reliable source evidence and is not counted as approval.
Independent reviewers Feynman and Kant reproduced four label and endpoint defects.
The fixes reject duplicate item IDs, duplicate normalized group titles, and headline collisions before and after fitting.
Meitner independently checked the final normalization fixes: 14 regression cases passed.
Kant checked the other scoped changes and actual browser outro: 228 tests passed.
The parent inspected decoded videos and rebuilt all eight after replacing the obsolete prc map outro.
