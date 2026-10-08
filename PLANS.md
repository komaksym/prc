# Repository reconciliation, 2026-10-08

## Summary

Recover all PRC work into one verified local baseline. Preserve experiments and unique branch evidence. Determine GitHub identity from facts. Publish an honest product and verification status.

- [x] Q1. Snapshot refs and pending work; classify branches, worktrees, and release changes.
- [x] Q2. Reconcile retained changes and archive unrelated experiments without deletion.
- [x] Q3. Verify the product and verification skill; resolve independent findings.
- [x] Q4. Commit the baseline and align local main. Sync only to a verified intended remote.
- [x] Q5. Record the tracker resolution, completeness, evidence, and exact remaining gates.

Throughput checkpoint. Parent owns backups, reconciliation, Git mutations, and artifact execution. Separate read-only agents own branch evidence, release/evaluation completeness, source review, and remote discovery. Each writes only its report. Existing worktrees remain intact.

The shared map is `.scratch/reconciliation/map.md`. Remote discovery does not block local consolidation.

# Project verification skill, 2026-10-08

## Summary

Create a Codex project skill at `.agents/skills/verify`. Drive PRC through the real CLI and generated browser pages. Reuse the existing fixture and Playwright dependency. Preserve all earlier release work.

- [x] V1. Inspect commands, fixtures, browser controls, isolation, and repository sync rules.
- [x] V2. Create the skill, five feature recipes, and an executable map driver.
- [x] V3. Execute launch, doctor, map interaction, screenshots, and cleanup. Validate the generated files and run the isolated verifier.
- [x] V4. Commit only these task files. Skip remote sync if no remote exists.

Throughput checkpoint. Parent owns the skill and driver. One independent reviewer checks the new files while the parent runs the driver. Each run owns a unique scratch store and evidence directory. This task does not resolve the unfinished release evaluation.

# Release completion, 2026-10-07

## Final review comparison, 2026-10-08

### Summary

Finish the automatic evidence and independent source review. Prepare three captured PRs for the user's final review. Compare the plain diff, PRC, and genuine available third-party review material. Record exact revisions, tool availability, time, answers, and familiarity. Repeated exposure is a learning effect; the comparison measures usefulness and incremental findings, not an unbiased speed ranking.

- [x] J1. Recover durable readers and measurements; replace the missing reviewer.
- [ ] J2. Finish fresh single-packet readers, grading, and current grounding audits.
- [ ] J3. Fix confirmed defects and run final package checks.
- [x] J4. Prepare PR12, PR16, and PR19 with fixed-revision plain diffs, PRC outputs, and authentic available comparison material.
- [ ] J5. Verify the comparison artifacts and give the user the final human review.

Confirmed blank-scene defect. Eight boards omit statistics and outro reveal cues. The engine correctly keeps uncued elements invisible, but the checker accepted them. Add rejection tests before changing validation. Preserve this scored run. Render corrected boards into a separate run and repeat affected C3/C4 reads.

Throughput checkpoint. Parent owns integration, comparison artifacts, and measurements. Fresh readers own one packet and write durable files under the run's reader-work directory. One independent reviewer owns a separate report. Do not reuse the unavailable Hooke verdict. Human responses remain blank until the user supplies them.

## Continuation, 2026-10-08

### Summary

Finish the interrupted offline rebuild and release verification. Obtain independent reviews of grading and presentation changes. Preserve frozen v1 question selection and reject incomplete reader sets. Keep product acceptance open until fresh readers and human checks meet the existing targets.

- [x] C1. Recover the current source and partial output run; dispatch separate grading and presentation reviewers.
- [x] C2. Finish twelve offline outputs and inspect screenshots through the background browser.
- [x] C3. Resolve confirmed review defects with regressions and rerun relevant checks.
- [x] C4. Run the isolated verifier and inspect installed-wheel evidence.
- [ ] C5. Record fresh evaluation coverage, limitations, and operator gates.

Throughput checkpoint. Reviewers read disjoint source areas and write separate temporary reports. The parent owns rendering, integration, and installed-package verification. Reader packets remain isolated from source files and answer keys. Exploratory batches are archived. Acceptance uses one fresh agent per packet, with dispatch IDs and payload hashes recorded.

## Full release audit, evening continuation

### Summary

Recheck the existing release candidate through its installed CLI. Audit acceptance and package correctness independently. Fix confirmed defects before publication. Keep frozen questions and targets unchanged. Human acceptance and D21 publishing decisions remain required.

### Milestones

- [x] F1. Read project authority and capture the current working-tree baseline.
- [x] F2. Run the isolated release verifier and audit acceptance evidence in parallel.
- [ ] F3. Add regressions for confirmed defects, then fix and check each unit.
- [ ] F4. Inspect installed-wheel screenshots and media, and obtain independent review.
- [ ] F5. Record a precise release status and the remaining operator gates.

Throughput checkpoint. The parent owns installed-package verification and integration. Two independent readers assess acceptance and distribution. Readers do not edit shared files. Further work follows their concrete findings. Audit evidence goes to `.audit/release-full-out.tsv`.

The supplied handoff adds unfinished packet generation to the scope. Its earlier design chose self-contained reader inputs. The worker implements that design in `/private/tmp/prc-packet-work-20261007`, then the parent reviews and integrates it. New payloads exclude answer keys, raw HTML, maps, and videos. Frozen evaluation files remain unchanged.

