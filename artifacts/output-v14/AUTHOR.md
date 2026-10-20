# Author one PRC v14 storyboard

You write one storyboard (board JSON) for one merged pull request. PRC turns the board into a narrated video, a clickable page, and an infographic. A reviewer opens it before the diff. Success is how well the reviewer understands what the pull request changes and where to start reviewing.

v5 adds three things to v4: a reading list that explains every changed unit on the page, five meaning colors in the infographic, and a check of the base version before you describe the state before the change.

## Inputs

- Worktree: `/Users/koval/dev/prc/.claude/worktrees/v3-study`. Run every command from there.
- Snapshot id `SID` and PR URL: given in your task message.
- Map: `artifacts/output-v14/prepared/SID/map.json` (the pinned diff).
- Git dir: the `git_dir` value in `artifacts/output-v14/prepared/SID/provenance.json`. The map holds `base_sha` and `head_sha`.

## Output

- Write the board to `artifacts/output-v14/boards/SID/board.json`. Set its `name` to `SID`.
- Write `artifacts/output-v14/boards/SID/log.json`: `{"check_runs": <number of prc board check runs>, "final_check": "pass" or "fail", "notes": "<one sentence>"}`.

## Steps

1. Read the full writing guide: `uv run prc board guide`. Follow every rule in it. It is the authority.
2. Read the diff: `uv run prc board show --map <map>`. Use `uv run prc board find` for line refs.
3. Read the base version of every modified file before you describe the state before the change: `git --git-dir <git_dir> show <base_sha>:<path>`. In v4, every model called an existing workflow "missing" because it read only the diff. Never say a thing did not exist unless the base shows that.
4. List the units: `uv run prc board units --map <map>`.
5. Write the board. Requirements in addition to the guide:
   - Put every behavior file on screen (code, CI workflows, config). The check fails otherwise.
   - Write ASD-STE100 plain English: one statement per sentence, active voice, simple common words, instructions at most 20 words, descriptions at most 25 words.
   - Use an `arrow` cue when two different names are related. Use `fly` only to copy the same value.
   - Keep the video between 45 and 150 seconds. The video tells the main story. It does not need every file.
   - Add a `reading` list (see the guide's "reading" section) with one entry for every unit that `prc board units` prints. Write the entries in reading order: entry point first, then what it calls, then CI, then tests, then docs. Each sentence says what the unit does in this pull request, in plain words a Python developer understands without the code. Name the real behavior, value or condition. Do not write filler such as "This function is updated."
   - Add an `infographic` field in `panels` mode (see the guide's "Panels infographic"): 3 or 4 panels, each with 2 to 4 lines of at most 6 words. Give each panel a `tone` (problem, change, part, proof, context) so the picture uses at least three meaning colors. A reader who never saw the PR must understand the change from the picture alone, so name the real component, the real behavior and the real result. Every line must be true to the diff.
6. Run `uv run prc board check <board> --map <map>`. Fix every failure. Repeat until it passes. Count the runs.
7. Run `uv run prc board preview <board> --map <map> --out /private/tmp/prc-v14-preview/SID --git-dir <git_dir>` once. Look at the stills and fix layout warnings that make text unreadable.

## Limits

- Write only inside `artifacts/output-v14/boards/SID/` and `/private/tmp/prc-v14-preview/`. Do not edit source code, the guide, other boards, or the map.
- Do not read `artifacts/output-v4/boards/`, `artifacts/output-v4/final/` or `artifacts/output-v4/judge/`.
- Never invent a name, value, or count. When unsure, say less.
- `uv run` and `git --git-dir` need paths outside the sandbox. Request escalation when the sandbox blocks a command.

## Final message

The board path, the last 5 lines of the final `prc board check` output, the number of check runs, and the number of reading entries and units. If the check never passed, say FAILED and give the last error.

