# Writing a storyboard for a pull request video

You write one JSON file, the board. `build.py` turns it into a narrated 1920×1080 video: a Kokoro voice reads your sentences, captions show them, and an engine animates your scenes. `check.py` refuses any board that puts something on screen the pull request does not contain.

The video sits in the pull request description on GitHub. The viewer is the reviewer: a developer who has never seen this pull request, watches once before reading the diff, maybe muted. After about a minute they should be able to say what behavior changed, for whom, which lines of code do it, and where to start reviewing. The video is a review aid, not an advertisement. Success is how well the reviewer understands the pull request, nothing else.

## Story rules

1. Behavior before code. Open on what a caller or user sees change, with one concrete case taken from the PR's tests or code: real fixture names, real values, real status strings. Show the code after the viewer already knows what it does.
2. Before, then after, in the same picture. Build a small picture of the situation, show what happened before the change, then replay the same picture under the new rule. Keep the groups, ids and columns identical between those scenes so only the changed part moves.
3. One idea per scene. One to three sentences per scene, each under 20 words, in plain words. No hype words, no slogans, no taglines, no wordplay. Describe the pull request; do not sell it.
4. Never invent. Every name, value, label and count on screen comes from the diff. If the PR adds no tests, do not mention tests. Counts come from checker facts, never typed by you.
5. Show code once, twice at most, with a diff scene of the lines that carry the change.
6. 45 to 75 seconds in total. `check.py` prints an estimate.
7. Close with the evidence (the tests the PR adds, when it adds any), then the outro, which hands the reviewer off to the diff.
8. Narration may simplify, but each sentence must be something the cited lines show. When unsure, say less.

## The board

```json
{ "name": "mdp12", "scenes": [ { "type": "title", "kicker": "Open pull request", "say": ["..."] }, ... ] }
```

Every scene has a `type`, a `say` list and usually `cues`. Optional fields are `cite`, `hold` and `assert`.

`say` is a list of sentences. A sentence is a string, or `{"show": "caption text", "speak": "what the voice reads"}` when the voice needs a different spelling (for example "A.I." for "AI"). Text in backticks shows as code in the caption and is read without the backticks, so give the voice words it can pronounce.

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

## Scene types

### title

`{"type": "title", "kicker": "Open pull request", "say": [...]}`. The engine fills in the PR title, size and number. No cues.

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
- `fly` with `from`, `to` and optional `arc` (pixels of lift), `dur` and `fade` moves a copy of an item to another item. The target fills when it lands and flashes. With `fade: true` the copy vanishes on arrival.
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

The scene opens on the old code: unchanged lines plus removed lines. At step k the removed lines of step k tint red and stay on screen, and the added lines of step k slide in beneath them in green. A removed line is paired with its replacement and the changed words are marked in both. Long lines wrap with a hanging indent. Each row shows its line number, so the reviewer can find it in the diff. Added and removed lines take step 1 unless you set `step`. `step: 0` on an added line shows it from the start, which suits a PR that only adds code. Every step number in use needs exactly one `step` cue. A `note` pins a callout to one listed line, by its ref.

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

`{"type": "stats", "cards": [{"value": "{tests_added}", "label": "new tests", "tone": "good"}], "cues": [{"at": "...", "do": "card", "i": 0}]}`. Values are fact strings.

### outro

```json
{ "type": "outro", "l1": "first line", "l2": "second line", "fine": "small print", "nocap": true,
  "say": [ "l1 and l2 read as one sentence or two" ],
  "cues": [ { "at": [0, 0.0], "do": "l1" }, { "at": [0, 0.5], "do": "l2" }, { "at": [0, 0.9], "do": "cmd" } ] }
```

`l1` and `l2` hand the reviewer off to the diff. `l1` says what changed in one plain sentence. `l2` names where to start reviewing (a file and what it decides) or what the PR leaves untested, whichever matters more for review. Both must be true to the diff. Never a slogan or a quotable line: "Unknown stays unknown" and "Evidence goes in, one report comes out" are wrong; "Report rows now carry the prospect's creation time" and "Start at the date helper in report.py; future timestamps are untested" are right (examples of form, not facts). The command line under them is filled in.

## Tools

Run these from the `explainer` directory.

- `python3 show.py <map.json> [path-substring ...]` prints the diff with the ref of every line.
- `python3 find.py <map.json> "needle" [...] [--path substr]` prints the lines that contain a needle, with refs.
- `python3 check.py <board.json> <map.json>` checks the board. Fix what it prints and run it again until it prints "receipts verified".
- Optional preview: `<python with playwright> build.py <board.json> <map.json> out/<name>-keys --keys-only` renders two stills per scene into `out/<name>-keys/keys/` (`NNa` mid-scene, `NNb` near the scene's end) and prints `layout:` lines for boxes that run into the captions. It needs speech and a headless browser, so run it with the sandbox disabled. Look at the stills with the Read tool.

`boards/mdp17b.json` is the reference board, with phrase cues, automatic group layout and a diff scene. `boards/mdp17.json` and `boards/mdp3.json` are older and place groups in pixels. Do not copy their `x`, `y` or `w`.
