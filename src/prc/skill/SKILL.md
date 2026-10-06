---
name: prc-explain
description: Write a board.json storyboard for one pull request so prc can render its explainer video.
---

# prc-explain: write the board for one pull request video

You write one JSON file, the board. `prc` turns it into a narrated 1920x1080
video plus a map page, and checks every fact in it. `prc` never posts
anything to GitHub: it only writes local files. Say that to the user at
the end.

The viewer is the reviewer: a developer who has never seen this pull
request, watches once before reading the diff, maybe muted. After about a
minute they should say what behavior changed, for whom, which lines of
code do it, and where to start reviewing. Describe the pull request; do
not sell it. One idea per scene, one to three sentences per scene, each
under 20 words, in plain words. No hype words, no slogans, no taglines,
no wordplay.

## 1. Render the deterministic outputs and read `map.json`

Run `prc doctor` first. If it reports anything missing, install it and
re-run until every line says ok. Then render the PR without a board:

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

Add `--map <stored map.json>` when step 1 needed it. A failed check
stops the render with exit 2 and one line per error: go back to step 5.
On success the command prints the `out` folder with the 5 files:
`map.json`, `map.html`, `board.json`, `video.mp4` and `run.json`.

## 8. Review your own frames and fix them

The checker proves the facts, not the picture. Extract stills across the
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
into the captions, no clipped callouts, no overlapping boxes. Also read
`run.json`: `layout_warnings` must be empty and the video duration must
be within 10% of `predicted_seconds`. Fix the board for anything
unreadable or wrong (fewer rows, shorter lines, shorter notes, a `hold`
for a picture that needs a beat), then repeat steps 5 to 8 until the
frames read cleanly.

## 9. Tell the user where the 5 files are

Report the `out` folder and its 5 files: `map.json` (the checked facts),
`map.html` (the browsable map), `board.json` (the story you wrote),
`video.mp4` (the narrated video) and `run.json` (check result, timings,
versions). Say how many tries `prc board check` needed, what the board
leaves out (step 6), and that prc posted nothing: the files are local,
and publishing the video or the comment text is the user's own step.
