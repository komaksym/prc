# Paired session hub

A participant reads one assigned PR at a time in a loopback hub. The hub owns buttons for prepare, start, answer, submit, abort, close, grade, and analysis.

## Sub-features

- `paired-prepare` shows the next PR without content.
- `paired-start` starts the timer for the prepared reading.
- `paired-answer` saves answers and survives reload.
- `paired-familiar-refusal` refuses a familiar reading with recovery guidance.
- `paired-submit` submits a reading and offers the next one.
- `paired-abort` aborts a reading and keeps the draft.
- `paired-close` closes the study after every reading is saved.
- `paired-grade` grades blinded answers and shows analysis.

## How to get to it (user POV)

Open the hub URL printed by `prc eval-session`. Click Prepare next reading. Report familiarity. Click Start timed reading. Read GitHub and the assigned aid. Answer questions. Click Submit reading or Abort reading. Click Close study. Click Save grades and analyze.

## Driving it with CLI and Playwright

Preconditions: use a temp copy, never `artifacts/paired-study/private/`. Fixture study mode only. Doctor reports Chromium ready.

- Run `.venv/bin/python scripts/verify_paired_hub.py`. Require `PASS` and inspect the printed proof directory.
- The driver builds a 2-pair fixture study in a temp dir. It prepares the study with `kit.prepare_study`. It serves the study over loopback. It never opens the sealed human study.
- The driver clicks every button in order: Prepare next reading, Start timed reading (clean), answer and Saved, reload and resume, Submit reading, Prepare next reading, Start timed reading with familiarity checked (refusal), Prepare next reading, Start timed reading (clean), Abort reading, Prepare next reading, Start timed reading (clean), Submit reading, Close study, Save grades and analyze.
- Require refusal text to name familiarity and recovery. Require the exact error to tell the reader to click Prepare next reading. A refusal with no next step is a dead end and fails.
- Require one screenshot per button path. Require `checks.json` to list every step with button, expected, observed, pass, and screenshot. Require zero page errors.
- Inspect screenshots before handoff. Cite the proof directory in the handoff note. API-only checks and single-path screenshots do not pass this recipe.
- Hub changes without a fresh `scripts/verify_paired_hub.py` PASS and cited proof are not ready for the operator.

## Gotchas

- Fixture mode skips live GitHub checks. It does not prove live revision checks.
- Familiar and exposed trials stay in grading as unknown. They must not vanish.
- The sealed human study stays untouched. Drive a temp copy only.
- Use `tests/test_paired_browser.py` for single-path browser detail. This recipe requires the full button path.

## Handoff (operator-facing)

Before any handoff message with a hub URL, prove the exact handed-off server with the supervised handoff script. Copy the study outside artifacts/paired-study/private first; never serve the sealed original.

Run .venv/bin/python scripts/handoff_study_hub.py <study-copy> from the repo root. The script starts or reuses one supervised hub process (detached setsid background nohup pidfile, with --stop), waits until the exact printed URL answers, and loads that exact URL in real Chromium with PLAYWRIGHT_BROWSERS_PATH set to the project browser cache.

Require the hub to render with Prepare next reading visible and zero page errors. Require one safe read-only interaction: click Prepare next reading and require the preview panel with a non-empty title. The check must not start a trial or mutate session.json. Hold a silent preconnect socket open during the check and require the hub to keep answering afterwards.

Require the handoff record JSON under artifacts/handoff/ with url, port, pid, pidfile, screenshot, and each check result. Cite the record and screenshot in the handoff note. Do not hand off a URL when the script exits nonzero or prints HANDOFF REFUSED; it refuses to print a URL when any check fails.
