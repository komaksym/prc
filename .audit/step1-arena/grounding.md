# Step 1 design grounding (infographic step and PR Lens map)

Worktree: /Users/koval/dev/prc/.claude/worktrees/readiness (branch feat/trustworthy-pr-explanations). Read-only for design runners.
Python 3.12 package `prc` (src/prc). Strict mypy, ruff, pytest. Read CONTEXT.md, docs/mvp/DECISIONS.md and PLANS.md for project vocabulary.

## What step 1 must deliver (user approved)

1. Infographic step. Each PR explanation gets one AI-drawn infographic made with the baoyu-infographic skill
   (/Users/koval/.codex/skills/baoyu-infographic/SKILL.md) through the agent's native image tool (Codex imagegen).
   PRC writes every word the image may show. An OCR gate checks the image. The image appears inline in comment.md,
   doc.html and the acceptance review page only when the gate passes. Otherwise the outputs fall back to the existing card.
2. Interactive map rebuilt on the MIT PR Lens renderer: npm @coldtea/pr-lens-renderer@0.3.2 and @coldtea/pr-lens-schema@0.7.0
   (graph contract 0.2.0, zod ^4.4.3). PRC's own computed ChangeMap feeds it. PRC keeps its own player and drawer.
3. (Not part of this design) Kokoro voice gate and the acceptance rebuild.

## Hard constraints

- PRC ships as a Python wheel. Runtime deps: numpy, pygments, tree-sitter. The `video` extra adds playwright (Chromium).
  `prc map` must keep working without playwright. No Node.js at runtime. Node 26 and npm exist on this dev machine and may be used only
  by a vendoring script that builds a committed, pinned bundle.
- Outputs are offline, self-contained and deterministic (same inputs give the same bytes).
- map.html CSP today: `default-src 'none'; script-src 'sha256-<hash>'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'`.
  PR-controlled strings reach the page only through one JSON data block (`<script type="application/json" id="map-data">`); scripts build DOM with textContent.
- PRC never calls an image model and never posts to GitHub. Only the agent that runs the prc-explain skill (src/prc/skill/SKILL.md) can call imagegen.
- baoyu-infographic rules that bind us: save each prompt to a file before generating; never repair text by painting over a bitmap; regenerate
  from a new prompt file instead. Technical profile = structural-breakdown layout + technical-schematic style, 16:9, en, backend auto (imagegen).
- Tesseract 5 is at /opt/homebrew/bin/tesseract on this machine. It is not a Python dependency. tests/test_card_comment.py already OCRs card.png.
- PRC's product claim on the map: "computed from the code, no AI drew this" (src/prc/presentation/render_map.py BRAND). The infographic is AI drawn,
  so it must say so where shown, and its words must come from PRC.

## Current code you must integrate with

- src/prc/pipeline.py run_explain (about lines 535-667): writes map.json, map.html (render_map(change_map)), and with --board: board.json, video.mp4,
  doc.html (explainer/doc.py render_doc), then card.html/card.png (presentation/card.py), comment.md (presentation/comment.py render_comment),
  run.json. Everything is staged in a temp dir and published atomically by _publish_explain.
- src/prc/cli.py: subcommands map, brief, explain (--source --map --board --git-dir --voice --out), board {guide,show,find,coverage,check,preview}, skill install, doctor, eval-analyze.
- src/prc/facts.py compute_facts(map_dict, brief) -> Facts(stats: CardStats(files, symbols_changed, call_sites, tests_touched, ci_*, untested_total),
  no_direct_test, limits, edges_added, edges_removed, ci_state, test_verdict). presentation/card.py: headline(m, board) (uses the board outro l1 when present),
  look_first(...), risky(...). These are the single source of PR facts; the card, comment and doc already share them.
- presentation/comment.py render_comment(m, brief, board, card_available, card_warning): headline, card image line, a checked Mermaid block, look-here-first, risky, test evidence.
- src/prc/changemap.py ChangeMap(pr, url, title, author, base_sha, head_sha, brief, files: FileNode, symbols: Symbol, edges: Edge, tour: Step).
  Symbol(id, path, qualname, kind class|function|method, status added|modified|deleted|context, span, base_span, added, removed, hunks, call_sites).
  Edge(source, target, status added|removed|kept, resolution exact|name). FileNode(path, kind code|test|opaque|..., status, language, sensitive, added, removed, hunks, symbols).
  Step(kind overview|risky_file|entry|callee|test|summary, focus ids, via).