The current verifier passed 495 tests, then failed while copying E2E files over read-only objects from an earlier attempt. A regression reproduces overwritten run logs. Each invocation now gets a fresh proof directory. `latest-success.txt` is written only after installed-wheel verification succeeds.

The deterministic grade replay records 275 disagreements across 410 non-free-text answers. This does not establish 275 wrong human-style grades. Prose answers and mechanical grading follow different rules. New readers must use canonical answer shapes. Two location grades contradict the script even without normalization. The frozen verdicts remain historical evidence, not a clean release measurement.

## Summary

Prepare a reproducible release candidate for `prc explain`. Preserve existing product fixes and unrelated local experiments. Public publishing remains gated by D21 and the human evaluation in `docs/mvp/EVAL.md`.

## Release predicate

The release source archive contains only the package, build metadata, and public usage documentation. The wheel installs into a clean environment and produces the offline map, card, comment, video, and walkthrough through the real CLI. The isolated release checkout passes lint, format, strict typecheck, tests, and build. Browser screenshots prove the map and walkthrough render. The evaluation scoreboard reports actual results and all unmet targets. Public release additionally requires every frozen EVAL.md target and the human acceptance gates to pass. An independent reviewer checks the final changes and decision trail.

## Milestones

- [x] R1. Audit current implementation, baseline checks, frozen evaluation evidence, and distribution contents.
- [x] R2. Add a failing source-distribution check before changing build configuration. Restrict archive contents and verify wheel assets.
- [x] R3. Complete the evaluation scoreboard and human review packet without changing frozen targets or questions.
- [x] R4. Update explain-first usage and prepare launch drafts with accurate release limitations.
- [x] R5. Run the full verification command in an isolated checkout of the release files. Install the wheel, drive the CLI, inspect video frames, and save browser screenshots.
- [ ] R6. Obtain independent review, resolve confirmed defects, and record remaining operator decisions.

## Baseline and throughput checkpoint

Measured at HEAD `e2477d2` with existing dirty product fixes. The root verification command fails on untracked `jobqueue/`, `tests/test_jobqueue.py`, `analyzer.py`, and `cli.py`. These files are outside the prc package. The built source archive includes those experiments and `.claude/worktrees/`. Keep unrelated files unchanged. Verify the release in an isolated tracked-file copy and check the archive boundary explicitly.

Parent owns packaging tests, build configuration, and runtime checks. Parallel read-only agents own evaluation evidence and CLI architecture. After those findings, delegate documentation or evidence completion only across disjoint file sets. Historical records show repeated product fixes but do not prove three consecutive scored fix rounds. Preserve targets. Reconcile grades before any further tuning. Rigor is high because archive publication exposes files and the product makes code-grounding claims.

## Current findings and next units

The final saved grades contain 480 verdicts. C1 is 20/96, C2 is 24/96, C3 is 45/96, C4 is 67/96, and C5 is 17/96. There are 44 wrong answers. All four absolute targets fail. Only C4 meets the required improvement over the frozen C0 baseline. The existing scoreboard hides these results because it reads a missing aggregate field.

The new stored-map E2E fails without a local git cache. A missing cache becomes the current directory, which the highlighter then treats as a git repository. Preserve the missing cache path to select the existing hunk fallback. Send fallback warnings to stderr so CLI JSON remains valid. Classify stored input directly from the provided map path.

Complete the scoreboard regression and renderer regressions first. Then prepare explain-first documentation and a complete blind human review sheet. Produce audible human samples separately from the frozen silent evaluation outputs. Run the full checks after integrating these units and inspect the installed wheel in a background browser. Independent review remains mandatory.

## Continuation, 2026-10-07

The next run finishes R5 and R6 and investigates every remaining automatic acceptance gap.
Use the current working files as the baseline. Preserve unrelated experiments.
Parent runs the isolated package verifier. Independent readers audit acceptance and distribution.
Save new evidence separately from the frozen scored run. Test confirmed defects before fixing them.
The release predicate stays unchanged. Human responses cannot be supplied by an agent.

## Operator gates

The user must choose the license and public repository name. D21 requires explicit approval before pushing, PyPI publication, or promotional posts. The human session and grader agreement remain measured requirements. Do not claim release readiness while those gates or automatic targets fail.

---

> **Current work (2026-10-06):** the end-to-end MVP. Start at `START-HERE.md`; the plan is `docs/mvp/PLAN.md`. The phases below are history.

# PLANS — hardened GitHub PR comprehension MVP

Run date: 2026-10-04. Authority: `CONTEXT.md`, `docs/design/architecture-checkpoint.md`, `docs/adr/0001-*`, `docs/design/evaluation-protocol.md` (copied with provenance in `docs/PROVENANCE.md`). Those contracts are not reopened here.

## Phase 3 (current): PR map, the visual MVP

### Summary

`prc map <PR>` turns one pull request into an interactive page and a 30-second video that show what the change does to the code's wiring. It works on any public GitHub PR, with no API key and no model calls. Every box and arrow comes from parsing the base and head code, and every one links to the diff lines behind it. The pitch is one sentence: "Your agent wrote 800 lines. Here's what it actually rewired, in 30 seconds, and no AI drew a single arrow."

