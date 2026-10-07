# Build plan: the prc MVP, end to end

## Summary

prc will turn one pull request into five outputs: a map, a narrated video, a written walkthrough, a PR card and a PR comment with a diagram. The user's own coding agent writes the story, and prc checks cited code and computed facts in it. The stages below take the working prototypes to an installable tool. Each stage ends in a check that you run and an output file that you look at. The last stage scores the tool on the 12 open `komaksym/linkedin-mdp` PRs with the evaluation in `EVAL.md`.

Read `START-HERE.md` and `DECISIONS.md` first. This plan does not repeat their reasons.

## What exists today (measured 2026-10-06)

- **The `prc` package.** `main` is at `c54b960`. The verify command passes: ruff, format, mypy, 320 tests and build, in 2 min 44 s. Commands are `map`, `brief`, `review`, `status`, `decide` and `eval-analyze`.
  - `prc map` parses base and head with tree-sitter. It writes `map.html` and `map.json`. With `--video`, it also writes a 30 s silent tour and `card.png`.
  - `prc map` ran live on open PR 19 in 14 s and produced 311 changed symbols and 639 calls.
- **The explainer prototype** (`prototypes/explainer/`, its own git repo).
  - `check.py` validates a board against `map.json`.
  - `build.py` renders the board with Kokoro, Chromium and ffmpeg.
  - `engine.js` draws the scenes. `BOARD.md` is the guide for board writers.
  - There are boards for PRs 12, 14, 17, 4 and 3. The PR 12 build takes 77 s and gives a 63.4 s video.
- **Spikes, tested.** `prototypes/explainer/spike/` holds the tree-sitter highlighter, line pairing with word marks, and soft wrap.
- **The diff scene spec.** `docs/mvp/diff-scene.md` is complete, with failure modes per step.

## The target shape

```
prc explain --source <PR URL | github:owner/repo#N | fixture:name>
            [--map map.json] [--board board.json] [--out artifacts/explain] [--voice kokoro|say|none]
  → <out>/<owner>-<repo>-<N>-<head12>/
      map.json  map.html  card.png  comment.md          (always)
      board.json  video.mp4  doc.html                   (with --board, after the check passes)
      run.json                                          (paths, counts, timings, versions)

prc board guide                 prints BOARD.md
prc board show  --source X [path ...]     the diff, with the ref a board uses on each line
prc board find  --source X "needle" ...   refs of lines that contain the needle
prc board check board.json --source X     exit 0 pass, exit 2 with one line per error
prc board coverage board.json --source X  what the board covers and what it leaves out
prc doctor                      checks ffmpeg, Chromium, the voice backend, espeak-ng, and whether a token is set (never its value)
prc skill install claude|codex --dest <dir>   installs the board-writer skill for the user's agent
```

`--map` skips acquisition and uses a stored `map.json`. Use it when a board was written against an older head. `prc map` writes `index.html` today. `prc explain` copies the map page to `map.html` in its own folder and leaves `prc map` unchanged.

Package layout:

```
src/prc/explainer/
  check.py      from prototypes/explainer/check.py
  highlight.py  from spike/tokens.py and spike/keys.py split()
  diffrows.py   from spike/pairs.py and spike/wrap.py
  timing.py     cue resolution, from build.py
  voice.py      kokoro | say | none
  render.py     Chromium seek and ffmpeg, from build.py
  doc.py        doc.html
  assets/       engine.js, engine.css, doc.css, BOARD.md
src/prc/presentation/card.py      the PR card
src/prc/presentation/comment.py   comment.md and the Mermaid block
src/prc/skill/SKILL.md            the board-writer skill
```

The names `presentation/build.py`, `presentation/check.py` and `presentation/doc.py` already exist for the older `review` command. Keep the explainer in its own `explainer/` package so that the names do not collide.

## Order and parallel work

```
Stage 0 start ─┬─ Stage 1 questions (eval)  ───────────────────────────┐
               └─ Stage 2 diff scene (prototype)                       │
                     └─ Stage 3 explainer into the package             │
                           ├─ Stage 4 doc.html                         │
                           ├─ Stage 5 card + comment + Mermaid         │
                           ├─ Stage 6 large PRs                        │
                           └─ Stage 7 skill, doctor, install           │
                                 └─ Stage 8 full evaluation and fixes ◄┘
                                       └─ Stage 9 human session, README, launch drafts
```

