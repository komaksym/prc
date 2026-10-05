# Renderer bakeoff plan (revised 2026-10-05)

Summary. Three contenders render the same two PR 12 scenes from `boards/mdp12.json` with the same Kokoro `af_heart` audio, all highlighting code with Shiki 4.5.0. The existing PR 12 render is the control. A contender is disqualified if any rendered code line's tokens do not join to the diff line exactly, or if OCR misses a receipt string. Survivors are ranked on legibility at GitHub inline-player width, render time and cost, install size and license, and blind side-by-side frames judged by the user and Opus. Nothing is downloaded or installed until the user approves the list in "Downloads to approve".

Changes from the shortlist in `PR explainer video rendering options.md`: option 4 (fframes, skia-python, resvg-py) is dropped. Remotion uses Shiki and `@shikijs/magic-move` instead of Code Hike. Our engine replaces its regex highlighter with Shiki.

Inputs and detail live in `research_notes/PR explainer video rendering options/`: `bakeoff_pins.md` (versions, sources) and `bakeoff_spec.md` (scene JSON, timings, expected strings, the 14 join-test failure modes, frame timestamps).

## Control

The current engine's existing render, `explainer/out/mdp12-kokoro/mdp12.mp4` (Kokoro `af_heart`, regex highlighter). It is not re-rendered. Frames are extracted at the sampled timestamps with ffmpeg. The control is scored on every measure except the join test, which it cannot pass by design: its regex highlighter emits HTML spans, not token data. Its DOM `textContent` per row is reported as a reference.

## Contenders and pinned versions

| Contender | Pins (exact, no caret) | Highlighting | Code morph |
|---|---|---|---|
| A. Our engine + Shiki | shiki 4.5.0, @shikijs/magic-move 4.5.0; existing Playwright Chromium 151.0.7922.34, ffmpeg 8.1 | Tokens baked in Node at build time, shipped as JSON in the board; `paint()` and `SYNTAX` in `engine.js` removed | `codeToKeyedTokens` + `createMagicMoveMachine`, positions interpolated in `seek(t)` |
| B. HyperFrames | hyperframes 0.8.133, Node >= 22.12 (local 26.8.1), puppeteer-core 25.10 (its dep), ffmpeg 8.1 | Its `code-diff` block fed our baked Shiki tokens (HyperFrames itself ships no Shiki) | Its `code-morph` pattern with our keyed tokens; GSAP vendored locally at 3.14.2, not loaded from a CDN |
| C. Remotion + Shiki | remotion, @remotion/cli, @remotion/renderer 4.0.533; react, react-dom 19.2.3; Chrome Headless Shell 149.0.7790.0 | Same baked token JSON | `@shikijs/magic-move` core machine driven by `useCurrentFrame()`; not `MagicMoveRenderer`, which runs on wall-clock CSS transitions and cannot be seeked |

One Node script, `shiki_tokens.mjs`, bakes the tokens for all three, so every contender draws identical token data. It tokenizes the whole hunk first, then selects the shown lines, then applies the indent cut, so context such as multi-line strings is correct. No Shiki notation transformers are enabled. Line highlights stay as each renderer's per-frame animation; if a contender uses Shiki Decorations, the join test checks the text before and after decorations are applied.

## Shared inputs

`dump_inputs.py` (in the spec) writes, once, the two scene-sliced boards and the audio boundaries: scene 1 (groups) 8.850 to 23.075 s, scene 3 (diff) 35.675 to 51.200 s of `out/mdp12-kokoro/narration.wav`. Every contender renders each scene as its own 1920x1080, 30 fps clip with that audio slice muxed in, and with the cue times from the spec.

## Gates (disqualify on fail)

