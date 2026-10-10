# Step 1 design: gated AI infographic and PR Lens map

## Summary

Step 1 adds two outputs to every explanation. The first is one AI-drawn infographic per PR. PRC writes every word it may show, and an OCR gate decides whether it is published. The second is the interactive map rebuilt on the MIT PR Lens renderer. PRC converts its ChangeMap into a GraphDoc, and a vendored, pinned, renderer-only bundle draws it in the browser. PRC keeps its own player, drawer and hooks. The Kokoro voice gate landed earlier at 38174a4 and 972756e.

## Synthesis decision

Source: architect arena under /private/tmp/arena-step1, copied to .audit/step1-arena/. Candidate 2 (Einstein, muse-spark) and candidate 3 (Goodall, glm) wrote designs. Candidate 1 (parent model) dropped out on HTTP 429 and wrote no design; its scratch measurements agree with the bundle sizes below. The cross-judge Heisenberg (muse-spark) scored a 23 to 23 tie and picked candidate 3 as the base. Its weak points are small grafts, while candidate 2 has architectural weak points: a 514 KB zod bundle in every page, animated hero edges in video frames, and risky-file steps with no node to focus.

Grafts from candidate 2:

1. The gate reads tesseract TSV with confidence values. Tokens below confidence 30 count for coverage but never as invented words. Short tokens and a fixed stopword set are exempt from invented detection. This graft decides whether real images can pass at all.
2. Name-only call edges get emphasis muted and the label "name-only", so the diagram itself shows them.
3. The real pinned zod schema validates every golden GraphDoc at vendoring time. The lock records each validated golden's sha256, and pytest checks that the goldens equal the converter output and match the lock. Zod never ships in the page.

Rejected from candidate 2: in-page safeParseGraphDoc, three animated hero edges, and lanes by top-level directory. PRC's semantic lanes fit a ChangeMap better.

Shared defects fixed during synthesis:

- Neither test list asserted screenshots. Browser tests now save screenshots and assert on their pixels.
- Both gates ignored short tokens, so a wrong one- or two-digit number could pass. Every numeric token read at confidence 30 or more must be an allowed number.
- Thresholds were not tuned. Worker A tunes them on the five session infographics that have prompt files, then on the three acceptance PR images.
- Duplicated page JSON was not measured. Verification reports the map block and graph block sizes for the three acceptance maps.

## Part A. Infographic

### Flow

1. prc explain writes infographic/brief.json on every run. run.json records infographic status missing.
2. The agent runs baoyu-infographic on the brief. It uses the technical profile (structural-breakdown layout, technical-schematic style, 16:9, en, backend auto, which is native imagegen in Codex). It saves the prompt file before it generates. It keeps prompt files and candidates in a working folder outside the explain output, for example <out-root>/<slug>-infographic/. _publish_explain replaces the output folder on every run, so nothing the agent writes inside it survives.
3. The agent runs prc explain again with --infographic <png>. The flag repeats. PRC gates the candidates in argument order and publishes the first one that passes, as infographic.png with the exact candidate bytes.
4. On a failure the agent redraws from a new prompt file, at most two times. It never paints over text. After that the card stays as the fallback.

Only candidates named in the current run's flags are gated. PRC keeps no state between runs, so the same inputs give the same bytes.

### Module

New module src/prc/presentation/infographic.py. Public surface:

- infobrief(m, brief, board) -> InfographicBrief(title, lines). Each BriefLine has a role (headline, label, chip, row, verdict, note) and a text.
- parse_tsv(tsv) -> tuple[OcrWord, ...], where OcrWord has text and conf.
- score_ocr(reads, br) -> GateDecision. This function is pure. reads is one OcrRead(mode, words) per tesseract mode.
- gate(png, br) -> GateDecision. It runs tesseract twice, with --psm 3 and --psm 11, in TSV mode. It does no preprocessing, cropping or repainting.

GateDecision has verdict (pass, missing, invented, unreadable or tool), missing (pairs of line text and missing tokens), invented (tokens with their confidence) and detail (token counts per mode, tesseract version, gate constants).

### Brief

Every word comes from sources that already feed the card, comment and doc:

