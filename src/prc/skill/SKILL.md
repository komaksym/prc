---
name: prc-explain
description: Write a board.json storyboard for one pull request so prc can render its explainer video.
---

# prc-explain: write the board for one pull request video

You write one JSON file, the board. `prc` turns it into a narrated 1920x1080
video, walkthrough, map, card, and comment draft. It checks cited code and explicit numeric assertions.
Review the prose against the captured code. A valid citation can support a false interpretation.
`prc` never posts
anything to GitHub: it only writes local files. Say that to the user at
the end.

The viewer is the reviewer: a developer who has never seen this pull
request, watches once before reading the diff, maybe muted. After about a
minute they should say what behavior changed, for whom, which lines of
code do it, and where to start reviewing. Describe the pull request; do
not sell it. One idea per scene, one to three sentences per scene, each
under 20 words, in plain words. No hype words, no slogans, no taglines,
no wordplay.

Counts describe parsed symbols and resolved calls. Unsupported languages can leave that analysis incomplete.
Do not infer no tests from zero parsed test functions. Check the changed test files and original diff.

## 1. Render the deterministic outputs and read `map.json`

Run `prc doctor` first. Video and card rendering require Chromium and ffmpeg.
Use `--voice none` for silent output when voice backends are unavailable.
Follow the user's installation policy before installing missing tools or voice models.
Then render the PR without a board:

```sh
prc explain --source https://github.com/<owner>/<repo>/pull/<N>
```

This writes `map.json`, `map.html` and `run.json` into
`artifacts/explain/<owner>-<repo>-<N>-<head12>/` and prints that folder as
`out`. Read `map.json` there: it is the only source of truth for the rest
of this skill. Every name, value, label and count you put on screen must
come from it.

If `prc explain --source X` cannot reach GitHub (for example no
`GITHUB_TOKEN` in this environment), pass a stored map instead:
`prc explain --source X --map <stored map.json>`. `--map` skips
acquisition and uses the stored file. Use the same `--map` flag on every
`prc board` command below and on the final render in step 7, so the board
and the video agree on the head.

## 2. Read the board guide and follow it

```sh
prc board guide
```

The guide is the schema: scene types, `say`, `cues`, `cite`, `hold` and
`assert`. Follow it exactly. Shape the story like this: a `title` scene,
one `groups` picture of the behavior before the change and the same
picture after it (same groups, ids and columns, so only the changed part
moves), one `diff` scene of the lines that carry the change, one evidence
scene (`list` of the tests the PR adds, or `bars`/`stats`), then the
`outro`, which hands the reviewer off to the diff. Show code once, twice
at most. Aim for 45 to 75 seconds in total.

Open on behavior before code, with one concrete case taken from the PR's
tests or code: real fixture names, real values, real status strings. Close
with the evidence (the tests the PR adds, when it adds any), then the
outro. The outro's two lines hand the reviewer off: what changed in one
plain sentence, then where to start reviewing (a file and what it decides)
or what the PR leaves untested. Never a slogan or a quotable line.
The card and comment headline use the outro's `l1` change summary when supplied.
Write `l1` about the resulting behavior. Keep the old behavior in the introduction or diff scene.

## 3. Pick lines with `board show` and `board find`

```sh
prc board show --map map.json [path-substring ...]
prc board find --map map.json "needle" [...] [--path substr]
```

`show` prints the diff with the ref of every line: `N` is a line after
the change, `-N` is a removed line. You list refs, never code; the text
comes from the diff. `find` prints the refs of lines that contain a
needle, such as a function or fixture name from the tests. Build every
scene from these refs. Never type a line number by hand and never quote
code from memory: copy the ref and copy the exact substring from the
line.

## 4. Write `board.json`

Write the board to `board.json` in your working folder. The rules that
past boards kept breaking, with the fixes:

- Every `cite` `match` must be an exact substring of its line. Copy it
  from step 3 output; retyping introduces mismatches the checker rejects.
- Every on-screen item `text` (or its `ground`) must appear on one of the
  scene's cited lines. Titles, subs and notes are not checked, so keep
  them literally true: a wrong unchecked sub ships silently.
- Never type a number on screen. A past board showed a big `4` for cases
  that "stay unknown" while the parametrized test actually had 7 cases,
  and read as the total. Use a checker fact (`{tests_added}`,
  `{changed}`, `{covered}`, `{added_total}`) in `big` and stat values, or
  leave `big` out and set `more` to `"+ N more cases"`.
