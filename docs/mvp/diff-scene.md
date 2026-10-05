# Diff scene: make it useful to a reviewer

Written 2026-10-06. This is Stage 2 of `docs/mvp/PLAN.md`. Read all of it before you change a file. In this file, "E" is the explainer prototype folder, and paths without a folder are inside E.

## Summary

The explainer video sits in a pull request description on GitHub. A reviewer watches it once before reading the diff, often muted, in an 800 px wide player. The diff scene is where the reviewer sees the code. Today it has three problems, all measured:

1. **The old code disappears.** At each step a removed line strikes through, fades to about 40%, and closes. The last frame shows only new code. A reviewer who pauses, or looks away for two seconds, cannot see what changed. In the mdp17b render, `if slots[candidate_row.company_id] <= 0` became `if any(slots[company_id] <= 0 for company_id in employers[candidate_row.profile_url].assignments)`, and the final frame shows only the second line.
2. **Long lines make all the code small.** The font size comes from the longest line, with a floor of 22 px and a cap of 32 px in a 1920 px frame. Across the 14 PR maps, 15.6% of changed code lines are over 80 characters and 6.6% are over 100 (measured, 9,982 lines). A scene shows about 8 lines, so about 3 in 4 scenes will have a line over 80 characters (inferred). That gives code of about 13 px or less at 800 px.
3. **The colours are weak.** A regex highlighter in `engine.js` leaves operators and arguments uncoloured. A blind judge ranked it below a real highlighter.

This handoff fixes all three, in Python, at build time:

- A **unified diff end state**. Removed lines stay on screen with a red tint, and the changed words inside a replaced line are marked, like GitHub's word diff.
- **Soft wrap and a bigger font**. Long lines wrap with a hanging indent, the font cap goes from 32 to 40 px, and a height limit keeps code above the captions.
- **Real highlighting**. tree-sitter handles Python, JavaScript and TypeScript, and Pygments handles everything else.
- **Line numbers** in a gutter, so the reviewer can find each line in the diff.

The join test stays the gate. Every row's tokens must join to the diff line exactly.

## 0. Decisions and why

The user set the goal: the video must be useful to reviewers, and people should want to use it. These decisions follow from that goal. Do not reopen them.

- **Python only, no Node.js, no Shiki.** This is the user's decision. prc is a Python tool.
- **tree-sitter for `.py .pyi .js .jsx .mjs .cjs .ts .mts .cts .tsx`, and Pygments for the rest.** prc's map branches already depend on tree-sitter. The installed versions are pinned in section 1.
- **Removed lines stay visible, and changed words are marked.** Reviewers mostly fail on code that is plausible but subtly wrong ("almost right" is the top AI-code complaint in our research, `prc/reports/AI code comprehension pain points.md`). The useful signal is what exactly changed inside a line. A still frame, a muted viewer and a paused video can all see a word-level mark. An animation cannot give that.
- **No magic-move glide.** An earlier plan gave tokens keys so they could slide from the old line to the new one. Motion carries the same information as the word mark, but only while the viewer is looking at that moment. It also adds the most engine risk. The word mark replaces it. Do not build the glide.
- **Soft wrap is required, not optional.** It is the only way long-line scenes reach a legible size. Wrapping is visual only. The text of every row is unchanged and still passes the join test.
- **The font cap is 40 px, bounded by width and height.** For PR 12 the expected size is 38 px, about 15.8 px at 800 px wide, up from 13.3 px (inferred).
- **Line numbers.** They are receipts, which check.py verifies, and they show how far apart the shown lines are. They cost about 3 to 4 columns of width.
- **A usefulness test decides "done".** Section 5 defines frame QA: questions that a reviewer should be able to answer from the final frame at 800 px. The baseline is measured, and the work is done when the new frames answer more of them.

## 1. Where things are

