# Unpublished launch thread draft

This draft describes a release candidate. It is not a launch announcement.
Do not post it until the evaluation, human review, license, and publishing gates pass.
There is no approved public repository or package link to include yet.

## Draft posts

1. Introduce the candidate with the existing [PR 12 diff frame](../media/explain-pr12-diff.png).

```text
prc is a release candidate for explaining pull requests. Your coding agent writes a storyboard. prc renders a local video, written walkthrough, interactive map, PR card, and comment draft. Evaluation and human review still block release.
```

2. Explain the source of the story and the evidence.

```text
The map and code rows come from the captured code. Your agent writes the narration, titles, and notes. Board checks verify cited lines, selected relationships, and explicit counts. They do not prove that the prose is true. Review the claims against the code.
```

3. Describe the workflow without claiming an automatic explanation.

```text
The prc-explain skill guides your coding agent through reading the map, choosing code receipts, writing board.json, checking the board, reporting omissions, and inspecting rendered frames. prc writes files locally. You decide what to publish.
```

4. State the fallback and dependency costs.

```text
No board? prc map gives you an interactive map. Video needs Chromium and ffmpeg. Voice is optional: Kokoro adds Python dependencies and model downloads; macOS say uses the system voice; --voice none makes a silent video.
```

5. State the current evidence limit.

```text
The current full-run scoreboard contains 480 final grades and 44 wrong answers. The results fail the frozen comprehension targets. Release also needs human review, a license choice, a privacy review, and publishing approval. This thread is an unpublished draft.
```

## Evidence and publication conditions

The [README](../../README.md) describes the current CLI and its dependencies.
The [scoreboard](../../eval/runs/2026-10-06-full/scoreboard.md) does not yet establish comprehension performance.
The [evaluation requirements](../mvp/EVAL.md) define the remaining checks.
The [human session](../../eval/human/2026-10-06.md) still needs recorded answers.

Before publication, confirm that each claim matches the final candidate and its recorded evidence.
Review the frame and any promo video for accuracy, readability, and permission to publish the displayed code.
Confirm the license, public repository name, package release, and private-content review with the user.
Add an approved public link only after it exists. Recheck each post's length after that change.
The user must approve posting separately. This draft authorizes no post, push, upload, or package publication.