- A cue phrase must occur exactly once in the scene's spoken text,
  matched as whole words ignoring case. Quote the sentence's exact words.
- The diff scene must show the branch the narration claims. A past board
  said "returns unknown when the timestamp is bad" but only showed the
  future-timestamp lines, not the invalid-timestamp lines. Add the refs or
  soften the sentence to what the shown lines prove.
- Name the rule the code shows, not a narrower one. A past board said
  "without a cited validation" when the code rejected an expired one, and
  "no validation" when the code meant no *applicable* validation. Read the
  branches; when unsure, say less.
- If the PR adds no tests, do not mention tests.

## 5. Run `prc board check` until it passes

```sh
prc board check board.json --map map.json
```

Exit 0 prints `<n> receipts verified`. Exit 2 prints one line per error;
fix what it prints and run it again. The usual errors and fixes:

| checker says | fix |
|---|---|
| `... is not a line of the diff` | that ref is not in `show` output; pick a ref that is |
| `... is not on that line ('...')` | `match` is not an exact substring; copy it from `show` |
| `... is on screen but on none of the scene's cited lines` | ground the item on a cited line or cite the line it comes from |
| `types a number; use a fact like {tests_added}` | replace the typed digit with a fact |
| `{items} counts only the items this board picked` | drop `big` or use a fact about the pull request |
| `names no such id` / `unknown cue ... for a ... scene` | re-read the guide's verb and id lists for that scene type |
| `lines wait for step N, but no cue says when` | every step number in use needs exactly one `step` cue |
| `narration says X = N, the map says M` | the `assert` disagrees with the map; change the sentence |
| `... is in no bar, so the bars would hide it` | every file of the PR must sit in exactly one bar |

Record which try the check first passed on: first, second, or later.

## 6. Run `prc board coverage` and say what is left out

```sh
prc board coverage board.json --map map.json
```

Cover the largest behavior change and name what the board leaves out.
The video's outro and the "Not covered" listing downstream say "covers X
of Y changed files" from this rule. A past board presented 4 example
cases as the whole test and a part of the report as the whole feature;
say "examples" or "in part" when the board shows a part. Tell the user
what is left out.

## 7. Render the video with the board

```sh
prc explain --source https://github.com/<owner>/<repo>/pull/<N> --board board.json
```

Add `--map <stored map.json>` when step 1 needed it. Pass `--out` as an
absolute path: a relative one currently crashes the renderer before the
first frame. A failed check stops the render with exit 2 and one line per
error: go back to step 5.
On success the command prints the `out` folder with the five product outputs
(`map.html`, `video.mp4`, `doc.html`, `card.png`, `comment.md`) plus evidence
(`map.json`, `board.json`, `run.json`).

## 8. Review your own frames and fix them

The checker verifies receipts and explicit assertions. Review prose accuracy and the picture separately.
Extract stills across the
video at 800 px wide and look at each one with the Read tool:

```sh
dur=$(python3 -c "import json; print(json.load(open('<out>/run.json'))['duration_seconds'])")
for i in 0 1 2 3 4 5 6 7; do
  t=$(python3 -c "print($dur * $i / 7)")
  ffmpeg -v error -y -ss "$t" -i <out>/video.mp4 -frames:v 1 -vf scale=800:-1 "frame0$i.png"
done
ffmpeg -v error -y -sseof -1 -i <out>/video.mp4 -frames:v 1 -vf scale=800:-1 frame_end.png
```

Every scene type must appear and read cleanly at 800 px: no text running
into the captions, no clipped callouts, no overlapping boxes. The still at
`t = 0` is usually blank (the title fades in); judge the title from a
later still. Also read `run.json`: `layout_warnings` must be empty and the
video duration must be close to `predicted_seconds` (about 15% with a
voice backend; wider gaps deserve a second render to rule out a stuck
scene). Fix the board for anything unreadable or wrong (fewer rows, shorter lines, shorter notes, a `hold`
for a picture that needs a beat), then repeat steps 5 to 8 until the
frames read cleanly.

## 9. Tell the user where the 5 files are

Report the `out` folder and its five product outputs:

- `map.html` is the browsable code map.
- `video.mp4` is the explainer video.
- `doc.html` is the written walkthrough.
- `card.png` is the PR card.
- `comment.md` is the comment draft.

