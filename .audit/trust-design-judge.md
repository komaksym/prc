# Cross-judge: design A versus design B

TL;DR. Select one contract: B's ownership with A's precision. Both shapes now
propose one facts module and an additive browser summary; A models parse limits
and direct evidence better, B keeps `map.json` untouched. The selected contract
takes each side where it wins. Written against caller usage, not sweeps.

## Selected contract

Owner: `src/prc/facts.py`, a domain module owning definitions, normalization,
direct-evidence policy and parse limits. It imports brief and codegraph types
only. Dataclasses move from card.py with fields unchanged.

    @dataclass(frozen=True, slots=True)
    class ParseLimit:
        path: str; reason: str

    @dataclass(frozen=True, slots=True)
    class Facts:
        stats: CardStats                        # moved, fields unchanged
        no_direct_test: tuple[UntestedEntry, ...]
        test_symbol_ids: tuple[str, ...]
        limits: tuple[ParseLimit, ...]          # code and test paths only
        edges_added: int; edges_removed: int

    def compute_facts(m, brief=None) -> Facts   # ignores any supplied summary
    def compute_stats(m, brief=None) -> CardStats       # compat wrapper
    def untested(m, brief=None) -> tuple[UntestedEntry, ...]  # compat re-export

card.py re-exports `CardStats`, `UntestedEntry`, `compute_stats`, `untested`,
so scripts/eval/gates.py and comment.py keep working. render_map injects
`"summary": facts_json(...)` into the page data block; `map.json` stays
byte-compatible, and old stored maps render after `_change_map_from_stored`
reconstruction. map.js consumes `MAP.summary`; header, badges, `describe()` and
`fillSummary()` stop counting rendered nodes.

Definitions keep today's card rules: files are distinct changed brief paths;
symbols are added, modified, deleted, tests included; call sites are existing
`call_sites` sums (head-tree calls, name matches included, not drawn edges);
tests are distinct changed test files; CI is passed and total. Evidence rule:
a live production target, added or modified, with an exact added-or-kept edge
from a live test symbol; deleted targets excluded; removed and name-only edges
cannot establish evidence; missing evidence does not establish missing tests.

Wording, adopted from A: "No direct test evidence in this map" and "Static
calls do not establish test coverage"; positive "Direct test-call evidence
found for all live changed production symbols in this map." This replaces
"has a direct test" and map.js "covers"; the ban at
tests/test_card_comment.py:291 stays in force.

## Disagreements, decided

1. Parse limits: A wins. B lumped every language-None file as unsupported,
   opaque or oversize. Adopt A's split via `codegraph.language_of` and brief
   kinds. Only code and test paths belong in `limits`; docs and config are not
   parse failures and must not be listed as unparsed. Opaque and generated
   skips report separately. Never invent size, binary or parse-error reasons
   from null language alone.
2. D8 attribution: parent evidence, out of scope here. The regression shows
   D8 is difflib autojunk alignment; the original Git diff does not add a
   decorator to an existing function. Facts must inherit changemap hunks and
   never re-derive line tallies. Attribution quirks are a changemap fix, not a
   facts limit, and must not be explained away as parsing.
3. Serialization point: B wins. A's `map_payload` adapter feeds both JSON and
   HTML, which writes `summary` into `map.json` and makes board tools learn
   the field. Inject at render only and recompute for stored maps.
4. Edge counts: A wins. B left added and removed edge counts to map.js. Move
   them into `Facts` so the browser stays a pure consumer.
5. Naming: A wins. `compute_facts` greps closer to `compute_stats` than B's
   `map_facts`.

## Rejected from each side

From A: the stored `test_evidence` string, derive wording at format time;
board-dependent facts; browser fallback calculators. From B: lumped unparsed
counts, the `map_facts` name, aggregate-only payload without symbol ids.

## Validation

Parent regressions: unsupported-only change, test-file counts, removed and
name edges, context tests, stored-map regeneration. CLI artifacts and browser
screenshots prove card and comment totals equal the serialized summary.

Next step: land `facts.py` with compat re-exports behind the parent's
regressions, then the render injection, then map.js consumption as one unit.
