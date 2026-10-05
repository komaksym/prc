# Renderer bakeoff results (2026-10-05)

TL;DR. Keep our own engine and swap its regex highlighter for Shiki. It ties Remotion for first place in the blind judging, passes every join test, reads the same under OCR, and adds about 13 KB with no license cost. Remotion is 3 s faster on two scenes but adds 442 MB and a company license. HyperFrames is as fast but showed two captions overlapping mid-transition. No renderer fixes the real problem: at GitHub's 800 px width, code renders at about 9 px and the longest line fails OCR in every contender.

Plan: `PR explainer video rendering bakeoff plan.md`. Work dir: X = `scratchpad/explainer/bakeoff/` (session scratchpad b315bb6a...). Each contender's `RESULT.md` has commands and raw numbers.

## Results

| | Control (old engine, regex highlighter) | Our engine + Shiki | HyperFrames 0.8.133 | Remotion 4.0.533 + Shiki |
|---|---|---|---|---|
| Join test (8 scene-3 frames + build file) | n/a, no token data | 9/9 PASS | 9/9 PASS | 9/9 PASS |
| OCR gate at 1920 px | 31/31 | 31/31 | 31/31 | 31/31 |
| OCR at 800 px (GitHub desktop) | 28/31 | 28/31 | 27/31 | 27/31 |
| OCR at 341 px (phone) | 7/31 | 8/31 | 8/31 | 8/31 |
| Render, both scenes, warm median | not timed per scene | 26.7 s | 24.0 s | 23.5 s |
| Added install | 0 | about 13 KB in page; Node + Shiki only at bake time | 125 MB node_modules | 442 MB incl. 193 MB headless shell |
| License | ours | ours + MIT | Apache-2.0, GSAP standard license | company license above 3 employees |
| Blind Opus, overall (1 to 5) | 4, rank 3 | 4, tied rank 1 | 3, rank 4 | 4, tied rank 1 |

OCR: macOS Vision, accurate, language correction off, whitespace-insensitive substring match against `check.py` receipts and the shown code rows (`score/score_ocr.py`). Every 800 px miss is `return {"date_added": None, "date_added_source": provenance}`; HyperFrames and Remotion also miss `if parsed > now:` once at t=2.0.

## Blind judging (fresh Opus, labels from a seeded shuffle)

Key: A = control, B = HyperFrames, C = our engine + Shiki, D = Remotion + Shiki.

- C and D tie. They differ only in the progress bar (C shows per-scene progress, an artifact of rendering scenes separately) and fade timing.
- A (control) loses on syntax colour: the regex highlighter leaves operators and arguments untinted.
- B (HyperFrames) draws the old and new captions on top of each other at s3 t=10.2, and shows stray separator glyphs in the empty code box at t=0.4. On settled frames it matches D.
- Shared by all four: code at 800 px is about 9 to 10 px tall; the receipts footer is unreadable; the `⋯` separators are nearly invisible; the red DATE_ADDED tag overlaps its pill border.

User vote (2026-10-06, after the synced blind clips in `blind/clips/`): no meaningful difference between A, C and D. B stands out for a different background and a proportional font in its code rows (visible at s3 t=12.0), which the Opus judge missed. The user read C's progress bar as the only correct one. It is the opposite: A, B and D show progress through the whole video, and C shows progress through one scene because the engine rendered each scene alone. In a full build C shows the whole-video bar. The user delegated the choice to cost, weight, speed and robustness.

Decision: our engine + Shiki (C).

Superseded 2026-10-06 by the user: keep our engine, but drop Shiki and Node.js. Highlight in Python with tree-sitter, with Pygments as the fallback. See `docs/mvp/DECISIONS.md` D12 to D16.

## Recommendation

Adopt Shiki inside our engine (contender C). It matches Remotion on every measure that a reviewer sees, costs nothing to install for prc users, and carries no license. Remotion's 3 s speed edge does not pay for 442 MB and a per-company license. HyperFrames brings no visual or speed gain and has a caption-layering defect.

The next gain is layout, not rendering: the diff scene must show fewer, shorter lines at a larger size so code reaches about 14 px at 800 px width. That is a change to the diff scene's font clamp and to how many rows a board may show, testable with the same OCR scorer.

## Defects and gaps

- `shared/shiki_tokens.mjs` writes wrong magic-move keys: only 26 of 52 step-1 tokens keep their key into step 2. Not exercised here (no PR 12 line moves between steps); Remotion recomputed keys locally. Fix before any morph ships.
- `shared/inputs/scene*.json` carry absolute cue times; every contender rebased them from `*_cues.json`. Fix in `dump_inputs.py`.
- The magic-move morph was never tested on moving code; PR 12's diff scene only adds rows.
- HyperFrames' builder lost its API connection before writing RESULT.md; the coordinator wrote it from its outputs. Its `oneLine` DOM check fails on every row while frames show single lines; probably a measuring artifact, unverified.
- Mid-transition judging used stills (s1 t=10.1, s3 t=10.2, 11.0), not the planned 3 s clips.
- The 800 px width assumes a video fills the GitHub description column (799 px at a 1280 viewport, measured); no video element was measured. On Retina screens that column shows 1600 device pixels, so 800 px is the worst case.
- Timings are one machine, three warm runs; the control's per-scene time was not measured.
