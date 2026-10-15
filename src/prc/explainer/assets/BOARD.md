# Writing a storyboard for a pull request video

You write one JSON file, the board. `prc explain --board` turns it into a narrated 1920×1080 video: a voice reads your sentences, captions show them, and an engine animates your scenes. `prc board check` refuses any board that puts something on screen the pull request does not contain.

The video sits in the pull request description on GitHub. The viewer is the reviewer: a developer who has never seen this pull request, watches once before reading the diff, maybe muted. After about a minute they should be able to say what behavior changed, for whom, which lines of code do it, and where to start reviewing. The video is a review aid, not an advertisement. Success is how well the reviewer understands the pull request, nothing else.

## Story rules

1. Behavior before code. Open on what a caller or user sees change, with one concrete case taken from the PR's tests or code: real fixture names, real values, real status strings. Show the code after the viewer already knows what it does.
2. Before, then after, in the same picture. Build a small picture of the situation, show what happened before the change, then replay the same picture under the new rule. Keep the groups, ids and columns identical between those scenes so only the changed part moves.
3. One idea per scene, in ASD-STE100 plain English. Write one to three sentences per scene. Each `say` entry holds one sentence, and each sentence makes one statement. An instruction (a sentence that starts with a verb such as Start, Open, Read or Check) has at most 20 words. A description has at most 25 words. Use the active voice: name who does the action ("the handler returns `not_found`", not "`not_found` is returned"). Use simple, common words with one meaning each. No hype words, no slogans, no taglines, no wordplay. Describe the pull request; do not sell it. `prc board check` fails each caption that breaks a rule and prints the scene, the sentence and the rule. It checks the caption text (`show`), counts a code span as one word, and flags a form of be or get followed by a past participle as passive.
4. Never invent. Every name, value, label and count on screen comes from the diff. If the PR adds no tests, do not mention tests. Counts come from checker facts, never typed by you.
5. Show code once, twice at most, with a diff scene of the lines that carry the change.
6. 45 to 150 seconds in total. `prc board check` prints a silent estimate and fails above 150 seconds. Spend the time on the behavior files: every changed code file, CI workflow and config file must be on screen (see "Behavior files" below). A short video that skips the CI change is wrong; cut a second before-and-after picture before you cut a behavior file.
7. Close with the evidence (the tests the PR adds, when it adds any), then the outro, which hands the reviewer off to the diff.
8. Narration may simplify, but each sentence must be something the cited lines show. When unsure, say less.

## The board

```json
{ "name": "myboard", "scenes": [ { "type": "title", "kicker": "Merged pull request", "say": ["..."] }, ... ] }
```

Every scene has a `type`, a `say` list and usually `cues`. Optional fields are `cite`, `hold` and `assert`.

`say` is a list of sentences. A sentence is a string, or `{"show": "caption text", "speak": "what the voice reads"}` when the voice needs a different spelling (for example "A.I." for "AI"). Text in backticks shows as code in the caption and is read without the backticks.

The caption keeps code names as written. The voice hears them split into words: `select_next_episode` becomes "select next episode", `ErrNotExist` becomes "error not exist", `s2e3` becomes "S 2 E 3" and `note.ts` becomes "note dot T S". When a name means something a listener would say differently, such as "season 2, episode 3", write it in `speak`. `prc listen` checks that a speech recognizer hears every code name the narration says.

`cues` start animations. Each cue is `{"at": <time>, "do": <verb>, ...}`. The verbs depend on the scene type and are listed below. Unknown verbs and unknown ids fail the check.

`cite` lists receipts as `{"line": "path:N", "match": "text"}`. The footer shows them. `path:N` is line N of the file after the change and must be an added line or an unchanged line inside a diff hunk. `path:-N` is line N of the file before the change and must be a removed line, and its `match` must not survive anywhere in the new version of that file. `match` must be an exact substring of the line.

`hold` adds seconds at the end of a scene, for a picture that needs a beat to land.

`assert` pins a number the narration speaks: `[{"fact": "tests_added", "equals": 3}]`. Use it whenever a sentence says a count.

### When a cue fires

