# System View flight test: swarm-deploy#116

This folder records the first System View board. The pull request is [swarm-deploy/swarm-deploy#116](https://github.com/swarm-deploy/swarm-deploy/pull/116), "Add shared faults package and structured compose errors".

`board.py` writes `board.json` next to itself. The board has six scenes: title, part map before, part map after, a walk of the error path, the added tests and an outro. It carries 89 receipts and shows no code lines.

To publish the page, video and infographic with the CLI:

1. Use the recorded PR map in `tests/data/trustworthiness/swarm-116/map.json`.
2. Run `python docs/flight-tests/system-view-swarm-deploy-116/board.py` if you edit the board source.
3. Generate an infographic candidate from the board's `storyboard-flow` brief. It must show `init job check → compose loader → compose errors`.
4. Run `prc explain --source github:swarm-deploy/swarm-deploy#116 --map "$MAP" --board "$BOARD" --voice none --infographic "$PNG" --out "$OUT"`.

`tests/test_e2e_infographic.py` generates a candidate and runs this command against the recorded map. The historical illustration and screenshots in this folder record the initial flight test.

See [ADR 0002](../../adr/0002-system-view-as-a-second-explanation-level.md) for the decision and its open gaps.
