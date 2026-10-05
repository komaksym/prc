# Decisions for the prc MVP

These decisions are closed. Each has its reason and its evidence. Do not reopen one unless a measurement in your own run contradicts it. If that happens, stop and write the measurement in your report.

Evidence labels: **measured** means someone ran it and recorded the number. **Inferred** means it follows from measured facts. **Guess** means nobody measured it.

## Product

**D1. The goal is usefulness to people who review or submit AI-written pull requests.** The user set this as the first requirement on 2026-10-06: "it should be useful, people should want to use this." When a choice trades usefulness against effort, choose usefulness.

**D2. Two users, one tool.** The reviewer must understand a PR they did not write. The author must understand and explain the PR their agent wrote before they submit it. Maintainer policies now reject PRs that the author cannot explain without help (Crossplane `AI_POLICY.md`, Ghostty, LLVM, kernel; see `reports/AI code comprehension pain points.md`). Both users run the same command on the same PR.

**D3. Facts are computed, and words are checked.** Structure (symbols, calls, files, tests, CI) comes from parsing the code. No model draws a box or an arrow. A model writes the story (the board), and `check.py` refuses any board that shows a name, value or line the PR does not contain. Reason: the top pain point is plausible but subtly wrong code, and reviewers distrust AI prose (`reports/`, ranks 1 and 4, strong evidence). A tool that adds its own wrong claims makes the problem worse.

**D4. Local first, no paid API.** prc runs on the user's machine. It reads public PRs with no token and private PRs with the user's `GITHUB_TOKEN`. It never needs an API key.

**D5. The user's own coding agent writes the board.** prc ships a skill (instructions plus commands) for Claude Code and an `AGENTS.md` section for Codex and other agents. The agent runs `prc`, writes the board, runs the checker until the board passes, renders, and reviews its own output. Reason: this needs no API key (D4), and it is how every board so far was made. Three sonnet subagents wrote passing boards for PRs 12, 14 and 4 in 83 to 116 s each (measured, 2026-10-05). A direct API mode can come later, only with a key the user provides.

**D6. Without an agent, prc still gives value.** `prc map` and every deterministic output (map page, card stats, comment with diagram) work with no board. The board adds the narrated video, the written walkthrough and the headline.

## Outputs

**D7. One PR gives five outputs.**

| Output | File | Needs a board | Where the user puts it |
|---|---|---|---|
| Interactive map | `map.html` | no | opens locally |
| Narrated explainer video | `video.mp4` | yes | dragged into the PR description |
| Written walkthrough | `doc.html` | yes | opens locally, or attached |
| PR card (infographic) | `card.png` | no (headline only with a board) | top of the PR comment, social post |
| PR comment | `comment.md` | no | pasted as a PR comment by the user |

The narrated video, the walkthrough and the card headline come from one board. One board means one story, checked once.

**D8. The narrated explainer is the video.** It replaces the 30-second map tour (`map --video`) as the main video. The map tour stays as the no-agent fallback. Reason: the user iterated on the explainer through three rounds and a renderer bakeoff. The map tour has no narration and no story.

**D9. Mermaid is the diagram in the PR comment.** GitHub draws a Mermaid block in a comment with no hosting and no upload. prc writes the diagram from `map.json` (computed calls only), with at most 12 nodes. Reason: the user asked to reuse what exists. Mermaid is the only diagram format that GitHub draws natively. CodeRabbit already writes model-drawn Mermaid diagrams, so the computed source is the difference (D3).

**D10. The PR card is the infographic.** One 1200x630 image (rendered at 2x). It shows the board headline when a board exists, the map stats, the look-first list, the risky surfaces and the changed functions without a direct test. It replaces the existing `card.png` from `map --video`, which is only a screenshot of the map page. It must stay readable at 800 px wide (OCR check). The older `review` command's `infographic.svg` is not the MVP card.

