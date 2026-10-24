# System View flight test: swarm-deploy#116

This folder records the first System View board. The pull request is [swarm-deploy/swarm-deploy#116](https://github.com/swarm-deploy/swarm-deploy/pull/116), "Add shared faults package and structured compose errors".

`board.py` writes `board.json` next to itself. The board has six scenes: title, part map before, part map after, a walk of the error path, the added tests and an outro. It carries 89 receipts and shows no code lines.

To render it in the game-review look:

1. Run `prc map` for the pull request to get `map.json`.
2. Run `python docs/flight-tests/system-view-swarm-deploy-116/board.py`.
3. Copy `board.json` into the map's render folder and run `prc board check` on it.
4. Call `prc.explainer.render.render_look(src, out, "labsheet")`, then `prc.explainer.page.render_page(board, map, out, duration, has_video=True, infographic=None, look_name="labsheet")`.

See [ADR 0002](../../adr/0002-system-view-as-a-second-explanation-level.md) for the decision and its open gaps.
