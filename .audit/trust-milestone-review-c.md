Model: opencode-go/glm-5.3-flash. Agent: 01a12009-b638-77a2-a924-f8e001fb2b1b.
Scope: 24e5300...6dbb336.

All checks pass against HEAD 6dbb336; the worktree holds no side effects from this review. Composing the final findings list now.

TL;DR: The trust-frozen review of `git diff 24e5300...6dbb336` is complete with no critical findings — 5 warnings and 4 nits. Two findings are reproduced with concrete inputs (a stale success pointer in verify-release.sh, a contradictory deleted-only verdict); the rest are static traces with exact locations. The clean-cache verification contract at 6dbb336 stays valid, and no repro from the three closed prior reviews resurfaced.

## Findings

### 1. [warning] Failed verify run leaves stale `latest-success.txt` evidence
**Location**: `scripts/verify-release.sh:31,150` (attempt stamp vs. success stamp)
**Finding**: The script stamps `latest-attempt.txt` at attempt start but writes `latest-success.txt` only on success, and never deletes or marks the old success pointer when a later run fails.
**Evidence**: Reproduced. I ran the frozen script with a fake `uv` that fails mypy and pytest. `latest-attempt.txt` named the new failed run (`run-ksaCv9`), while `latest-success.txt` still named the older success (`run-mdM0PT`). Anyone reading the success pointer after a failed rerun — the parent's own "rerun at 6dbb336" claim depends on this pointer — silently reads stale evidence.
**Suggestion**: Delete `latest-success.txt` at attempt start, or stamp failed attempts into the success slot with an explicit `FAILED` marker.

### 2. [warning] `:(literal)` pathspec in inventory numstat breaks on directory-form paths
**Location**: `src/prc/inventory.py:95` (`_line_counts`)
**Finding**: `_line_counts` builds `f":(literal){change.path}"`. The `:(literal)` prefix makes git treat the spec literally, but a change path in directory form (trailing `/`, as a tree entry) matches no file records, and numstat then yields zero or several records instead of the one expected.
**Evidence**: Static trace, not reproduced against a real map: working-tree diffs emit file entries, so the failing input requires a directory-form change path in stored state. On that input the code reaches `GitError("numstat expected one record…")` and aborts full acquisition instead of skipping one entry.
**Suggestion**: Filter or normalize directory-form paths before the numstat call, or query per-file with a disambiguating form that cannot match trees.

### 3. [warning] Isolated release copy verifies working-tree content, comment claims git index
**Location**: `scripts/verify-release.sh:40,48`
**Finding**: The comment says the copy is "restricted to committed or staged inputs (git index)", but the loop does `shutil.copy2(root / name, target)` for every `git ls-files` path — it copies working-tree content.
**Evidence**: Static trace of the copy loop. Unstaged edits to tracked files are silently included in the verified build, so the published wheel can differ from the committed tree the run claims to verify. `test_d16_isolated_copy…` asserts only path presence/absence, not content equality.
**Suggestion**: Copy index content (`git checkout-index` or `git archive`) into the isolated tree, or fix the comment and document the working-tree contract.

### 4. [warning] Note-geometry constants duplicated with no binding test
**Location**: `src/prc/explainer/preflight.py` (`_scene_geom`, `note_risks`) vs `src/prc/explainer/assets/engine.js` (`MAKERS.diff`)
**Finding**: Preflight re-implements the engine's note-fit math: WRAP_WIDTH 72, `1560 / ((longest+gutter)*0.6+2)`, topAt 489, safe bottom 862, label 72, pad 48, plus NOTE_PX_PER_CHAR 15/PAD 37 vs the DOM-measured values. It also diverges by 1px: preflight flags when `desired > limit`, the engine clamps only when `want > limit + 1`.
**Evidence**: Static trace. If engine.js constants change, preflight silently diverges and reports false risk limits or misses real overflow. No canary test binds the two copies.
**Suggestion**: Derive the constants from one shared source or add a canary test that fails when engine constants move.

### 5. [warning] Deleted-only production change prints a contradictory verdict
**Location**: `src/prc/facts.py:143` (verdict) vs `src/prc/presentation/comment.py`
**Finding**: When the only production change is a deletion, the verdict reads "No live production symbols changed." while the same comment/card prints `symbols 1` and "parsed symbols changed".
**Evidence**: Reproduced. I ran a map with one `deleted` symbol: card and comment showed `symbols 1` with the changed-count wording, while the verdict sentence claimed no live production symbols changed. A human reviewer reads a direct contradiction in the same block.
**Suggestion**: Word the deleted-only case distinctly, e.g. "Production symbols deleted; nothing added or modified."

### 6. [nit] Facts fields written with no consumer
**Location**: `src/prc/explainer/check.py:488-489`, `src/prc/explainer/preflight.py:150-152`
**Finding**: `facts["changed_missing"]`, `facts["changed_known"]`, `files_shown`, `files_total`, and `symbols_touched` are written into facts or the coverage dict with no consumer; the summary line uses only shown/total/unavailable counts.
**Evidence**: Grep over `src/`: no reader of these keys outside the writers. The counts also include unchanged context rows that sit after diff rows in the check pass — harmless for the changed-line contract, since context rows are not in `changed`, but noise for file/symbol counts.
**Suggestion**: Drop the write-only keys or feed them into the summary the way `line_coverage` is fed.

### 7. [nit] Facts re-export and wrapper noise
**Location**: `src/prc/presentation/card.py:19-39`, `src/prc/presentation/comment.py:32`, `src/prc/presentation/card.py:80`, `src/prc/explainer/preflight.py` (`_post`)
**Finding**: `card.py` has seven separate `from prc.facts import …` blocks with `CHANGED as CHANGED` re-exports; `comment.py` redefines `CHANGED` locally at line 32 while importing `TEST_NOTE`/`compute_facts` from facts two lines above; `_test_paths(brief)` is a one-line wrapper for `test_paths({}, brief)`; `preflight._post` duplicates `diffrows.prepare`'s per-row transform.
**Evidence**: Static trace; verified by grep. Same constant maintained in two places, and four one-hop indirections add reader load without behavior.
**Suggestion**: Collapse the import blocks, import `CHANGED` from facts in comment.py, inline `_test_paths`, and reuse `diffrows.prepare` in preflight.

### 8. [nit] Stale test docstring names removed behavior
**Location**: `tests/test_release_package.py:1`
**Finding**: The module docstring still says "including untracked local files", but 79407d2 removed exactly that behavior from the package contract.
**Evidence**: Docstring vs the test body at 6dbb336; the suite no longer packages untracked files. Misleads the next reader about what the tests pin.
**Suggestion**: Update the docstring to the current archive contract.

### 9. [nit] verify.yml double-runs PR branches and rebuilds the uv cache every run
**Location**: `.github/workflows/verify.yml:4-5,20,24`
**Finding**: `on:` triggers both `push` and `pull_request`, so PR branches run the whole verify suite twice per push; `brew install ffmpeg tesseract` runs on every job; `UV_CACHE_DIR=$(mktemp -d)` discards the default cache the preceding `uv sync` already populated.
**Evidence**: Workflow lines as cited; each open PR costs two full macOS jobs with fresh tool installs and a full package re-download.
**Suggestion**: Trigger on `pull_request` only (or `push` for the default branch only), and reuse a cached `UV_CACHE_DIR` keyed on the lockfile.

Suggested next step: bundle findings 1–3 into one shippable verify-contract PR — fresh success pointer, index-content copy, and safe numstat pathspec handling with tests for each — rather than three micro-fixes.