E means `/Users/koval/dev/prc/prototypes/explainer`. It is its own local git repo (branch `main`, baseline commit `371e0be`). The prc repo ignores it. Commit your work in E with Conventional Commit messages, one commit per milestone, and never add a `Co-Authored-By` line. Do not push. In this stage, change nothing outside E except `docs/mvp/LOG.md`.

- `E/build.py`. The board and `map.json` go in, and an MP4 comes out. `fill()` (line 149) prepares the diff rows. Lines 185 to 195 do tab expansion, rstrip, and the common-indent `cut`. The page loads at line 258, and `window.lint` warnings print at line 262.
- `E/check.py`. It validates boards. `diff()` (line 101) builds each diff row as `{ref, op, num, text, step}`. `op` is `+`, `-` or a space. `step` is 0 for context lines.
- `E/engine.js`. It draws the frames.
  - Lines 25 to 43 hold `SYNTAX` and `paint()`.
  - `MAKERS.diff` starts at line 516.
  - Line 529 sets the font size.
  - Line 532 is the row markup.
  - Line 535 sets the open time `tin` of each added row.
  - Line 539 sets `tallest`.
  - Lines 552 to 590 hold the per-frame update. It handles the removed row's strike, close and opacity, the added row's open and flash, and the notes.
  - Lines 616 to 631 hold the layout lint. It reports any box that ends below y=862.
- `E/engine.css`. Lines 119 to 126 style the diff rows.
- `E/BOARD.md`. This is the guide for board writers. Line 101 describes the diff scene animation.
- `E/boards/`. `mdp12.json` is the main test, and it has only added lines. `mdp17b.json` has two removed lines that are each replaced (`-1018` by `1031`, and `-1021` by `1035`).
- `E/../mdp/maps/prN/<id>/map.json`. These are the PR maps.
  - PR 12 is `pr12/26ed8fadac86c489`.
  - PR 17 is `pr17/2e85e566fdcd1ec7`.
  - PR 4 is `pr4/67dc3d18a1929895`.
  - PR 14 is `pr14/018f2ec8f4a82b41`.
- `E/../mdp/store/git-cache/komaksym__linkedin-mdp__N.git`. These are bare repos with the head and base commits of PR N. Read a whole file with `git --git-dir <cache> show <sha>:<path>`, using `head_sha` or `base_sha` from map.json.
- `E/spike/`. This is tested reference code. Port it, and do not import from it.
  - `tokens.py` makes coloured runs per line from whole files.
  - `keys.py` holds `split()`, which makes tokens.
  - `pairs.py` pairs rows and flags changed tokens.
  - `wrap.py` soft-wraps one row.
  - `run12.py` joins every PR 12 line.
  - Each file runs its own checks: `../.kvenv/bin/python pairs.py` prints `ok`.
- `E/bakeoff/shared/jointest.py`. This is the join test (`python3 test_jointest.py` gives 25/25).
- `E/bakeoff/score/score_ocr.py` and `ocr`. These are the OCR scorer and the macOS Vision tool.
- `E/eval/questions.json` and `E/eval/baseline/`. These are the frame-QA questions and the baseline frames.

Environment: `E/.kvenv/bin/python` (Python 3.12). It has Kokoro, Playwright 1.62.0, soundfile, tree-sitter 0.26.0, tree-sitter-python 0.25.0, tree-sitter-javascript 0.25.0, tree-sitter-typescript 0.23.2 and Pygments 2.21.0 (measured). It has no pytest. Do not install anything. If you need a package, stop and report.

Run these from E. Chromium, ffmpeg, the OCR tool and git commits need the sandbox disabled.

