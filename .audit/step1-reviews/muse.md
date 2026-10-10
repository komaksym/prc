**TL;DR:** The change does not meet its own “trustworthy” bar. The OCR gate passes images with extra words it claims to forbid, the map cap logic hangs or silently drops the diagram on large PRs, and the vendored renderer is pinned on paper but never verified at runtime.

I read the diff `972756e..a6b0e62` in `/Users/koval/dev/prc/.claude/worktrees/readiness`, read `infographic.py`, `graphdoc.py`, `render_map.py`, `pipeline.py`, `comment.py`, `doc.py`, and `vendor-prlens.mjs` in full, and ran `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_infographic.py tests/test_graphdoc.py tests/test_render_map.py` with 44 passed. Those tests pass because they avoid the cases below.

## Findings

### 1. [critical] Gate explicitly allows extra short and stopword text
**Location**: `src/prc/presentation/infographic.py:398` in `score_ocr`
**Finding**: Any OCR token shorter than 3 characters or in `STOPWORDS` is marked good without checking the brief.
**Evidence**: I built a brief with allowed words `cart, totals, 2, files, infographic, drawn, by, ai, words, from, prc`, then scored one OCR stream containing exactly those plus extra `q`, `zx`, and `the` at confidence 90. The verdict was `pass` with empty invented and missing. `the` is not in the brief, and `q`/`zx` are decorative letters of the kind the prompt rules forbid, yet the gate ignores them by construction. Combined with `WINDOW` skipping and the join/neighbor heuristics, an image can carry filler words between brief lines and still pass coverage while the invented check looks away.
**Suggestion**: Remove the length and stopword exemptions. If they exist to cut false positives, allowlist only exact brief stopwords in their exact positions instead of exempting the whole class everywhere.

### 2. [critical] OCR text matching cannot enforce “never shows words PRC did not write”
**Location**: `src/prc/presentation/infographic.py:360-458` (`score_ocr`, `_read_mode`, `gate`) plus `src/prc/explainer/doc.py:224-232`
**Finding**: The trust claim rests on Tesseract readings at two resolutions, but anything Tesseract cannot read at confidence 70 is accepted by design, and anything that is not text at all is never examined.
**Evidence**: `score_ocr` skips every token below `CONF_FLOOR`, returns `unreadable` only when no token reaches 70, and otherwise ignores low-confidence extras. A clear-to-human caption rendered faint, small, stylized, or as a QR/barcode, logo ligature, or watermark yields either no high-confidence token or a decode Tesseract never attempts, so the gate passes while a human reads invented content. `render_doc` then embeds the raw candidate bytes as a `data:image/png` blob with no file-size, dimension, or content cap, so one adversarial candidate permanently bloats `doc.html` and ships a machine-readable payload the gate cannot see.
**Suggestion**: Cap candidate bytes/dimensions, reject QR-like structure explicitly, and stop stating the guarantee as absolute. Record the gate as a fuzzy text check, not proof of no extra words.

### 3. [critical] Map node cap hangs instead of capping on many single-symbol files
**Location**: `src/prc/presentation/graphdoc.py:242` in `_select`
**Finding**: The `while len(risky)+len(picked)+len(aggregates())>MAX_NODES` loop can make no progress, and the slices above it do not enforce the cap when `len(risky)` exceeds 256.
**Evidence**: With 300 files holding one changed symbol each and no risky files, `picked` starts at 256 and `aggregates()` returns 44, for a total of 300. Each loop iteration removes one picked symbol and that file becomes a new aggregate, so the total stays 300 forever. I simulated this counting logic and confirmed the total never moves. Separately, `(changed+context)[:MAX_NODES-len(risky)]` with a long list and negative length does not yield empty: `list(range(500))[:256-300]` has length 456. A risky-heavy PR therefore exceeds the cap before validation, fails `validate_contract`, and degrades to `graph=None`.
**Suggestion**: Replace the fixpoint loop with a one-pass budget: take risky file nodes first, then changed symbols by churn, then fill remaining budget with aggregates, never recomputing aggregates inside a loop. Clamp negative budgets to zero.

### 4. [critical] Bundle pin is never checked when the page is built
**Location**: `src/prc/presentation/render_map.py:103` plus `src/prc/presentation/map_assets/prlens.lock.json`
**Finding**: `render_map` reads `prlens.bundle.js` and hashes it for CSP, but never compares it to `bundle_sha256` in the lock. The lock is only read by the vendor script.
**Evidence**: I grepped `src/`, `scripts/`, and the render test for `prlens.lock`; only `scripts/vendor-prlens.mjs` references it. A modified or stale bundle still renders because its CSP hashes are recomputed from its current bytes. Pinning without runtime verification is provenance theater, and the CSP gives no additional protection since it whitelists whatever is on disk.
**Suggestion**: Verify the bundle hash against the lock inside `render_map` or a tested helper, and fail closed on mismatch. If startup cost matters, verify once and cache.

### 5. [warning] `MAX_WORDS 80` is not enforced
**Location**: `src/prc/presentation/infographic.py:193` in `_fit_words`
**Finding**: The shrink loop only drops `Risky surfaces` and `Look here first` rows. Briefs with no such rows keep every chip, verdict, and headline word.
**Evidence**: I built a trimmed brief with a long headline, six chips, and a verdict totaling 152 words and no look/risky section. `_fit_words` returned all 152 words against `MAX_WORDS 80`. The intent says the brief is capped, but the cap silently fails exactly when chips and verdict are longest.
**Suggestion**: Enforce the budget across all roles, or record over-budget as an explicit gate input instead of asking the image model to render an impossible word count.

