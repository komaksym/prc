TL;DR: Choose B, with one pure facts module and one additive browser summary. Current counts disagree, and test wording exceeds static evidence. Existing imports, map fields, and CLI commands stay compatible.

## Caller usage first

Paths below are relative to `src/prc/` in the readiness worktree. Proposed functions are sketches, not existing APIs.

```python
# presentation/card.py:build_card_html and comment.py:render_comment
facts = compute_facts(m, brief)
stats, missing = facts.stats, facts.no_direct_test

# pipeline.py:run_map, _live_map_dict, load_map_dict, run_explain
payload = map_payload(change_map)  # existing fields plus summary

# presentation/render_map.py:data_block
payload = map_payload(change_map)  # same serialization contract
```

```javascript
// map_assets/map.js: header, badges, describe(), fillSummary()
const facts = MAP.summary;
const missing = new Set(facts.no_direct_test.map(s => s.id));
```

The browser reads facts before layout filtering. It never counts rendered nodes to produce PR totals.

## Minimal shape

```python
# facts.py; frozen records
# Move existing CardStats and UntestedEntry without changing their fields.
ParseLimit(path: str, reason: str)
Facts(stats: CardStats, no_direct_test: tuple[UntestedEntry, ...],
      test_symbol_ids: tuple[str, ...], limits: tuple[ParseLimit, ...],
      edges_added: int, edges_removed: int, test_evidence: str)

compute_facts(m: dict[str, Any],
              brief: Brief | dict[str, Any] | None = None) -> Facts
compute_stats(m, brief=None) -> CardStats  # compatibility: compute_facts(...).stats
untested(m, brief=None) -> tuple[UntestedEntry, ...]  # compatibility

# presentation/render_map.py
map_payload(change_map: ChangeMap) -> dict[str, Any]
# raw = to_jsonable(change_map)
# return raw | {"summary": to_jsonable(compute_facts(raw))}
```

Normalize the optional brief internally using today's precedence. Ignore any supplied summary when computing facts.
Re-export `CardStats`, `UntestedEntry`, `compute_stats`, and `untested` from `presentation/card.py`.
The existing import in `scripts/eval/gates.py:gate_card_facts` must keep working.

## Definitions and limits

Keep the card's count definitions. Files are distinct changed paths in the normalized brief, including opaque and generated files.
Changed symbols include added, modified, and deleted symbols, including test symbols.
Call sites sum their existing `call_sites` values. These represent resolved head-tree calls, including name matches, not drawn edges.
Tests touched counts distinct changed test files, including unsupported test languages. CI uses the existing passed/total check counts.
Added/removed call links count full-map edges by status, not call sites.

Classify test symbols through explicit file kinds. For unchanged context paths, reuse `brief.kind_of(Delta(path, False, 0, 0))`.
Never infer test identity from a layout lane.

Direct evidence requires a live production target and an exact, added or kept edge from a live test symbol.
Deleted targets are excluded from missing-evidence counts. Removed edges and name-only matches cannot establish direct evidence.
`untested_total` equals the missing-entry count. Sort entries by symbol ID.

Use "No direct test evidence in this map" and "Static calls do not establish test coverage."
A positive result says "Direct test-call evidence found for all live changed production symbols in this map."
Replace `comment.py`'s "Not covered by tests", positive direct-test claims, and `map.js:describe`'s "covers" wording.
The map omits some context callers. Missing evidence does not establish missing tests.

List changed code/test paths with null language. Use `codegraph.language_of` to distinguish unsupported extensions from other unparsed inputs.
Report opaque/generated skips separately. Do not invent size, binary, or parse-error reasons from null language alone.
Explain that supported languages still have unrecognized constructs and unresolved dynamic calls.
Zero parsed symbols must not mean no code changed. Show limits in card, comment, map empty state, and summary.

## Responsibility map

| Owner | Responsibility |
|---|---|
| `facts.py` | Normalization, totals, direct-evidence policy, parsing limits, qualified evidence wording. |
| `brief.py`, `changemap.py`, `codegraph.py` | Classification, parsed symbols, graph data, parser registry. |
| `card.py`, `comment.py` | Existing headline, board ranking, risky entries, markup and escaping; ranking reads shared evidence. |
| `render_map.py`, `pipeline.py` | One payload adapter for JSON and HTML; recompute after stored-map reconstruction. |
| `map_assets/map.js` | Presentation and interaction; render serialized facts in every summary location. |

Keep `data_block`'s escapes and script hashing. The changed script gets its newly computed CSP hash.

## Synthesis decision

A keeps `compute_stats` in `card.py`, expands its facts, and serializes them everywhere. It can fix numeric drift.
Its smaller initial diff retains domain policy inside a renderer that imports templates and screenshot resources.
Every future output must discover that ownership.

The cross-judge agrees with B's ownership. Both shapes can eliminate browser duplication.
Choose B's domain ownership and retain A's existing definitions and compatibility imports.
Move only fact policy; preserve presentation helpers. Accept one new module in exchange for independent fact computation.
Reject extra files, board-dependent facts, and browser fallback calculators.

Validation remains with the parent's regression suite. Check unsupported-only changes, test-file counts, removed/name edges, context tests, and stored regeneration.
Require CLI artifacts and browser screenshots proving card/comment totals equal the serialized map summary.

Suggested next step: implement consistent, qualified facts across card, comment, and browser with the parent's CLI regression artifacts.

