# Notes review hub

A reviewer reads eight PRs, each with its PRC artifacts and one free-text
notes box. The hub shows only the PR title, a GitHub link, the infographic
image, the narrated video, the clickable page.html link, and the notes box.
There are no questions, confidence scores, timers, or grades. Notes autosave
to notes.json (one entry per PR with updated_at) and survive a hub restart.

## Sub-features

- notes-list shows all eight PR sections with titles and GitHub links.
- notes-artifacts serves each PRC output live from its render directory.
- notes-save autosaves a typed note and keeps it across a reload.
- notes-restart keeps every saved note across a hub restart.

## How to get to it (user POV)

Open the hub URL printed by prc notes-review. Read each PR with its
artifacts. Type notes in a PR notes box; the box reports Saved. Reload at
any time; notes persist. There is nothing to submit and no timer.

## Driving it with CLI and agent-browser

Preconditions: serve PRC outputs live from their render directories; never
copy them into the hub. Doctor reports Chromium ready.

- Run .venv/bin/python scripts/verify_notes_hub.py. Require PASS and inspect
  the printed proof directory.
- The driver serves a scratch notes dir (real roster, empty scratch notes)
  over loopback in an isolated agent-browser session. It asserts every GitHub
  href, opens every infographic (naturalWidth>0), plays every video to
  currentTime>1, opens every page.html with zero console errors, types a note
  in every box, reloads, and requires every note to persist with updated_at.
- Require one screenshot per PR plus checks.json listing every step with
  expected, observed, pass, and screenshot. Require zero page errors.
- Inspect screenshots before handoff. Cite the proof directory in the
  handoff note. API-only checks and single-path screenshots do not pass
  this recipe.
- Hub changes without a fresh scripts/verify_notes_hub.py PASS and cited
  proof are not ready for the operator.

## Gotchas

- The archived graded study stays untouched under its archive directory.
  The hub never shows its questions, answers, or grades.
- PRC re-renders land in the render directories; the hub serves them live
  at request time, so never copy outputs into the hub or the proof.
- Clearing a notes box saves the empty text like any other edit.

## Handoff (operator-facing)

Before any handoff message with a hub URL, prove the exact handed-off server
with the supervised handoff script.

Run .venv/bin/python scripts/handoff_study_hub.py <notes-dir> from the repo
root. The script starts or reuses one supervised hub process (detached setsid
background nohup pidfile, with --stop), waits until the exact printed URL
answers, and loads that exact URL in a real browser with an isolated
agent-browser session.

Require the hub to render all eight PR sections with zero page errors.
Require every GitHub href to be the right github.com pull URL and every
infographic to answer. The checks never type notes, so notes.json must read
identical before and after.

Require the handoff record JSON under artifacts/study-v3/handoff/notes/ with
url, port, pid, pidfile, screenshot, and each check result. Cite the record
and screenshot in the handoff note. Do not hand off a URL when the script
exits nonzero or prints HANDOFF REFUSED; it refuses to print a URL when any
check fails.
