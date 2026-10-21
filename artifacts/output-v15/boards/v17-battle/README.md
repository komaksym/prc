# Tuxemon double battle review

This review uses Tuxemon/Tuxemon #2370, "combat animation 2".
The head is 4dc3b4fb0dd61dde22e89e18d1db7215eb929a65.
The base is e3317587bcb3a48dae551a52ae3b6022e28e5131.

## Scope

The PR separates monster sprites in double battles and refactors battle helpers.
The Before and After screenshots come from the PR author. PRC did not run the game.
The before shot shows overlapping sprites; the after shot shows each pair in separate positions.
Both screenshots already show two status panels per side.

The board has nine scenes. Its reading path covers all sixteen changed units.
It uses the existing renderer and approved labsheet light look.

## Reproduce

Run from the repository root with the existing locked Python environment.
Capture source inputs first with `python artifacts/output-v15/add_pr.py v17-battle Tuxemon Tuxemon 2370 "game UI: double battle layout"`.

1. Run `prc board check artifacts/output-v15/boards/v17-battle/board.json --map artifacts/output-v15/prepared/v17-battle/map.json`.
2. Run `prc board preview artifacts/output-v15/boards/v17-battle/board.json --map artifacts/output-v15/prepared/v17-battle/map.json --out /private/tmp/prc-v15-preview/v17-battle --git-dir <git_dir from provenance.json>`.
3. Generate the candidate from the saved brief through baoyu-infographic and inspect the result.
4. Run `prc explain` with the pinned map, board, Git directory, Kokoro voice and gated infographic candidate.
5. Run `scripts/render_looks.py` on the result with `--look labsheet` to build the light-mode review.

Keep generated media and private proof outside tracked source, as required by .gitignore.
START-HERE.md requires approval before pushing or opening a pull request.

Independent factual review identified overlapping sprites in the before image.
The final wording distinguishes sprite positions from the four existing status panels.
The reading path covers all changed units; the video selects representative lines instead of reading the entire diff.