Also report `map.json`, `board.json`, and `run.json` as evidence and run metadata.
Say how many tries `prc board check` needed, what the board
leaves out (step 6), and that prc posted nothing: the files are local,
and publishing the video or the comment text is the user's own step.

## 10. Gate one AI infographic per PR

Every explain run writes an image vocabulary first: read
`infographic/brief.json` in the output folder. It holds the title, the
allowed lines with their roles, the relations, the sorted allowed words,
the disclosure, the image profile, the fixed prompt rules, and the gate
constants. Node lines name code-derived relations. PRC selects up to three
exact added or removed production calls.
It can add one node counting distinct test callers with added exact calls to a displayed symbol.
Static calls do not prove test coverage.
When no such calls are available, it can extract Go call-to-typed-error mappings.
These require the full file at the pinned head revision and matching captured head diff rows.
Explain reads that source from its Git directory. Missing or mismatched source yields no mapping for that file.
Only supported call/error-return patterns in production Go files qualify. This does not build a Go call graph.
Changed Python function docstring summaries add `Before docs:` and `After docs:` excerpts from the complete pinned base and head files.
These are source documentation excerpts, not behavior inferred from board scenes.

Each relation joins two node lines. PRC publishes an image only when all
four OCR modes succeed, their readings cover every brief line, and no
unexcused foreign word appears at confidence 70 or more.
Every related node pair must also have connecting ink.
A brief without relations returns `flat` after passing word checks and cannot publish an infographic.

Keep prompt files and candidate images outside the explain output folder,
for example in `<out-root>/<slug>-infographic/`. Each explain run
replaces the whole output folder, so anything written inside it is lost.
Save the prompt file before generating, then generate one candidate at a
time with the baoyu-infographic technical profile from the brief
(structural-breakdown layout, technical-schematic style, 16:9, English).
Copy `prompt_rules` from the brief into the prompt, and list the relations
as "source -> target" pairs so the drawing shows the structure. Draw it as
a diagram: each node line alone in its own box, one straight arrow per
relation from source box to target box, dashed for a removed call, with
plain canvas between boxes. Place the headline above the diagram, the
legend near the arrows, and the facts, rows, verdict and disclosure
around it. Show every brief line exactly once, spelled exactly, and add
no other words or numbers. Icons are allowed beside text or elsewhere on
the canvas if they contain no letters or digits.
Keep them away from numerical fact lines and all other lines that contain numbers.
OCR can read an icon as a digit and reject the candidate.

Gate each candidate by re-running explain with repeatable flags, in the
order drawn:

```sh
prc explain --source https://github.com/<owner>/<repo>/pull/<N> --board board.json --infographic cand1.png --infographic cand2.png
```

PRC gates the candidates in argument order and publishes the first one
that passes as `infographic.png` with the exact candidate bytes.
`run.json` records the status and every attempt; `infographic/check.json`
records the verdict with missing and invented words, successful reading
modes and failed modes, and connecting-ink evidence for each relation.
PRC checks and hashes an unchanged copy of each
candidate. On a pass the comment
embeds `infographic.png` and the walkthrough shows it at the top. The card
stays in the bundle as the fallback.

On a failure, read `infographic/check.json` first. It names the words OCR
read that the brief does not hold and the lines OCR could not confirm.
A `flat` verdict means the word checks passed but the brief has no relations
or a required connection is missing. The `relations` rows identify missing connections.
For a relation-free brief, keep the card as the fallback. Board edits cannot invent code relations.
Change the next prompt to fix exactly those, for example by drawing an
unconfirmed line larger and away from icons, or by drawing the missing
arrow straight from one box to the other. Redraw from a new prompt
file, at most two times. Never
paint over text in an image editor: a redraw is a fresh generation from an
updated prompt. After that the card stays as the fallback, and the run
records the failed status.

Read the selected drawing by eye before presenting it. OCR can miss faint text.
Matching has no generic edit-distance tolerance. Prose permits only the explicit I/l glyph confusion after case normalization.
Non-code tokens that mix letters and digits permit the explicit I/l/1 and O/0 glyph confusions.
Code tokens and pure numbers match exactly after punctuation and case normalization.
Split or joined OCR words must still cover the ordered brief text.
The geometric gate proves connecting ink only. Confirm arrow direction, arrowheads, and correct endpoints by eye.
Also check dashed removed calls and extra connectors. Redraw a candidate with an incorrect or extra arrow.