Stages 1 and 2 can run at the same time. Stages 4, 5, 6 and 7 can run at the same time in separate git worktrees after Stage 3 merges. Each parallel agent owns its own files. Merge one stage at a time and run the verify command after each merge.

`prototypes/` is ignored by git, so a worktree does not contain it. In a worktree, call prototype tools by absolute path (`/Users/koval/dev/prc/prototypes/...`). No test under `tests/` may read `prototypes/`. Copy what a test needs into `tests/data/` and commit it first.

---

## Stage 0. Start (every agent, every session)

1. Run `date`. Read `START-HERE.md`, `DECISIONS.md`, this file and `EVAL.md`.
2. Run the verify command. If it fails before you change anything, stop and report.
3. Append a line to `docs/mvp/LOG.md` with the time, the stage, the commit, and the verify result.

## Stage 1. Freeze the questions and measure the baseline

Do this before any product work is scored. It needs no product code.

1. Use `EVAL.md` part C to write `eval/questions/pr<N>.json` for all 12 open PRs. Re-read each PR at its current head. Record `head_sha` in the file. The schema is `{pr, head_sha, version: 1, questions: [{id, ask, type, key, key_facts?, evidence: ["path:line"]}]}`.
2. A fresh verifier agent checks every key against the code. Fix or drop any question that it cannot prove.
3. Commit the files: `test(eval): freeze comprehension questions v1`.
4. Build the C0 packets (title and description) and run the readers. Grade them, then write the C0 column and the targets into `eval/runs/<date>-baseline/scoreboard.md`. Commit.

Failure modes, each one a check in `scripts/eval/validate_questions.py`:

- A question has no evidence.
- An evidence line does not exist at the head sha.
- A key is not a substring of its evidence line when its type is exact code.
- q8 has no clear true or false answer.
- The C0 score is above 60%, so the questions are too easy.

Done when: 12 question files are committed, verified and validated, and the C0 baseline is in a committed scoreboard.

## Stage 2. The diff scene

Follow `docs/mvp/diff-scene.md` exactly. It works only inside `prototypes/explainer/` (its own git repo) and has its own steps, tests and done conditions. It ends when the mdp17b final frame shows the old and the new code with changed words marked, and frame QA scores mdp17b 4/4 and mdp12 5/5. The prototype runs on `.kvenv` (Python 3.12) and needs nothing new.

## Stage 3. Move the explainer into the package

Goal: `prc explain --source fixture:shop --board tests/data/boards/shop.json --voice none` writes a video, and the verify command runs it.

1. **Write the E2E test first.** `tests/test_e2e_explain.py` drives the `prc` entry point on `fixture:shop`.
   - First write `tests/data/boards/shop.json` by hand from the shop fixture, following `BOARD.md`. Use one scene of each type: title, groups, diff, list, stats and outro. A fixture's `map.json` has `url: null`. Today the outro crashes on it (`build.py` line 184, `m["url"].removeprefix`). The outro and the doc links must show `pr` when `url` is null.
   - The test asserts these things:
     - the exit code is 0;
     - each output file exists;
     - ffprobe reports 1920x1080 and 30 fps, with a duration within 10% of `run.json`'s estimate;
     - `run.json` lists the board check as passed.
   - It copies the output to `artifacts/e2e/explain/`. It skips when ffmpeg or Playwright is missing, like `tests/test_map_video.py`.
   - **Test data.** Copy into `tests/data/explainer/` and commit: the PR 12 and PR 17 `map.json` files (paths in `eval/corpus/linkedin_mdp_open.json`), the prototype boards that the tests use, and the base and head blobs of each file that the highlighter tests read (export them with `git --git-dir <cache> show <sha>:<path>`). Rewrite `jointest.py`'s default map path (line 22) to an argument.