- headline: card.headline(m, board).
- label: fixed PRC section labels, reused from the card's constants.
- chip: the facts.compute_facts stat chips, with the card's wording.
- row: card.look_first(3) rows, then card.risky rows.
- verdict: the facts test verdict.
- note: the disclosure, exactly "Infographic drawn by AI. Words from prc."

The PR title is not part of the brief. Caps are 80 words and 96 characters per line. When the brief is too long, risky rows drop first and look-first rows second. Headline, chips, verdict and note never drop.

brief.json holds the lines, the sorted allowed words and numbers, the disclosure, the baoyu profile, fixed prompt rules and the gate constants. It is written with sorted keys and no clock. The prompt rules are:

- Show every line exactly once, spelled exactly.
- Add no other words, numbers, titles, legends or watermarks.
- Icons and decorations contain no letters or digits.
- Keep the disclosure line visible.

### Gate rules

Both sides use the same tokenization: NFKD, drop combining marks, casefold, split on every character outside a-z and 0-9, drop empty tokens. A tesseract word can give several tokens, and each inherits the word's confidence.

Coverage. Each brief line's tokens must match in order inside one mode's token sequence, with at most WINDOW = 6 unmatched tokens between two matches. Coverage uses all tokens, whatever their confidence. Two tokens match when they are equal, or when both have 4 or more characters and their Levenshtein ratio is at least WORD_SIM = 0.80. Tokens of 3 or fewer characters and tokens that contain a digit must be equal. A brief token also matches the join of two adjacent OCR tokens, for words split at a line break. A line is covered when either mode covers it.

Invented words. Check every token read at conf >= CONF_FLOOR = 30 in either mode:

- A token that contains a digit must equal an allowed token. This closes the wrong-number hole.
- An alphabetic token shorter than 3 characters is ignored.
- A token in STOPWORDS is ignored. STOPWORDS is small and fixed: a, an, and, are, as, at, be, by, for, from, in, is, it, of, on, or, the, to, with. It never contains negations or quantifiers, so all, every, no, none, not, never, only and without are always checked.
- Any other token passes when it equals an allowed word, or has 4 or more characters at ratio >= WORD_SIM to an allowed word, or joins with its neighbor in the same mode to match an allowed word.
- Every other token is invented.

Precedence. tool (tesseract absent or failed) comes first, then unreadable (no token at conf >= 30 in either mode), then invented, then missing, then pass.

Tuning. Run the gate on the five session infographics that have prompt files. Build each allowed word list from its prompt file's exact text. All five must pass. If they do not, report the failing tokens and change only the named constants. Never loosen negations, quantifiers or numbers. Commit the tesseract TSV outputs as small test fixtures. Do not commit the images.

### Records

- infographic/brief.json: always written.
- infographic/check.json: one record per candidate gated in this run. A record has the file name, sha256, byte size, verdict, missing tokens, invented tokens with confidence, tesseract version and gate constants.
- run.json gets infographic = {status passed|failed|missing, published_sha256 or null, attempts [{name, sha256, verdict}]}. status is missing when no candidate was given, failed when every candidate failed, and passed when one was published. Names are file names only, never absolute paths.

### Embedding

- comment.md: on a pass, the card image line becomes ![Infographic drawn by AI. Words from prc.](infographic.png). Otherwise the card line stays exactly as it is today.
- doc.html: on a pass, a figure at the top of the walkthrough holds an img with a data:image/png;base64 source (the CSP allows only data: images), alt text set to the disclosure, and the disclosure as figcaption.
- card.html and card.png stay in the bundle on every run.
- doctor reports tesseract with its version, or says the infographic gate is unavailable and the card is used.

### CLI and skill

- prc explain --infographic PATH is repeatable. The CLI checks that the file exists and starts with the PNG signature. run_explain gets infographics: Sequence[Path] = ().
- src/prc/skill/SKILL.md gets the agent loop from the Flow section above.

### Part A tests (each names the defect it catches)