Why this replaces the text brief as the product:

- Text summaries are a commodity. Any agent writes one for free, and CodeRabbit already draws LLM mermaid diagrams.
- Nobody offers a reliable, clean, interactive picture of a change, or a video of it. "Reliable" is the moat. Computed structure cannot hallucinate.
- A video and a social card spread on Twitter. A paragraph does not.

The brief survives as overlay facts on the map: CI on the head commit, risky surfaces, and description-vs-diff mismatches.

### What one run produces

`prc map --source <github:owner/repo#N | GitHub PR URL | fixture:name> --out artifacts/maps [--video]` writes `<out>/<snapshot short id>/` with these files:

- `map.json`, the `ChangeMap` below;
- `index.html`, one self-contained offline page with no CDN and no network;
- with `--video`, `tour.mp4` (H.264, 30 fps, 1920x1080 frames of a 1280x720 viewport at 1.5x, as long as the tour) and `card.png` (a 1200x630 viewport at 2x, the overview as a social card).

It prints JSON with the paths and the counts.

### The page

- **Header.** It shows the PR title, `repo#N` and the author. Stat chips show files, symbols changed, call sites affected, tests touched, CI on the head commit and risky surfaces.
- **Canvas.** The flow runs left to right. Unchanged callers sit on the left, changed symbols in the middle (layered by call depth inside the change), and unchanged callees on the right. A top lane holds non-code files (CI, config, docs) as chips with risk badges. A bottom lane holds tests.
- **Nodes.** Each node is a card with a status color bar. Added is green, modified amber, deleted red with a struck name, and context grey. A node also shows its name, its file, `+a −r`, its call-site count and an "untested" badge.
- **Edges.** Edges are curves. An added call is green with a flowing dash. A removed call is red and dashed. A kept call is thin grey. A call matched only by name is dotted, and the legend says so.
- **Interaction.** Click a node to open a drawer with that symbol's diff, its callers, its callees and the tests that reference it. Hover dims everything but the node's neighbors. Pan and zoom work.
- **Tour.** "Play" walks the computed steps. The camera eases between nodes, everything else dims under a spotlight, and a caption sits in the lower third. Arrow keys and space step through it.
- **Video hook.** `window.prcTour = {duration, seek(t)}` renders the exact frame at time `t`. Normal playback calls `seek` from `requestAnimationFrame`. Video export steps `seek` frame by frame, so no frame is dropped.
- **Brand line.** The footer of every screenshot says "PR map · computed from the code, no AI drew this".

### Data shape (`src/prc/changemap.py`)

`ChangeMap(pr, url, title, author, base_sha, head_sha, brief, files, symbols, edges, tour)`:

- `FileNode(path, kind, status, language, sensitive, added, removed, hunks, symbols)`. `language` is None when the file is not parsed (unsupported, opaque or over the size limit).
- `Symbol(id, path, qualname, kind, status, span, base_span, added, removed, hunks, call_sites)`. The id is `path::qualname`, for example `src/shop/cart.py::Cart.subtotal`.
- `Edge(source, target, status, resolution)`. `status` is `added`, `removed` or `kept`. `resolution` is `exact` (same file, an import, or `self`/`this`) or `name` (a unique name in the repo).
- `Step(kind, focus, via)`. `kind` is `overview`, `risky_file`, `entry`, `callee`, `test` or `summary`. Captions are written by the renderer from the step kind and map data, so the domain holds no prose.
- `Hunk(old_start, new_start, lines)` and `DiffLine(op, old, new, text)`.

### Rules

1. **Languages.** Python, JavaScript, TypeScript and TSX, parsed with tree-sitter (`tree-sitter` plus the official grammar wheels) through one registry table that maps an extension to a grammar and its queries. Adding Go or Rust adds a row. A source file over 512 KB, or any file in the generated kind, is not parsed.
2. **Symbols.** These are functions, classes and methods, plus arrow functions and function expressions bound to a name at top level or in a class. A line belongs to the innermost symbol whose span holds it. Top-level lines outside every symbol (imports, constants) stay on the file, not on a symbol.
3. **Status.** A symbol is matched by `path::qualname` between base and head. In head only means added. In base only means deleted. In both, with a changed line inside its head or base span, means modified. Unchanged symbols appear only as context.
4. **Calls.** A call is a call expression whose callee is a bare name, `self.x`, `this.x`, or `obj.x`. Instantiating a class counts as a call to the class. A JSX element whose name starts with a capital letter (`<CartView />`, `<Ui.Button>`) counts as a call to that component. Resolution goes in order:
   1. a definition in the same file;
   2. a name imported from a repo file (Python `from a.b import x`, `import a.b`; JS/TS relative imports with index and extension probing; CommonJS `const x = require("./x")` and `const { a } = require("./x")`);
   3. a method of the enclosing class for `self.x` or `this.x`;
   4. by name (`resolution="name"`), only for `obj.x()` and inherited `self.x()`, and only when exactly one candidate survives these filters:
      - the method name is not a dunder;
      - the receiver is a plain name chain whose root is not bound by an import, so a literal, a call result or `fs` from `require("fs")` never matches;
      - for `obj.x()`, the words of the receiver's last identifier are a subset of the words of the candidate's class name (a method) or of its module's file stem (a top-level function), so `cart.subtotal()` matches `Cart.subtotal` and `download.prepare()` matches `pushbutton_download.prepare`, while `db.execute()` matches nothing;
      - for `self.x()`, the candidate is a method.

   Anything else is dropped. A wrong arrow is worse than a missing one.
