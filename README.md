# prc explain

`prc explain` turns a pull request and an agent-authored board into a local video, written walkthrough, map, card, and comment draft.

Code rows come from the captured diff. Your coding agent writes the explanation.

This is a release candidate. Release remains blocked by evaluation and human, license, and publishing gates.

## Install from this checkout

Python 3.12 is required for Kokoro. The base package supports Python 3.12 and later.
Git is required to acquire PR code. Public GitHub PRs need no token.
For private repositories or higher rate limits, set `GITHUB_TOKEN` in your environment.

```sh
uv sync
```

The base dependencies include NumPy, Pygments, tree-sitter, and its Python, JavaScript, and TypeScript grammars.
See [pyproject.toml](pyproject.toml) for versions and extras.

Video rendering needs Playwright, Chromium, `ffmpeg`, and `ffprobe` on `PATH`.
Card rendering also needs Playwright and Chromium.
The following commands install the video extra and Chromium, then report available tools.

```sh
uv sync --extra video
uv run playwright install chromium
uv run prc doctor
```

Install `ffmpeg` and `ffprobe` with your system package manager if `doctor` reports them missing.
Missing voice backends do not prevent a silent render with `--voice none`.

## Render the offline example

This example uses a hand-authored test board and a local fixture. It does not read GitHub.

```sh
uv run prc board check tests/data/boards/shop.json --source fixture:shop
uv run prc explain --source fixture:shop --board tests/data/boards/shop.json --voice none --out "$PWD/artifacts/explain"
```

The CLI prints the output folder and file paths as JSON.
The silent video still needs Chromium and ffmpeg.
Fixture output demonstrates the renderer. It is not evidence about a live PR.

## Five outputs from one board

With a valid board and the rendering dependencies available, `explain` writes these outputs.

| Output | File | Purpose |
|---|---|---|
| Interactive map | `map.html` | Browse changed symbols, calls, tests, and diffs. |
| Explainer video | `video.mp4` | Watch the board with narration or silent captions. |
| Written walkthrough | `doc.html` | Read the same board and follow code receipts. |
| PR card | `card.png` | View the headline and computed map statistics. |
| PR comment draft | `comment.md` | Review text and a computed Mermaid diagram before posting. |

The folder also contains `map.json`, the checked `board.json`, and `run.json`.
`run.json` records the map source, board check, voice backend, timings, and layout warnings.
Output folders include the PR identity and the first 12 characters of the captured head SHA.
Each successful rerun replaces the complete generated folder. A boardless rerun removes earlier video and walkthrough files.
Handled rendering failures leave the prior successful folder intact. Treat that folder as generated output, not a place for manual files.
Publication uses a short lock and staged directory replacement with rollback. A process kill during replacement can leave a recovery backup and lock.
Inspect those paths before restoring a backup or removing a lock. Publication does not guarantee uninterrupted reads during replacement.
A card-render failure can leave `card.png` absent. Inspect the printed `card` value and `run.json` warnings.

prc writes local files. It does not post comments, upload videos, or publish a repository.

## Your agent writes the board

`explain` does not call an LLM or write the story for you.
Your coding agent reads the map and diff, selects evidence, and writes `board.json`.
The packaged [prc-explain skill](src/prc/skill/SKILL.md) describes that workflow.

Install the instructions for your agent with one of these commands.
The installer asks before writing to its default destination.

```sh
uv run prc skill install claude
uv run prc skill install codex
```

Claude's default destination is `~/.claude/skills/prc-explain/SKILL.md`.
Codex's default destination is an added section in the current directory's `AGENTS.md`.
`--dest` selects a different destination folder.
The agent has its own model and authentication requirements. prc itself needs no model API key.

For a real PR, first acquire the map without a board.

```sh
uv run prc explain --source https://github.com/komaksym/linkedin-mdp/pull/12 --voice none
uv run prc board guide
```

Use the printed `map` path for the board tools.
In the following commands, `map.json` and `board.json` are your local files.

```sh
uv run prc board show --map map.json
uv run prc board find --map map.json "date_added"
uv run prc board check board.json --map map.json
uv run prc board coverage board.json --map map.json
uv run prc explain --source https://github.com/komaksym/linkedin-mdp/pull/12 --map map.json --board board.json --voice none --out "$PWD/artifacts/explain"
```

