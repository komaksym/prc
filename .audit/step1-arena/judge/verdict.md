# Arena Phase C verdict — PRC step 1 design (infographic + PR Lens map)

Role: read-only cross-judge. No files edited, no code executed; all judgments from reading.
Read: arena SKILL.md (Phase C), architect design-red-flags.md, grounding.md.
Candidates read end to end: candidate-2/design.md + sketch/infographic.py, lensdoc.py, player.js, tests.md;
candidate-3/design.md + sketch/prc_infographic.py, prc_graphdoc.py, prlens_player_outline.js, tests.md,
vendor_prlens.mjs, plus candidate-3/scratch/vendor experiment files. Reference repo (read-only).
Candidate 1 dropped out (rate limit): no design.md exists, so it is not scored. Its scratch/ experiments
(full bundle about 526 KB, renderer-only about 53 KB) corroborate the measured facts both candidates cite.

## Scores (1-5, evidence in file + section)

C2 trust 4 / hooks 4 / runtime 3 / conversion 4 / depth 5 / verifiability 3 = 23.
C3 trust 2 / hooks 5 / runtime 5 / conversion 3 / depth 4 / verifiability 4 = 23.
Tie on sums; the base pick below is on judgment, not arithmetic (Phase D: pick the base a maintainer
can extend without breaking invariants).

## 1. Trust of the infographic

C2 (4): design.md Shape gate drops tokens under 3 chars and TSV conf below 30, fuzzy-matches len>=5
at edit distance at most 1, fails any surviving non-allowlisted token and any missing headline word or
stat number, fails closed (absent tesseract gives skipped + card fallback), never repaints
(regenerate-from-new-prompt-file). Every measured noise token is filtered (ittubonty/seesteen/teamtne/
borate/present/second conf 0-28 below 30; x/Se under 3 chars; quote-all-66-close survives the filters
and depends on the claimed 40-word stopword set — but sketch/infographic.py shows only 4 stopwords,
so that set is asserted, not evidenced). Hole: invented 1-2 char tokens (a wrong 2-digit number) are
dropped by MIN_TOKEN_LEN, not failed.

C3 (2): sketch/prc_infographic.py score_ocr is well-structured (pure core, ordered-window coverage,
exact short-word and number match, dual-psm better-wins, five verdicts incl. unreadable and tool,
check.json + run.json attempt records, fixed DISCLOSURE sentence) but has no confidence input — it
consumes plain text. The measured facts warn that invented-word detection without a confidence floor
fails the six visually-verified-correct images (ittubonty 8 letters, seesteen, borate sit below any
0.55-similarity floor with no exemption). So the gate is fail-closed yet would rarely publish on
icon-heavy images; thresholds are admitted quote-reasoned-anchors-not-yet-tuned-close (design.md Open
questions). Structure is the best of the two; calibration contradicts the measurements.

## 2. Hook and caller compatibility

C2 (4): design.md Shape keeps window.prcTour exact shape, data-node s-i hit rects from atlas, untouched
drawer/Escape/play/zoom ids and aria contracts, map_video.py and verify scripts unchanged,
single-inline-script CSP built as today. Ding: raw SVG injected into the DOM widens PR-controlled-string
surface beyond the JSON-block discipline (mitigated only by renderer XML-escaping, which grounding confirms
but the design does not re-verify), and it adds a second lens-doc JSON block beside map-data.

C3 (5): same hooks and ids preserved (sketch/prlens_player_outline.js), map_video.py untouched, drawer
built with textContent only; SVG goes into an img element as a data URL so PR-controlled label text lives
in image bytes and the DOM keeps only the data block — strictly tighter than today; two-hash CSP stays
hash-based, which no caller forbids (verify scripts assert hashes of map.json, not of scripts).

## 3. Runtime constraints

C2 (3): no Node at runtime and pinned vendoring hold, but it ships renderer+schema+zod (about 514 KB
measured) to every reader for per-page safeParse, about 10x candidate 3's measured 53.8 KB; up to 3
animated hero edges put SMIL animation into recorded video frames, working against deterministic output;
the node:crypto stub quote-throws-on-use-close with the never-touching-it proof left as its own question.

C3 (5): renderer-only 54 KB bundle verified by a real experiment this session
(scratch/vendor/prlens-renderer-only.js, rendertest.mjs reading atlas.nodes, shim-r/shim-s no-op shims
for the only node:crypto consumers); animated false on all edges keeps video seeking deterministic;
no generatedAt; tarball and bundle hashes pinned in prlens.lock.json with a vendor smoke test.

## 4. Conversion correctness