```bash
M12=../mdp/maps/pr12/26ed8fadac86c489/map.json
M17=../mdp/maps/pr17/2e85e566fdcd1ec7/map.json
G12=../mdp/store/git-cache/komaksym__linkedin-mdp__12.git
G17=../mdp/store/git-cache/komaksym__linkedin-mdp__17.git
python3 check.py boards/mdp12.json $M12                                  # "... receipts verified"
(cd bakeoff/shared && python3 test_jointest.py)                          # 25/25 behave
.kvenv/bin/python build.py boards/mdp12.json $M12 out/mdp12-new          # about 77 s
.kvenv/bin/python build.py boards/mdp17b.json $M17 out/mdp17b-new
.kvenv/bin/python build.py boards/mdp12.json $M12 out/mdp12-keys --keys-only   # stills + "layout:" lines, fast
(cd spike && ../.kvenv/bin/python run12.py)                              # "lines 287 mismatch 0"
```

Baseline, measured 2026-10-06: check passes with 30 receipts, the join tests give 25/25, and the mdp12 build takes 77 s and gives a 63.4 s video. PR 12 scene starts are 0, 8.85, 23.075, 35.675, 51.2 and 55.875 s. The mdp17b diff scene runs from 43.96 to 55.19 s.

To get a frame, run `ffmpeg -v error -y -ss <seconds> -i <mp4> -frames:v 1 -vf scale=800:-1:flags=lanczos <png>`. Then look at the PNG with your image-reading tool. Read scene times from `window.BOARD.scenes[i].start` and `.end` in `out/<dir>/player.html`.

## 2. Data shape

After `fill()`, a code row of a diff scene keeps its fields and gains new ones:

```json
{"ref": "1031", "op": "+", "num": 1031, "step": 1,
 "text": "if any(slots[company_id] <= 0 for company_id in employers[candidate_row.profile_url].assignments):",
 "tokens": [{"text": "if", "cls": "k"}, {"text": " ", "cls": ""}, {"text": "any", "cls": "f", "chg": true}, ...],
 "pair": "-1018",
 "hang": 4,
 "breaks": [14]}
```

- `text` is the row after `expandtabs(4).rstrip()` and the cut, exactly as `fill()` makes it now. Keep it.
- Invariant: `"".join(t["text"] for t in tokens) == text`. The join test proves it.
- `cls` is one of `""`, `"k"`, `"s"`, `"n"`, `"c"` or `"f"`. These are the existing engine.css classes.
- A token is a word (`\w+`), one punctuation character, or a run of whitespace (`spike/keys.py` `split()`). A token never crosses a colour boundary. Wrap may split one very long token into pieces.
- `chg: true` marks a token that changed inside a paired row. It is absent otherwise.
- `pair` is the ref of the row that this row replaces or is replaced by. It is absent on unpaired rows.
- `hang` is the indent of continuation lines, in columns.
- `breaks` lists the token indices where a new visual line starts. It is absent or empty when the row fits on one line.
- The scene gains `gutter`, the width of the line-number column in columns (Step 5).
- Gap rows (`{"gap": true}`) get no tokens.

**Colour rules (measured in the spike).** A capture name maps to a class by its first matching prefix:

| Capture prefix | Class |
|---|---|
| `comment` | c |
| `string`, `escape` | s |
| `number` | n |
| `keyword`, `operator`, `constant.builtin`, `variable.builtin` | k |
| `function` (includes `.method`, `.builtin`, `.call`) | f |

Every other capture gets the base colour `""`. Overlap rules:

- The inner node wins.
- On one node, a coloured capture beats the base colour.
- Among coloured captures on one node, the earliest query pattern wins.

Without the second rule, `update` in `row.update(` stays base, because `property` wins (measured). Python `self` stays base, because the Python query has no capture for it. Accept that.

TypeScript has no `HIGHLIGHTS_QUERY` constant. Read `queries/highlights.scm` from the `tree_sitter_typescript` package folder, and put the JavaScript `HIGHLIGHTS_QUERY` before it (`spike/tokens.py` line 7).

## 3. Rules for you