- A phrase, the preferred form: `"at": "every company"` fires when the voice starts saying those words. The phrase must occur exactly once in the scene's spoken text, matched as whole words, ignoring case.
- `[k, f]` fires at fraction f of sentence k (0-based).
- A number fires that many seconds after the scene starts.

Notes also take `until`, in the same forms, to disappear.

### Facts the checker computes

`{tests_added}` new test functions, `{changed}` changed non-test functions, `{covered}` changed functions the board's receipts touch, `{added_total}` lines added. Use them inside `big` and stat `value` strings. A digit typed there by hand fails the check.

### Behavior files

A behavior file is a changed file, not deleted, whose change alters what the software does:

- code: `.py`, `.js`, `.ts`, `.tsx`, `.go`, `.sh`, `.sql`, `.rb`, `.rs` and other source files;
- CI: `.github/workflows/*.yml`, `.gitlab-ci.yml` and other CI config;
- config: `pyproject.toml` and other `.toml`, `.yml`, `.yaml`, `.ini`, `.cfg`, `.env.example`, `Dockerfile`, `Makefile`, `package.json`.

Tests (`tests/`, `test_*.py`, `*_test.py`, `*.test.*`), lock files (`uv.lock`, `poetry.lock`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `*.lock`), generated or binary files (images, PDFs, minified files, `dist/`, `build/`), evidence and reports (`artifacts/`, `reports/`, JSON data that is not config) and docs (`*.md`, `docs/`) are not behavior files.

`prc board check` fails when a behavior file is on no scene, and it lists every missing file. A scene shows a file through a diff scene's `file`, or through a `cite` line, a list item `cite`, or a receipt row `line` in that file. A behavior file with no diff line to quote (an empty file, a pure rename, an oversize file) cannot be cited, so the check does not require it.

## Scene types

### title

`{"type": "title", "kicker": "Merged pull request", "say": [...]}`. The engine fills in the PR title, size and number. No cues. Write the real state of the pull request in the kicker (Open or Merged); never copy the example word for word.

### groups, the behavior picture

Boxes holding short items: people, companies, slots, queue entries, states. Use it for the before and after.

```json
{ "type": "groups",
  "groups": [
    { "id": "pa", "title": "Person A", "sub": "two current jobs", "col": 0, "row": true, "ground": "PROFILE_A",
      "items": [ { "id": "a", "text": "A", "ground": "PROFILE_A" } ] },
    { "id": "cob", "title": "co-b", "sub": "max 3 invitations", "col": 1, "row": true, "ground": "co-b",
      "items": [ { "id": "b1", "text": "B", "kind": "slot", "ground": "PROFILE_B" },
                 { "id": "bx", "text": "A", "outside": true, "tone": "bad", "ground": "PROFILE_A" } ] } ],
  "cite": [ { "line": "tests/e2e_x.py:1061", "match": "claims = {PROFILE_A: employer_set(\"co-a\", \"co-b\")" } ],
  "say": ["..."], "cues": [ { "at": "Nothing stopped A", "do": "fly", "from": "a", "to": "bx", "arc": 120 } ] }
```

A group has `id`, `title`, an optional `sub`, `items`, `row` (true lays items side by side, false stacks them), `col` (0 is the left column, then 1 and 2; groups in one column stack top to bottom) and an optional `ground`.

An item has `id` and `text` (a letter, a short name or a value). Optional fields are `kind: "slot"` (a dashed empty seat until filled), `outside: true` (drawn just outside its group), `tone` (bad, good, info or blue), `label` (a small tag inside the pill) and `ground`.

Grounding works like this. Every item's `text`, or its `ground` when the text is a stand-in such as "A", must appear on one of the scene's `cite` lines. So must every group's `ground`. Cite the test or code lines those names come from. Titles, subs and notes are not checked, so keep them literally true.

Layout is automatic, so never give pixels. Use two or three columns, at most three groups per column and at most five items per row group.

Cues:

