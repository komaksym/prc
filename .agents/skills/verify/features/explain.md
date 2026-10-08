# Explainer

A reviewer receives a video, walkthrough, map, card, and comment from a checked story board.

## Sub-features

- `explain-board` checks a supplied board and renders five outputs.
- `explain-stored` uses captured map JSON.
- `explain-fallback` produces available outputs without a board.
- `explain-voice` produces silent or narrated video.

## How to get to it (user POV)

Run `prc explain --source fixture:shop --board tests/data/boards/shop.json --voice none`.
Users can supply a GitHub source, `--map`, `--git-dir`, output directory, and voice backend.
Open the printed files.

## Driving it with CLI and Playwright

Preconditions: doctor reports Chromium and ffmpeg ready. Start at the repository root.

- Run `.venv/bin/python -m prc.cli explain --source fixture:shop --board "$PWD/tests/data/boards/shop.json" --voice none --store "$VERIFY_STORE" --out "$VERIFY_PROOF/explain"`.
- Require `check_passed: true` and all five files. Probe MP4 for 1920 by 1080, 30 fps, and positive duration.
- Open doc.html in Playwright. Wait for `window.docReady === true`. Require `.shot` scenes and save a full-page screenshot.
- Open the map, click checkout, and save its drawer screenshot.
- Repeat with `--map` pointing to generated map.json and a separate output directory. Require `map_source: stored` in run.json.
- Capture a real MP4 diff frame with ffmpeg. Inspect it and the card image.
- For audible proof, use `--voice say` where available. Require an audio stream and finite ffmpeg volumedetect volume.
- Exercise fallback and rejected-board paths through `tests/test_e2e_explain.py`. Preserve artifacts and exit codes.

## Gotchas

- Silent video has no audio stream. This is expected only for `--voice none`.
- Receipt checks establish quoted code, not every prose claim.
- Output slugs can repeat. Use separate directories for different inputs.
