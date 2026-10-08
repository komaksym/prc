# Evaluation and benchmarks

## Summary

The evaluation answers one question: does prc help a person understand a pull request, without telling them anything false? Agents run 90% of it. The user does one 30-minute session and spot-checks the agent graders.

The test set is the 12 open pull requests of `komaksym/linkedin-mdp`, a public repo that the user owns (`eval/corpus/linkedin_mdp_open.json`). They run from 204 to 8,081 added lines: 4 small, 6 medium and 2 large. The 28 public agent-written PRs in `eval/corpus/public_agent_prs.json` check the computed map and diagram only.

There are five parts:

- **A. Gates.** Scripts check that the facts and files are correct.
- **B. Grounding audit.** Agents look for false claims.
- **C. Comprehension test.** Agents answer fixed questions from the outputs alone.
- **D. Legibility and speed.** OCR and timing numbers.
- **E. Human session.** The user checks the agents.

## Where things go

```
eval/
  corpus/                         PR lists (tracked)
  questions/pr<N>.json            frozen question sets with answer keys (tracked)
  runs/<YYYY-MM-DD>-<label>/      one folder per scored run (tracked except large media)
    outputs/pr<N>/                map.html, doc.html, video.mp4, card.png, comment.md, board.json
    packets/pr<N>/<condition>/    what one reader agent sees, plus prompt.md
    answers/pr<N>/<condition>.json
    audit/pr<N>.json              skeptic findings and verifier verdicts
    results.json                  every number in this file, per PR
    scoreboard.md                 the table a person reads, with the previous run beside it
  human/<YYYY-MM-DD>.md           the user's session sheet
scripts/eval/                     the harness (tracked)
```

Keep generated MP4 and WAV files under `eval/runs/*/outputs/` out of Git.
Keep PNG packet frames out of Git.
Track the remaining evaluation files so runs can be compared.

The harness prepares packets and grades answers. Agents read packets and write answers. Any agent runtime can then do the agent steps, and the scripts stay deterministic.

## A. Gates (scripts, every PR, every run)

Every gate is a script in `scripts/eval/`. Each one prints PASS or FAIL per PR and writes its numbers to `results.json`. One FAIL means the run fails.

1. **Receipts.** The board check passes.
2. **Join.** For every diff scene, each row's tokens join to the diff line (`jointest.py`).
3. **DOM text.** In the rendered page, each diff row's text equals the row text.
4. **Layout.** The engine's layout lint reports no warnings.
5. **Diagram.** Every edge in the `comment.md` Mermaid block exists in `map.json` with the same status, and the diagram has no more than 12 nodes. The syntax check renders the block with a pinned Mermaid build in headless Chromium. Mermaid is a download, so ask the user before you add it. Until then, a grammar test checks the subset that prc writes.
6. **Card facts.** Every number on the card equals the number computed by the stat definitions in `PLAN.md` Stage 5, from `map.json` and the brief. Check it from the card's HTML before the screenshot, and with OCR at 800 px after it.
7. **Doc links.** Every receipt link in `doc.html` points at `https://github.com/<repo>/blob/<sha>/<path>#L<n>` with the head or base sha. The text of that line in the git cache contains the receipt's `match` text.
8. **Video file.** Use ffprobe to check 1920x1080 at 30 fps, and ffmpeg `volumedetect` to check that audio exists (unless the voice is `none`). Length is 45 to 80 s, or up to 90 s for large PRs. The skill tells the writer to aim for 60 s. The prototype mdp17b render is 75.4 s (measured).
9. **Arrow precision.** On the 28 public PRs, at least 99% of the drawn arrows have a call of the target on a line of the source. The 2026-10-04 run measured 879 of 882. Old scripts are in `prototypes/scratch-2026-10-05/edge_check.py` and `map_corpus.py`.

## B. Grounding audit (agents)

This part finds wrong statements. The checker cannot find them because each word is real but the sentence is false, for example "skips the company" when the code keeps it.