1. Join-the-tokens test. Each contender writes `OUT/tokens.json` at build time and at every sampled timestamp from the live page. For every displayed code row, the concatenated token texts T must equal the diff line from `map.json` byte for byte, after one declared transform: `cut` leading spaces removed, the same `cut` for every row, and only if those characters are all spaces. No `+`, `-` or `−` marker inside T, no NBSP, no entity escapes, no zero-width characters, codepoints compared without normalization. All 14 failure modes in `bakeoff_spec.md` section 3 get a test, with synthetic fixtures for tabs, CRLF, trailing spaces, empty lines, `[!code]` comments and a 140-character line. The test is written and run against fixtures before any contender is built.
2. OCR. macOS Vision (`VNRecognizeTextRequest`, accurate, language correction off) on the settled frames listed in the spec (scene 1 at 5.8, 8.0, 11.5 s; scene 3 at 2.0, 12.0, 13.2 s). Every receipt string from `check.py` for those frames must be found, at 1920 px and at the measured GitHub width. Ligature readings (`!=` as `≠`) and the `⋯` and `−` glyphs are flagged, not failed; all contenders set `font-variant-ligatures: none`.

## Scores (survivors only)

- Legibility at GitHub inline-player width: character error rate of OCR on code rows at the downscaled size, plus a check that no row wraps, clips or runs under the captions.
- Render time: wall clock for both scenes, three runs, median, same Mac, plus cold first run. Cost per video: local compute only, $0 for all three unless Remotion's company license applies (see below).
- Install footprint: bytes added under `node_modules` plus any browser download, and the license.
- Blind side by side: the same stills and two 3 s mid-transition clips per contender and the control, seeded shuffle, labelled A to D, shown at GitHub width first and as a 1:1 code crop second. The user and a fresh Opus judge score each separately: code legibility, token color contrast, marker clarity, motion smoothness, caption and cue sync within 100 ms.

## GitHub inline-player width

Measured, not assumed: the rendered `<video>` element width and devicePixelRatio in a PR description at 1280 and 1440 px desktop viewports and on mobile, in a background browser tab on an existing public PR. Nothing is posted. Until then, 800 px is a planning placeholder only.

## Downloads to approve

| Item | Source | Size | Used by |
|---|---|---|---|
| shiki 4.5.0 and @shikijs/magic-move 4.5.0, with their deps | npm | under a few MB (registry unpacked sizes in `bakeoff_pins.md`) | all three |
| hyperframes 0.8.133 and its deps | npm | 33.9 MB unpacked, deps extra | B |
| gsap 3.14.2 | npm | about 6 MB unpacked (guess) | B |
| A Chrome for HyperFrames, if it will not reuse the local Chromium 151 | puppeteer download | unknown, about 200 MB if needed (guess) | B |
| remotion, @remotion/cli, @remotion/renderer 4.0.533, react and react-dom 19.2.3 | npm | not measured, tens of MB (guess) | C |
| Chrome Headless Shell 149.0.7790.0 | Remotion first render | not documented, about 196 MB (comparable local build) | C |

All installs go into separate folders under the scratch `explainer/bakeoff/` directory, never globally. No paid API or key is needed.

## Licenses

Shiki and magic-move are MIT. HyperFrames is Apache-2.0. Remotion is source-available and free for evaluation and for companies of 3 or fewer people; shipping it inside prc would require each larger user company to buy a license (inferred from its terms page). A Remotion win therefore carries that cost, and the report will say so.

## Order of work

1. Write the join test and its fixtures; run them against hand-made token files that pass and that fail each mode.
2. `shiki_tokens.mjs` plus `dump_inputs.py`; join test passes on the baked tokens.
3. Contender A, then B, then C, each built by a fresh subagent from this plan; each must pass gate 1 on its own `tokens.json` before rendering frames.
4. Measure the GitHub player width.
5. Extract frames, run OCR, scores, and the blind judging.
6. Report: one table, frames side by side, the winner, and what adopting it changes for prc's install.

## Open decision

The control strips a common 4-space indent (`build.py` `fill()`), so "the diff line exactly" is defined here as the line minus a declared, verified run of leading spaces. The strict alternative is to keep every byte and shift the code block left by the indent width instead.