**D11. prc never posts anything.** It writes files. The user pastes the comment and uploads the video. Reason: posting is outward-facing, and GitHub has no public API to upload a video into a PR description (inferred from GitHub's REST docs; the web UI upload is the known path). A `--post` flag is out of scope for the MVP.

## Video engine

**D12. Keep our own engine.** It is HTML and JS, seeked frame by frame in headless Chromium, encoded with ffmpeg. The 2026-10-05 bakeoff measured it against HyperFrames 0.8.133 and Remotion 4.0.533. It tied Remotion in blind judging and on OCR. Remotion adds 442 MB and a company license. HyperFrames showed two captions on top of each other and a proportional font in code rows. The user saw no meaningful difference and delegated the choice to cost, weight, speed and robustness (`reports/PR explainer video rendering bakeoff results.md`).

**D13. No Shiki, no Node.js. Highlight in Python.** The user decided this on 2026-10-06. tree-sitter (already a prc dependency for `map`) colours Python, JavaScript and TypeScript. Pygments colours other languages. The highlighter parses the whole file, then selects the shown lines. Every row's tokens must join to the diff line exactly (the join test). Measured: 287 of 287 PR 12 lines join, 0 mismatches (`prototypes/explainer/spike/run12.py`).

**D14. No token glide (magic move).** Changed words are marked instead, like GitHub's word diff. A word mark shows the change on a paused frame and to a muted viewer. Motion shows it only while the viewer watches that moment. The glide was also the riskiest engine change. This replaces the user's earlier plan for per-state token keys, under the user's 2026-10-06 instruction to decide by usefulness.

**D15. Removed lines stay on screen.** The diff scene ends as a unified diff: removed lines in red, added lines in green, changed words marked. Measured: a blind reader of today's final frames answered 5 of 5 questions for PR 12 but only 2 of 4 for PR 17. It could not answer either "what was the old code" question, because removed lines close and vanish (`prototypes/explainer/eval/baseline/RESULT.md`).

**D16. Long lines wrap, and the code font goes up to 40 px.** Across 14 PR maps, 15.6% of changed lines are over 80 characters (measured, 9,982 lines). Today one long line shrinks every line in the scene. Rows over 72 columns wrap at token boundaries with a hanging indent. The font cap goes from 32 to 40 px, limited by width and by the caption area.

**D17. Voice backends, in order: Kokoro, macOS `say`, none.** Kokoro 0.9.4 (`af_heart`) is the default when the `voice` extra is installed. It needs Python 3.12 or lower (its metadata says `<3.13`). It pulls PyTorch, spaCy and the `en_core_web_sm` model, downloads its weights from Hugging Face on first use, and needs espeak-ng from Homebrew (measured in `.kvenv`). So prc's dev venv moves to Python 3.12, and the first voice install in any venv is a download the user approves. macOS `say` needs no install. `none` makes a silent video with captions, timed by an estimate, and the tests use it so they stay fast and repeatable. Kokoro output is not byte-identical between runs, but scene start times were identical (measured).

## Scale

**D18. Large PRs get an overview first.** Measured on open PR 19 (62 files, 311 changed symbols, 639 calls): the map page shows a grid of about 300 cards with text too small to read and no visible arrows. It mapped in 14 s, so speed is not the problem. When a PR changes more than 40 symbols, the map opens grouped by file or folder, with counts. A click expands a group. The board covers the main story, and every output states what it did not cover (for example "covers 6 of 62 files; the rest are listed below"). Reason: research pain point 2 is PR size, and reviewers ask what was not checked.

## Process

**D19. Evaluation is 90% automatic.** Agents grade correctness, grounding and comprehension on the 12 open `komaksym/linkedin-mdp` PRs. The user does one short session and spot-checks the graders. See `EVAL.md`.

**D20. Questions are written before outputs exist.** A question writer sees the PR and the code, never a prc output. The questions and answer keys are frozen in git before the first scored run. Reason: a writer who has seen the video asks about what the video shows.

**D21. Publishing waits for the user.** Pushing the GitHub repo, publishing to PyPI, posting the promo and choosing a license all need the user's explicit yes in chat. Agents prepare drafts only.
