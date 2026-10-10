**TL;DR: The change is in good shape — 44 focused tests pass, ruff and mypy are clean, the gate and converter are deterministic, and the vendor pinning chain (tarball → bundle → lock → goldens) is enforced by tests. But the review found 6 warnings and 4 nits. The worst ones: a graphdoc validation failure silently renders a map page that falsely claims no symbols changed, and the published infographic bytes are snapshotted before the OCR gate reads the file, so the recorded verdict can describe different bytes than the published image.**

## Findings

### 1. warning — A validation-failure fallback renders a page that lies about the PR

**Location**: [render_map.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/render_map.py:63) (`page_data`, `except ValueError`) and [map.js](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/map_assets/map.js:120)

**Finding**: When `to_graph_doc` raises `ValueError`, `page_data` swallows it, sets `graph = None`, and `map.js` renders the `.empty` state: "No function or class changed in a parsed file." That message is shown beside stat chips computed from the same map, which say, for example, "62 parsed symbols changed".

**Evidence**: The only way `GRAPH` is null is a converter/contract defect — `to_graph_doc` raises only from `validate_contract`. The genuinely-empty case (no symbols, no files) also produces `graph = None`, so the two states share one message. For a milestone whose premise is "every surface states facts that match the PR", the degraded state is the one surface that contradicts the map. No test covers it: the browser suite asserts `.fallback` count 0 or 1 for render errors, and no test exercises `graph = null` (grep for `.empty` / "No function or class" in tests returns nothing).

**Suggestion**: Put an explicit marker in the payload (for example `layoutError` with the issues, or `empty: true` only when symbols and files are both empty), render an honest error banner for the failure case, and add a browser test for it. Fail the `prc map` build instead is also defensible; silent degradation is the one option that violates the intent.

### 2. warning — Published infographic bytes are snapshotted before the gate runs

**Location**: [pipeline.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/pipeline.py:614)

**Finding**: `raw = cand.read_bytes()` runs before `verdict = infographic.gate(cand, brief)`. The gate shells out to tesseract, which re-opens the file from disk. The bytes published at line 631 and the recorded `sha256` are the pre-gate snapshot, so the verdict describes whatever tesseract saw at gate time, and the published content is whatever was on disk at read time.

**Evidence**: These are two separate reads of a mutable path with a subprocess in between (four tesseract invocations, up to 12 minutes of timeout budget). If the file changes between them, `check.json` records a pass for bytes that were never read by tesseract. Likelihood is low in the documented workflow, but `check.json` exists precisely as the provenance record, and the fix is one line.

**Suggestion**: Read the bytes once, write them to a temp file under `work/`, gate the temp copy, and publish those gated bytes. Passing the image via tesseract stdin also works.

### 3. warning — The walkthrough infographic figure has no layout CSS

**Location**: [doc.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/doc.py:225) and `src/prc/explainer/assets/doc.css`

**Finding**: `figure.infographic` and its `<img>` get zero rules in `doc.css`. The only max-width handling in the file is for `pre`.

**Evidence**: The doc body is `max-width: 1060px` with 22px padding, so the content column is 1016px. AI-generated PNGs are typically 1024–2048px wide; at natural size they overflow the column horizontally, and at the 480px mobile breakpoint they overflow by hundreds of pixels. The e2e test (`test_e2e_infographic.py`) asserts the data URI and figcaption text exist in the HTML, so nothing catches this. The CSP is fine (`img-src data:` pre-exists), so the image renders — just oversized.

**Suggestion**: Add `.infographic img { display: block; width: 100%; height: auto; border: 1px solid #1F2738; border-radius: 14px; }` to `doc.css`, and when S7 runs the real-browser pass, assert the rendered image width stays inside the content column.

### 4. warning — A "pass" can rest on fewer than four readings, and check.json cannot show it

**Location**: [infographic.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/infographic.py:458) (`gate`, `_read_mode`) and [pipeline.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/pipeline.py:616)

**Finding**: `_read_mode` returns `None` on any tesseract failure or timeout, and `gate` silently drops failed readings. `score_ocr` never knows how many readings ran, so a verdict of `pass` can stand on a single degraded reading. Worse, the persisted record in `pipeline.py` writes `constants`, `invented`, `missing`, `tesseract`, and `verdict` — but not `verdict.detail["modes"]` — so `check.json` gives the reader no way to see that readings were dropped. If all four fail, the verdict is `tool` even though tesseract exists and ran four times.

**Evidence**: The four-reading design (dense psm 3, sparse psm 11, plus dpi-150 variants) is the invention detector. A pass on one reading is formally consistent with "no reading contains a foreign word", but it is weaker evidence than the intent describes, and the audit record hides the difference. Probability of partial failure is low, which is exactly why it must be visible when it happens.

**Suggestion**: Persist `detail["modes"]` into each `check.json` entry, and either require at least two successful readings for a pass or introduce a distinct verdict for partial reads.

### 5. warning — Stopword and short-token carve-outs weaken the stated guarantee

**Location**: [infographic.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/infographic.py:398) (`score_ocr` invented scan)

**Finding**: Any OCR token in `STOPWORDS` (19 words: "and", "for", "with", "the"...) or shorter than 3 characters is accepted at any confidence, even when the brief never contains it. The stated guarantee in the milestone description and in D23 is "no foreign word at confidence 70 or more".

