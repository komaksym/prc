# Atomic explain publication design

TL;DR: Render a complete new artifact in a private directory before publication. Prefer design A for the smallest compatible fix.
Design A preserves the previous artifact after handled failures, subject to successful rollback.
Design B provides an atomic pointer switch, but changes the output directory into a symlink.
Do not describe design A as crash-safe or continuously available.

## Scope and status

This is a read-only design sketch, written on 2026-10-07.
Only this audit document changes. No implementation or tests belong to this work unit.
The parent owns failing E2E tests and the independent reviewer.
The designs below are proposals, not verified product behavior.

Throughput checkpoint: n/a, read-only investigation.
Exploration used two labelled sequential passes because no subagent slots were available.
The comparison is one author's analysis, not an independent cross-judge verdict.
Independent review remains pending with the parent.
The working tree already contains product changes. Line references describe the inspected working copy.

The architect phases are recorded here.

- [x] Ground. Trace callers, writers, and existing output contracts.
- [x] Sketch. Compare two structurally distinct publication designs.
- [x] Agree. Record a recommendation within the requested design scope.
- [ ] Implement. Skip because the user requested no implementation.
- [ ] Scrap. Skip because no implementation exists to reconcile.

The arena phases are recorded here.

- [x] Frame. Fix the requirements and comparison criteria.
- [x] Fan out. Substitute labelled sequential passes A and B.
- [ ] Cross-judge. Pending with the parent's independent reviewer.
- [x] Pick. Prefer A for handled failures and compatibility.
- [x] Graft. Adopt complete-generation membership and explicit path separation.
- [x] Verify. Check source evidence and filesystem assumptions. Product tests remain with the parent.

## Problem and traced model

[`run_explain`](/Users/koval/dev/prc/src/prc/pipeline.py:478) owns output orchestration.
[`explain_slug`](/Users/koval/dev/prc/src/prc/pipeline.py:366) selects a stable directory using the PR and twelve head characters.
The same head therefore selects the same directory on every rerun.

The current write sequence has these effects.

1. `load_map_dict` selects the stored or live map. `select_voice` selects the backend.
2. Lines 496-499 create the published directory and overwrite `map.json` and `map.html`.
3. Lines 514-518 read and validate the board. Invalid boards raise `ExplainCheckError` after the map writes.
4. Lines 528-542 render media, write the filled board, and write the document.
5. Lines 544-576 write the card, comment, and run metadata. `CardError` becomes a warning.
6. Lines 578-592 return paths in `ExplainResult`.

[`render`](/Users/koval/dev/prc/src/prc/explainer/render.py:256) writes more than `video.mp4`.
It writes `audio/`, `tokens_s*.json`, optional `phrases.json`, `narration.wav`, `player.html`, and `keys/`.
It mutates the board with filled scene data and timings before the pipeline serializes the board.
[`fit_sentences`](/Users/koval/dev/prc/src/prc/explainer/timing.py:107) removes transient clip paths before serialization.
[`render_doc`](/Users/koval/dev/prc/src/prc/explainer/doc.py:186) writes `doc.html` beside a relative `video.mp4` link.
These functions already accept an output directory. They need no publication knowledge.

A render failure can leave partial media beside new maps and old metadata.
A boardless rerun skips all board and media writes, but deletes none of the previous files.
The returned optional paths become `None` while stale files remain accessible.
A failed card screenshot can also leave an old `card.png` beside a warning that reports no card.

[`_write_bundle`](/Users/koval/dev/prc/src/prc/pipeline.py:248) is unsuitable without broader changes.
Its replacement mode deletes the previous directory before the rename.
It also catches rename errors and returns a path without proving publication succeeded.
Keep this helper and its unrelated callers outside the proposed fix.

## Usage and outcome contract

Keep the existing `run_explain` signature, `ExplainResult` fields, and `explain_slug` unchanged.
Keep the CLI flags and JSON keys in [`main`](/Users/koval/dev/prc/src/prc/cli.py:278) unchanged.
Keep the head-based path and filenames unchanged.
Preserve relative paths when the caller supplies a relative `out_root`.

These existing calls retain their caller contract.

```python
result = run_explain(source, ref, clock, policy, out_root, board_path=board_path, voice="none")
assert result.video == result.out_dir / "video.mp4"

result = run_explain(
    source, ref, clock, policy, out_root, map_path=stored_map, board_path=board_path, voice="none"
)
assert result.map_json == result.out_dir / "map.json"

result = run_explain(source, ref, clock, policy, out_root, voice="none")
assert result.board_json is result.video is result.doc_html is None
```