- `show` with `ids` and an optional `step` fades in groups or items, staggered by `step` seconds (default 0.12). Anything never shown by a cue appears when the scene starts.
- `fill` with `ids` makes the text of slots appear.
- `fly` with `from`, `to` and optional `arc` (pixels of lift), `dur` and `fade` moves a copy of an item to another item. Use it only for a real copy of the same value: the source and target items must have the same `text`. A fly between two different texts would rename the box mid-flight, so the check fails it and asks for an `arrow`. The target fills when it lands and flashes. With `fade: true` the copy vanishes on arrival.
- `arrow` with `from`, `to` (item or group ids), an optional `label` under 30 characters, `tone`, and optional `until` draws an arrow with an arrowhead from the edge of the source box to the edge of the target box. Nothing moves and no text changes. Use it to show that one thing feeds, calls or becomes another.
- `tone` with `id` or `ids` and `tone` recolors a group border or an item.
- `strike` with `id` strikes an item through. It does not reveal the item: an item with no `show` cue is on screen from the start, so give it a `show` cue if it should appear later.
- `mark` with `id`, `text` ("✗" or "✓") and `tone` stamps a badge on a box corner.
- `note` with `id`, `text`, `tone`, `side` ("right", "above" or "below", default below) and optional `until` shows a callout under 30 characters.

### diff, the code, quoted from the diff

```json
{ "type": "diff", "file": "src/linkedin_mdp_mcp/invitation_shortlist.py", "label": "The change, line for line",
  "lines": ["1030", "-1018", "1031", "1032", "1033", {"ref": "-1021", "step": 2}, {"ref": "1034", "step": 2}, {"ref": "1035", "step": 2}],
  "say": ["...", "...", "..."],
  "cues": [ {"at": "every company", "do": "step", "n": 1},
            {"at": "uses up a slot", "do": "step", "n": 2},
            {"at": "each of them", "do": "note", "line": "1035", "text": "−1 slot at each employer", "tone": "good"} ] }
```

You list line refs, never code. The text comes from the diff. "N" is a line after the change (added or unchanged) and "-N" is a removed line. List refs top to bottom in diff order, which puts a removed line before the line that replaces it. Skipped lines show as a ⋯ row. At most 12 rows are allowed, ⋯ rows included, and the code box must end above the captions: the font shrinks to fit (22 to 40 px) and the build warns below 28 px, so prefer fewer and shorter lines.

Replacement rows open 0.55 seconds after their step cue. Row reveals take another 0.45 seconds.
Each selected row must finish its reveal before the scene's settled frame, 0.5 seconds before its end.
Wrapped visual lines count toward the height limit. Split a diff scene if its code block cannot fit above the captions.
The checker tests silent timing. Rendering checks actual narration timing before encoding.
Move a late cue earlier or increase the scene's `hold`. Coverage excludes rows that miss this interval.
The same join validator checks quoted text before rendering and after syntax highlighting.
Empty diff scenes fail. Blank rows fail when they cannot support the selected common indent.

The scene opens on the old code: unchanged lines plus removed lines. At step k the removed lines of step k tint red and stay on screen, and the added lines of step k slide in beneath them in green. A removed line is paired with its replacement and the changed words are marked in both. Long lines wrap with a hanging indent. Each row shows its line number, so the reviewer can find it in the diff. Added and removed lines take step 1 unless you set `step`. `step: 0` on an added line shows it from the start, which suits a PR that only adds code. Every step number in use needs exactly one `step` cue. A `note` pins a callout to one listed line, by its ref. Keep notes under 30 characters. A note that cannot fit beside its line moves below the row and the check flags it, so pick short lines for noted rows.

### list

Tests or concrete cases, each quoted from a line.

```json
{ "type": "list", "big": "{tests_added}", "label": "new tests", "tone": "good", "mark": "✓", "code": false, "more": null,
  "items": [ { "text": "exact substring of the cited line", "cite": "tests/test_x.py:42" } ],
  "cues": [ { "at": [0, 0.1], "do": "items", "step": 0.3 } ] }
```

Each item's `text` must be an exact substring of its `cite` line, such as a test's name or docstring. `big` is optional. Leave it out when no fact counts what the list shows: the number of items you picked is not a fact about the pull request, and a viewer reads a big number as the total. `code: true` renders items as code. `more` is a string shown under the list, or null. With `big: "{tests_added}"` and fewer items than new tests, leaving `more` out shows "+ N more". The `items` cue is required.