C2 (4): zero-symbol file nodes, tour-first cap policy with disclosed dropped count, muted + name-only
labels keep name-only edges distinguishable in the diagram, walkthrough clamped 2..12, and it is the only
candidate proving validity against the real schema per doc (in-page safeParseGraphDoc) plus a Python
mirror for pytest. Risk: risky_file steps map quote-to-node-focus-close while file nodes exist only in
the zero-symbol case, so a risky file with no parsed symbol (em-5756 has patch/lock/docs files) has no
named node — underspecified.

C3 (3): strongest selection design (tour-referenced file nodes up to 12 so every risky_file step names a
node; deterministic changed-then-context ordering; per-file aggregate nodes subtitling shown-symbol
counts; exactly one hero; fully inflated fields so no zod defaults needed). Dings: name-only edges keep
kind call with the fact drawer-only, losing the rubric quote-stay-distinguishable-close in the diagram;
contract proof is a Python mirror plus a fixture-only vendor smoke — no real-schema validation of
production docs anywhere.

## 5. Interface depth and reader load

C2 (5): one CLI flag, two modules (3+2 public functions), callers coordinate nothing, lane packing and
capping and sanitation hidden; deletes map_layout.py + 2 test files; player reuses existing
camera/drawer/tour code (smallest diff). No red-flag smells (single layout owner, one way to run loop).
C3 (4): equally small surface (3+2 functions, zero new subcommands) and deletes more (layout + dense
mode); slightly larger record surface (brief.json every run + check.json + published png + data.stepKinds
parallel array — derived from one source, so not a hand-synced list, but a second array for the reader);
about 600-line player rewrite versus candidate 2 quote-adapter-close.

## 6. Verifiability

C2 (3): sketch/tests.md names the defect per test and covers hooks/CSP/no-Node/absent-tesseract, but
scratch/ is empty — no experiment was run — sketches are signatures with NotImplementedError bodies, and
there are no screenshot, video-frame, determinism-bytes, or lock-hash tests.
C3 (4): 22 defect-named tests spanning brief determinism, gate noise tolerance, lock-hash match,
byte-identical renders, CSP/data-block, browser hooks, video seeks, and no-playwright CLI; vendor
experiments were actually executed with numbers in the record. Still no explicit screenshot assertions.

## Recommended base: candidate 3

Candidate 3 is the base because its load-bearing choices are measured (54 KB bundle experiment, atlas
shape, shim surface), its converter covers the hardest acceptance case explicitly (tour-referenced file
nodes for em-5756-style risky files, aggregates with truthful counts, deterministic inflation, SMIL-free
video), and its weakest point — gate calibration — is a small well-understood graft, whereas candidate
2 quote weak points (10x page weight on every reader, animated heroes versus deterministic video,
risky-file focus with no node) are architectural. A future maintainer extends candidate 3 by editing
selection templates and named threshold constants without touching page weight, hook shapes, or vendoring.

## Grafts from candidate 2 into the base (priority order)

1. Confidence + short-token floors in the gate (fixes criterion 1): parse tesseract TSV alongside text,
   drop conf-below-30 tokens and exempt under-3-char tokens from invented detection, keeping candidate 3
   quote ratio/window/substring machinery and verdict taxonomy. Source: candidate-2/design.md Shape
   normalization. This is the one graft that decides whether the feature ever publishes on real images.
2. Muted emphasis + name-only label for name-resolution edges (fixes diagram distinguishability): keep
   candidate 3 quote drawer fact, add candidate 2 quote in-diagram signal. Source: candidate-2/design.md.
3. Real-schema proof without page weight (fixes quote-not-only-by-a-Python-mirror-close): validate golden
   GraphDocs against the pinned zod schema with dev-only Node in pytest/vendor smoke (candidate 2 quote
   insight that the real schema must judge somewhere, under candidate 3 quote discipline that zod never
   ships). Rejected from candidate 2: in-page safeParseGraphDoc (470 KB reader cost), 3 animated heroes
   (video nondeterminism), directory-lane scheme (semantic lanes fit ChangeMap better).

## Defects both share (fix during graft, before verify)

- Neither test list asserts screenshots, though rubric and repo invariants require real-browser checks
  with screenshots; add them to the browser-hook tests.
- Both gates ignore short tokens for invented detection, so an invented 1-2 char token (a wrong 2-digit
  stat) slips past; decide explicitly whether digit-only extras must be allowlisted.
- Both thresholds are untuned on real acceptance images (each admits this in Open questions); tune the
  named constants against the six session images before landing.
- Both keep the full map block beside the lens doc on the page; measure that duplication cost in verify.
