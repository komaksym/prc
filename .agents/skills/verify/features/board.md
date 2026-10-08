# Board tools

A board writer finds changed code, measures coverage, and checks a story before rendering it.

## Sub-features

- `board-guide` prints current writing rules.
- `board-show` displays captured code.
- `board-find` locates named code.
- `board-coverage` reports quoted changes.
- `board-check` validates receipts and animation cues.

## How to get to it (user POV)

Run `prc board guide`, `show`, `find`, `coverage`, or `check`.
Use `--source fixture:shop` or a captured `--map`.

## Driving it with CLI and Playwright

Preconditions: shop fixture and `tests/data/boards/shop.json` exist. These commands need no browser.

- Run `.venv/bin/python -m prc.cli board guide`. Save stdout and require type and cue rules.
- Run `.venv/bin/python -m prc.cli board show --source fixture:shop --store "$VERIFY_STORE" src/shop/cart.py`. Require checkout code.
- Run `.venv/bin/python -m prc.cli board find --source fixture:shop --store "$VERIFY_STORE" apply_discount`. Require changed call or definition.
- Run `.venv/bin/python -m prc.cli board coverage --source fixture:shop --store "$VERIFY_STORE" tests/data/boards/shop.json`. Save its report.
- Run `.venv/bin/python -m prc.cli board check --source fixture:shop --store "$VERIFY_STORE" tests/data/boards/shop.json`. Require successful exit and verified receipts.
- Copy the shop board to `VERIFY_PROOF/invalid-board.json`. Remove the stats scene's first `card` cue.
- Run the same `board check` command against that copy. Save stdout, stderr, and the exit code.
- Require exit code 2 and stderr containing `card 0 needs a reveal cue`.
- Repeat with a fresh board copy. Set its groups scene's first cite `match` to `missing_verification_quote`.
- Require exit code 2 and stderr containing `missing_verification_quote` and `is not on that line`.
- Preserve both invalid inputs and transcripts. `tests/test_explainer_check.py` provides additional checker coverage.

## Gotchas

- Preserve the original board when comparing runs.
- A successful check does not replace semantic source review.
