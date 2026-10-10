# Candidate 3: infographic step and PR Lens map

## Problem

PRC step 1 adds two artifacts to every explanation. Part A is one AI-drawn infographic per PR: the agent's image model (Codex imagegen, driven by baoyu-infographic) draws it, PRC authorizes every word that may appear, an OCR gate decides whether it may be published, and comment.md, doc.html and the acceptance review page embed it only after a pass. Part B is the interactive map rebuilt on the MIT PR Lens renderer (renderer 0.3.2, schema 0.7.0, graph contract 0.2.0): PRC's computed ChangeMap becomes a GraphDoc, the renderer draws it in the browser, and PRC keeps its own player. Constraints that shape everything: no Node.js at runtime (a vendored, pinned browser bundle only), the map page CSP with hash-pinned inline scripts and one JSON data block, prc map without playwright, deterministic outputs (same inputs, same bytes), and the product rule that the map says computed-from-the-code while the infographic must say AI-drawn. Hooks that must survive: window.prcTour = {duration, steps: [{kind, focus, via, start, duration, caption}], seek(t)}; symbol elements with data-node="s{i}" where i is the index into map.json symbols; a drawer that opens for fixture checkout, shows apply_discount, closes on Escape with aria-hidden true; #play / #zoom-in / #zoom-out / #zoom-fit; no page errors; and the callers of those hooks (scripts/verify-release.sh, .agents/skills/verify/scripts/map.py, the map tests).

## Usage (caller's view)

The agent that runs the prc-explain skill is the consumer of part A. One loop:

    prc explain --source fixture:shop --store ... --board board.json
    # publishes out/<slug>/infographic/brief.json; run.json records
    # "infographic": {"status": "missing", "attempts": []}
    # The agent runs baoyu-infographic on the brief: analysis, structured
    # content, the prompt file infographic/prompts/01-infographic-<slug>.md
    # saved BEFORE generation, then the imagegen call; the candidate is saved
    # at infographic/candidate-01.png. Then the agent re-runs:

    prc explain ... --board board.json --infographic <run>/infographic/candidate-01.png
    # gates the image, publishes it only on pass, records the attempt.

Two internal call sites: pipeline.run_explain computes br = infobrief(m, brief, board), writes brief.json into every run and stages gate(candidate, br) for each --infographic path; the comment builder becomes render_pr_comment(..., infographic="infographic.png" if published else None) and keeps the existing card image line when None. CLI surface: one flag, zero new subcommands.

Reviewer-facing usage of part B does not change: prc map opens map.html; prc map --video records the tour and the card frame. Maintainer-only, node tools/vendor-prlens.mjs rebuilds and re-pins the committed bundle src/prc/presentation/map_assets/prlens.bundle.js when PR Lens versions bump.

## Shape

Data structures first. Part A is one module, src/prc/presentation/infographic.py, with exactly three public functions: infobrief(m, brief, board) -> InfographicBrief; score_ocr(text, br) -> GateDecision (pure, the testable core); gate(png, br) -> GateDecision (tesseract subprocess outside the pure core). InfographicBrief carries a title and an ordered tuple of BriefLine(role, text); role is headline | chip | row | verdict | note. Sources are exclusively card.headline, the facts.compute_facts chips, card.look_first(3, board), card.risky, a facts-computed test-verdict chip, and the fixed disclosure line with the exact text "Infographic drawn by AI. Words from prc.". Caps: 80 words total, 96 chars per line. brief.json stores the lines, the baoyu technical profile (structural-breakdown layout + technical-schematic style, 16:9, en, backend auto), and the path conventions; it is written on every run, deterministic, and exists before any image does.

The gate. tesseract 5 runs twice, --psm 11 and --psm 6; the better decision wins; the tesseract version is recorded. No image preprocessing, no repaint, no crop. The scorer is pure word-level matching: coverage requires each brief line's words to match in order inside a window of at most 6 interleaved OCR tokens; words of 4+ chars match at Levenshtein ratio >= 0.80; 1..3-char words and whole numbers must match exactly. Invented detection fails the image when any token of at least 5 alphabetic chars has best similarity below 0.55 against every allowed word and is also no substring or superstring of an allowed word. One-glyph noise and split words therefore pass; a novel token and missing required words fail, with the words named. Verdicts are pass | missing | invented | unreadable | tool (tesseract absent). infographic/check.json appends one record per candidate (sha256, byte size, verdict, missing words, invented words, tesseract version). run.json carries infographic: {status: passed|failed|missing, attempts: [...], published_sha256}. On pass the exact candidate bytes are published as out/<slug>/infographic.png (never repainted); on fail or missing, outputs fall back to the existing card. comment.md then swaps its card image line for the infographic with the disclosure alt text, doc.html gains an img plus the same caption line at the top of the walkthrough, and card.html/card.png remain in the bundle as fallback. Embedding is one optional parameter on the comment builder and on render_doc.

