# Design B: one domain facts module (chosen shape)

## Caller usage (written first)

The calculator moves to a domain module. Existing import paths stay.

    # comment.py - public import unchanged, body delegates
    from prc.presentation.card import compute_stats      # kept, thin alias
    stats = compute_stats(m, brief)                      # -> prc.facts numbers

    # card.py - build_card_html formats only
    facts = map_facts(m, brief)
    stats_html = _stat_cells(facts)

    # render_map.py - page data block only, at render time
    {"facts": facts_json(facts), ...}                    # additive page key

    // map.js - consume, never recompute
    const F = MAP.facts;                                 // header, summary, captions
    const flagIds = new Set(F.untested.map((u) => u.id));

CLI, `map.json` schema, and board tools: unchanged. The summary serializes into
the page data block at render time; `map.json` stays byte-compatible, and old
stored maps still render because `_change_map_from_stored` rebuilds a
`ChangeMap` first and `render_map` injects `facts` afterwards.

## Types and signatures (minimal)

    # src/prc/facts.py - domain layer; imports prc.brief types only
    @dataclass(frozen=True, slots=True)
    class FactsEntry:
        id: str          # symbol id "path::qualname"
        name: str        # qualname
        path: str

    @dataclass(frozen=True, slots=True)
    class MapFacts:
        files: int                 # brief.files; map.files equals it (one inventory)
        symbols_changed: int       # symbols added|modified|deleted, tests included
        call_sites: int            # sum sym.call_sites over those symbols
        tests_touched: int         # brief files of kind "test"
        ci_passed: int             # brief.checks with state "passed"
        ci_total: int              # len(brief.checks)
        ci_state: str              # "passed"|"failed"|"pending"|"none", derived once
        risky_total: int           # brief files with a sensitive reason
        unparsed_files: int        # changed files with language None
        untested: tuple[FactsEntry, ...]   # definition below

    def map_facts(m: dict[str, Any] | ChangeMap, brief: Any = None) -> MapFacts
    def facts_json(facts: MapFacts) -> dict[str, Any]

`map_facts` also owns the brief normalization duplicated in card.py and
comment.py (`Brief` object or embedded dict); card's `_brief_dict`/`_brief_of`
move there. `compute_stats` stays a one-line wrapper building `CardStats` from
`map_facts`, so tests/test_card_comment.py and comment.py work unchanged.

## Definitions (one per label)

- files: brief files; map.files is built from the same inventory, and a
  regression pins `MAP.files.length == facts.files`.
- symbols changed: added, modified, deleted symbols, tests included.
- call sites: sum of `call_sites` over changed symbols (card rule; map.js drops
  its changed-lane-only variant).
- tests touched: brief files of kind test (card rule; map.js switches from
  changed test symbols to this file count).
- CI: passed and total from brief.checks; `ci_text` and `ci_state` derive once.
- no direct test: added or modified symbols outside test files with no incoming
  edge of status other than "removed" whose source is a test symbol shown in
  this map. map.js's rule wins; card widens to match (it now counts deleted
  symbols and removed edges as covered).

## Wording and limits

- "no direct test" stays. Positive text: "Every changed symbol is called by a
  test in this map." Card and comment replace "Every changed symbol has a
  direct test." (tests/test_card_comment.py:291 already bans it).
- Wording never claims test coverage: a call edge from a test symbol is display
  evidence from shown code, not a coverage proof. The drawer line "no test in
  this map calls it" states the boundary and becomes the shared wording.
- Unsupported parsing: files with language None (unsupported, opaque, oversize)
  yield no symbols, call sites or edges. `unparsed_files` makes the limit
  visible; card and map show "N files not parsed" when above zero, so counts
  are self-describing.

## Responsibility map

- prc/facts.py: definitions, one calculator, brief normalization. No
  presentation imports. Unit-testable without a browser.
- presentation/card.py: layout, escaping, tones, png capture; `compute_stats`
  alias retained for EVAL gate 6 and comment.py.
- presentation/comment.py: markdown assembly and formatting only.
- presentation/render_map.py: page assembly; injects `facts` for fresh and
  stored maps.
- map_assets/map.js: DOM, tour, camera; consumes `MAP.facts` verbatim and keeps
  only display derivations (flag nodes by id, plural labels, tone classes).
- Parent regressions: same numbers across card HTML, comment text, and rendered
  page; wording bans; `unparsed_files` visible when parsing is partial.

## Why shape A loses

A serializes card-computed statistics into every output and keeps the calculator
in card.py. Four failures:

1. Wrong boundary. Domain consumers (comment, EVAL gate 6, future map.json
   readers) would import statistics from a presentation module; the dependency
   arrow points from domain to GUI.
2. Two calculators survive. `map.json` gains a schema field, so old stored maps
   lack it and render still needs a fallback calculator. A never removes the
   duplication it exists to remove.
3. Wrong payload. CardStats carries aggregates only; the map needs untested
   symbol ids for node flags, so map.js keeps recomputing partial facts anyway,
   which is the defect being fixed.
4. Rigid extension. New facts (`unparsed_files`, `ci_state`) extend one dataclass
   and one definition table here; under A they touch the card signature, the
   serialization step, and each consumer's fallback path.

B keeps one calculator in the domain, preserves the card's public import, and
ships one additive page key. Definition fixes surface as changed displayed
numbers, which the parent's regressions encode.