1. test_infobrief_words_are_checked: brief lines come only from the named sources. Catches unchecked words entering the image vocabulary.
2. test_infobrief_deterministic: the same map and board give byte-equal brief.json. Catches hidden clocks or ordering.
3. test_gate_exact_text_passes: TSV with exactly the brief words passes. Catches a gate that can never publish.
4. test_gate_missing_word_fails: a missing headline word fails and the record names the word. Catches publishing before reading.
5. test_gate_invented_word_fails: a long word outside the brief at conf 90 fails. Catches invented claims.
6. test_gate_wrong_number_fails: "7 files" where the brief says "2 files" fails with 7 named. Catches the short-number hole.
7. test_gate_negation_fails: "not" at conf 90 outside the brief fails. Catches claim inversion through stopwords.
8. test_gate_measured_noise_passes: brief words plus the measured noise (ittubonty 4, seesteen 0, teamtne 0, borate 9, fae 0, present 24, second 28, x 68, Se 79) pass. Catches thresholds too tight for real icons.
9. test_gate_low_confidence_counts_for_coverage: a brief word read at conf 20 still covers its line. Catches the confidence floor leaking into coverage.
10. test_gate_split_word_passes: "check" plus "out" covers "checkout". Catches line-break splits failing real images.
11. test_gate_unreadable and test_gate_without_tesseract: a blank image gives unreadable, and a PATH without tesseract gives tool. Neither publishes. Catches crashes and dependence on an optional binary.
12. test_gate_session_images_pass: the committed TSVs of the five session images pass with their prompt-derived word lists. Catches untuned thresholds.
13. test_gate_real_tesseract_images: Chromium renders the brief as an HTML page, saves a PNG, and the real gate passes it. The same page with one invented word, then with one wrong number, then with one missing row fails with the right verdict. Catches a gate that works on fixtures but not on real pixels.
14. test_explain_publishes_first_passing_candidate: an E2E run through the CLI with --infographic bad.png --infographic good.png publishes infographic.png with the good file's bytes. run.json lists both attempts with verdicts. comment.md embeds infographic.png with the disclosure alt text. doc.html has the data URL and the caption. Catches pre-gate embedding, repainting and trusting the last candidate.
15. test_explain_without_infographic_keeps_card: no flag gives status missing, brief.json present, and comment.md with the card line unchanged. Catches regressions in the fallback.

## Part B. Map on PR Lens

### Converter

New module src/prc/presentation/graphdoc.py, beside the map code it replaces. Public surface:

- to_graph_doc(change_map) -> Plotted(doc, symbol_index, file_index, dropped_symbols, dropped_edges).
- validate_contract(doc) -> tuple[str, ...]. It restates the pinned contract in Python: counts, label lengths, id charset, enums and referential integrity. to_graph_doc raises when validation finds a violation, because a violation is a converter defect.

Ids. s{i} is the index into map.json symbols, f{i} the index into map.json files, and e{i} the index into map.json edges. Walkthrough step ids, when the contract needs them, are w{i}.

Lanes. Use PRC's semantic lanes from map_layout._lanes: test symbols go to tests, changed symbols to changed, context symbols that call a changed symbol to callers, and other context symbols to callees. All file nodes go to a files lane labeled Changed files. Emit only non-empty lanes, in the order files, callers, changed, callees, tests.

Node kinds. A symbol in the tests lane is test, a class is module, and a function or method is function. File nodes map through one table from FileNode.kind: test to test, config to config, lock and package files to package, everything else to module or other. Deltas map added to added, modified to modified, deleted to removed, and context to unchanged.

Labels. A symbol's label is its short qualname, cut at a whole word to 120 characters or fewer. A file node's label is its path, cut from the left so the file name stays. Badges stay within 6: a line-count badge when nonzero and a sensitive badge for sensitive files. File refs carry path, startLine, endLine and revision head or base. Deleted symbols use base.

Node selection, deterministic, cap 256:

1. File nodes for files that risky_file tour steps reference, 12 at most, so every risky_file step can focus a node.
2. When the PR parsed no symbols, one file node per changed file, so the Go case is never an empty diagram.
3. Changed symbols, sorted by (-(added + removed), map index).
4. Context symbols, by map index.
5. One aggregate file node per file whose symbols all dropped, with the subtitle "N of M symbols shown".