- Map front end today: presentation/render_map.py (158 lines) + map_layout.py (732 lines, Python layout with lanes, folders, dense mode for large maps)
  + map_assets/map.js (1132 lines: camera pan/zoom/fit/flyTo, folder collapse, drawer with diff view and callers/callees, tour with captions and summary)
  + map_assets/map.css (1128 lines). presentation/map_video.py records the tour into an MP4 by seeking window.prcTour, and captures a 1200x630 card frame.
- Tests on the map: tests/test_render_map.py, test_map_browser.py, test_map_grouping.py, test_map_layout.py, test_map_video.py, test_e2e_map.py, test_map_cli.py.

## Map hooks other code depends on (keep them or change every caller)

- window.prcTour = {duration, steps: [{kind, focus, via, start, duration, caption}], seek(t)}. map_video.py and tests seek it.
- Every symbol node is an element with data-node="s{i}", i = index into map.json symbols.
- Clicking [data-node="s{i}"] for fixture:shop's checkout opens #drawer (aria-hidden="false", transform none when settled) and the drawer text includes apply_discount (its callee).
- Escape closes the drawer (aria-hidden="true", drawer left >= innerWidth when settled).
- #play button, #zoom-in, #zoom-out, #zoom-fit. No page errors.
- Callers: scripts/verify-release.sh (installed-wheel smoke), .agents/skills/verify/scripts/map.py, tests above.

## PR Lens facts (measured from the npm tarballs unpacked at /private/tmp/prlens/{r,s}/package)

- renderer: ESM, sideEffects false. render(doc, {lens: "architecture"|"data-flow", theme: "light"|"dark"|"neutral", view?, config?}) -> {svg, width, height, atlas, animated}.
  atlas.nodes[id] = {x, y, width, height} in SVG viewBox units; also lanes, edges, flow messages. Pure: no clock, no file, no randomness.
  Only manifest.js imports node:crypto (used by renderAll/buildManifest, not by render). Animation is SMIL inside the SVG. Labels are XML-escaped by the renderer.
- schema: parseGraphDoc / safeParseGraphDoc (zod 4, structure + referential integrity). json-schema/graph-doc.schema.json exists (structure only).
  Contract limits: lanes 1..16, nodes 1..256, edges <= 512, label <= 120 chars, ids ^[A-Za-z0-9][A-Za-z0-9._:/-]*$ <= 128, node kind enum
  (service, app, module, function, route, job, queue, datastore, cache, external, ui, config, test, package, other), delta added|modified|removed|unchanged,
  node files[{path, startLine, endLine, revision head|base}], badges <= 6, edge kind enum (call, http, rpc, event, queue, data, dependency, render, other),
  edge emphasis normal|hero|muted, animated bool. Walkthrough: 2..12 steps, heading <= 48 chars, body <= 140 chars, focus {kind:"all"} or selection of lane/node/edge ids,
  optional stage view/flow, optional detail text <= 240 with cites. Examples in /private/tmp/prlens/s/package/examples/.
- The hosted PR Lens canvas player is not published. PRC must write its own player around the SVG.

## Acceptance PRs the result must handle (map.json under artifacts/trustworthiness/2026-10-09/acceptance/<case>/output/<slug>/)

- librarysync-98: 2 files (python code + test), 20 symbols, 19 edges, tour overview, entry, callee, test, summary.
- em-5756: 7 files (typescript, tsx, a yarn patch, docs, yarn.lock), 6 symbols, 5 edges, 2 risky_file steps.
- swarm-116: 7 Go files, 0 symbols, 0 edges (Go is not parsed), tour overview, summary. The diagram must not be empty: use file nodes.
- Larger real PRs exist (PRC has a dense mode for maps with many symbols). The contract caps nodes at 256.

## Verification the result must allow

- Real-browser checks with screenshots (Playwright Chromium headless; PLAYWRIGHT_BROWSERS_PATH=/Users/koval/dev/prc/artifacts/release/browser-cache).
- Tests must assert behavior (an identifiable defect fails them), not mirror implementation.