### bars

Where the added lines went. Every file of the PR must sit in exactly one bar. A path ending in "/" matches a folder. Values and the headline are computed.

```json
{ "type": "bars", "label": "lines added",
  "bars": [ { "id": "core", "label": "report logic", "paths": ["src/"], "tone": "blue" },
            { "id": "rest", "label": "tests, docs, evidence", "paths": ["tests/", "docs/", "PLANS.md"], "tone": "grey" } ],
  "cues": [ { "at": [0, 0.1], "do": "bars", "step": 0.2 }, { "at": "...", "do": "dim", "keep": ["core"] },
            { "at": "...", "do": "note", "id": "core", "text": "..." } ] }
```

### stats

Give each card a `card` cue with its zero-based `i`. The checker rejects any card without a reveal cue.

`{"type": "stats", "cards": [{"value": "{tests_added}", "label": "new tests", "tone": "good"}], "cues": [{"at": "...", "do": "card", "i": 0}]}`. Values are fact strings.

### outro

Include `l1`, `l2`, and `cmd` cues. The checker rejects missing reveal cues because those elements would stay invisible. `fine` is optional small print under the command; when absent the checker fills an empty default and the video shows nothing there.
Each outro reveal takes 0.5 seconds. Fine print starts 0.5 seconds after the command and takes another 0.5 seconds.
All provided text must finish its reveal before the settled frame. The outro has a longer tail when it contains fine print.

```json
{ "type": "outro", "l1": "first line", "l2": "second line", "fine": "small print", "nocap": true,
  "say": [ "l1 and l2 read as one sentence or two" ],
  "cues": [ { "at": [0, 0.0], "do": "l1" }, { "at": [0, 0.5], "do": "l2" }, { "at": [0, 0.9], "do": "cmd" } ] }
```

`l1` and `l2` hand the reviewer off to the diff. `l1` says what changed in one plain sentence. `l2` names where to start reviewing (a file and what it decides) or what the PR leaves untested, whichever matters more for review. Both must be true to the diff. Never a slogan or a quotable line: "Unknown stays unknown" and "Evidence goes in, one report comes out" are wrong; "Report rows now carry the prospect's creation time" and "Start at the date helper in report.py; future timestamps are untested" are right (examples of form, not facts). The command line under them is filled in.

## Tools

All commands read the map you pass.