Success publishes exactly the files produced by this invocation.
Boardless success publishes maps, card HTML, an optional card PNG, the comment, and run metadata.
Its published directory contains no previous board, video, document, audio, player, keys, phrase log, or token files.
Remove stale media by replacing the complete artifact, rather than maintaining a deletion list.
Treat the head directory as pipeline-owned. Preserve no manually added files during successful replacement.

Before publication, any fatal validation, render, document, comment, or metadata error preserves the previous published artifact.
The previous artifact includes file membership and file bytes, including `run.json`.
With no previous success, a failed invocation leaves no public head directory.
Preserve the current `ExplainCheckError` conversion and nonfatal `CardError` policy.
Unexpected exceptions remain fatal. Publication errors must propagate.

All returned paths and path-valued `run.json` fields name the public directory.
Temporary paths must never appear in `doc`, `card`, `comment`, or returned paths.
Keep `run.json.board` as the original input path.
Keep existing map semantics, rebuilt brief signals, voice timing, and stored-map head metadata.

## Shared preparation changes

Both candidates keep generation in `pipeline.py` and reuse the existing renderers.
No new production dependency, public type, renderer parameter, or module is necessary.

The exact proposed changes to `run_explain` are as follows.

1. Keep `out_dir = out_root / slug` as the public path. Stop creating or writing that directory during preparation.
2. Read and validate the board before artifact writes. Preserve validation against `used`, not the rebuilt presentation map.
3. Create a unique private `work_dir` on the same filesystem as `out_dir`.
4. Redirect map writes, `explain_render.render`, board serialization, and `render_explain_doc` to `work_dir`.
5. Redirect card HTML, card PNG, comment, and `run.json` writes to `work_dir`.
6. Pass the staged `card.html` path to `render_pr_card_png`. Its browser must read the new HTML.
7. Keep result variables such as `board_out`, `video`, and `doc_out` rooted at `out_dir`.
8. Serialize public paths into staged `run.json`. Do not serialize renderer write paths.
9. If `CardError` occurs, remove any partial staged `card.png` and set the returned card path to `None`.
10. Prepare the complete `ExplainResult` before publication. Return that result only after publication succeeds.

Preserve the renderer's mutation order. Write the board and document after `explain_render.render` returns.
Do not use file-by-file replacement or copy files into the existing public directory.

## Sequential pass A. Staged directory with rollback

### Shape

The public head path remains a real directory.
A fresh sibling directory holds the whole candidate artifact.
A unique backup directory holds the old artifact during the commit.
One private helper owns publication and rollback.

The proposed private signature is `_publish_explain(staging: Path, out_dir: Path) -> None`.
Keep it in `pipeline.py`, beside `run_explain`.
Its invariant is complete-directory replacement with explicit error propagation.
Do not create a generic transaction class or separate methods for begin, commit, and rollback.
The caller delegates one operation and needs no backup details.

### Exact publication protocol

1. Use `tempfile.TemporaryDirectory` under `out_root` for `.explain-staging-*`. Render the entire invocation inside its context.
2. Acquire an exclusive commit lock with an atomic `mkdir` at `out_root / f".explain-{slug}.lock"`.
3. If the lock exists, fail before changing the public directory. Do not guess whether the lock is stale.
4. Create a unique `.explain-backup-*` container under `out_root` using `tempfile.mkdtemp`.
5. If `out_dir` exists, rename it to the container's `previous` child. Never delete it before this rename.
6. Rename the completed staging directory to `out_dir`. This successful rename is the commit point.
7. If step 6 raises, rename `previous` back to `out_dir`, then propagate the publication error.
8. If restoration also fails, retain `previous` and report its path with both errors. Never clean that backup automatically.
9. After commit, remove the backup and release the lock. Cleanup failures must not turn committed success into reported failure.
10. Before commit, clean only this invocation's staging and empty backup container. Never clean another invocation's directories.

The lock serializes only publication, so separate invocations can render independently.
Keep the lock through rollback. A concurrent publisher must not occupy the public path during restoration.
Use `Path.rename`, `tempfile`, and `shutil`. These are standard-library facilities already used in this file.
Post-commit cleanup can warn on stderr. It must not corrupt the CLI's JSON stdout.
Retain a lock after a process crash until explicit recovery. Automatic lock theft would invalidate rollback safety.

