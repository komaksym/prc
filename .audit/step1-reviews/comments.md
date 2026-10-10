**TL;DR:** The final comment pass is complete at `e262626`. Deleted 20 comments/docstrings across 11 files and kept five public contracts. The 75 requested tests, parent Ruff, and patch checks pass. Three `MUST KILL` targets remain for a separate implementation pass.

Clone: `/private/tmp/step1-comments-final`. HEAD: `e26262691ac34aca40438087e1a511653e90ebab`. The checkout started clean and remains at the same commit.

Scope: comments/docstrings added or modified by `git diff 972756e..e262626` in `src/`, the two named scripts, and `tests/*.py`. The vendored bundle and all fixture paths were excluded from comment review and edits.

Counts: 25 scoped blocks reviewed; 20 deleted; five public contract blocks kept; three flags. The patch deletes 24 comment/docstring source lines plus 11 blank lines. It adds no lines.

Touched files:

| File | Deleted blocks | Deleted lines, including whitespace |
| --- | ---: | ---: |
| [scripts/vendor-prlens.mjs](/private/tmp/step1-comments-final/scripts/vendor-prlens.mjs) | 1 | 1 |
| [scripts/verify_prlens_vendor.py](/private/tmp/step1-comments-final/scripts/verify_prlens_vendor.py) | 2 | 3 |
| [src/prc/presentation/graphdoc.py](/private/tmp/step1-comments-final/src/prc/presentation/graphdoc.py) | 8 | 14 |
| [src/prc/presentation/infographic.py](/private/tmp/step1-comments-final/src/prc/presentation/infographic.py) | 1 | 2 |
| [src/prc/presentation/render_map.py](/private/tmp/step1-comments-final/src/prc/presentation/render_map.py) | 1 | 2 |
| [tests/pngcheck.py](/private/tmp/step1-comments-final/tests/pngcheck.py) | 1 | 2 |
| [tests/test_e2e_infographic.py](/private/tmp/step1-comments-final/tests/test_e2e_infographic.py) | 2 | 3 |
| [tests/test_graphdoc.py](/private/tmp/step1-comments-final/tests/test_graphdoc.py) | 1 | 2 |
| [tests/test_infographic.py](/private/tmp/step1-comments-final/tests/test_infographic.py) | 1 | 2 |
| [tests/test_map_browser.py](/private/tmp/step1-comments-final/tests/test_map_browser.py) | 1 | 2 |
| [tests/test_render_map.py](/private/tmp/step1-comments-final/tests/test_render_map.py) | 1 | 2 |

Keeps:

- `Plotted` in [src/prc/presentation/graphdoc.py](/private/tmp/step1-comments-final/src/prc/presentation/graphdoc.py:69). Defines how public index maps refer to the input map.json collections.
- `groups_of` in [src/prc/presentation/graphdoc.py](/private/tmp/step1-comments-final/src/prc/presentation/graphdoc.py:192). Defines the grouping threshold, members, folder fallback, and stable order.
- `picked_steps` in [src/prc/presentation/graphdoc.py](/private/tmp/step1-comments-final/src/prc/presentation/graphdoc.py:255). Defines the public None sentinel for overview and summary steps.
- `page_data` in [src/prc/presentation/render_map.py](/private/tmp/step1-comments-final/src/prc/presentation/render_map.py:59). Defines the public payload contents used by the page renderer.
- `data_block` in [src/prc/presentation/render_map.py](/private/tmp/step1-comments-final/src/prc/presentation/render_map.py:100). Defines the escaping guarantee for embedding JSON in a script element.

The embedded MIT license comment generator in [scripts/vendor-prlens.mjs](/private/tmp/step1-comments-final/scripts/vendor-prlens.mjs:159) also survives the legal exception. It is separate from the 25 parsed prose blocks. The Node shebang remains an executable directive.

`MUST KILL` flags. These identify targets only. No application code was changed:

- `MUST KILL` `_select` at [src/prc/presentation/graphdoc.py](/private/tmp/step1-comments-final/src/prc/presentation/graphdoc.py:236). The private name hides node-budget allocation, risky-file precedence, and three positional result collections. Encode that selection policy through named results or an explicit selection name.
- `MUST KILL` `_order_edges` at [src/prc/presentation/graphdoc.py](/private/tmp/step1-comments-final/src/prc/presentation/graphdoc.py:276). The private function also filters and caps edges, then selects a hero index. Rename the selection or extract the hero choice so the extra responsibility is visible.
- `MUST KILL` `render_lines_png` at [tests/test_e2e_infographic.py](/private/tmp/step1-comments-final/tests/test_e2e_infographic.py:50). The generic renderer owns OCR-oriented Georgia and tracking choices inside an unnamed CSS string. Name the OCR test styling. The removed claims about exact OCR failures lack live proof today.

The `how` investigation traced `render_lines_png`, its callers, and the Tesseract gate. The two exact OCR failure claims have no live proof today. Georgia and tracking belong to the test CSS. The note was deleted under the doubt-means-delete rule.

Proof:

- Before edits: 75 tests passed in 2.97s; parent Ruff passed.
- After edits: 75 passed in 3.25s; parent Ruff 0.16.10 passed over all 19 existing scoped Python files.
- Python ASTs match HEAD for all 10 edited Python files after documentation nodes are removed.
- The vendor script is byte-identical after its one authorized comment line is removed.
- Every deletion is an approved diff comment/docstring or adjacent whitespace. All 46 unchanged context blocks remain byte-identical.
- All five retained contracts and the generated legal header remain byte-identical.
- `git diff --check` and `git apply --reverse --check` pass. The index is clean and HEAD is unchanged.
- `.git` and the Git common directory both belong to this isolated clone.

Import checks:

- `prc` imports `/private/tmp/step1-comments-final/src/prc/__init__.py`.
- `prc.presentation.graphdoc` imports `/private/tmp/step1-comments-final/src/prc/presentation/graphdoc.py`.
- `prc.presentation.infographic` imports `/private/tmp/step1-comments-final/src/prc/presentation/infographic.py`.
- `prc.presentation.render_map` imports `/private/tmp/step1-comments-final/src/prc/presentation/render_map.py`.

Commands ran from `/private/tmp/step1-comments-final`. Python commands also set `PYTHONDONTWRITEBYTECODE=1`:

```sh
PYTHONPATH=src /Users/koval/dev/prc/.claude/worktrees/readiness/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_infographic.py tests/test_infographic_pipeline.py tests/test_graphdoc.py tests/test_render_map.py
/Users/koval/dev/prc/.claude/worktrees/readiness/.venv/bin/ruff check --no-cache scripts/verify_prlens_vendor.py src/prc/cli.py src/prc/explainer/doc.py src/prc/explainer/doctor.py src/prc/pipeline.py src/prc/presentation/comment.py src/prc/presentation/graphdoc.py src/prc/presentation/infographic.py src/prc/presentation/render_map.py tests/pngcheck.py tests/test_e2e_infographic.py tests/test_e2e_map.py tests/test_explainer_doc.py tests/test_graphdoc.py tests/test_infographic.py tests/test_infographic_pipeline.py tests/test_map_browser.py tests/test_map_video.py tests/test_render_map.py
git diff --check
git apply --reverse --check /private/tmp/step1-comments-final.patch
```

Artifacts:

- [Patch](/private/tmp/step1-comments-final.patch). SHA-256: `92b2b8e0701d0d2618bae18ee994753c50da462cdcaf798c60954cf7669a1572`.
- [Machine-readable proof](/private/tmp/step1-comments-final-proof.json). Includes each deletion, keep, flag, file hash, and command.
- [Pytest output](/private/tmp/step1-comments-final-tests.log).
- [Ruff output](/private/tmp/step1-comments-final-ruff.log).

Skips: vendored minified bundle; all fixture review and edits; deleted files; unchanged comment context; full suite; browser; video; typecheck; build. The requested logic tests may read existing fixture inputs. No fixtures were changed. No commits, pushes, or PRs were made.

All source edits remain uncommitted in this clone. No parent checkout or other clone was edited.

**Next step:** Integrate this comment patch. Handle the three named targets in one scoped GraphDoc and OCR test readability pass.