- `prc board show --map <map.json> [path-substring ...]` prints the diff with the ref of every line.
- `prc board find --map <map.json> "needle" [...] [--path substr]` prints the lines that contain a needle, with refs.
- `prc board coverage <board.json> --map <map.json>` prints how many changed lines are on screen.
- `prc board check <board.json> --map <map.json>` checks the board. Fix what it prints and run it again until it prints receipts verified, a silent estimate, and the changed-line coverage.
- `prc board preview <board.json> --map <map.json> [--out dir] [--git-dir dir]` renders two stills per scene into `<out>/<name>/keys/` (`NNa` mid-scene, `NNb` near the scene's end) without encoding a video, and prints layout warnings. It needs the cached Chromium but no ffmpeg, and writes no video or narration audio. `--git-dir` pins highlighting to a git checkout; without it (or a source repo) colors fall back to hunk text. Open the stills in an image viewer.
- `prc explain --source <PR-URL> --board <board.json> --voice none --out <dir>` renders the full silent video.

A good reference board uses phrase cues, automatic group layout, and one diff scene of the lines that carry the change. Never place groups in pixels: give columns, rows, and items, not `x`, `y` or `w`.

## High-level infographic from a scene

Set the board's `infographic` field to `{"mode":"storyboard-flow","scene":1}` to select an existing groups scene.
The infographic uses that scene's group titles as nodes and its `fly` and `arrow` cues as directed relationships.
Each fly or arrow must join cited, grounded boxes in distinct groups. Select one to three distinct relationships.
Give each item a unique ID. Use a headline that differs from every group title.
Give each group a unique title after case and punctuation normalization. Keep the fitted headline distinct from each title.
The video, clickable page, and infographic then share these authored endpoints and directions.
The legend says these are storyboard flows. They are not inferred call edges or proof of execution.
Review the semantic titles and narrated flow against the original source before drawing.
The receipt checker validates item ground and citations, but does not prove every title's meaning.
Boards without this selector keep the source-derived call and documentation brief.

## Panels infographic

Set the board's `infographic` field to panels mode for a blueprint picture of the change in titled panels:

```json
{ "mode": "panels",
  "headline": "Missing references get an explicit result",
  "subtitle": "One status check in the handler",
  "panels": [ { "title": "BEFORE", "lines": ["404 had no name", "Callers guessed the meaning"] },
              { "title": "SWITCH", "lines": ["Handler checks the status", "Returns not_found"] },
              { "title": "PROOF",  "lines": ["One test covers 404"] } ],
  "footer": ["Start at the status check"] }
```

Write 2 to 4 panels, each with a title and 1 to 4 lines. A title or line has at most 6 words. Give each panel a unique title. The footer holds 0 to 3 short items. The brief numbers the panel headers ("1. BEFORE", "2. SWITCH") and adds the disclosure line to the footer bar. All the text, disclosure and key included, has at most 90 words.

Each panel has one meaning color. The video and the page use the same five colors:

| `tone` | Key word | Color | Use it for |
|---|---|---|---|
| `problem` | Problem | vermillion #D55E00 | the state before, a bug, a removed part |
| `change` | Change | orange #E69F00 | what the pull request changes |
| `part` | Part | sky blue #56B4E9 | the parts or components involved |
| `proof` | Proof | bluish green #009E73 | tests, results, added evidence |
| `context` | Context | grey #8A93A6 | background that did not change |

Set `"tone"` on a panel to pick its color. Without it, the brief reads the title: BEFORE gives problem, CHANGE or SWITCH gives change, PROOF or TESTS gives proof, PARTS gives part, and anything else gives context. The brief adds one key word per tone it uses to the footer bar, and the gate requires those words too.

The brief's permitted text is exactly these strings: the headline, the subtitle, the numbered panel headers, the panel lines, the footer items, the key words and the disclosure. Nothing comes from the pull request title or the checker verdict. The gate passes an image only when OCR reads every line and finds no other word.

The brief's `prompt` (also written to `infographic/prompt.md`) asks for the baoyu-infographic technical profile: a technical-schematic blueprint style, a structural-breakdown layout, landscape 16:9, numbered panel headers, one simple icon per panel, one arrow from each panel to the next, and a footer bar. The brief records those arrows as relations from panel i to panel i + 1 and no other pair.

The gate does not check the arrows between panels. A panel frame holds many text lines, so the ink test that joins two text boxes is not reliable there. Check by eye that each panel points to the next before you publish.

Panel text is not checked against the diff. Keep every line literally true to the pull request, and use the same names the video uses.

## reading, the page's full explanation

The video picks the changes that carry the story. The page goes deeper: its reading path explains every changed unit. A unit is one changed function, method or class, the changed module lines outside them, one settings block, job or step of a CI workflow, or one other changed file. Run `prc board units --map <map.json>` to list every unit with its id.

```json
"reading": [
  { "units": ["src/app/report.py::render_report"], "say": "The function builds the report text from the counts." },
  { "units": [".github/workflows/report.yml::step Update the doc"], "say": ["The step runs the report script each morning.", "It reads the token from a secret."] },
  { "units": ["tests/test_report.py::test_empty", "tests/test_report.py::test_full"], "say": "Two tests check an empty report and a full report." }
]
```

`prc board check` checks the list when the board has one:

- Every unit has exactly one entry. A missing, repeated or unknown id fails.
- `say` is one or two sentences, and each follows the narration rules: one statement, active voice, ASD-STE100 length.
- An entry holds units of one role. Code, CI and config entries stay in one file and hold at most 4 units, so each function gets its own words. Test, docs and data entries may join files.
- Write the entries in reading order: the entry point first, then what it calls, then the tests.

The page lists the entries by role (code, CI, configuration, tests, docs, other files). Each unit name opens its first changed line on GitHub, and a fold shows its changed lines.