Reject a public symlink or unexpected file before moving the previous directory.
This candidate defines replacement of a pipeline-owned real directory.

### Rationale and limits

This is the smallest complete fix for handled rerun failures.
It changes output ownership in one function and adds one private publication helper.
Fresh staging removes every stale renderer file without a synchronized filename list.
The public API and real-directory layout stay stable.

The two renames are not one atomic filesystem operation.
Between them, readers can observe a missing head directory.
A process kill in that interval leaves the previous artifact in the backup, rather than at its public path.
Rollback cannot guarantee restoration if the filesystem also rejects the restore operation.
The helper preserves the old bytes for recovery in that case, but does not satisfy continuous public-path availability.
Power-loss durability would require a separate synchronization and recovery contract.

## Sequential pass B. Immutable generations with an atomic pointer

### Shape

Each invocation renders into a unique generation under `out_root / ".explain-generations" / slug`.
The public head path is a relative symlink to the selected generation.
Publication replaces that symlink in one filesystem operation.
Old generations remain untouched.

The proposed private signature is `_publish_explain_generation(generation: Path, out_dir: Path) -> None`.
Keep it in `pipeline.py`.
The helper hides relative-target calculation, temporary-link ownership, and replacement.
`ExplainResult` still contains the same public head paths.
The filesystem contract changes because `out_dir.is_symlink()` becomes true and `out_dir.resolve()` selects a generation.

### Exact publication protocol

1. Create the generation with `tempfile.mkdtemp` inside `out_root / ".explain-generations" / slug`.
2. Render everything there using the shared preparation changes.
3. Create a unique sibling temporary symlink with a relative target calculated from `out_dir.parent`.
4. Use a private `mkdtemp` container in that parent for the temporary symlink, avoiding a filename reservation race.
5. Replace the public symlink with `os.replace(temp_link, out_dir)`. This operation is the commit point.
6. If link creation or replacement fails, delete only the unpublished generation and temporary container.
7. After commit, retain the selected generation and all previously published generations.
8. Do not run automatic garbage collection in `run_explain`. Open readers may still use previous generations.

Import `os` for `os.replace` and `os.path.relpath`. This introduces no production dependency.
Concurrent invocations write distinct generations and links. The last successful pointer replacement selects the visible result.
A failed publisher cannot roll back another publisher's success.
The public path always selects an entire generation once this layout exists.

The pointer switch provides atomic lookup, not a snapshot across several separate file opens.
A reader can open an old map, then a new video after another commit.
Readers that need a multi-file snapshot must resolve the generation once and use that path.
Keep this limitation distinct from partial writes inside a selected generation.

### Existing real-directory migration

Portable `os.replace` cannot replace an existing nonempty real directory with a symlink.
Therefore design B needs an explicit legacy-output policy.
The smallest safe default is to refuse publication when the public path is a real directory.
The previous success remains untouched, but same-head reruns require migration before they can succeed.

A migration could move the old directory into the generation store, then install the public symlink.
That migration needs design A's lock and rollback protocol.
It has the same visibility gap and process-kill risk for the first conversion.
Do not advertise that conversion as atomic.
Strict atomic conversion needs platform-specific directory exchange support or a changed public path.
Neither belongs in the smallest portable fix.

### Rationale and limits

This candidate provides the stronger steady-state commit guarantee.
Handled errors and a process kill before pointer replacement leave the old public artifact selected.
Boardless publication selects a generation with no board media. Old media remains only in historical generations.
The public filenames and Python API stay stable, but symlink behavior, backups, and disk retention change.
Windows permissions and tools that reject symlinks need separate compatibility validation.
Atomic pointer replacement alone does not guarantee power-loss durability.

## Comparison and red-flag screen

The rubric uses five criteria. The table records concrete outcomes rather than unexplained numeric scores.

| Criterion | Design A | Design B |
| --- | --- | --- |
| Smallest complete diff | One redirected write directory and one rollback helper. A short commit lock is required. | Generation layout, pointer helper, legacy policy, and retention documentation increase scope. |
| Public API stability | Signature, result fields, JSON keys, lexical paths, and real-directory behavior remain stable. | Signature and lexical paths remain stable. Symlink and resolved-path behavior change. Legacy reruns need migration. |
| No new dependencies | Existing standard library only. | Standard library only, with an `os` import. |
| Failed rerun preserves previous success | Preparation failures preserve it. Commit failure restores it if rollback succeeds. Crash can require recovery. | Pointer-managed outputs keep the old generation selected until commit. Legacy conversion remains a separate risk. |
| Boardless removes stale media | Whole-directory replacement removes all previous media from the public artifact. | New pointer selects a generation without media. Historical media stays outside the selected artifact. |