- Write the test before the code. Each milestone lists its failure modes. Turn each one into a test first, see it fail, then write the code. Tests are plain `assert` scripts, `E/test_highlight.py` and `E/test_diffrows.py`, run with `.kvenv/bin/python <file>`. Each prints `ok`.
- Run the narrowest check after each change. At the end of each milestone, run all of section 1's commands. Do not start the next milestone while one fails. Commit at the end of each milestone.
- Verify through the real artifact. A passing test does not prove that a frame looks right. Extract the frames each milestone names and look at them.
- Do not edit boards or questions to make a check pass. Do not change `bakeoff/` except to read it.
- If a result surprises you, stop and write it down in your report. Do not tune constants until a test passes.

## 4. Milestones

### Step 1. `highlight.py`: tokens from the whole file

Create `E/highlight.py` by porting `spike/tokens.py` and `split()` from `spike/keys.py`. Functions:

- `file_runs(path: str, data: bytes) -> list[list[tuple[str, str]]]`. Line N (1-based, numbered like `str.splitlines`, as the map numbers lines) gives a list of `(text, cls)` runs.
- `row_tokens(runs, cut) -> list[dict]`. It applies `expandtabs(4)` across runs, aware of columns, strips trailing whitespace, removes `cut` leading spaces, and splits into tokens. Port `expandRstrip` and `cutTokens` from `bakeoff/shared/shiki_tokens.mjs` lines 47 to 81.
- `attach_tokens(rows, path, cut, git_dir, head_sha, base_sha, hunks)`. It reads the head file for rows that are not `-`, and the base file for `-` rows, then sets `tokens` on every code row.

Source of the text:

- With `--git-dir`, read whole files from git. If git fails for a file that a row needs, stop the build with a clear message.
- Without `--git-dir`, join the hunk's lines for that side with `\n` and parse that. Print one warning that colours may be wrong at hunk edges.
- Skip highlighting for files over 512 KB, or with a NUL byte in the first 8 KB. Give such a file one base-colour run per line.
- Decode with `data.decode("utf-8", "replace")` and encode again, so byte offsets match the text. Number lines with `splitlines(keepends=True)`.

Failure modes, each one a test:

1. A real line does not join. Test every line of every file in the PR 12, 17, 4 and 14 maps, on both sides, against the `map.json` text with the git cache. Expect 0 mismatches. PR 12 is measured. The others are a guess.
2. A multi-byte character (é, an emoji, CJK) shifts offsets.
3. CRLF line endings leave `\r` in a token.
4. A tab after other tokens expands to the wrong column. `a\tb` and `ab\tc` must match `str.expandtabs(4)`.
5. Trailing spaces or tabs survive.
6. A form feed (`\x0c`) in a Python file shifts line numbers compared with `splitlines`.
7. A file is missing at a sha. An added file has no base, which is fine unless a `-` row needs it.
8. An extension that Pygments cannot lex gives one base run, with no crash.
9. A file with a syntax error. Tokens must still join.
10. A file over 512 KB, or binary, gives plain runs.
11. Hunk-only mode joins, and it prints the warning.
12. A cut that hits a non-space character raises an error. Never slice silently.
13. Colours.
    - PR 12 head line 453: `if`→k, `len`→f, `!=`→k, `1`→n.
    - Line 1031: `update`→f, `_date_added`→f.
    - Line 473: `"reason"`→s.
    - Line 474: `None`→k.
    - Synthetic Python: `# note`→c.
    - JavaScript `const f = () => 1`: `const`→k, `=>`→k.
    - TypeScript `type A = {a: number}`: `type`→k.
    - Rust through Pygments: `fn`→k, `// hi`→c.

Done when all the tests pass and `spike/run12.py` still prints 0 mismatches.

### Step 2. The build attaches tokens, the engine draws them, the join gate runs

1. In `build.py`, add the `--git-dir <path>` flag. In `fill()`, for each diff scene, call `attach_tokens` after the existing cut, with the same `cut` value. Do not compute the cut twice.
2. In `build.py`, for each diff scene i, write `out/<dir>/tokens_s<i>.json` in join-test format.
   - The format is `{"scene": i, "file": ..., "cut": cut, "transform": "build", "refs": [code refs in order], "frames": [{"t": null, "rows": [{"ref", "tokens", "marker"} or {"gap": true}]}]}`.
   - Run `python3 bakeoff/shared/jointest.py <file> --map <map.json>`.
   - If it exits non-zero, print its output and stop the build. Dict tokens with a `text` field are accepted (jointest.py line 30).