2. **Port the checker.** Port `check.py` to `prc.explainer.check`. Turn `plant.py`'s 10 planted mistakes into pytest cases. Each planted board must fail with its message, and the clean board must pass.
3. **Port the highlighter and the diff rows.** Port them with the tests from Stage 2. Turn the join test fixtures (`bakeoff/shared/test_jointest.py`, 25 cases) into pytest cases.
4. **Port the engine and render.** Copy `engine.js` and `engine.css` into `assets/`. Port `build.py`'s render loop to `render.py`. Port its cue timing to `timing.py`. Keep frame-by-frame seek. Never record in real time.
5. **Voice.**
   - `kokoro` imports lazily and comes from a new optional extra: `voice = ["kokoro==0.9.4; python_version < '3.13'", "soundfile==0.14.0"]`. Kokoro 0.9.4 requires Python below 3.13 (its metadata says `<3.13,>=3.10`). The prc `.venv` runs 3.13.5 today (measured). Pin the dev venv to 3.12 with `uv python pin 3.12` (3.12 is already in `~/.local/share/uv/python`), re-run `uv sync`, and re-run the verify command before you continue. Record the result in `LOG.md`.
   - Installing the voice extra into any new venv downloads PyTorch, spaCy, the spaCy model `en_core_web_sm` 3.8.0, and the Kokoro weights from Hugging Face on first use. misaki calls `spacy.cli.download` by itself when the model is missing. Ask the user before the first install in any new venv. Give the names and sizes. The prototype's `.kvenv` already has all of them.
   - `say` runs `/usr/bin/say` on macOS. It needs the sandbox off.
   - `none` estimates each sentence's length from its character count. Measure the rate from the PR 12 Kokoro timings in `prototypes/explainer/out/mdp12-baseline/` (`player.html` and `phrases.json`). Write the constant in a comment, with where you measured it.
   - Phrase cues. Today `build.py` times a phrase cue by synthesizing the words before it (line 108 and lines 88 to 97). With `kokoro`, keep that. With `say`, synthesize the prefix with `say`. With `none`, use the character share (`--timing share`), so `none` never imports Kokoro. A test runs `--voice none` with Kokoro import blocked.
   - The default is the first backend that works, in the order above.
6. **Board tools.** Port `show.py`, `find.py` and `coverage.py` to `prc board show|find|coverage`. Add `prc board check` and `prc board guide`.
7. **Dependencies.** Add `pygments==2.21.0` to the main dependencies. Reason for the report: it colours code in languages that tree-sitter does not cover here. Pin `tree-sitter` and its grammars to the versions measured in `.kvenv` (section 1 of `diff-scene.md`). Install nothing else without asking the user.
8. **Real PR check.** Build mdp12 and mdp17b through `prc explain` with `--voice kokoro`. Use the boards from the prototype, and the sources `github:komaksym/linkedin-mdp#12` and `#17`. The boards were written against the stored maps. First compare the live `head_sha` with the stored map's `head_sha`. If they differ, pass `--map <stored map.json>` and record the change in `LOG.md`. Compare the frames with the prototype's frames at the same times. They must match apart from colour.

Failure modes, each one a test:

- The board check passes in the prototype but fails in the package, or the reverse. Run both on the 6 boards that have maps (mdp12, mdp14, mdp17b, mdp4, mdp4high and mdp4zoom, maps in `diff-scene.md` section 1) and compare.
- A cue phrase resolves to a different time with `none` than its order with `kokoro`. The test checks the order only.
- A missing ffmpeg or Chromium gives a stack trace. It must give one line that says what to install. `prc doctor` must say the same.
- The output folder for one PR holds files from an older head. Each head gets its own folder (`<head12>`).
- PR text breaks the page: a `</script>` or a quote in a title, label or code line. Reuse the escaping tests from `render_map`.

Done when: the verify command passes with the new E2E test, `artifacts/e2e/explain/video.mp4` plays, and you looked at 4 of its frames. The mdp12 and mdp17b videos from `prc explain` match the prototype. Copy the frames you compared into `docs/mvp/evidence/stage3/`. After that, freeze the prototype: no more changes to `prototypes/explainer/`.

## Stage 4. The walkthrough, `doc.html`

Goal: a reviewer who reads instead of watching gets the same story, and can search and copy it.

