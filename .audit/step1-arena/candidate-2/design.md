# Candidate 2: spec-owned infographic, converter-owned map

## Problem

Step 1 adds two artifacts with opposite trust models to one pipeline. The infographic is AI-drawn, so PRC must author every word it may show and prove the pixels contain no other words, while never calling an image model itself. The map is computed, so PRC must feed the MIT PR Lens renderer a valid GraphDoc yet keep its own player, hooks, CSP shape, and offline wheel with no Node at runtime. The non-obvious part is the seam: who writes the prompt, who runs the gate, where the renderer bundle lives, and how ChangeMap semantics (name-only edges, tour, file-nodes-for-Go, 256 cap) survive a foreign layout engine.

## Usage (caller's view)

The agent running the prc-explain skill renders the PR first without an image:

prc explain --source https://github.com/<owner>/<repo>/pull/<N>

This writes map.json, map.html, comment.md, doc.html, run.json plus two new files: infographic.spec.json (every word the image may show) and infographic.prompt.md (the exact prompt file the baoyu-infographic skill requires before generating). The agent then runs the skill in technical profile (structural-breakdown + technical-schematic, 16:9, en) through its native image tool and saves infographic.png next to the spec. A second run gates it:

prc explain --source ... --map <stored> --infographic ./infographic.png

On gate pass, comment.md and doc.html embed the image with an AI-drawn disclaimer; on fail or absence they render exactly today's card fallback. No new subcommands; one flag and two modules are the whole surface.

The map needs no new invocation: prc map and prc explain emit the same map.html, now drawn by the vendored renderer bundle on page load, with the same window.prcTour, data-node, drawer, and zoom hooks the video recorder and tests already use.

## Shape

New module prc/infographic.py owns the infographic end to end. build_spec(map_dict, brief, board) derives an InfographicSpec (title, headline, stat lines, look-first entries, risky entries, test verdict, brand footer) purely from facts.compute_facts and card.headline/look_first/risky, so the card, comment, doc, and image can never disagree. write_prompt(spec, path) emits the frozen prompt file: profile line, exact-words block, word budget (headline + at most 5 panels x 3 bullets). gate_image(png, spec) shells to tesseract (optional binary, like Chromium: absent means status skipped, never pass) and returns GateResult(pass, missing_required, invented, ocr_text). Normalization before comparison: lowercase, strip punctuation except + - . /, drop tokens under 3 chars and tesseract words with conf below 30, then fuzzy-match required words at edit distance <= 1 for length >= 5 (this is the OCR-noise allowance). Any surviving token outside the allowlist (spec words plus a fixed 40-word stopword set) is invented and fails the gate; any missing headline word or stat number fails it. Bodies raise NotImplementedError in the sketch; signatures and dataclasses are the contract.

run.json records infographic: {status pass|fail|skipped|absent, attempts: [{prompt_sha, png_sha, passed, missing, invented}]} so retries accumulate instead of overwriting. comment.py embeds ![PR infographic](infographic.png) plus the line _AI-drawn illustration of PRC-computed words; the map below is computed from the code_ only when status is pass, else today's card block verbatim. doc.py does the same with an <img> tag. The skill file gains a short section pointing the agent at spec, prompt, imagegen, and the --infographic re-run.

New module prc/presentation/lensdoc.py owns the ChangeMap to GraphDoc conversion behind one public function build_lens_doc(change_map) -> LensDoc (typed dataclasses mirroring contract 0.2.0) plus validate_lens_doc(doc) -> list[str] implementing the structural limits in Python (lanes 1..16, nodes 1..256, edges <= 512, label <= 120, id regex, referential integrity) so invalid docs fail in pytest, not in a browser. Lanes come from top-level directories (max 15 plus other); symbols map class to module, function/method to function, anything under a test path to test; files carry path/startLine/endLine/revision head|base from span/base_span. Symbol node ids are s{i} (index into map.json symbols, preserving the data-node hook); file nodes f{i} exist only when the map has zero symbols (swarm-116 Go case) or for changed files with no parsed symbols alongside symbol nodes? No: file nodes only in the zero-symbol case, keeping one rule. Deltas map added|modified|removed directly and context to unchanged. Call edges become kind call; name-resolution edges get emphasis muted plus label name-only (the dotted-line meaning survives as data); added edges on the tour path get emphasis hero and animated true, capped at 3 heroes. Node cap policy: tour-referenced symbols first, then added/modified, then deleted, then context; overflow is recorded in run.json lens.capped_dropped and in the summary walkthrough body, never silently. Walkthrough steps derive 1:1 from tour Steps (overview to kind all, risky_file/entry/callee/test to node focus, summary to all), clamped to 2..12 by merging middle steps; headings from short qualnames (<= 48), bodies from the same headline/look-first strings the captions use today (<= 140).