**Evidence**: The carve-outs are deliberate — `tests/test_infographic.py` enshrines them (`("Se", 79)` in `NOISE` must pass) — and `brief.json` records `STOPWORDS` in its gate constants, so the drawing agent sees them. But the human-facing records (D23, the milestone statement) state an absolute rule the code does not enforce. A candidate can add decorative stopword text freely at confidence 100.

**Suggestion**: State the carve-outs in D23 and the README (one sentence each), or tighten the relief so a foreign stopword must sit adjacent to an allowed token to be excused.

### 6. warning — Split-word tolerance defeats "code names must match exactly"

**Location**: [infographic.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/infographic.py:320) (`_covers`, the `(1, 2)` branch) and line 402 (`_allowed_neighbor`); DECISIONS.md D23

**Finding**: A brief code token can be matched by two OCR words joined together. So "onComplete" drawn as "on Complete" (visible space) passes: "on" is a stopword, "complete" is in `allowed_words`, and coverage matches via the join. Same for "multicursor" drawn as "multi cursor". D23 says "Code names must match exactly," and the measured acceptance case ("onCComplete") was caught only because the extra C broke the join.

**Evidence**: Trace: `_covers` matches the brief token via `_match(here, ocr[pos] + ocr[pos + 1], code)` — fold equality holds for the concatenation. The invented scan then excuses both halves. The two-word tolerance is tested and deliberate (`test_gate_split_word_passes`), but nothing restricts it to prose tokens.

**Suggestion**: In `steps()`, allow the `(1, 2)` split relief only for non-code tokens. If the tolerance must stay for real tesseract behavior, say so in D23 next to "must match exactly".

### 7. nit — check.json hides concurrent missing lines when an invented word exists

**Location**: [infographic.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/infographic.py:384) (`score_ocr` early return)

**Finding**: The `invented` verdict returns before `missing` is computed. A candidate with both an invented word and a missing line records only the invented word.

**Evidence**: SKILL.md section 10 tells the agent to fix "exactly those" from check.json, and describes the record as naming both the foreign words and the unconfirmed lines. In the both-present case the redraw loop burns one of the two allowed redraws discovering the missing line. Verdict precedence can stay; the record should not lose information.

**Suggestion**: Compute `missing` regardless and store it in `detail`, letting the verdict keep its precedence.

### 8. nit — `dropped` payload is written and tested but never read

**Location**: [render_map.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/render_map.py:65)

**Finding**: `page_data` computes `dropped` counts into every map.html, two tests assert its presence, and `map.js` never reads it. In the `ValueError` fallback it is set to all symbols and edges, which nothing surfaces either.

**Evidence**: grep for `dropped` in map.js and map.css returns zero hits. Dead data per page, and the tests assert a dead field. Rendering it would actually serve D18's "state what it did not cover"; today it does nothing.

**Suggestion**: Either render it (a footer line like "3 of 62 symbols shown") or delete it.

### 9. nit — PNG magic check duplicated and placed only in the CLI boundary

**Location**: [cli.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/cli.py:309) and [infographic.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/infographic.py:101)

**Finding**: The CLI rebuilds the PNG magic as `bytes((137, 80, 78, 71, 13, 10, 26, 10))` while `infographic._PNG_MAGIC` already defines it. The validation also lives only in the CLI; `run_explain(infographics=...)` trusts its argument.

**Evidence**: Any future caller of `run_explain` (eval harness, another subcommand) gets no PNG check, and the gate then produces garbage verdicts from whatever tesseract says. Boundary validation belongs at `run_explain`, where the sequence enters the pipeline.

**Suggestion**: Move the check into `run_explain` (or a shared helper) and reuse `_PNG_MAGIC`.

### 10. nit — Dead defensive branches for unknown tour-step kinds

**Location**: graphdoc.py `_finish` (walkthrough loop) and [render_map.py](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/render_map.py:86) (`page_data`)

**Finding**: `picked_steps` only yields `None`, `risky_file`, `entry`, `callee`, and `test`. The final `else` branches that fall back to `step.kind` as heading/body are unreachable.

**Evidence**: Reading `picked_steps`: the middle list is built from three explicit kind filters. If the guard is intentional, it is undocumented; the code-quality bar here is to delete it or state why it exists.

**Suggestion**: Delete the branches, or keep one with a comment naming the invariant that makes it dead.

### 11. nit — A boards test lives in test_graphdoc.py

**Location**: [test_graphdoc.py](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_graphdoc.py) (`test_board_coverage_states_changed_file_budget`)

**Finding**: The test imports `prc.explainer.boards.coverage` and tests board file-budget wording. Nothing about it concerns graphdoc.

**Evidence**: It reads as a leftover from the deleted `test_map_grouping.py`. It belongs in a boards/explainer test module; file placement is the only issue.

**Suggestion**: Move it next to the other board-coverage tests.

**Next step**: Bundle the four fixable warnings into one shippable scope before S5 — honest layout-failure state with a browser test, snapshot-then-gate ordering, `figure.infographic` CSS plus a rendered-width assertion, and `modes` persisted into check.json — then run the S5–S7 integration pass (full checks, real-browser screenshots of doc.html and map.html) against the rebuilt acceptance PRs.