1. A skeptic agent (opus, high effort, fresh context) reads the PR diff and these outputs: the board's spoken text, `doc.html` text, `comment.md` and `card.png`. It lists every statement that it thinks is false, overclaimed or misleading. For each one, it gives the statement, the output, and the code line that contradicts it.
2. A verifier agent (sonnet, fresh) checks each finding against the code. Its verdict is `confirmed` or `rejected`, with the line.
3. **Judge check, every run.** Copy one board and plant 3 false statements that the checker cannot catch, such as a wrong direction, a wrong condition or a wrong count in words. Run the skeptic on the copy. If it finds fewer than 2 of the 3, the audit is not valid for this run. Report that, and do not count its zero as a pass. The 2026-10-05 trial found 5 of 5 known defects with Opus (measured, `prototypes/explainer/reviews/`).

The metric is confirmed false statements per PR. The target is 0. Fix each one at its source: the board writer skill, the checker, or a renderer. Then re-run.

## C. Comprehension test (agents)

### Questions

Write the questions before any scored output exists (decision D20). For each PR, one writer agent (opus, high effort) reads the PR description, the diff and the head code from git. It never sees a prc output. It writes `eval/questions/pr<N>.json` with 8 questions from this template:

| id | Asks | Answer type |
|---|---|---|
| q1 | What behaviour changes, and for whom? | free text, with 2 to 3 key facts that must appear |
| q2 | Which function or class carries the main change? | exact name |
| q3 | What was the old condition, value or call, and what is the new one? (Use a PR with a modified line. If it only adds code, ask what the new code checks.) | exact code or value |
| q4 | Which other files or areas change? | set of paths or areas |
| q5 | Which risky surface does it touch (CI, dependencies, auth, schema, secrets, external calls), or none? | set or "none" |
| q6 | Which changed function has no direct test? Or, which behaviour do the new tests pin? | exact name or free text |
| q7 | Where should a reviewer start reading? | path and function |
| q8 | True or false: a specific statement about something the PR does **not** do | true or false |

Each answer key has `evidence`: the `path:line` lines that prove it. A second agent (sonnet, fresh) checks every key against the code before you commit the file. Commit the questions in their own commit, before the first scored run. Never edit a frozen question after a scored run. Add a new version file instead.

### What each reader sees (conditions)

| Condition | Packet | Stands in for |
|---|---|---|
| C0 baseline | PR title and description from GitHub | what a reviewer has today before reading code |
| C1 card | `card.png` scaled to 800 px wide | a 3-second glance |
| C2 comment | `comment.md` text, plus the Mermaid block rendered to PNG once Mermaid is approved | the PR comment |
| C3 video | one frame 0.5 s before each scene ends, plus one frame 0.6 s after each cue, at 800 px; no more than 30 frames | a muted viewer of the video |
| C4 doc | the text of `doc.html`, plus screenshots at 800 px wide | the walkthrough |
| C5 map | a screenshot of the first screen at 1280x800 | the map's first impression |

One fresh reader agent (sonnet) gets one materialized packet. `scripts/eval/packets.py` writes each viewing condition into the packet folder and records SHA-256 hashes for its source and payload files. The prompt contains question IDs, types, and asks. It excludes answer keys and evidence.

- C1 contains the card resized to 800 pixels wide.
- C2 contains the comment text.
- C3 contains up to 30 actual video frames resized to 800 pixels wide. It uses recorded scene and cue times.
- C4 contains visible document text and screenshots at 800 pixels wide.
- C5 contains the first map viewport at 1280 by 800 pixels.

Readers use only the packet files. They return the answer shape requested by each question type. They quote code exactly and answer `CANNOT TELL` only when the packet does not show the answer.

A reader never sees two conditions of the same PR. Run the 4 pilot PRs (11, 12, 17, 19) on all conditions first, then the other 8.

### Grading

`scripts/eval/grade.py` grades exact answers (names, code, sets, true or false) after it normalizes whitespace and quotes. A grader agent (sonnet) grades free text against the key facts. Each answer is `correct`, `partial`, `wrong` or `cannot_tell`.