Vendoring: scripts/vendor_pr_lens.py (dev-only, Node 26) unpacks the two pinned tarballs, esbuild-bundles renderer dist plus the schema exports render needs into one IIFE at src/prc/presentation/map_assets/prlens.bundle.js exposing window.PRLens = {render, safeParseGraphDoc}, aliasing node:crypto (used only by the manifest path, never by render) to a local stub that throws on use, and writes prlens.pin.json {renderer, schema, bundle_sha}. Only the bundle and pin are committed; zod ships inside the bundle so no Node exists at runtime. render_map.py inlines bundle + player as a single script (same CSP hash-of-inline-script construction as today, now covering bundle+player), keeps the map-data JSON block for drawer diff content, and adds a lens-doc JSON block; PR strings still reach the page only through JSON blocks and DOM is built with textContent plus renderer-escaped SVG.

Player: map.js is rewritten (same filename, new internals) as a thin adapter: on load it safeParseGraphDocs the lens-doc block, calls PRLens.render(doc, {lens architecture, theme}), injects the SVG, builds transparent hit rects from atlas.nodes[id] each carrying data-node s{i}, and reuses the existing camera/drawer/tour code with coordinates converted from atlas viewBox units. window.prcTour keeps its exact shape {duration, steps: [{kind, focus, via, start, duration, caption}], seek(t)}; drawer, Escape, play/zoom/fit ids and aria contracts are untouched, so map_video.py and the verify scripts need no changes. Deleted: map_layout.py (layout belongs to the renderer now), test_map_layout.py, test_map_grouping.py (folder lanes replace grouping; lane assignment is unit-tested in test_lensdoc.py). Rewritten: render_map.py, map.js, map.css (chrome only; node styling comes from the renderer theme), test_render_map.py, test_map_browser.py. Untouched: changemap.py, facts.py, card.py, comment.py structure, map_video.py.

Interface depth: the public surface grows by one CLI flag and two modules with 3 and 2 public functions. The converter hides lane packing, capping, id sanitation, and caption truncation; the gate hides OCR normalization and fuzzy policy. Callers coordinate nothing.

## Synthesis decision

## Tradeoffs accepted

- We accept tesseract as an optional binary (absent = skipped, outputs fall back) in exchange for zero new runtime deps; the wheel constraint wins over gate ubiquity.
- We accept a strict invented-word fail (regenerate from a new prompt file) in exchange for never letting model-invented claims through; prompt iteration is the documented recovery.
- We accept shipping the zod runtime inside the committed bundle in exchange for no Node at runtime and a single inline script under the existing CSP pattern.
- We accept deleting Python layout and folder grouping in exchange for one layout owner; dense mode becomes the 256-cap selection policy with a disclosed drop count.
- We accept keeping the full ChangeMap map-data block beside lens-doc in exchange for an untouched drawer and video path; the page grows by a duplicated-but-compressed JSON block.

## Alternatives considered

- Gate by CLIP/embedding similarity instead of OCR words: hides no complexity (needs a model + threshold tuning) and cannot prove absence of invented words, so it lost to token allowlisting.
- New prc infographic subcommand family (prompt, check, attach): more commands for the same capability; one flag on explain reuses staging, atomic publish, and run.json, so it lost on surface size.
- Pre-render SVG at build time with Node during explain: violates no-Node-at-runtime and breaks determinism across machines; client-side render of a pure function keeps bytes identical, so it lost.
- Keep Python layout and use the renderer only as a validator: two layout owners and split-ownership of geometry; deleting map_layout.py gives one owner, so it lost.

## Implementation reconciliation

## Open questions and risks

- Tesseract quality on stylized technical-schematic lettering may force prompt word budgets lower than 5x3 bullets; should the budget adapt after a failed attempt or stay fixed?
- The node:crypto stub throws only on manifest paths; is there a vendor-time test proving render and renderAll-without-manifest never touch it?
- Walkthrough bodies reuse caption strings; do we need the span() escaping discipline for PR-controlled strings inside lens-doc, or does JSON-block plus renderer escaping suffice?

## Next implementation step

Implement lensdoc.py build_lens_doc plus validate_lens_doc against the swarm-116 and librarysync-98 maps, then rewrite render_map.py around the vendored bundle.