- One offline HTML file with the same CSP style as `map.html`. It loads no network resources.
- A header shows the PR title, `repo#N`, the author, the head sha, and links to GitHub.
- One section per scene. Each section has these parts:
  - the scene's sentences as prose, using the caption text, not the voice spelling;
  - the scene drawn by the same engine, frozen at its settled time;
  - its receipts as links to `https://github.com/<repo>/blob/<sha>/<path>#L<n>`.
- **Engine change.** `engine.js` is one function bound to `#stage`, `#header` and `window.BOARD`, with absolute 1920x1080 coordinates (`engine.js` lines 593 to 595). Refactor it to `mount(root, board, sceneIndex)`. Each mount draws a 1920x1080 stage, scaled by CSS `transform: scale(var(--k))` to its container's width. Freeze a scene with `update(scene.end - 0.5)`. The video uses the same `mount` with the whole board. Keep one inline script allowed by a CSP hash. The Stage 3 video E2E must still pass after the refactor.
- Diff scenes are real text, not images, with the same colours, word marks, wrap and line numbers as the video.
- A "Not covered" section at the end lists every changed file and symbol that the board does not show. Use the same rule as `prc board coverage`.
- If `video.mp4` exists beside it, a link at the top says "Watch the 60 s video".

Failure modes, each one a test:

- The doc text says something that the board does not. Every sentence in the doc must be a board sentence or a fixed template string.
- A receipt link has the wrong sha or line. Gate 7 in `EVAL.md` checks this.
- A code row's text in the doc is not the diff line. Use the join test on the doc's DOM.
- The doc needs the network. Load it in Chromium with network blocked, and count failed requests. There must be 0.
- The "Not covered" list misses a changed file. Compare it with `map.json`.
- The doc does not fit a phone. Screenshot it at 390 px wide, and check that nothing scrolls sideways except code blocks.

Done when: `doc.html` exists for mdp12 and mdp17b, the tests pass, and you looked at screenshots at 1280 and 390 px wide. Save them in `docs/mvp/evidence/stage4/`.

## Stage 5. The PR card and the PR comment

**Card (`card.png`, 1200x630 at 2x).** The `card.png` from `map --video` is only a screenshot of the map page at time 0 (`map_video.py` lines 122 and 139 to 140). It has no headline, stats or lists. Build a new `card.html` template and screenshot it at 1200x630, scale 2, with the same Chromium code as `map_video`. Keep the map page's colours and fonts. Use these parts in this order:

1. the headline, which is the board's resulting-behaviour summary (`outro.l1`), then its title-scene sentence, then the PR title;
2. the stats;
3. look-first, the first 3 tour entry symbols with their files;
4. risky surfaces, by name;
5. changed symbols with no direct test, by name, at most 3, then "+N more";
6. the footer "computed from the code" with `repo#N` and the head sha.

Stat definitions. Write these in the card code and use the same code in gate 6 of `EVAL.md`:

- files: the number of files in the brief (`brief.files`);
- symbols changed: symbols with status `added`, `modified` or `deleted`;
- call sites affected: the sum of `call_sites` over the changed symbols;
- tests touched: brief files of kind `test`;
- CI: passed checks out of all checks on the head commit (`brief.checks`), or "no CI";
- no direct test: a changed symbol outside test files with no edge from a symbol in a test file.

**Comment (`comment.md`).** Use these parts in this order:

1. the headline;
2. the card image placeholder `![PR card](card.png)` with a note that the user uploads it;
3. a Mermaid `flowchart LR` of the core change;
4. look-first;
5. risky surfaces and mismatches between the description and the diff, from the existing `brief` domain (`prc.brief`);
6. "Not covered by tests";
7. a one-line footer naming prc and the head sha.

Every PR-controlled string in the Markdown text goes through the existing code-span helper (`render_brief.span()`). Strings inside the Mermaid block never go through `span()`. They follow the Mermaid rules below.

**Mermaid rules.**

- Choose nodes in this order, up to 12:
  - the changed symbols on the tour path;
  - then the symbols with the most added or removed calls;
  - then their direct callers.