Both candidates have a small private interface that hides publication complexity.
Neither adds public options for internal preparation stages.
Renderers write private directories. Only the pipeline publisher changes the public selection.
This prevents split ownership without moving rendering policy into a storage framework.
Whole-artifact replacement avoids hand-synchronized deletion lists.
Candidate A's weakness is its multi-step commit and recovery state.
Candidate B's weakness is its extra directory protocol and legacy compatibility policy.
Neither candidate should coexist with direct writes to the public directory.

## Synthesis decision

Use A as the base for the stated rerun defects and smallest compatible change.
Graft B's complete-generation membership rule and separation of private write paths from public result paths.
Reject B's symlink migration and retained-generation layout for this narrowly scoped fix.
Reject file-by-file replacement because failures can still expose mixed artifacts.
Reject validation-only reordering because renderer and metadata failures still modify the public directory.
Reject deletion of selected stale filenames because renderer auxiliary files also belong to the previous invocation.

The recommendation assumes that failure means a handled invocation failure, rather than process death or continuous reader availability.
If strict atomic public-path replacement is a hard requirement, choose B with an explicit legacy policy instead.
An A implementation must use the phrase "staged publication with rollback" in its documentation.
Calling two renames atomic would hide a material limitation.

The Laziness Protocol principle keeps the public API and renderer signatures unchanged.
The Exhaust the Design Space principle produced directory replacement and pointer replacement as distinct whole designs.
The Separate Before Serializing Shared State principle gives each invocation a private directory.
Only A's shared commit needs serialization. B replaces a pointer to already complete data.

## Proposed file changes and parent test contract

The future implementation has this bounded file scope.

- `src/prc/pipeline.py` redirects all explain writes to staging and adds the chosen private publisher.
- `tests/test_e2e_explain.py` adds rerun regressions through the CLI. The parent writes the failing tests first.
- `README.md` documents replacement semantics, boardless cleanup, and the selected failure guarantee.

No production changes are proposed for `cli.py`, the renderers, `ExplainResult`, `explain_slug`, or `_write_bundle`.
The parent can add isolated publisher tests where the real CLI cannot reliably inject filesystem errors.

The required behavior checks are as follows.

1. Produce a successful board artifact through `python -m prc.cli explain` with `fixture:shop` and `--voice none`.
2. Save a recursive filename and SHA-256 inventory of that artifact.
3. Rerun the same head with changed presentation input and an invalid board. Check exit code 2 and identical previous inventory.
4. Fail after maps would have been written, including render, document, and `run.json` failures. Check identical previous inventory.
5. Rerun the same head successfully without a board. Check refreshed maps and complete absence of previous media and auxiliary files.
6. Check that CLI JSON and `run.json` contain public paths with no private directory names.
7. Check `CardError` success separately. The warning remains, the card path is null, and no stale or partial card PNG exists.
8. Inject A's second-rename failure and restoration failure separately. Check restored output or retained recovery backup as specified.
9. Exercise competing publishers. A must refuse an occupied commit lock. B must preserve complete selected generations.
10. Retain recursive inventories, CLI outputs, and browser screenshots under `artifacts/e2e/explain/publication/`.

Inspect the successful document and card in the parent's background browser.
Use real screenshots and `ffprobe` for rendered output. A mocked publisher test cannot prove media rendering.
Before implementation closure, run the repository's lint, format, typecheck, tests, and build command from `README.md`.

## Verification and reconciliation

Source inspection traced every pipeline write and renderer output listed above.
A disposable Python filesystem experiment on this macOS host tested both publication assumptions.
`os.replace(new_nonempty_directory, old_nonempty_directory)` raised `OSError` with errno 66 and preserved the old marker.
Replacing a symlink selected the new marker while the old generation marker remained unchanged.
These observations verify local filesystem behavior, not crash safety or product E2E behavior.

No implementation, GUI checks, lint, typecheck, tests, or build ran for this design-only unit.
The parent retains those checks and the independent review gate.
No accepted implementation deviations exist. Record future accepted deviations in this same document.
The next implementation step is the parent's failing same-head CLI regression with a saved artifact inventory.