3. In `engine.js`, delete `SYNTAX` and `paint()`. At line 532, draw each token as `<span class="mt ${cls}">${esc(text)}</span>`. If a row has no tokens, keep `esc(r.text)`.
4. In `engine.css`:
   - Add `font-variant-ligatures: none` to `body` and `.drow`, so that `!=` never draws as `≠`.
   - Add `.drow .mt { display: inline-block; }`.
   - Keep `.k .s .n .c .f`.
5. In `build.py`, after `page.goto` (line 258), check in the page that each diff row's `.ct` `textContent` equals its row `text`. Stop the build if they differ.

Done when:

- check passes;
- the mdp12 and mdp17b builds pass the join gate and the DOM check;
- the PR 12 frame at 47.675 s shows `!=` and `=` in keyword colour and `len` and `update` in function colour.

### Step 3. A unified diff end state with changed words marked

**Data.** Port `spike/pairs.py` into `E/diffrows.py` as `pair_rows(rows)`, and call it in `fill()` after tokens are attached. The rules are tested in the spike:

- A block is a run of removed rows followed directly by added rows of the same step, with no gap row between them.
- Inside a block, each removed row, in order, takes the most similar added row after the previous pair, if their token similarity (`difflib.SequenceMatcher` over non-whitespace token texts, `autojunk=False`) is at least 0.4.
- Paired rows get `pair`, and their tokens in non-equal opcodes get `chg: true`.
- After pairing, also set `chg: true` on a whitespace token whose nearest non-whitespace neighbours on both sides are changed. This lets the marks join into one span, the way GitHub's do.

**Engine.** Change only the diff maker's per-frame update (`engine.js` lines 552 to 590):

- Removed rows no longer close. Keep `k = 1` for `-` rows. Delete the strike width animation and the `.strike` element. Text opacity goes from 1 to 0.85 over 0.3 s from `R.t0`, not to 0.55. The row background goes to `rgba(red, 0.14)` over 0.3 s from `R.t0`. The sign `−` fades in red, as it does now.
- Changed tokens in a removed row get the background `rgba(red, 0.40 * prog(t, R.t0 + 0.15, 0.3))`.
- Added rows open as they do now, at `R.tin`, with the same flash. Changed tokens in an added row get the background `rgba(green, 0.34 * prog(t, R.tin + 0.3, 0.3))`. After the flash decays, an added row keeps the background `rgba(green, 0.10)`, so the end state reads like a unified diff.
- A row whose step is still in the future looks exactly as it does now.
- Everything stays a pure function of `t`. Use no CSS transitions and no timers.
- Mark changed tokens with a class, `chg`, at build time, and set only the background alpha per frame.

**Layout.** Removed rows now keep their height, but `tallest` (line 539) already counts every row, so the box size does not change. Check this with the lint.

**Failure modes, each one a test in `test_diffrows.py`.**

1. mdp17b pairs `-1018` with `1031` and `-1021` with `1035`, and leaves `1034` unpaired.
2. A gap row between a removed and an added row blocks pairing.
3. Rows of different steps never pair.
4. A pair below 0.4 similarity stays unpaired.
5. Two removed rows and one added row: at most one pair, in order.
6. Whitespace tokens are not marked unless both neighbours are changed.
7. The changed tokens of `-1018` are exactly `candidate_row` and `.`. In `1031` they are `any`, `(` and the run from `for` to `)` before the final `:`.
8. Pairing changes no token text. The join still holds.

**Done when:**