- Node ids are `n1`, `n2` and so on. Labels are the short qualname in double quotes. Strip backticks, newlines and control characters. Then escape in this order: `#` as `#35;` first, then `"` as `#quot;`, `<` as `#lt;` and `>` as `#gt;`. Cut a label to 60 characters.
- Edges use these forms:
  - `-->` for added calls, with `linkStyle` green;
  - `-.->` for removed calls, with `linkStyle` red;
  - `---` for kept calls.
- Use `classDef` for added, modified and deleted nodes.
- Use only constructs that the grammar test knows.
- If the PR has more than 12 core symbols, the last line under the diagram says "Showing 12 of N changed symbols. Full map: map.html".

Failure modes, each one a test:

- A Mermaid edge is not in `map.json`, or it has the wrong status.
- A label breaks Mermaid. Test the characters `" ` ` < > [ ] ( ) { } | # ;` and a 200-character name.
- The diagram goes over 12 nodes.
- A card number differs from `map.json`. Gate 6 in `EVAL.md` checks this.
- Card text is unreadable at 800 px. Run OCR on the card scaled to 800 px. Every stat and name must be found.
- A PR with no code changes (docs only) still gives a valid card and comment, with "No code symbols changed".

Done when: `card.png` and `comment.md` exist for PRs 11, 12, 17 and 19, the tests pass, and you looked at all 4 cards at 800 px. Paste one `comment.md` into a GitHub Markdown preview only if the user offers to. Otherwise, the grammar test is the check. Save the evidence in `docs/mvp/evidence/stage5/`.

**Mermaid download.** The syntax gate in `EVAL.md` needs a pinned `mermaid.min.js` (MIT). Ask the user once. State the version, the source (`cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.min.js`) and the size. If they agree, vendor it under `scripts/eval/vendor/`, not in the package.

## Stage 6. Large PRs

Measured problem: open PR 19 (62 files, 311 changed symbols) gives a map of about 300 tiny cards with no visible arrows. The screenshot is at `docs/mvp/evidence/pr19-map-before.png`.

1. **Map overview.** When a PR changes more than 40 symbols, the map opens grouped. There is one card per folder, or per file when a folder has fewer than 3 files. Each card shows its counts: symbols added, modified and deleted, and tests. Edges between groups are summed, and an edge's width shows its call count. A click expands a group in place, and Escape collapses it. The tour visits groups first. Keep `window.prcTour` working.
2. **Board budget.** `prc board coverage` prints which files and symbols the board covers. The skill tells the writer to cover the largest behaviour change and to name what it leaves out. The video's outro and the doc's "Not covered" section show "covers X of Y changed files".
3. **Speed.** Record the map time and the render times for PR 19 in `results.json`. Stop and report if `prc explain` on PR 19 takes more than 5 minutes, not counting board writing.

Failure modes, each one a test:

- A small PR (40 or fewer symbols) changes appearance. Its existing browser tests must still pass unchanged.
- An expanded group loses edges. The total edge count after expanding all groups must equal `map.json`.
- A group's counts differ from the sum of its members.
- The grouped first screen is unreadable. Screenshot it at 1280x800 and run OCR. Every group label must be found.

Done when: the PR 19 first screen shows at most about 25 readable group cards with visible arrows, the tests pass, and the before and after screenshots are in `docs/mvp/evidence/stage6/`.

## Stage 7. The skill, doctor and install

1. **The skill.** Write `src/prc/skill/SKILL.md`, the board-writer skill. Its steps:
   1. Run `prc explain --source X` for the deterministic outputs and `map.json`.
   2. Run `prc board guide` and follow it.
   3. Use `prc board show` and `find` to pick lines.
   4. Write `board.json`.
   5. Run `prc board check` until it passes.
   6. Run `prc board coverage`, and say what is left out.
   7. Run `prc explain --source X --board board.json`.
   8. Review your own frames. Extract the scene-end frames at 800 px and look at them. Fix any text that is unreadable or wrong.
   9. Tell the user where the 5 files are, and that prc posted nothing.

   Base it on how the 2026-10-05 writers worked (the prompts and results in `prototypes/explainer/reviews/` and `prototypes/scratch-2026-10-05/todo.md`). `prc skill install claude` copies it to `<dest>/prc-explain/SKILL.md`, where `--dest` defaults to `~/.claude/skills`. `prc skill install codex` writes an `AGENTS.md` section to `--dest`. Both print the path they wrote. Tests use `tmp_path`. Never install into the user's real `~/.claude` without asking. That folder is the user's own configuration.
