# Independent interrogate review (glm-5.3-flash)

Worktree: /Users/koval/dev/prc/.claude/worktrees/paired-evaluation (feat/paired-pr-evaluation).
Review surface: git diff --cached plus git diff for src/prc/evaluation/{kit,session,assets,io,__init__}.py, src/prc/cli.py, src/prc/explainer/highlight.py, scripts/prepare_paired_materials.py, and tests under tests/test_paired_*.py, tests/test_prepare_paired_materials.py, tests/test_explainer_highlight.py.
No code was edited, nothing was committed or pushed, and nothing under artifacts/paired-study/private was opened. The only file written is this report.

## Verification commands used

- Test sweep on the final sources: PYTHONPATH=src /Users/koval/dev/prc/.claude/worktrees/readiness/.venv/bin/python -m pytest tests/test_explainer_highlight.py tests/test_paired_kit.py tests/test_paired_session.py tests/test_paired_regressions.py tests/test_paired_grading_session.py tests/test_prepare_paired_materials.py -q -> 81 passed in 17.81s.
- Reviewed source hashes: kit.py 25570e30..., session.py 20f9af63..., assets.py e61661a8....
- The parent review's three blockers are confirmed resolved in this tree: a Lens entry page is required (kit.py:129), MC credit is derived from the frozen key with blank rejection (kit.py:799-805), and the shared answer-save queue recovers after a failed save (tests/test_paired_browser.py).
- All repros below are fixture-only probes built on tests/paired_builder.py; no real study material was touched.

## Held areas (checked, no findings)

A. Seal coverage of roster, artifacts, questions, keys, assignment - payload study_data covers the roster (snapshot metadata with pr_identity), per-snapshot/tool artifact tree hashes, frozen questions with keys, evaluator_versions, assignment draws, card permutation, per-pair reading order, and the opaque trial map (kit.py:501-611). load_study verifies the digest (kit.py:653-657), compares study.json top-level questions/snapshots/assignment against the frozen payload (kit.py:658-660), enforces session.json order and trials (kit.py:661-666), and recomputes tree hashes on disk (kit.py:668-671).

B. Condition assignment and reading order derive from the recorded seed - one PCG64 stream draws assignment coins, exposure coins, then the shuffle (protocol.py:127-176); product_first drives per-pair reading order with adjacent trials (kit.py:495-505).

C. One aid per PR, one PR of each pair in each condition - each pair contributes exactly two trials, one per snapshot, split by the assignment coin (kit.py:539-573). Duplicate identities, even at a different head, are rejected (tests/test_paired_kit.py:26-58).

D. Old-tab isolation - artifact GETs are bound to the active trial id (session.py:518-528); save_answers/submit/abort reject a stale trial id (session.py:213-228, 277-295); POST origin and Host checks are exact (session.py:437-442). tests/test_paired_regressions.py::test_old_tab_cannot_save_or_finish_a_new_reading covers the sequence.

E. Deadline bypass - every state read, save, finish, and close first runs _sweep_deadline, which converts an expired active trial to timed_out with ended_at = started_at + DEADLINE_SECONDS and clears active_trial (session.py:101-114); a submit after the sweep refuses with 'no active trial to finish'. I probed sweep boundary timing with a patched clock; no bypass surface. Server clock only; refresh does not pause the timer.

F. Unknown or exposed outcomes dropped from analysis - pending trials, including ineligible familiar PRs, stay state unknown in apply_scores (kit.py:821-828); aborts keep aborted=true; cross-exposure reports and ineligible reasons survive in deviations (kit.py:846-866), verified in tests/test_paired_regressions.py and tests/test_paired_kit.py.

G. Multiple-choice scoring against the exact frozen key - apply_scores recomputes expected as (saved answer == key) and rejects any off-key award (kit.py:801-805); blanks must score 0 (kit.py:799-800). Covered by tests/test_paired_regressions.py::test_wrong_multiple_choice_cannot_receive_full_credit; the browser sheet computes the same value so a hand-edited wrong score is rejected.

H. Path traversal and symlink escape in artifact serving - _resolve_allowed resolves the request against the active-tree root and fail-closes outside it (session.py:401-411); /artifact/{trial}/github/../../study.json returns 404; the tree-symlink check recurses via rglob over every nested path (kit.py:415-422); copies dereference symlinks (copytree default).