### 6. [warning] `l`-to-`i` folding breaks the “code-like tokens exact” rule
**Location**: `src/prc/presentation/infographic.py:134-145` (`_fold`, `_match`)
**Finding**: `_match` returns true on `_fold` equality before it consults the code-word set, digit check, or similarity threshold.
**Evidence**: `_match("login","iogin",frozenset({"login"}))` is true in my probe, even though `login` was passed as a code word demanding exactness. Any code token differing only by `l`/`i` confusion passes, and the same fold is reused for invented, join, neighbor, and coverage checks, so one heuristic weakens every boundary.
**Suggestion**: Apply exact matching first for code and digit tokens, and confine folding to the prose path only.

### 7. [warning] Vendoring patches the renderer with unexplained shims
**Location**: `scripts/vendor-prlens.mjs:23-37,142-143`
**Finding**: The script overwrites both `dist/manifest.js` files with stubs returning empty hashes and empty manifests.
**Evidence**: The shim text is hardcoded with no comment, issue link, or test that the renderer still enforces what the manifest was for. The smoke test only checks that an SVG, width, height, and one atlas node exist. The `zod not in bundle` and `node:crypto not in bundle` checks are substring heuristics, and the 100KB cap is arbitrary. A future renderer that relies on manifest integrity will silently lose it.
**Suggestion**: Document why the manifest must be stubbed for offline use, assert the exact renderer behavior that replaces it, or stop patching third-party internals.

### 8. [warning] Explain output locking and infographic gating are not safe under retry or concurrency
**Location**: `src/prc/pipeline.py:503-504` (`_publish_explain`) and `src/prc/pipeline.py:538` (`run_explain` candidate loop)
**Finding**: The lock is `lock.mkdir()` with no `exist_ok`, timeout, or stale-lock recovery, and gating runs four 180-second Tesseract calls per candidate sequentially with no candidate cap.
**Evidence**: Two background explain runs on the same slug collide on the lock directory and abort with `FileExistsError`. A crashed run leaves the lock behind and every later run fails until manual cleanup. Ten `--infographic` flags mean up to 40 subprocess runs and a worst-case hours-long block. Partial Tesseract failures are also invisible: `gate` keeps whatever reads succeed, but `infographic/check.json` does not record how many of the four modes succeeded, and `run.json` collapses tool-unavailable into `failed`.
**Suggestion**: Use a real file lock or atomic staging with stale detection, cap candidates, gate in parallel with an overall timeout, and persist per-mode success plus the `tool` verdict distinctly.

### 9. [warning] Large-PR and tour-focus losses degrade silently
**Location**: `src/prc/presentation/graphdoc.py:_overview_doc`, `_finish`, `_focus_ids`
**Finding**: Over-budget grouped maps slice with a possibly negative `room`, and walkthrough steps whose focus symbols were dropped collapse to `{"kind":"all"}` with no marker.
**Evidence**: `room=MAX_NODES-len(walk)-len(risky)` can be negative, and `groups[:room]` with negative `room` returns almost every group instead of none, pushing the node count over contract and flipping the whole diagram to the “no function changed” fallback. Separately, `_focus_ids` returns an empty list for dropped symbols and `_selection` maps that to full-map focus, so `map.js` marks the step plain and the user sees a full view while the caption names a specific symbol. `page_data` has drop counts, but the step itself does not say it lost focus.
**Suggestion**: Clamp `room` at zero, prioritize groups versus walk symbols explicitly, and emit an explicit `dropped-focus` state per step instead of reusing `all`.

### 10. [warning] Truncation and comment fallback mislead the reader
**Location**: `src/prc/presentation/infographic.py:152` (`_trim_line`), `src/prc/presentation/comment.py:189-194`, `src/prc/presentation/graphdoc.py:437`
**Finding**: Three small trust leaks compound: trimmed lines show no ellipsis, the infographic comment has no upload instruction while the card does, and provenance accepts any `http` URL.
**Evidence**: `_trim_line` hard-cuts at 96 characters and returns a fragment that looks complete, so a path or verdict can change meaning without any visible marker. When `infographic=True`, the comment embeds `infographic.png` alone; unlike the card branch, it never tells the user images do not embed from the repo, so the posted GitHub comment renders broken while the fallback card disappears from the comment. `_provenance` allows any `http` URL into the graph document handed to the third-party renderer.
**Suggestion**: Add a visible truncation marker or refuse overlong lines, keep the card reference or upload note alongside the infographic, and restrict provenance URLs to `https` GitHub PR URLs or omit them.

### 11. [nit] Dead bytes constant and duplicated PNG check
**Location**: `src/prc/presentation/infographic.py:101` and `src/prc/cli.py` explain parser
**Finding**: `_PNG_MAGIC` is defined in the gate module but never used; the CLI redefines the same eight bytes inline.
**Evidence**: Grep shows one definition and zero uses in `src/`. Validation therefore lives only at the CLI boundary, so library callers of `run_explain` bypass the PNG check while the gate module carries dead code that suggests it enforces the format.
**Suggestion**: Move the magic check into the gate or pipeline library, reuse one constant, and delete the unused one.

**Next step:** Ship one hardening scope that makes the trust claim testable: strict gate exemptions plus image caps, terminating cap logic with regression tests for single-symbol floods, runtime bundle verification, and explicit tool-versus-failed reporting.