2. **`prc doctor`.** It prints one line per dependency with ok or missing and the install command: Python, ffmpeg, Playwright Chromium, the voice backend (Kokoro import, espeak-ng library, or `say`), and whether `GITHUB_TOKEN` is set. It never prints the value.
3. **Install.** Test a clean install from the wheel. Use a new folder and a new `uv venv -p 3.12`. Run `uv pip install "$(ls dist/prc-*.whl)[video]"`, then `prc doctor`, then `prc explain --source https://github.com/komaksym/linkedin-mdp/pull/12 --map <stored PR 12 map.json> --board <PR 12 board> --voice say`. Reuse the Chromium already in `~/Library/Caches/ms-playwright`. Ask the user before any `playwright install`. Record each command and its result.
4. **E2E through the skill.** A fresh agent with only the skill text (installed with `--dest` into a temporary folder, and no repo access) explains PR 11 from a clean folder. Record its wall time and whether `prc board check` passed on the first, second or a later try.

Done when: the clean install works, `prc doctor` passes, and the skill-driven E2E gives the 5 outputs for PR 11. Save the transcript summary in `docs/mvp/evidence/stage7/`.

## Stage 8. Full evaluation and the fix loop

1. Build the harness in `scripts/eval/` (`EVAL.md`, layout and parts A to D).
   - `run.py` makes outputs for a list of PRs. It writes boards through the skill flow, one fresh writer agent per PR.
   - `packets.py` builds reader packets.
   - `grade.py` grades answers.
   - `gates.py` runs part A.
   - `scoreboard.py` writes the table.
2. Pilot on PRs 11, 12, 17 and 19. Read every failure. Fix it at its source, re-run, and commit each fix with the scoreboard change in the message body.
3. Run all 12 PRs. Run the grounding audit with the judge check, and the comprehension test on all conditions.
4. Repeat until the MVP pass in `EVAL.md` holds, apart from the human items. Never edit a frozen question or a target to pass.

If a target fails three fix rounds in a row, stop. Write down what you tried, with the numbers, and report to the user. The target or the design may be wrong, and that is the user's call.

## Stage 9. Human session, README, launch drafts

1. Prepare `eval/human/<date>.md` from `EVAL.md` part E, with every path filled in, and tell the user it is ready. Record their answers in the same file. Update the scoreboard.
2. Rewrite `README.md` around `prc explain`. Cover these parts:
   - one sentence on what it does;
   - a GIF or frame from a real linkedin-mdp video;
   - install;
   - the 5 outputs;
   - how the skill works;
   - what is computed and what the agent writes, and how the checker keeps the agent honest;
   - the evaluation numbers, with a link to the scoreboard.
3. Write the launch drafts in `docs/launch/`:
   - a tweet thread draft;
   - a 30 to 45 s promo video cut from a real explainer, rendered by prc itself;
   - a checklist for publishing the repo, with these items:
     - check for private content: `reports/`, `prototypes/`, `eval/runs/` and the git history;
     - add a license (the user chooses);
     - choose the repo name;
     - publish to PyPI.

   Do not post, push or publish anything. The user does that or approves each step in chat (decision D21).

## Rules for every stage

- Write the test before the code. List the failure modes, turn each one into a test, see it fail, then write the code.
- Run the narrowest check after each change. At the end of a stage, run `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest && uv build`.
- Verify through the real output. Open the file, extract the frame, take the screenshot, and look at it. A passing test is not proof that a picture is right.
- Use one Conventional Commit per finished step, such as `feat(explainer): ...`, `test(eval): ...` or `fix(card): ...`, with a body. Never add a `Co-Authored-By: Claude` line.
- Append to `docs/mvp/LOG.md` at the end of each stage: what changed, the checks and their results, the evidence paths, and the open problems. Label every number measured or estimated.
- If something surprises you, stop and write it in `LOG.md` before you change course. Do not tune constants until a test passes.