`--map` uses a stored capture and skips live acquisition. It does not establish that the PR is still current.
Its run manifest reports `map_source: stored` and a null `live_head_sha`. The captured SHA remains in `stored_head_sha`.
For full-file highlighting offline, `--git-dir` can supply a bare repository containing the captured base and head commits.
Without those blobs, the renderer uses the stored diff for highlighting.

## What the checker proves

prc computes symbols, call relationships, diff rows, and statistics from captured code and provider data.
The parser supports Python, JavaScript, TypeScript, and TSX. Static call analysis can miss dynamic calls or use name-only matches.
A missing direct test link does not prove that a function has no test coverage.

The agent authors the scene order, narration, titles, labels, notes, and interpretation of behavior.
`board check` checks cited lines, exact substrings, supported symbols and edges, cue references, and explicit numeric assertions.
A failed board check stops the board render.

These checks do not prove that the prose is true.
Titles, subtitles, and notes can contain unchecked claims. A correct citation can still support a wrong interpretation.
Review the narration against the code and inspect the rendered frames.
`board coverage` identifies omitted changed files and symbols. Coverage is not proof that the story explains them correctly.

## Map-only fallback

Without a board, `explain` writes the map, comment draft, and run metadata.
It attempts the card, but does not write a video or walkthrough.
Use `--voice none` to avoid voice backend selection for this mode.

For a map that needs no video or voice dependencies, use the existing `map` command.

```sh
uv run prc map --source fixture:shop
uv run prc map --source https://github.com/komaksym/linkedin-mdp/pull/12
```

`map` writes `index.html` and `map.json` under `artifacts/maps/` and prints their paths.
`map --video` adds the older, silent `tour.mp4` and a map screenshot `card.png`.
That tour needs the video dependencies. It is separate from the board-based explainer.

## Voice choices and downloads

`--voice auto` selects an available backend in this order: Kokoro, macOS `say`, then `none`.
Availability does not guarantee that synthesis succeeds.
Choose `--voice none` explicitly for silent output and estimated timing without Kokoro imports.
`--voice say` uses `/usr/bin/say` on macOS and ffmpeg for audio conversion.

Kokoro needs the optional `voice` extra and Python 3.12 with this package's Python requirement.
Installing that extra brings PyTorch and spaCy. First use can download `en_core_web_sm` and Kokoro weights.
Review those downloads before choosing voice installation.
To keep the video extra when installing voice, use `uv sync --extra video --extra voice`.
Kokoro also needs the eSpeak phonemizer runtime. The backend currently defaults to Homebrew paths on macOS.
Set `ESPEAK_DATA_PATH` and `PHONEMIZER_ESPEAK_LIBRARY` for a different installation.

## Evaluation and release gates

The [current scoreboard](eval/runs/2026-10-06-full/scoreboard.md) records checks and video artifacts.
The final saved grades contain 480 answers across C1 through C5.
C1 card scored 20.8%, C2 comment 25.0%, C3 video 46.9%, C4 doc 69.8%, and C5 map 17.7% correct.
There were 44 wrong answers. These results fail the frozen release targets.
The frozen C0 baseline scored 32.3% correct. Its author also read and graded it, so independent validation remains required.

Release remains blocked until the [evaluation requirements](docs/mvp/EVAL.md) pass and the [human session](eval/human/2026-10-07.md) is complete.
The human review must assess correctness and usefulness, including the narration and muted video.
The user must choose a license and repository name, review private content and history, and approve each publishing action.
The [Stage 9 plan](docs/mvp/PLAN.md#stage-9-human-session-readme-launch-drafts) defines those gates.
The [launch thread](docs/launch/TWEET.md) is an unpublished draft.

## Other commands and verification

`brief` computes a text brief. `review`, `status`, and `decide` retain the earlier review and freshness workflow.
`eval-analyze` handles the earlier paired evaluation format, separate from the MVP comprehension scoreboard.
Run `uv run prc --help` and a command's `--help` for its arguments.

The repository verification command is:

```sh
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest && uv build
```

`tests/test_e2e_explain.py` drives the CLI with `fixture:shop` and `--voice none`.
Successful video tests copy their output under `artifacts/e2e/explain/`.
They skip when ffmpeg or Chromium is unavailable. A skipped test does not verify a rendered video.

To verify the release package without unrelated local experiments, run `bash scripts/verify-release.sh`.
It saves check logs, E2E output, a clean wheel install, and CLI media under `artifacts/release/verify/`.