I. HTTP Range handling - probed live: bytes=0- on 1-byte body gives 206 'bytes 0-0/1'; bytes=-0 gives 416; bytes=-5 on 1-byte body gives 206 with the whole body (suffix longer than size selects all, per RFC 7233); bytes=0-0 gives the first byte; bytes=1000-99999 on a 1024-byte file clamps to the 24-byte tail 206; bytes=1-3 on a 1-byte file gives 416. Clamping and unsatisfiable-range behaviour match RFC 7233; the seek path is covered by tests/test_paired_session.py::test_artifact_range_request_lets_the_browser_seek_video.

J. Lens page builder leaves no remote images and never substitutes bytes that mismatch the captured hash - lens_page refuses uncaptured remote render URLs, swaps in local captured assets only after verifying sha256(asset bytes)[:32] equals the content-addressed name, dark-source variants are stripped, surviving remote img tags are replaced with alt-text spans (scripts/prepare_paired_materials.py:57-73), covered by tests/test_prepare_paired_materials.py:59-137. No remote URL survives in the built page (verified on the fixture output).

K. CRLF highlight remap aligns byte-for-byte - classes_pyg walks the canonical bytes, gives the CR of each CRLF an empty class, and consumes one lexed entry per remaining byte (src/prc/explainer/highlight.py:91-110). Pygments normalizes CRLF and lone CR before lexing (verified in the installed pygments lexer.py:240-241), so consumed counts match. The bounds guard prevents overrun; test_explainer_highlight.py::test_crlf_file_highlights_every_line_in_place fails on any off-by-one.

L. CLI surface (cli.py eval-*) and io.py - eval-prepare/session/export/grade route the kit and session errors verbatim; io.load_pairs_with_protocol preserves the legacy 12-pair path while new results carry the sealed protocol. No defect.

## Findings

### Finding 1 (P1) - preparation accepts an unverified Lens rendered page

Defect: kit.py:129 checks the lens tree only for the existence of index.html. The hash the kit pins is the comment body sha256 (kit.py:520-523, field lens_body_sha256), and the live recheck in _verify_live (session.py:391-394) also only compares the live comment body. The served aid page /artifact/<trial>/aid/index.html is never compared with the captured comment contents or pinned by hash, unlike the PRC page which is pinned via prc.output_hash (kit.py:226-238).

Failing scenario (reproduced on fixture materials): build_manifest(pairs=1); overwrite lens tree index.html with fabricated text; kit.prepare_study(manifest, study) succeeds. Rebuilding the same fixture twice with different lens/index.html bytes and an unchanged manifest also both succeed, so a fabricated or drifted baseline aid enters the study sealed as if genuine.

Fix: record the Lens entry page sha256 in the manifest snapshot metadata and verify it in prepare/load the way prc output_hash is verified.

### Finding 2 (P2) - artifact serving is not constrained to the pinned file envelope

Defect: serving under /artifact/<active trial>/{github,aid}/... resolves any file inside the active snapshot tree whose suffix is allow-listed (session.py:545-552 plus session.py:401-408), but preparation never restricts the tree to the pinned envelope (lens: index.html + svg_files + check and comment records; prc: index_path + map.json). A nested directory inside the active trial's aid tree is reachable and served.

Failing scenario (reproduced): build_manifest(pairs=2); inside the second pair's snapshots write nested/notes.json containing the snapshot identity; prepare and serve; start the second-pair trial; GET /artifact/<active trial>/aid/nested/notes.json returns 200 with the other reading's PR identity. Earlier probes failed only because the random reading order activated the first pair, whose tree lacked the file; with nesting present in the active tree the leak triggers deterministically.

The resolved candidate path stays inside the active snapshot tree, so this is not traversal; the integrity risk is serving stray or unsealed content (including another PR's identity smuggled into a captured tree). Fix: prepare-time reject of files outside the pinned envelope, or a serving allow-list derived from the manifest.

## Recorded, not findings

1. session.py:352-361 preview() exposes the next PR's identity, title, and head_sha before timing starts - intentional familiarity gate per docs/design/paired-evaluation-v2.md:45-52; keys are not exposed.
2. session.py:47-50 _atomic_write_json writes session.tmp without a unique suffix - hardening note only; the single-writer flock (session.py:71-82) currently serializes writers.
3. seals: nothing under artifacts/paired-study/private was read; fixtures carry display-only identities.

## Verdict

Two findings stand: one P1 (unverified Lens entry page, Finding 1) and one P2 (unconstrained nested serving, Finding 2). Every other requested hunt area checked clean. 81 tests pass on the final sources; the parent report's blockers are resolved in this tree.