`scripts/eval/grade_round.py` uses the frozen v1 files, even when unverified v2 files exist.
It rejects duplicate, unknown, or missing question answers and unanswered materialized packets.
Before comparing runs, it requires identical PR, condition, and question coverage.
Each grade records the question file's SHA-256 hash.
When a run has `question-hashes.json`, grading rejects missing or changed keys against that record.
Historical runs without this record do not prove that their keys stayed unchanged.
It leaves free-text verdicts as `NEEDS_HUMAN` until an independent grader supplies them.
JSON booleans and leading `True` or `False` tokens with reasons are accepted.
`CANNOT TELL` with a reason remains an abstention.

`wrong` is the worst result. A wrong answer from C1 to C5 means a prc output misled the reader. Count it on its own as **misleading answers**. The target is 0. Trace each one to the output that caused it.

### Targets

Measure C0 on all 12 PRs first. Then write the targets into `scoreboard.md` and commit them, before any product condition is scored. The proposed targets are a guess:

- C4 doc: at least 85% correct;
- C3 video: at least 70%;
- C2 comment: at least 60%;
- C1 card: at least 35%;
- each condition: at least 30 points above C0;
- misleading answers: 0.

If C0 is already above 60%, the questions are too easy. Make them harder in a new version before you score the product.

Baseline already measured on the old engine: a reader of the final diff frame alone answered PR 12 5/5 and PR 17 2/4 (`prototypes/explainer/eval/baseline/RESULT.md`). That test only covers the diff scene and uses its own questions. It is the gate for the diff scene work (`diff-scene.md`), not for C3.

## D. Legibility and speed

- **OCR.** Use `prototypes/explainer/bakeoff/score/score_ocr.py` (macOS Vision) on the PR 12 frames at 1920, 800 and 341 px. The baseline is 31/31, 28/31 and 8/31 (measured 2026-10-05). The target at 800 px is 31/31.
- **Speed.** Record wall time per PR for each step: map, board writing (agent wall clock), board check, video render, doc, card. Render times are the median of 3 warm runs. Record the machine. Reference numbers: PR 12 video build 77 s, PR 19 map 14 s, board writing 83 to 116 s per PR (all measured).
- **Size.** Record the bytes of each output. `map.html` and `doc.html` must stay single offline files.

## E. Human session (the user, about 30 minutes)

The user wrote these PRs. They judge correctness well, but they cannot judge what a cold reviewer understands. The agent readers stand in for the cold reviewer. The session sheet is `eval/human/<date>.md`. Make it from this template, with the output paths filled in.

1. **Three PRs.** Use PR 12 (small), PR 13 or 16 (medium) and PR 19 (large). For each one:
   - Watch the video once, muted.
   - Watch it again with sound.
   - Open the doc, the map and the comment.
   - Answer these questions:
     - Is any statement wrong? Which one?
     - Score each output from 1 to 5 for "this helps someone understand the PR".
     - Which output is most useful, and which is least useful?
     - Would you put this on your PR? Answer yes or no, and say why.
2. **Grader check.** Grade 10 random agent answers yourself, without seeing the agent's grade. The harness picks them. If you agree with fewer than 8 of 10, the agent grades are not trusted. Fix the grader first.
3. **Audit check.** Read 5 random skeptic findings, both confirmed and rejected. Agree or disagree with each one.

## The scoreboard

`scoreboard.md` is one table per run, with the previous run beside it:

- gates passed, out of 12;
- confirmed false statements;
- the judge check result;
- per condition: correct %, partial %, wrong count and cannot-tell %;
- misleading answers;
- OCR at 800 px;
- median render time;
- output sizes;
- the human scores, when the session has happened.

Under the table, list every failure with a link to its files.

## MVP pass

The MVP passes when all of these hold:

- all gates pass on 12 of 12 PRs;
- the judge check is valid, and there are 0 confirmed false statements;
- every comprehension target is met, with 0 misleading answers;
- OCR at 800 px is 31/31;
- in the human session, the user would put prc on at least 2 of the 3 PRs;
- grader agreement is at least 8/10.
