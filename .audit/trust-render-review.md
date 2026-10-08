# Review: explainer render integration (0dc7090), read-only

TL;DR. The integration is correct where regressions demanded it: one preflight
feeds check and render (join parity verified by probe), D7 reveal cues and the
outro fine line are enforced, changed-line coverage is literal with a typed
unavailable bucket, notes that cannot fit are moved below the code and lints,
and the CLI offers an exact silent estimate before any synthesis. Three small
real issues remain: a stills-only preview still requires and runs ffmpeg,
`verify_board` exits via `SystemExit` as an API, and the coverage note says
"opaque or oversize" where the current vocabulary is "not inspected".

## Probe evidence (pure, no Chromium launched)

- Join parity: a map with a blank removed line gives the identical message
  ("scene 1: -4 is a blank changed line ... [CUT_NOT_SPACES]") from
  `join_preflight`, inside `verify_board` failures, and in the `RenderError`
  `join_gate` raises before any rendering. `render.fill` + `join_gate` also run
  preflight first (render.py:195-199), so check and render reject the same
  boards with the same words.
- D7: check.py:289 requires every stats card index to have a reveal cue;
  check.py:295 requires outro l1/l2/cmd cues and a `fine` line; engine.js:487
  renders `s.fine == null` as an empty string, so no undefined print.
- Literal coverage: probe map 3 lines shown of 503 total with an opaque 500-line
  file printed "changed lines 3/503 on screen; 500 without line refs (opaque or
  oversize files)", denominator from file totals, and `files_shown` counts only
  cited paths. `boards.coverage` and `doc.py` use the same `line_coverage`, so
  board, doc and render cannot disagree; missing rows link typed refs
  (head_sha for +, base_sha for -, doc.py:67-71).
- Note fit: probe note on a 68-char line fires "note on line 2 overlaps code;
  shorten the note" in both `note_risks` and check facts; engine.js:563-585
  clamps such notes below the row and grows the row, and engine.js:677-700
  runtime-lints real overlaps via getBoundingClientRect, so no silent bad
  frames in the render; CLI preview prints those warnings.
- Estimate: `predict(board, NoneBackend())` is non-mutating (probe) and
  check/CLI print "~X s silent (voice none)" before synthesis; the label
  honestly scopes it to voice none.
- Preview: `prc board preview` runs `verify_board`, then `render(...,
  keys_only=True)` writes two stills per scene (NNa/NNb) in `<out>/<name>/keys`
  and prints layout warnings; BOARD.md documents the same contract.

## Findings (ranked, minimal fixes)

1. P2: `prc board preview` needs ffmpeg and generates a silent wav.
   [render.py:43-51](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/render.py:43)
   checks ffmpeg/ffprobe unconditionally and render.py:252 `silence()` shells
   out to ffmpeg even with voice none; keys_only stills need neither. Fix:
   in `render`, run the ffmpeg half of `check_tools` and `silence()` only when
   `keys_only` is false (`cursor` still comes from `fit_sentences`).
   Parent machines have ffmpeg, so this only bites clean preview hosts.
2. P3: `verify_board` raises `SystemExit` (check.py:457) to communicate
   failures. cli.py handles it and returns 2, but `render_board`
   (render.py:384) does not: `prc explain` prints the raw message with exit 1,
   and programmatic callers cannot catch a domain error. Fix: raise
   `RenderError` from `render_board` or convert `verify_board` to an exception
   and keep `sys.exit` only in its module `main`.
3. P3: [preflight.py:139](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/explainer/preflight.py:139) says
   "opaque or oversize files" while the facts layer now calls opaque inputs
   "not inspected". Align the phrase (or say "not inspected") so the video,
   doc and facts use one vocabulary.
4. P3: `note_risks` estimates size with `len(text) * 15 + 37` px while the
   engine measures `el.offsetWidth`; borderline notes can warn in check yet fit
   at render (or the reverse). The runtime lint covers actual overlap, so
   nothing is silently broken; later, share one note-width formula in
   preflight and engine.

## Out of scope, verified anyway

SourceError now prints a clean CLI message (cli.py:188-195, from 97c02fd);
stored maps pass `git_dir=None` and highlight falls back to hunk colors; the
new BOARD.md preview text matches the CLI contract.

## Per constraint

I did not launch Chromium (no cached browser path in this sandbox; parent owns
browser/e2e runs) and did not edit prod or tests; probes used /tmp only.

Next step: parent merges worker integration; my final read-only pass re-runs
the same probes plus D-coverage sweep on the merged tree.