5. **Edges shown.** Only edges with at least one changed symbol at an end. Base edges come from the base versions of changed files. A head edge missing from base is added, a base edge missing from head is removed, and the rest are kept.
6. **Context.** Unchanged callers of changed symbols, and unchanged callees whose edge the PR added, removed or touched. A kept call is touched when one of its call lines is a `+` line. A kept call from changed code to an untouched helper is background and is not drawn. At most 6 callers and 6 callees per changed symbol, chosen by edge status (added, removed, touched, kept), then file, then line. `call_sites` counts every resolved call site in the head tree, so the card can say "47 call sites" while drawing 6.
7. **Tests.** A test symbol is any symbol in a test-kind file. A changed code symbol with no live edge from a test symbol has "no direct test". The card and the drawer use exactly that wording, because a test may still reach it through a caller.
8. **Tour.** The order is:
   1. overview, with an empty `focus`;
   2. one step per sensitive file, files the description does not name first, then by path, at most 3;
   3. entry points, which are changed non-test symbols with no changed non-test caller, largest first (`added + removed`), then by id;
   4. after each entry, its changed callees depth-first, each with `via` set to its caller. Callees go in order of the call's head line, removed calls after the rest (by base line), then by id;
   5. remaining changed non-test symbols, by id;
   6. one `test` step whose `focus` is every changed test symbol, by id, at most 6;
   7. summary, with an empty `focus`.

   Each symbol appears once. Removed edges count for traversal, so a deleted function is reached through its former caller. Steps 3 to 5 stop after 10 symbol steps in total, so a tour never runs past about 14 steps and 50 seconds. The summary card counts the changed symbols the tour skipped.
9. **Safety.**
   - Data goes in one `<script type="application/json">` block, with `<`, `>`, `&`, U+2028 and U+2029 escaped.
   - The page builds every PR-controlled string with `textContent` or `createElementNS`, never `innerHTML`.
   - The CSP is `default-src 'none'`, with the one inline script allowed by its sha256 hash.
   - There are no external URLs.
   - The `hostile` fixture must render inert.
10. **Determinism.** The same PR and code give byte-identical `map.json` and `index.html`. Layout is computed in Python from the map and is stable.
11. **Edge routing.** No edge passes through a card that is not one of its ends. The layout computes each edge's waypoints in Python:
    - an edge between adjacent columns crosses the gutter between them;
    - a longer edge crosses each column in between through the free gap nearest its straight line;
    - a test edge rises through the strip above the tests lane, then up the gutter left of its target's column.

    The page draws a smooth path through the waypoints.
12. **Dense maps.** When a map has more than 30 symbols, cards shrink to one-line rows grouped under their file, and only the edges of the hovered, selected or toured symbol are drawn. A map with no symbols says that no function or class changed in a parsed file.
13. **Viewport.** The page opens fitted to the canvas, or to the changed-code lane when fitting the whole canvas would shrink text below legibility. The header never overflows. The title truncates, and the Play button stays visible from 1280 px wide.
14. **Diff text.** Every diff line ends with a newline, and a missing final newline is marked with git's `\ No newline at end of file` line, so the last line of a file never glues onto the next diff line.

### Milestones

- **M0 (blocking, lead).** This plan, `changemap.py` types, the `shop` fixture (a Python and TSX shop with an added function, a modified caller, a deleted function, a removed call, a new test, and a CI workflow edit the body does not mention), and `tests/test_e2e_map.py`, written first. The E2E test fails until M1 and M2 land.
- **M1 (domain, delegate A, `map-domain`).** Owns `src/prc/codegraph.py` (registry, parse, definitions, calls, imports, resolution), the `build_change_map` logic in `src/prc/changemap.py`, their unit tests, and the tree-sitter dependencies in `pyproject.toml`. Check: unit tests on the fixture repo and on hostile and edge inputs.
- **M2 (presentation, delegate B, `map-view`).** Owns `src/prc/presentation/map_layout.py`, `src/prc/presentation/render_map.py` (page, inline CSS and JS, CSP hash, data block), `pipeline.run_map`, `prc map` in `cli.py` (including GitHub PR URLs), and their tests against a hand-built `ChangeMap`. Check: unit tests, plus screenshots of the sample page reviewed by the lead.
- **M3 (lead).** Merge M1 and M2. The E2E passes. Run on real PRs from the corpus (Python and TS), check every drawn edge by hand on 5 PRs, and fix.
- **M4 (video, delegate C).** `--video` through Playwright (an optional `video` extra) with frame-stepped `seek` capture and ffmpeg to `tour.mp4`, plus `card.png`. Check: an E2E that asserts duration, size and codec with ffprobe, run when the extra is installed.
- **M5 (lead).** README "Try it in 10 seconds", a demo page and video from a real public agent PR, and draft tweet copy. Nothing is posted without the user.
- **Later.** A GitHub Action that comments with the card and links the page; Go and Rust; an optional model narration tier.

Throughput checkpoint:

