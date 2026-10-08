# Change map

A reviewer generates an interactive map and inspects changed symbols, callers, callees, and tests.

## Sub-features

- `map-generate` writes HTML and JSON.
- `map-drawer` opens symbol code and closes with Escape.
- `map-tour` walks the map through its Play control.
- `map-video` writes a tour MP4 and card.

## How to get to it (user POV)

Run `prc map --source fixture:shop`, `prc map --source github:komaksym/linkedin-mdp#12`, or use a GitHub PR URL.
Open the printed HTML path. Select a symbol or Play. Add `--video` to export media.

## Driving it with CLI and Playwright

Preconditions: doctor reports Chromium ready. Video also needs ffmpeg.

- Run `.venv/bin/python .agents/skills/verify/scripts/map.py`. Require 7 changed symbols, 12 edges, and 10 steps.
- Click checkout through its `[data-node]` handle. Require `#drawer[aria-hidden="false"]` and `apply_discount` text.
- Press Escape. Require `#drawer[aria-hidden="true"]`. Inspect overview, drawer, and closed screenshots.
- For export, run `.venv/bin/python -m prc.cli map --source fixture:shop --store "$VERIFY_STORE" --out "$VERIFY_PROOF/maps" --video`.
- Inspect printed MP4 and card paths. Probe media with ffprobe and capture a frame with ffmpeg.
- For tour controls, click `#play`. Require `#play-label` to show Pause, then click again and require Play tour.
- Reload the page to reset tour state. Then press ArrowRight twice. Require `#caption` to show CI workflow changed. Capture screenshots after the caption appears.
- Use `tests/test_map_browser.py` for seek and summary expectations.

## Gotchas

- Node indices depend on JSON order. Resolve checkout by `qualname` before selecting its node.
- Fixtures set `live_verified` to false. They do not establish live GitHub coverage.
- HTTP links navigate externally. Keep offline checks on the page itself.