- `out/mdp17b-new` builds;
- its final diff frame (`end - 0.5` s), viewed at 800 px, shows both removed lines in red with their changed words marked, and both replacements in green with their changed words marked;
- a frame 0.2 s after each step cue shows the red tint starting, with no strike line;
- the PR 12 final diff frame looks as it did in Step 2, because PR 12 has no removed lines.

### Step 4. Soft wrap, font cap 40 px, height limit, small-font lint

**Wrap (Python).** Port `spike/wrap.py` into `diffrows.py` as `wrap_row(tokens, cols)`. It returns `hang` and the visual lines. Store `breaks` as token indices into the row's flat token list. Wrap may split a token: replace it in `tokens` with its pieces, and copy `cls` and `chg` to each piece. Set `cols = 72 - gutter`, where `gutter` is the Step 5 gutter width, or 0 until Step 5 exists. The join still holds, because the pieces join to the same text. Width counts East Asian wide characters as 2 columns.

**Engine.**

- At each break index, draw `<br><span class="hang" style="display:inline-block;width:${hang}ch"></span>`. `textContent` stays the row text, because neither element adds characters.
- A row's height is `RH * (breaks.length + 1)`.
- Change the `tallest` sum to use these heights.

**Font.** At line 529, the font becomes `FS = max(22, min(40, widthBound, heightBound))`.

- `longest` is the widest visual line in columns, counting `hang` on continuation lines.
- `widthBound = floor(1560 / ((longest + gutter) * 0.6 + 2))`.
- `heightBound` is the largest FS for which the `.code` box ends at or above y=862. The box top is `max(118, 489 - tallest / 2)`. `tallest` is the row heights plus `2 * TOP`, plus 72 if there is a label, plus 48. Step FS down from 40 by 1 until it fits. A loop is easier to get right than algebra.
- If the final FS is below 28, push a message to `window.lint`: `scene <i>: diff font <FS> px is small at GitHub width; show fewer or shorter lines`. Board writers see it as a `layout:` line in `--keys-only`.

**Notes on wrapped rows.**

- Anchor a note to the row's last visual line. Its top is `R.y + R.h * R.hk - RH / 2`.
- Its left is after the last line's text. Measure the width of the last line's tokens with `getBoundingClientRect`, or use characters times CW. Measure CW once per scene; `bakeoff/engine/engine.js` shows how (search `const CW`).
- Keep the existing clamp to the right edge.

**Failure modes, each one a test.**

1. A wrapped row does not join. Test every row of every diff scene in `boards/`, plus a synthetic 150-character string row.
2. A visual line is wider than `cols`, unless it is one split piece.
3. A short row wraps. Rows of 72 columns or fewer stay one line.
4. A whitespace token starts a continuation line. Whitespace stays at the end of the line before.
5. A 12-row scene (10 code rows and 2 gaps) puts the code box below 862. Build a synthetic board from mdp12 with more refs from the same hunk, keep it out of `boards/`, and use `--keys-only`.
6. A note runs off the right edge or covers wrapped text. Check the mdp17b frames.

**Done when:**

- mdp12 builds with FS 38 (expected, so check it in the DOM);
- mdp17b builds with line `1031` wrapped into two lines and FS at least 30;
- no `layout:` line appears for any diff scene in mdp12, mdp17b, mdp4 or mdp14;
- the final mdp17b frame at 800 px is readable to you.

### Step 5. Line-number gutter

Show each row's `num` (from check.py) in a dim column left of the sign.

- Use the new-file number for `+` and context rows, and the old-file number for `-` rows.
- Style: colour `#5B6475`, `font-size: 0.72em`, right-aligned, 12 px of padding before the sign column.
- `gutter` (in columns) is `ceil((digits + 1) * 0.72)`, where `digits` is the digit count of the largest `num` in the scene. Python computes it in `fill()` and stores it on the scene, so wrap and the font size use the same value.
- Gap rows show no number.

Failure modes, each one a test:

1. A removed row shows its new-file number.
2. A wrapped row shows its number on a continuation line. The number belongs on the first visual line only.
3. The font size ignores the gutter, so code clips at the right edge. The lint and a frame catch this.

Done when the mdp12 and mdp17b final frames show the line numbers, and the Step 4 conditions still hold.

### Step 6. Measure, update the guide, report

1. **OCR.** Extract six frames from `out/mdp12-new/mdp12.mp4`:
   - `s1_t05.8.png` at 8.85+5.8 s
   - `s1_t08.0.png` at 8.85+8.0 s
   - `s1_t11.5.png` at 8.85+11.5 s
   - `s3_t02.0.png` at 35.675+2.0 s
   - `s3_t12.0.png` at 35.675+12.0 s
   - `s3_t13.2.png` at 35.675+13.2 s

   Check the scene starts in `player.html` first. Save the frames at 1920 px, with no scaling. Run `python3 bakeoff/score/score_ocr.py <folder> out/mdp12-new/ocr.json`. The baseline is 31/31 at 1920 px, 28/31 at 800 px and 8/31 at 341 px. All three 800 px misses were the `return {"date_added": None, ...}` line. Report the new numbers as they are.
2. **Frame QA.** Do section 5 for the new mdp12 and mdp17b renders.
3. **BOARD.md.** Rewrite the diff scene paragraph (line 101) for the new behaviour:
   - removed lines stay, tinted red;
   - a replaced line is paired with its replacement, and the changed words are marked;
   - long lines wrap;
   - the font shrinks as visual lines grow, and the build warns below 28 px;
   - so prefer fewer and shorter lines.

   Also replace "At most 12 rows fit, ⋯ rows included" with the rule the build now enforces.
4. **Report.** Write `E/HANDOFF-RESULT.md`. Use section 6's format.

## 5. Usefulness test: frame QA

This test says whether a reviewer can get the facts of the change from the video. It is the main measure of done.

1. For each board in `eval/questions.json`, extract the final settled frame of the diff scene, at `end - 0.5` s, scaled to 800 px wide. Save it as `eval/<label>/<board>_diff_end.png`.
2. Give the PNGs and the questions, without the answers, to a fresh agent. It must not have seen the code, the boards or `questions.json`. Copy the PNGs to a neutral folder, and paste the questions into its prompt. Tell it to read only those images, to quote code exactly, and to answer `CANNOT TELL` when the image does not show the answer or it cannot read it confidently.
3. Grade each answer against `questions.json`. It is correct only if it states the substance of the answer key. Record correct, wrong and `CANNOT TELL` per question.

The baseline frames are in `eval/baseline/` (current engine). The baseline score is recorded in section 7. The redesign is done when the new frames score higher than the baseline on mdp17b and no lower on mdp12. Expected: mdp17b's "before" questions go from unanswerable to answerable (inferred from the design).

## 6. Report format

`E/HANDOFF-RESULT.md`. For each milestone, give:

- what changed, one line per file;
- the commands you ran, with results: test counts, join gate, DOM check, FS per scene, OCR at 1920, 800 and 341 px, frame QA scores, and build time;
- the frame files you looked at, and what you saw;
- anything that surprised you.

Mark every number as measured or estimated. List what you did not finish and why.

## 7. Baseline frame QA (current engine, measured 2026-10-06)

A fresh sonnet agent read only the two 800 px PNGs in `eval/baseline/`. Raw answers are in `eval/baseline/RESULT.md`.

| Board | Correct | Wrong | CANNOT TELL |
|---|---|---|---|
| mdp12 | 5/5 | 0 | 0 |
| mdp17b | 2/4 | 0 | 2 (2a old skip condition, 2c old decrement) |

The reader said why it could not answer. The frame shows no removed lines. This confirms problem 1. The bar for the redesign is mdp17b 4/4 and mdp12 5/5.

mdp12 already scores 5/5, so frame QA cannot show the legibility gain on that board. OCR at 800 and 341 px measures legibility (Step 6, item 1).
