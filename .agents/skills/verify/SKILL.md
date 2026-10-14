---
name: verify
description: "Drive PRC's CLI, clickable explanation page, infographic, video, and paired study hub. Use after changes to explain, board tools, review state, or skill installation. Capture commands, browser screenshots, and file effects."
---

# Verify PRC

Read [the feature index](features/README.md), then select the recipe matching the changed user path.
PRC's primary interface is its CLI. It writes local browser pages and videos.
Run commands from the repository root. Keep browser work in the background.

## Launch

Use the existing `.venv`, Python 3.12 or newer, and dependencies from `uv.lock`.
If dependencies are missing, run `uv sync --frozen`. Video uses Playwright and Chromium.
Ask before `playwright install chromium`, as required by `START-HERE.md`.
Use the existing project browser cache when its directory exists:

```sh
export PLAYWRIGHT_BROWSERS_PATH="$PWD/artifacts/release/browser-cache"
.venv/bin/python -m prc.cli --help
```

Otherwise use Playwright's installed default cache. Require help output listing `explain`, `board`, `review`, and `skill`. `map` is not a public command.
PRC exits after each command. No server or port requires teardown.
For manual recipes, create a disposable directory with `mktemp -d /tmp/prc-verify-XXXXXX`.
Set `VERIFY_STORE` to its `store` child. Set `VERIFY_PROOF` to a new directory under `artifacts/verification`.
Use absolute paths for both. Save the scratch path for cleanup.

## Doctor

```sh
.venv/bin/python -m prc.cli doctor
```

For browser recipes, require `chromium ok`. For video recipes, also require `ffmpeg ok`.
`GITHUB_TOKEN unset` is expected for fixtures. Silent video uses `--voice none` and needs no speech model.
Doctor launches and closes a background browser. Inspect its output, not just its exit code.
If package identity is uncertain, run `.venv/bin/python -c 'import prc; print(prc.__file__)'`.
Require this checkout's package before attributing a result to this source.

## Drive

Run `scripts/verify_page.py --page <exact page.html> --shots <new proof directory>` with the current generated output.
The isolated Vercel agent-browser driver clicks every scene, code hunk, narration control, infographic, and coverage control.
Require PASS and inspect each saved screenshot. Verify current output hashes against the report.
For other paths, use [the feature map](features/README.md). Every browser check must save a screenshot.
For paired session hub changes, run `.venv/bin/python scripts/verify_paired_hub.py` instead of API-only checks. Require PASS, every button screenshot, refusal recovery text, and cited proof from [paired hub](features/paired.md).
Before any operator-facing handoff of the hub URL, run .venv/bin/python scripts/handoff_study_hub.py against the exact handed-off server and require its handoff record. Require the printed exact URL, the supervised pidfile, and the handoff record JSON under artifacts/handoff/ with url, port, pid, pidfile, screenshot, and checks. Do not hand off a hub URL without that record; the script refuses to print a URL when any check fails.
The scripted driver uses the repo's Playwright harness. If Vercel agent-browser is required and available, use the same visible controls.
Record a driver limitation if unavailable. DOM-only checks do not establish GUI behavior.

## Evidence

The page driver writes report.json and screenshots in the supplied proof directory.
Inspect the screenshots before declaring the feature verified. Manual recipes preserve commands, files, exit codes, and screenshots.
The paired hub needs a full button pass on a disposable study, followed by verification of the exact live hub.
Copies preserve the operator's readings. They do not establish that the handed-off server is alive.
Keep fixture checks local. Avoid public writes and global skill installs.
Report tested and untested entry points. One mapped feature does not prove the whole product.

For infographics, compare `infographic/brief.json` with the captured code evidence.
Source-derived calls must be exact added or removed production calls.
An explicit storyboard-flow selection uses cited group items and their directed fly cues.
Check group titles against the pinned source; receipts alone do not prove semantic prose.
The test-call node counts distinct test callers with added exact calls to a displayed symbol.
Python `Before docs:` and `After docs:` lines are source docstring excerpts, not inferred board behavior.
Go call-to-typed-error mappings require full pinned head source that matches the captured head diff rows.
OCR matching permits only explicit glyph confusions, with no generic edit-distance tolerance.
Require `flat` after passing word checks when no relations exist.
The geometric gate proves connecting ink only. Inspect direction, arrowheads, endpoints, dashes, and extra connectors in the screenshot.
Icons can appear elsewhere on the canvas, away from numerical fact lines and other lines that contain numbers.
Read recognizer and planted-control verdicts from the current output's `listening.json`.
Keep human pacing, tone, and acceptance pending until the user supplies evidence.

## Cleanup

The page driver closes its browser and local server, including on failure.
The paired hub driver also removes its disposable study and records `scratch_removed: true` in `cleanup.json`.
Evidence survives cleanup.
Confirm screenshots still exist after exit.
For manual runs, close the browser you started and remove only the saved scratch directory.
Never kill by process name. Keep `VERIFY_PROOF` and earlier release artifacts.

## Helpers

`scripts/verify_page.py` requires the project environment, Vercel agent-browser, and cached Chromium.
It exits nonzero when a visible control, code hunk, narration, or screenshot check fails.
Full package checks remain `bash scripts/verify-release.sh`, with the selected browser cache environment.
The verifier uses unique proof directories and rejects skipped tests.
Use `/maintain-verification-skill` when commands, controls, or feature coverage change.
