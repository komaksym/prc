---
name: verify
description: "Drive PRC's CLI and generated map or walkthrough pages. Use after changes to map, explain, board tools, review state, or skill installation. Capture commands, browser screenshots, and file effects."
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

Otherwise use Playwright's installed default cache. Require help output listing `map`, `explain`, `board`, `review`, and `skill`.
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

```sh
.venv/bin/python .agents/skills/verify/scripts/map.py
```

The driver runs the real `map --source fixture:shop` entry point with its own store.
It opens generated HTML in headless Chromium, clicks checkout, and presses Escape.
Require `PASS` and inspect the printed proof directory.
For other paths, use [the feature map](features/README.md). Every browser check must save a screenshot.
The scripted driver uses the repo's Playwright harness. If Vercel agent-browser is required and available, use the same visible controls.
Record a driver limitation if unavailable. DOM-only checks do not establish GUI behavior.

## Evidence

The driver prints a unique `artifacts/verification/map-*` directory.
It saves CLI stdout, stderr, exit codes, actions, page errors, requests, package identity, revision, and map hash.
Its `output` folder preserves HTML and JSON. Screenshots show overview, open drawer, and closed drawer.
Inspect the screenshots before declaring the feature verified.
Manual recipes preserve commands, resulting files, exit codes, and screenshots in `VERIFY_PROOF`.
Check mutations through a second CLI or artifact read.
The fixture replaces the external provider at PRC's existing boundary; the pipeline and renderer run unchanged.
The driver rejects browser HTTP requests. This proves the captured page loads offline.
It does not establish network isolation for every CLI command. Live GitHub acquisition requires separate evidence.
Keep fixture checks local. Avoid external link navigation, public writes, and global skill installs.
Report tested and untested entry points. One mapped feature does not prove the whole product or release acceptance.

## Cleanup

The driver closes its browser and removes only its own scratch store, including on failure.
Evidence survives failed attempts and cleanup. Require `cleanup.json` to report `scratch_removed: true`.
Confirm screenshots still exist after exit.
For manual runs, close the browser you started and remove only the saved scratch directory.
Never kill by process name. Keep `VERIFY_PROOF` and earlier release artifacts.

## Helpers

`scripts/map.py` is executable and requires the project's Python environment and Playwright.
Invoke it as shown under Drive. It exits nonzero on failure and prints the proof path before work begins.
Full package checks remain `bash scripts/verify-release.sh`, with the selected browser cache environment.
The verifier uses unique proof directories and rejects skipped tests.
Use `/maintain-verification-skill` when commands, controls, or feature coverage change.