Edges. Only edges between plotted nodes. When there are more than 512, keep them in this priority order: tour-walk edges, added, removed, kept exact, kept name-only. Every edge has kind call. Deltas map added to added, removed to removed, and kept to unchanged. Removed edges get emphasis muted. Name-only edges get emphasis muted and the label "name-only". At most one edge is hero: the first added edge with exact resolution on the tour walk. When no such edge exists, no edge is hero. Every edge has animated false, which keeps video frames deterministic.

Walkthrough. Steps are [overview], risky_file[:2], the entry and callee walk[:8], one optional test step, then [summary]. Clip to 12 steps and keep at least 2. Headings stay within 48 characters and bodies within 140. They use fixed templates per kind, filled with facts computed in Python. Overview and summary focus {kind: all}. Other steps focus {kind: selection, nodes: [...]} with only plotted ids, and fall back to {kind: all} when none are plotted. The page data carries a parallel steps array [{kind, via}], with via taken from Step.via. The player keeps the tour's kind-paced timing and its exact via without deriving it.

Inflation. Fill every field the renderer reads: edges, views and flows arrays, badges, emphasis and animated. The page never depends on zod defaults. There is no generatedAt field.

### Vendoring and lock

New script scripts/vendor-prlens.mjs, for maintainers only. Node runs here and never inside prc.