Part B is one conversion module plus a thinned front end. src/prc/graphdoc.py owns ChangeMap -> GraphDoc with to_graph_doc(change_map) -> Plotted (doc, symbol/file index maps, dropped counts) and restates the pinned contract as validate_contract (counts, label caps, id charset, enums, referential integrity). Node ids are s{i} and f{i} aligned to map.json indices, which is what keeps data-node="s{i}" true; edge ids e{i}; delta mapping added|modified|deleted|context -> added|modified|removed|unchanged. Selection is deterministic with the 256-node cap encoded: first file nodes for tour-referenced files (at most 12) so every risky_file step names a node; when the PR parsed no symbols, one file node per changed file (the Go acceptance case cannot be an empty diagram); changed symbols sorted by (-(added+removed), callers, id) until the cap; then context symbols until the cap; then one aggregate file node per file whose symbols all dropped, with subtitle "N of M symbols shown". Edges run between plotted nodes only, in priority order tour-walk, added, removed, kept, then capped at 512; exactly one hero edge (the first added edge reached on the tour walk); removed edges render muted; name-resolution edges keep kind call and the resolution fact shows in the drawer data. Walkthrough: [overview] + risky[:2] + walk[:8] + optional test + summary, clipped to 12 and always at least 2; headings and bodies are python-computed templates within the 48/140 caps; data.stepKinds is a parallel array in the JSON block so the player keeps kind-paced timing and kickers without a second tour data model.

The page. map_assets/prlens.bundle.js (about 54 KB, renderer only, zod excluded; verified by experiment this session) is committed and inlined as the first inline script; the CSP gains a second script hash (bundle hash, player hash). The rewritten player (map.js, target ~600 lines vs 1132 today) does: render in-browser inside try/catch, with PrLensRenderError shown as a fixed fallback card and never an uncaught page error; the SVG goes into an img element as a data url, so PR-controlled label text lives in image bytes and the DOM keeps only the data block; a hit-target overlay of transparent buttons is positioned from the returned atlas boxes (atlas.nodes[id] = {x, y, width, height} in viewBox units, verified session); the camera reuses today's fit/flyTo/zoomAt math against the img scale; window.prcTour is built from the walkthrough (kind pacing, captions whose main line is the step heading and whose sub line is the JS-computed symbol facts); the drawer reads the map block and builds with textContent only, including the name-resolution fact. map_video.py keeps working without edits because the page keeps the ids and classes it hides. Deleted: presentation/map_layout.py (732 lines of python lane layout) and the dense folders mode; render_map.py keeps shell, data_block and CSP work and drops layout_json; map.css shrinks to page chrome. Vendoring: tools/vendor-prlens.mjs pins tarball hashes in prlens.lock.json, extracts, replaces both packages' dist/manifest.js with generated no-op shims (the only node:crypto consumers; verified this session), bundles the named entry (import { render } from "@coldtea/pr-lens-renderer") to an IIFE with global prcLens, smokes render on a committed fixture GraphDoc, and writes the bundle sha into the lock.

Two measured facts the design encodes: the renderer applies zod defaults only through schema parsing, so to_graph_doc inflates every field (edges/views/flows arrays, badges, animated false, emphasis) instead of relying on schema defaults, which is also what keeps zod out of the page; and the renderer can still throw (NOTHING_TO_RENDER), so the page catches and falls back. animated false on all edges keeps SMIL out of the frames, which keeps video seeking deterministic.

## Synthesis decision

(empty)

## Tradeoffs accepted

- A 54 KB committed JS asset and a two-hash inline script, in exchange for no Node at runtime and no zod in the page.
- Contract violations surface at convert time through python mirrored checks, with a browser fallback only as the last net, in exchange for a 470 KB bundle not shipping to every reader.
- A 257+ symbol PR shows at most 256 symbol nodes plus per-file aggregate nodes; counts stay truthful in header chips and aggregate subtitles.
- Fuzzy OCR thresholds could forgive one bad glyph, in exchange for real images passing; the 0.55 invented-word floor, full coverage and the 80-word brief keep passing tight.
- Gating a new candidate re-runs explain (full deterministic re-render), in exchange for keeping the atomic publish invariant.
- Map labels are not selectable text (the SVG is an image), in exchange for keeping PR strings out of the DOM except the JSON block.

## Alternatives considered

- Ship zod plus safeParseGraphDoc in the page (514 KB measured) as the single contract authority. Lost: the page re-validates what conversion and tests already prove, and readers download nearly 10x bytes for the same guarantee.
- Produce the SVG on the python side (port the renderer, or call it via a build step with Node) and inject it. Lost: Node at runtime breaks a hard constraint; DOM SVG would put PR-controlled text inside the DOM, which the present CSP discipline forbids.
- Keep the python layout and let PR Lens draw only PRC's geometry (or embed PRC boxes as a PR Lens doc). Lost: dense folders survive to age in place; the contract buys nothing and the 732-line layout remains the maintenance surface.
- A prc infographic subcommand family (brief/check verbs). Lost: two new public verbs for one loop; publishing still must happen inside explain for atomicity, and check outside the loop adds no record the loop does not need.

## Implementation reconciliation

(empty)

## Open questions and risks

- OCR thresholds 0.80 / 0.55 and the 5-letter floor are reasoned anchors, not yet tuned on real acceptance images; tuning before landing keeps them as named constants. Acceptable?
- For the largest real PRs, is the per-file aggregate plus header counts enough honesty for dropped symbols, or should the page also print a visible "N symbols not drawn" notice?
- Name-only call edges lose their dotted visual under the renderer's fixed edge kinds; the drawer keeps the fact. Acceptable for v1?
- baoyu lets the agent choose the image backend; the brief pins backend auto. Where imagegen is unavailable the image stays missing and the card holds. Confirm this is desired behavior rather than a doctor warning.
- The vendored bundle is committed; pytest runs without Node, so staleness is caught by the lock-hash test only. Does verify-release.sh gain a hash check, or does this stay maintainer-side?

## Next implementation step

Build src/prc/graphdoc.py with to_graph_doc plus its unit tests (ids and integrity, limits, no-symbols file nodes, delta mapping, determinism), because the page, the player and every browser test hang off the GraphDoc shape.