- **Blocking first steps.** M0, so both delegates build on the same frozen types and fixture.
- **Independent workstreams.** M1 and M2 touch disjoint files. `changemap.py` types are frozen at M0, and any change goes through the lead. M1 alone edits `pyproject.toml`. M2 alone edits `pipeline.py` and `cli.py`.
- **Shared mutable state.** None after M0. Each delegate has its own worktree and branch off `visual-map`.
- **Smallest safe decomposition.** Two workers, because domain and presentation meet only at the frozen types. Video waits for the page's `seek` API.

### M3 results (2026-10-04)

M1 and M2 merged into `visual-map` (42d0320, 439a68f). The E2E passes, and the 6 browser tests pass outside the sandbox. Then `prc map` ran on the 19 corpus PRs that change Python, JS or TS. All 19 finished in 3 to 9 s each, GitHub fetch included, and every page loads with no console error.

- **Exact edges.** 820 drawn. 816 have a call of the target's name on a line of the source span. The other 4 are generic calls `f<T>(...)` (3) and one call through a re-export alias, all correct on inspection.
- **Name edges.** 114 drawn, mostly false. Examples are `"".join(...)` to a repo method `join`, `db.execute(...)` to `_ScratchProof.execute`, `res.json()` to a top-level `json` in another file, and `fs.writeFile` (a CommonJS `require`) to a test helper. The true ones had a receiver named after its class or module (`cli_runner.invoke` to `EnvCliRunner.invoke`, `download.prepare` to `pushbutton_download.prepare`). Rule 4.4 now encodes that.
- **Size.** 7 of the 19 PRs change 34 or more symbols. Those maps are unreadable at fit zoom, and their tours run 60 to 226 s. Rules 6, 8, 12 and 13 respond.
- **Routing.** An edge that crosses a column is drawn over the cards in it, so `CartView -> total` reads as `legacy_total -> total`. Rule 11 responds.
- **Header.** At 1280 to 1440 px a long title pushes the Play button off screen. Rule 13 responds.

Next milestones, in parallel from `visual-map`:

- **M3b domain (delegate D, `map-domain2`).** Rules 4, 6, 8 and 14 in `codegraph.py`, `changemap.py` and `gitutil.py`. The shop E2E keeps its counts, because `CartView -> total` is touched.
- **M3c page (lead, `visual-map`).** Rules 7, 11, 12 and 13 in the layout, page script and styles, checked on screenshots of real PRs.
- **M4 (delegate F, `map-video`).** As above. The video module injects its capture styles itself and reads only `window.prcTour` and stable element ids, so it does not edit the page assets.

### M3b, M3c and M4 results (2026-10-04)

All three landed on `visual-map` (merges 5371d38 and 6a671a7, page commits 316cef0 to 92b464b). The verify passes with 320 tests and none skipped when run outside the sandbox, where Chromium can launch.