- The pins live in src/prc/presentation/map_assets/prlens.lock.json: renderer 0.3.2, schema 0.7.0, the zod and esbuild versions, tarball sha256 values, bundle_sha256 and validated_goldens {file: sha256}.
- The script fetches tarballs with npm pack, using an npm cache inside a scratch folder. It also accepts --tarballs <dir> and --node-modules <dir> for offline runs; /private/tmp/prlens has both. It checks tarball hashes against the lock, or writes them with --update.
- It replaces both packages' dist/manifest.js with no-op shims. These are the only node:crypto users.
- It bundles import { render } from "@coldtea/pr-lens-renderer" with esbuild as a minified IIFE with global prcLens. The bundle is renderer only. The script asserts that zod is absent and the size is under 100 KB; about 54 KB was measured. The MIT notice goes into the bundle header, because every map.html inlines the code.
- It smoke-tests render() on a fixture GraphDoc.
- It validates every tests/data/graphdoc/*.json golden with safeParseGraphDoc from the pinned schema, then writes validated_goldens and bundle_sha256 into the lock.

### Page and player

- render_map(change_map) keeps its signature. The shell keeps #title, #meta, #stats, #play, #viewport, #world, the caption, progress, summary, legend, the zoom buttons, #drawer and the footer brand line "computed from the code, no AI drew this". Update the legend to the new edge styles, including name-only.
- One JSON block, <script type="application/json" id="map-data">, holds {map, graph, steps, dropped}. Grep every consumer of map-data and map.json (tests, .agents/skills/verify/scripts/map.py, scripts/verify-release.sh, map_video.py, evaluation code) and update each one in the same change.
- Inline script 1 is the bundle and inline script 2 is the player. The CSP lists both sha256 hashes.
- The player calls prcLens.render(doc, {lens: "architecture", theme}) inside try/catch. The theme matches the current page palette. A render error shows a fixed fallback box and never becomes an uncaught page error.
- The SVG is shown as an img with a data URL, so PR-controlled label text stays in image bytes and out of the DOM.
- Transparent hit-target buttons sit on the atlas.nodes boxes. Each carries data-node="s{i}" or "f{i}", and its aria-label is set with setAttribute.
- Reuse today's camera math: fit, flyTo, zoomAt, drag, wheel, Space to step the tour and F to fit. Tour focus shows as a ring overlay on the focus box and a lighter ring on the via box, plus the existing spotlight. The SVG image itself is never restyled.
- window.prcTour = {duration, steps: [{kind, focus, via, start, duration, caption}], seek(t)} keeps today's shape and kind pacing. The caption's main line is the step heading and its sub line holds the symbol facts.
- The drawer is built from the map block with textContent only. It shows qualname, path, status, line counts, call sites, the hunk diff view, and callers and callees with the name-only fact. Escape closes it.
- A map with no nodes keeps the existing "no change in a parsed file" card.
- map.css keeps page chrome only. Delete node, edge, folder and dense styles.
- map_video.py must keep working. Change it only if a hidden id or class moved.

### Deletions

Delete presentation/map_layout.py, dense mode in CSS and JS, tests/test_map_layout.py and tests/test_map_grouping.py. Move _lanes logic into graphdoc.py.

### Correction after synthesis: keep D18 grouping

The arena designs dropped decision D18 by accident. D18 says a map with more than 40 changed symbols opens grouped by file or folder, with counts, because a measured 311-symbol PR drew about 300 unreadable cards. A 256-node GraphDoc would bring that failure back. So:

- Overview mode applies above GROUPED_AT = 40 changed symbols. It plots one group node per folder, or per file when a folder holds fewer than 3 changed files, using the folders_of rule sorted by label. Group ids are g{i}. The subtitle gives the counts, and a badge marks test members.
- Overview mode also plots the symbols the tour walks and the file nodes risky_file steps need. Context symbols are not plotted. Edges run only between plotted nodes.
- A group hit target carries data-node="g{i}". Clicking it opens the drawer with the member list. Clicking a member shows its diff.
- Added test: test_graphdoc_large_pr_groups, a grouped golden, and a browser case for the group and member clicks with screenshots.

### Part B tests (each names the defect it catches)

1. test_prlens_lock_matches_bundle_and_goldens: the bundle sha equals the lock, and every golden's sha equals lock.validated_goldens with no extra or missing names. Catches a stale bundle, and a golden that changed without passing the real schema.
2. test_graphdoc_matches_goldens: to_graph_doc output is byte-equal to the committed goldens for fixture shop, librarysync-98, em-5756, swarm-116 and a synthetic large map. Inputs are copied into tests/data/graphdoc/inputs/. Catches converter drift and nondeterminism.
3. test_graphdoc_ids_and_integrity: every id is s{i}, f{i}, e{i} or w{i} and aligns with map.json. Every edge endpoint and walkthrough focus exists, and every lane is used. Catches breakage that would crash the renderer.
4. test_graphdoc_limits: a synthetic map with 300 symbols and 2000 edges gives at most 256 nodes, 512 edges and 12 steps, labels within their caps, aggregate subtitles "N of M symbols shown", and truthful dropped counts. Catches silent contract overflow.
5. test_graphdoc_no_symbols_uses_file_nodes: swarm-116 gives 7 file nodes and at least 2 steps. Catches the empty diagram.
6. test_graphdoc_risky_steps_focus_file_nodes: each em-5756 risky_file step focuses an f{i} node. Catches risky files with nothing to point at.
7. test_graphdoc_delta_and_emphasis: the delta mapping holds. At most one hero exists, and it is an added exact tour edge. Removed edges are muted. Name-only edges are muted and labeled "name-only". animated is false everywhere. Catches status language drift and video nondeterminism.
8. test_render_map_csp_and_data_block: the two CSP hashes match the two inline scripts. The JSON block parses into {map, graph, steps, dropped}. No qualname appears outside the block. Catches CSP and injection regressions.
9. test_render_map_deterministic_bytes: two renders of one fixture are byte-identical. Catches page churn.
10. test_map_browser_hooks (real Chromium): for shop and swarm-116 the diagram renders. A saved screenshot shows the diagram, measured by pixel variance in the diagram region, with no fallback box. Hit targets align with atlas boxes. Clicking the checkout data-node opens #drawer with apply_discount, and a screenshot is saved. Escape closes it. #play and the zoom buttons work. prcTour has steps, seek(0) works, and each shop step gets a screenshot. There are no console errors or page errors. Catches player regressions on the only surface where the bundle runs.
11. test_map_browser_render_error_falls_back: when render throws, the fallback box shows, the drawer still opens from the file list, and no uncaught error occurs. Catches a renderer error that blanks the page.
12. test_map_video_seeks_record: recording over prcTour.seek gives distinct frames. Catches a broken camera path.
13. test_map_cli_no_playwright_required: prc map renders without playwright. Catches an accidental import.

## Ownership

- Worker A owns src/prc/presentation/infographic.py, pipeline.py, cli.py, presentation/comment.py, explainer/doc.py, explainer/doctor.py, skill/SKILL.md, the new Part A tests and fixtures, and the existing tests its change breaks.
- Worker B owns presentation/graphdoc.py, render_map.py, map_assets/*, scripts/vendor-prlens.mjs, the deletions, the new Part B tests and goldens, rewrites of test_render_map.py, test_map_browser.py, test_map_video.py and test_e2e_map.py, and map_video.py, the verify skill map script and the verify-release.sh map smoke only if they read the moved data.
- The parent owns PLANS.md, docs, README, PROVENANCE, .audit, integration and the acceptance rebuild.
- Neither worker edits tests/conftest.py or pyproject.toml. The wheel already ships everything under src/prc.

## Implementation reconciliation

Measured on the integrated tree unless marked otherwise.

### Gate (Part A)

The tuning rule asked for all five session images to pass by changing named constants only. Measurement showed that constants alone cannot do it, and that two faithful images stay out of reach of tesseract 5.5.2. The final gate differs from the rules above in seven ways:

1. CONF_FLOOR is 70, not 30. On the session images, icon strokes read as words at 66 or less (a bar chart read as "all" and "2"). Drawn text read at 75 or more. Planted invented words, numbers and negations at confidence 90 still fail on all five images (test_gate_session_images_with_a_clear_extra_word_fail). Limit: a wrong number drawn in a hard spot can read below 70 in every reading and pass. One acceptance candidate read its CI chip at 26 in one reading and at 80 in another.
2. An OCR token that equals two adjacent brief tokens of one line is allowed ("PR A" drawn as "PRA"). Coverage also accepts that merge, by exact equality only. A first version accepted fuzzy merges. It let "AI Words" be covered by "Words" alone, and the acceptance run found it. The fix has its own test.
3. The gate reads each image four ways, psm 3 and psm 11 at the default resolution and at 150 DPI. The default reading lost 8 lines of icon boxes on the review-bias image, and the 150 DPI reading recovered 7 of them. Upscaling, downscaling and other thresholding methods recovered less or added confident misreads. Gate wall time is 1.6 to 2.1 seconds per image (five session images and five acceptance candidates).
4. A capital I and a lowercase l count as the same letter. Tesseract read every "CI" chip as "Cl" and every "AI" as "Al", at confidence 91 to 96.
5. Code tokens must match exactly, with no fuzzy tolerance. A code token comes from a word with an inner dot, slash, underscore or colon, or with camelCase. The first em-5756 candidate drew "onCComplete" for "onComplete", and the fuzzy rule passed it. Prose keeps the OCR tolerance.
6. A fifth prompt rule asks for plain dark text on a light background. The next-steps image lost its small white caption on a red bar.
7. Two session images still fail, and the tests pin that. next-steps-roadmap is missing the badge digits 1 and 2 and the small caption "Everything frozen". The first two break the icon rule that the old prompt did not have. review-bias reads "all" from its bar chart icon at 150 DPI. A false reject costs a redraw. The skill allows two redraws, then the card stays.

The session TSV live check was removed. It asserted only that the file parsed. The TSVs equal live tesseract 5.5.2 output (checked with diff for review-bias), and test_e2e_infographic.py runs real tesseract on rendered images.

Acceptance run: the gate rejected the first librarysync-98 drawing ("Words from pnc") and the first em-5756 drawing ("onCComplete"), and passed the redraws. swarm-116 passed on the first drawing. I read all five drawings by eye, and each verdict matches what I saw.

### Map (Part B)

- Group metadata lives in map.groups, so the data block keeps exactly four keys: map, graph, steps, dropped.
- Above the 256 node cap, tour and risky-file targets keep priority, and groups use the remaining budget.
- The pixel probe now reconstructs PNG rows correctly. The old threshold of 1500 rested on wrong pixel values. Real diagrams pass at 100 and a blank one stays below it.
- map.html sizes: 127,301 to 172,383 bytes, including the 54,919-byte MIT bundle and the 32,419-byte player. Renderer time in Chromium: median 3.85 ms (grouped) and 7.40 ms (librarysync-98) over ten runs.
