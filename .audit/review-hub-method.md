# Review hub correction, 2026-10-11

Summary: the live acceptance hub separates artifact acceptance from a future matched PR study.
The three exposed packets support quality acceptance only. Each scored PR must be unseen
and read once in its assigned condition. The study size, questions, timing rules, and comparison
arms remain to be reconciled and frozen. No study roster or scored run was created.

## Changes

The builder writes separate navigation and instruction sections in light mode.
Acceptance decisions are accepted, changes requested, or deferred. GitHub is an optional fact-check.
The worksheet migration preserves case findings and answered old ratings as legacy notes.
Those notes do not count as study scores. Pending score prompts are removed.
The launch document retires its old GitHub-first flow. The method document records how to rebuild.

## Verification

Proof folder in the readiness checkout: `artifacts/verification/review-hub-method`.

- `tests/test_review_hub.py` exercises the real builder through subprocesses.
  The old builder failed all three tests. The first migration also lost answered ratings.
  That regression now passes, including byte-identical worksheet regeneration.
- `pytest tests/test_review_hub.py tests/test_rebuild_acceptance.py -q`: 4 passed.
- `ruff check .`, `ruff format --check .`, and strict `mypy`: passed.
- Full `pytest -q`: 992 passed, zero failures, errors, or skips. Result is `tests.xml`.
- `uv build`: wheel and source distribution passed. Files are in the proof folder's `dist` directory.
- `verify-review-hub.py`: 13 browser screenshots. Both sections, worksheet, agent evidence,
  map, walkthrough, three muted inline videos, and mobile layout passed without page errors.
- `integrity.json`: all 1,573 packet-file hashes unchanged, all 47 original links retained,
  and no missing local links. `regeneration.json`: live hub and worksheet remain byte-identical after rebuilding.

The initial sandboxed full test run could not launch Chromium due to macOS permission errors.
The final full run used the same cached Chromium outside the sandbox. No browser download occurred.
Existing videos and infographics were not regenerated. Browser playback was muted.
The agent inspection statement links to the earlier requirement audit; this change does not claim a new content review.

## Remaining boundaries

Independent GLM Flash review found one stale scoring sentence in the launch notes.
It is corrected. The review found no other actionable defect. The parent removed duplicate test assertions.

Human acceptance remains pending. The review method is documented, but the scored study is not prepared.
The existing D21 gate keeps push, PR creation, and publication separate from this local correction.
Routing correction is owned by separate work.
