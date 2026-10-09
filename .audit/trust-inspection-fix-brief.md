# Brief: five regression fixes from the final acceptance inspection

Read these skills in full before you start: /Users/koval/.codex/plugins/cache/pstack-claude/pstack/0.9.79/skills/poteto-mode/SKILL.md, /Users/koval/.codex/plugins/cache/pstack-claude/pstack/0.9.79/skills/tdd/SKILL.md and /Users/koval/.codex/plugins/cache/pstack-claude/pstack/0.9.79/skills/principle-test-behavior-not-implementation/SKILL.md.

Workdir: /Users/koval/dev/prc/.claude/worktrees/readiness (branch feat/trustworthy-pr-explanations). You are not alone in this checkout. The lead edits PLANS.md, docs/, .audit/ and artifacts/. Do not touch them. Do not run git add, git commit, git push, or any git command that writes. Do not install anything and do not run playwright install. Chromium is available with PLAYWRIGHT_BROWSERS_PATH=/Users/koval/dev/prc/artifacts/release/browser-cache.

Write scope. Edit only these files:
- src/prc/facts.py
- src/prc/explainer/doc.py
- src/prc/explainer/preflight.py
- src/prc/explainer/assets/engine.css
- src/prc/explainer/assets/doc.css (only if code spans in prose need a style)
- tests/test_trustworthy_facts.py, tests/test_card_comment.py, tests/test_changemap.py, tests/test_explainer_doc.py, tests/test_trust_render_preflight.py

Cadence for each defect. Write the failing test first. Run it and keep the failure output. Quote the assertion diff, not the assertion line. Then make the smallest fix and run the test again. Fix the root cause named below. Do not add guards around symptoms.

## D18. Wrong coverage verdict when no live change has test evidence

Observed. The em#5756 card, comment.md and map.html say "No direct test evidence in this map for some live changed production symbols." All 3 of its 3 live changed production symbols lack direct test evidence.
Root cause. compute_facts in src/prc/facts.py uses the "some" sentence whenever missing is non-empty. missing comes from untested() and is always a subset of live_prod.
Required behavior. When every live changed production symbol lacks direct test evidence, the verdict is exactly "No direct test evidence in this map for any live changed production symbol." Keep the "some" sentence when only part lacks evidence. Leave the other verdict branches unchanged.
Tests. Add one case where all live changed production symbols lack evidence. Assert the "any" sentence on facts.test_verdict and in the rendered card HTML and comment. Add one case where only part lacks evidence and assert "some". tests/test_changemap.py near line 504 asserts "some" for a case whose only live changed symbol is untested. That expectation encodes the defect, so change it to the "any" sentence. tests/test_card_comment.py near line 886 (crowded_card_map) also asserts "some". Find out whether all or only part of its live production symbols lack evidence, and set the expectation the required behavior gives. Do not weaken any other assertion.

## D19. Walkthrough captions show raw Markdown backticks

Observed. librarySync#98 doc.html scene 4 shows "`select_next_episode` now finds the last watched episode in the list." with literal backticks. Scenes 5, 6 and 7 do the same.
Contract. src/prc/explainer/assets/BOARD.md says "Text in backticks shows as code in the caption and is read without the backticks". The video caption formatter at src/prc/explainer/assets/engine.js line 16 is: const fmt = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
Root cause. _scene_section in src/prc/explainer/doc.py renders captions with html.escape only.
Required behavior. Doc prose applies the same rule as fmt. Escape first, then turn each backtick pair into <code>...</code>. An unpaired backtick stays literal, as in fmt. Hostile text stays escaped (see test_hostile_text_cannot_break_doc).
Tests. In tests/test_explainer_doc.py, a board sentence with a backticked name renders as <code>name</code>, and the prose text has no backtick. Update test_prose_is_board_sentences and test_doc_adds_no_new_claims only as far as the contract requires. The prose text must equal the show text with the backtick pairs removed.

## D20. The sign of a wrapped diff row sits between its visual lines

Observed. librarySync#98 line 132 and em#5756 line 24, in doc.html and in the video frames. The line number is on the first visual line. The + sign is centred across both lines.
Root cause. In src/prc/explainer/assets/engine.css, .drow has align-items: center and .drow .ln has align-self: flex-start. .drow .sg has no override.
Required behavior. The sign sits on the first visual line, like the line number. Single-line rows do not move.
Test. Extend the real-browser harness in tests/test_trust_render_preflight.py (see test_wrapped_diff_fits_in_real_browser and wrapped_change()). For each wrapped row, the vertical centre of .sg must lie on the first visual line of .ct, within 2 px of row top plus half the line height. For single-line rows the sign centre must equal the text line centre within 2 px. Save the bounds JSON and a screenshot under artifacts/e2e/ like the existing test.

## D21. "Changed lines not shown" lists removed lines in descending order

Observed. The swarm-deploy#116 doc.html lists file.go#L178 (removed), #L171 (removed) and so on down to #L81 (removed), then the added lines in ascending order.
Root cause. line_coverage in src/prc/explainer/preflight.py sorts missing by (path, signed n), and removed lines have negative n.
Required behavior. Within each path, list removed lines in ascending order, then added lines in ascending order. The removed group stays first, as today. The prc board coverage output follows the same order.
Test. Use a map with several removed and added lines that the board does not show. Assert the exact order of line_coverage(...)["missing"] and of the doc's "Changed lines not shown" labels.

## D22. Receipt labels hide which side a line is on

Observed. The swarm-deploy#116 scene 3 receipts show "internal/compose/file.go#L77" twice. One links to the head commit (a context line). The other links to the base commit (a removed line). The "Changed lines not shown" list already labels base lines with " (removed)".
Root cause. _scene_section in src/prc/explainer/doc.py builds the receipt label from path and n only, and drops removed.
Required behavior. Receipt labels for removed lines end with " (removed)", exactly as in _not_covered. Links do not change.
Test. Use a diff scene with a context row and a removed row that share a line number. Assert two receipts with distinct labels and the base and head hrefs.

## When done

Run these from the workdir with the PLAYWRIGHT_BROWSERS_PATH above: uv run pytest -q; uv run ruff check .; uv run ruff format --check .; uv run mypy

Final answer. For each D-number give the test names, the quoted failing output (the assertion diff), the passing output and the changed file paths. List every expectation you changed in an existing test, and say why. Do not commit.