- **Name edges.** The 19-PR corpus now draws 100 name edges, against 114 before. Every receiver names its target's class or module (`serving.as_of_date` to `ServingDB`, `cli_runner.invoke` to `EnvCliRunner`, `config.*_rules` to `PolicyConfig`). The false matches from M3 are gone. Exact edges are 782 of 785 with a call line, and the 3 left are the known generic and re-export cases.
- **Size.** Tours run 9 to 53 s, against 60 to 226 s before. Maps over 30 symbols use grouped rows and draw edges on hover only. The page opens at a legible zoom on the changed lane.
- **Routing.** A test samples every route of four maps and fails if any point enters a card. Planted bugs (no passages, a channel through a test card) fail it.
- **Video.** `prc map --video` on SFHacks2026#21 writes a 34 s 1920x1080 H.264 tour in about 85 s, at roughly 70 ms per frame. `card.png` is the page's opening view.
- **Open.** When a context lane splits into two columns (moonproject#216 has 20 callees), the edges to the second column bundle through the gaps of the first. They stay correct but look busy. The fix is a layout choice: allow taller context columns, or shrink context cards to one line.
- **Prior art checked.** [code-review-graph](https://github.com/tirth8205/code-review-graph) (MIT, about 32k stars) builds a tree-sitter call graph of 30+ languages for MCP context, with a force-directed D3 view. It is a candidate language backend but brings MCP, fastmcp and watchdog as hard dependencies, and it graphs a working tree, not base against head. ELK's layered algorithm routes long edges through dummy nodes, as our router does. Inlining elkjs would move layout into the browser and add about 1.4 MB (unmeasured) for little gain at our graph sizes. Existing PR video tools narrate with an LLM over code slides. None computes the call wiring.

## Phase 2 (done): PR brief, the free tier

### Summary

`prc brief` turns one pull request into one GitHub comment. Everything in it is computed from the diff, the PR description and the CI results, so it makes no model calls. It tells a reviewer of an agent-written PR four things in seconds:

- how big the real change is once lockfiles and generated files are set aside;
- whether CI passed on this exact commit;
- where the description and the diff disagree;
- the three places to look first, and why.

It reuses capture, snapshot, inventory and verification as they are. The store, the model pipeline and the HTML view are not involved. Validation means running it on real public agent PRs, then on the user's own repos through a GitHub Action. The 12-pair lab pilot is not part of this phase.

Why this comes first (evidence in `reports/AI code comprehension last three months.md`):

- The AI-written PR description is itself the complaint. Kenton Varda put a moratorium on them. GitHub's own blog calls them "long-yet-shallow". Reddit calls them a slop vector.
- Readers cannot tell a wrong AI assertion from a right one (Kaufman et al. 2026-07-09).
- Maintainers triage in seconds.
- Computed facts cannot hallucinate, cost nothing per PR, and never send code to a vendor.

### Milestones

- **B1.** `prc brief` on a fixture through the CLI, with the E2E test written first. Check: `artifacts/e2e/briefs/<id>/brief.md` is byte-identical on rerun, and verify passes.
- **B2.** Run it read-only on at least 20 public agent PRs (Copilot coding agent, Devin, Claude Code, Codex). Hand-check every flagged item to get precision per check type. Tighten or delete any check below 80% precision. Check: `artifacts/corpus/` holds the briefs and the precision table.
- **B3.** A GitHub Action runs `prc brief` on `pull_request` and creates or updates one comment, found by its marker. It is built and tested locally. Installing it on any repository needs the user's go-ahead.
- **B4.** Install it on the user's own repos, then offer it to maintainers. The signals are installs that stay, and comments saying it caught something. Every external message needs authorization.

Deferred until B4 shows people want it:

- the computed import and call map for the visual view (Python `ast` first);
- the model tier;
- the pilot protocol v2 from the 2026-10-04 interrogate review.

### B1 spec

Data shape. The domain lives in `src/prc/brief.py`. It is pure and reads only `Acquisition`.

- `Brief(pr, title, head_sha, files, checks, mismatches, look_first)`
- `FileChange(path, kind, added, removed, named, sensitive)`
- `Kind`: code, test, docs, config, generated or opaque
- `Mismatch(kind, quote, fact, subjects)`, where kind is `changed_claim_not_in_diff`, `symbol_claim_not_found`, `test_claim_vs_ci` or `tests_claim_no_test_files`. `fact` is our fixed sentence. Anything taken from the PR goes in `subjects`.
- `Pointer(path, reason, lines)`

File kinds and sensitive surfaces are ordered rule tables, not if-chains. The renderer is `src/prc/presentation/render_brief.py`. It sends every untrusted string (path, quote, title, check name) through one code-span helper, so PR content can never produce a mention, link, image or HTML. Output starts with the marker `<!-- prc-brief -->`. `pipeline.run_brief` and `prc brief --source … --out artifacts/briefs` write `<out>/<snapshot short id>/brief.md` and `brief.json`, then print JSON.

Rules:

1. **Kinds.** The first match wins, in this order:
   - opaque inventory item: opaque;
   - lockfiles, snapshots, minified files, `dist/`, `vendor/` and generated code: generated;
   - test paths: test;
   - `.github/`, dependency manifests, Docker, CI files, `*.toml`, `*.ini`, `*.cfg`, YAML, non-lock JSON, `.env*`, `Makefile` and `*.tf`: config;
   - Markdown, rst, txt, `docs/` and LICENSE: docs;
   - anything else: code.
2. **Sensitive surfaces** apply to any kind, and the reason text is ours. They are:
   - secret-scanner allowlists and package registry configs;
   - workflows and other `.github/` files;
   - dependency manifests, shown with up to 3 added lines;
   - Docker and infrastructure;
   - migrations and SQL;
   - paths whose names suggest auth or security;
   - env and secret files;
   - other CI configs.
3. **Claim units.** These are the bullet lines, checkbox lines, table rows and sentences of the title and body, taken after removing fenced code, HTML comments, `<details>` blocks and blockquotes. Bold and underline markers outside code spans are dropped. An unchecked checkbox claims nothing.
4. **`changed_claim_not_in_diff`.** A unit has a change verb (add, update, modify, change, fix, bump, remove, delete, rename, move, replace, create, edit, rewrite, refactor and their inflections) or an arrow (`→` or `->`) outside its code spans. It names a path-like token, meaning one with a slash or a file extension, that matches no changed path. The token must also exist in the base or head tree, so routes, package names and planned files never fire. A path matches by full path, by a suffix on a segment boundary, or by basename. A directory token matches any changed path under it. URLs, domains, package scopes and slash commands are not paths, and `:12` or `#L5` suffixes are stripped.
5. **`symbol_claim_not_found`.** A unit has a create, remove or rename verb (add, create, introduce, new, remove, delete, rename and their inflections). At most 3 words from a fixed list of articles and code nouns sit between the verb and a backticked identifier. The identifier appears in no diff line and no head content of any changed file. `name(args)` is checked as `name`, and a qualified name by its last segment. The check is skipped when any changed file is opaque.
6. **`test_claim_vs_ci`.** A checked checkbox or a sentence claims that tests, lint, typecheck, the build or CI passed. Either a check on this commit failed (failure, timed_out, cancelled, action_required or startup_failure), or no checks ran.
7. **`tests_claim_no_test_files`.** A unit claims tests were added, written or updated, and no test-kind file changed.
8. **Hedges.** Rules 4 and 5 skip a unit that says not, no, never, without, kept, unchanged, untouched, already, would, could or instead. Rules 6 and 7 skip a unit that negates, defers or reports a failure.
9. **Named.** A changed file counts as named when any description token or prose word matches one of these:
   - its path, a path suffix or its basename;
   - its stem or name in any spelling (case, hyphens and underscores ignored, at least 3 characters);
   - every part of its stem of 3 or more characters, as words, plural allowed;
   - the parent directory instead, when the stem is generic (index, page, route, layout, main, mod, init, server, handler, utils, types);
   - a symbol defined or changed in its diff.

   Named only feeds look-first. The brief no longer lists unnamed files, because run 1 showed that list was mostly semantic misses.
10. **Look first.** At most 3 pointers, in a fixed order:
    1. sensitive files the description doesn't name;
    2. other sensitive files;
    3. the largest code change.
11. **Generated files** are counted in a separate total. They never appear in look-first.
12. **Uninspectable files.** The size line says how many changed files could not be inspected (binary, or over the 64 KB inventory limit).

### B2 results (2026-10-04)

Corpus: 28 recent public PRs from small repos, 7 each from the Copilot coding agent, Devin, Claude Code and Codex. The list and runner live outside the repo. Briefs and `runs.json` are under `artifacts/corpus/` (gitignored). All 28 ran in both rounds. Every flag was checked by hand against the PR.

| Check | Run 1 flags, correct | Run 2 flags, correct |
| --- | --- | --- |
| `changed_claim_not_in_diff` | 13, 0 | 0 |
| `symbol_claim_not_found` | 3, 0 | 0 |
| `test_claim_vs_ci` | 3, 3 | 3, 3 |
| `tests_claim_no_test_files` | 0 | 0 |
| sensitive file not in the description (look-first) | not separated | 4, 4 |

Run 1 false positives came from tokens that are not repository paths (routes, domains, package scopes, number fragments, `file.py::symbol`), table rows and bold markers merged into one unit, data names read as symbols, and negated sentences. Rules 3, 4, 5 and 8 above are the fixes. Run 2 found no real description-vs-diff disagreement, so the recall of rules 4, 5 and 7 is unmeasured.

What held up:

- **Unbacked test claims.** All 3 are Devin PRs that report local test runs as passing while no CI ran on the head commit.
- **Unmentioned risky surfaces.** Three PRs change a CI workflow without mentioning it, and one changes the secret-scanner allowlist (`.gitleaksignore`).

Corpus facts:

- 12 of 28 PRs claim tests, lint or the build passed. CI on the same commit backs 9 of them, none is contradicted, and 3 have no CI.
- 8 of 28 have no CI on the head commit.
- 7 of 28 touch a sensitive surface, and 6 touch CI workflows.
- 9 of 28 contain a file the brief cannot inspect.
- None contain generated files.

Premise finding: these agents did not misstate which files they changed. The brief's value is a quiet, precise card of claims against evidence and risky surfaces, not a lie detector.

## Phase 1 (done): MVP

## TLDR

1. Build the full MVP as a Python 3.12 package `prc` (stdlib + numpy for the protocol's PCG64) with one real entry point, the `prc` CLI, that turns a GitHub PR source into a published, hash-identified review view (overview, required infographic, evidence-adjacent claims, selected table/flow/prose artifacts) plus recorded reviewer decisions.
2. Contracts implemented in code: Code Comparison Identity separate from per-check Verification Evidence Identity; Source Basis / Snapshot identities; Git-tree Change Surface Inventory (real `git`); Semantic Input Manifest; bounded 3-attempt timed capture with unknown-consistency; Claim Validation with mechanical vs model-assessed basis; many-to-many Coverage Ledger with closure falsification; inert presentation with URL/output checks; PublishedViewIdentity; atomic canonical publication; freshness reconciliation + local CAS decisions; solo evaluation protocol engine.
3. Live GitHub: a real REST/`git` adapter implementing the same `PullRequestSource` contract is included but **unverified live** (no credentials were exercised). All development and E2E use clearly labelled deterministic local fixtures (real local git repos, fixture provider data, fixture model). Fixture behaviour is never reported as live verification.
4. Models: the comprehension and validator model clients are protocol-typed. Only deterministic **fixture models** ship; they are labelled `fixture` in every artifact. No real LLM adapter is wired (deferred).
5. Out of scope: video, non-GitHub sources, autonomous merge, permanent quiz/merge gate, cross-revision semantic reuse, running the pilot (no pilot results are claimed), PR publishing/deployment.
6. Deferred follow-ups: live LLM adapters, live GitHub run, web server UI for decisions (CLI + static HTML for MVP), frozen treatment-ID registration for a real cohort.

## High-Level Flow

```text
prc review --source fixture:<name> | github:<owner/repo#N>
  │
  ▼ acquisition/  PullRequestSource.observe()  ──► capture.capture_bundle (≤3 attempts, drift check)
  │                                               └─ ObservationBundle {resources, interval, consistency}
  ▼ identity.py   CodeComparisonIdentity (repo, PR, head, base tip, merge-base)   [no check data]
  ▼ inventory.py  git diff-tree over pinned commits ─► ChangeSurfaceInventory (opaque items kept)
  ▼ verification.py  per-check VerificationEvidenceIdentity + eligibility (gaps for missing/conflicting)
  ▼ manifest.py   SemanticInputManifest (content-addressed records)
  ▼ snapshot.py   SourceBasisIdentity ─► SourceSnapshot (ReviewSnapshotIdentity)
  ▼ comprehension.py  ModelClient.generate (untrusted) ─► candidate concepts/claims/coverage
  ▼ validation.py  deterministic checks + independent assessor ─► ValidatedSemanticArtifact
  ▼ coverage.py   many-to-many ledger + closure falsification ─► gaps
  ▼ presentation/ typed doc ─► html/svg/table/prose renderers ─► output checks ─► hashes
  ▼ publication.py  PublishedViewIdentity; sqlite UNIQUE(publication_key) atomic canonicalize
  ▼ reviewer.py   freshness reconcile ─► CAS decision (snapshot_id, view_id) ─► reviewer state
  ▼ artifacts/<run>/{index.html, infographic.svg, semantic.json, snapshot.json, manifest.json}

evaluation/  protocol.py (assignment, roster seal) → scoring.py → analysis.py (PCG64 bootstrap, scenarios)
```

## Milestones (each ends in a verified state)

- [x] M0 Workspace: docs copied with provenance, uv project, PLANS.md.
- [x] M1 Identity + models core: canonical hashing, branded ids, frozen models. Tests: hash stability/order independence, identity layering (check change ⇒ basis change, comparison unchanged).
- [x] M2 Acquisition: `PullRequestSource` contract, fixture source building real local git repos, GitHub live adapter (unverified), `inventory.py` (add/del/mod/mode/symlink/submodule/binary/LFS/opaque), `capture.py` (drift ≤3 attempts, unknown consistency), verification eligibility + gaps.
- [x] M3 Manifest + Snapshot: manifest, SourceBasis, snapshot identities; late context ⇒ new snapshot.
- [x] M4 Comprehension + Validation + Coverage: model protocols, fixture models, claim validation (mechanical vs model-assessed, scope witnesses, disagreement ⇒ inference/gap), many-to-many ledger, closure falsification, adversarial fixtures.
- [x] M5 Presentation: typed document, inert HTML/SVG/table/prose renderers, URL policy, output validator, infographic always; hostile markup/URL tests per renderer; relation direction + epistemic-state preservation.
- [x] M6 Publication + reviewer state + freshness: PublishedViewIdentity, sqlite atomic canonical key, freshness reconcile (match/stale/unknown + deadline), CAS decisions.
- [x] M7 Evaluation engine: assignment, three-item instrument scoring, fallback, PCG64 bootstrap, adverse/favorable scenarios, decision rule. Acceptance examples from the protocol as tests. (Delegated to a subagent; reviewed by me.)
- [x] M8 CLI + E2E: `prc review|decide|status|eval-analyze`; E2E test through CLI ending in `artifacts/e2e/` repeatable artifact.
- [x] M9 Independent validation by a fresh-context agent (finite: one pass, fix confirmed defects), docs (README), final verify: ruff, mypy --strict, pytest, build.

## Verify command

`uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest && uv build`

## Progress log

- 2026-10-04 00:36 start. 00:45 M0–M4+M7 (6/10), 52 tests. 00:52 M5–M6 (8/10), 93 tests. 00:55 M8 E2E green, full verify green (97 tests, build ok). M9 independent validation running.
- 01:05 Independent validator (fresh context, one finite pass) reported 1 CRITICAL + 2 MAJOR: mechanical checks not bound to claim text/kind and able to close coverage; assessor crash not contained; losing publication overwrote the canonical bundle. All three fixed test-first and re-verified with the validator's own repro scripts. Final verify: ruff, format, mypy strict, 101 tests, build all pass. 10/10.
- Decisions: Python 3.12 + stdlib + numpy (PCG64 fixed by protocol); SQLite for atomic publication/CAS; static HTML/SVG with no script (CSP `default-src 'none'`); fixture models and fixture sources are labelled in every artifact.

---

# Clean rebaseline and hillclimb, 2026-10-07 (continued)

## Summary

Rebuild all 12 PR outputs with current source into a new run, re-read with fresh readers on materialized packets, and hillclimb comprehension against the frozen targets. Frozen questions, targets, grades, and outputs stay unchanged. Grade-audit review shows the deterministic replay disagrees with reviewers 275/410 times, so reviewer grades remain the instrument of record and product tuning follows reviewer-marked wrong answers only.

## Milestones

- [ ] H1. Rebuild 12 outputs with current source and frozen boards into `eval/runs/2026-10-07-rebaseline/`, then materialize packets with hashes.
- [ ] H2. Fresh readers score pilot PRs (11, 12, 17, 19) on all conditions, then the other 8. Grade and record a clean scoreboard.
- [ ] H3. Trace each misleading answer to its causing output and fix at source, test-first. One commit per accepted win.
- [ ] H4. Complete measurement evidence: timing medians, OCR diagnosis, judge check and grounding audit on current outputs.
- [ ] H5. Independent review, launch docs, full verifier, commit. Operator gates (license, repo name, push, PyPI, human session) stay with the user.

Q4/Q5 outcome, 2026-10-08: baseline committed on verification-skill; local main fast-forwarded (ancestor, no unique commits). No remote is configured, so no push or PR exists. Ticket 01 resolved. Ticket 02 stays blocked on the human repository-identity decision. Ticket 03 stays open for human review. Final independent recheck of the four source fixes is pending; narrow tests, lint, types, and the 572-test package check pass.
