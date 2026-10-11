# Independent parent review

**TL;DR:** Do not start the scored study. Three confirmed blockers remain: missing Lens delivery, incorrect MC credit, and failed autosave recovery. Earlier seal, threading, and browser defects changed during review; they are not current findings.

Reviewed independently with the parent model's judgment. No agents were spawned. Only this report was written in the checkout. Reproductions used temporary fixture studies. No real study answers, candidate records, or application files were edited.

## Review boundary

Root: `/Users/koval/dev/prc/.claude/worktrees/paired-evaluation`.

Read `kit.py`, `session.py`, `assets.py`, CLI and evaluation I/O changes, paired tests, design, and decision TSV. Also checked the cited materials report and anonymous Lens capture properties. Candidate identities are omitted.

Another writer changed the implementation during review. The final kit and session snapshot was copied at 2026-10-11 19:12:17 UTC. The updated assets file was then copied and exercised separately. These final hashes still matched the checkout at 19:16 UTC:

| File | SHA-256 |
| --- | --- |
| `src/prc/evaluation/kit.py` | `19566f8662d576f7e3a39f6cd01720954df6a4d95ea428fe4ad256aebd3ca5b3` |
| `src/prc/evaluation/session.py` | `86e7056d2cdf2339ed3bdd7bf399466e3f51b2846aa22069acd613d320f1375e` |
| `src/prc/evaluation/assets.py` | `4dee582ae51b2b431b2949486782229204f46dcd5aa403f4c1d877c9404b7d29` |

Frozen sources and tests: `/private/tmp/paired-parent-cutoff-tuscmy6k`. Findings below apply to those hashes. Later changes need their own verification.

At report closure, `session.py` changed to `e2c304aa7c3e6a4443a3effe78f0ff1a532231579246b430a55f2d523f154528`. The inspected diff only imports `cast` and casts the HTTP server before reading its port. It does not change the findings below. The other two hashes still match.

## Current blockers

### [P1] Preparation accepts a Lens packet with no deliverable entry page

[kit.py:188](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/src/prc/evaluation/kit.py:188) validates SVG records but never requires a Lens entry page. [session.py:163](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/src/prc/evaluation/session.py:163) always assigns `aid/index.html`. [session.py:431](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/src/prc/evaluation/session.py:431) returns 404 when that file is absent.

Evidence: `build_manifest()` passed preparation. Preview and start returned 200 with `aid_kind=lens`. GET on the returned `aid_url` returned **404**. The prepared study contained zero `lens/index.html` files. All six inspected genuine source captures also lack that entry file. Their state annotations parse as `graphKey`, `headSha`, and `v`.

This starts the timed baseline reading without its assigned tool. Require and verify the actual Lens presentation entry before accepting the packet. Preserve the genuine captured diagrams and canvas provenance.

Screenshot from the updated page: [latest-active.png](/private/tmp/paired-parent-cutoff-tuscmy6k/latest-active.png). The earlier frozen-page artifact failure is retained at [current-artifact-failure.png](/private/tmp/paired-parent-cutoff-tuscmy6k/current-artifact-failure.png). The HTTP 404 is the decisive evidence.

### [P1] MC awards need not match the frozen answer key

[kit.py:729](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/src/prc/evaluation/kit.py:729) checks allowed anchors and blank answers. It never compares a nonblank MC answer with `question["key"]`.

Evidence: the frozen fixture key is `cache/evict.go`. Saved `docs/notes.md`, submitted, and closed through `StudySession`. Imported `{q1: 1, q2: 0, q3: 0}` with the correct digest. `apply_scores()` accepted it and emitted **`[1.0, 0.0, 0.0]`**. This reproduction used the final kit and session hashes.

Incorrect objective answers can therefore change the measured treatment difference. Compute MC credit from the frozen key, or reject an imported award that disagrees. Keep short-response awards on the specified rubric anchors.

### [P1] One failed autosave prevents all later saves and completion

[assets.py:49](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/src/prc/evaluation/assets.py:49) rethrows an error into the shared promise queue. Each later save chains with `queue.then(...)`, so its request never runs. [assets.py:60](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/src/prc/evaluation/assets.py:60) also awaits the rejected queue before sending submit or abort.

Browser reproduction: start a fixture reading. Wrap `fetch` to reject only the first `/api/answers` request. Enter Question 2, wait 600 ms, edit again, wait 600 ms, then click Abort. The network wrapper permits every subsequent request.

Observed **one save attempt**, empty persisted answers, and a trial that remains **active**. The page reports “Save failed. Keep this page open.” Keeping it open does not restore the queue. Reload would discard the unsaved text.

Recover the save queue after failure while retaining the current draft. A later save or completion must retry persistence. Evidence: [latest-poisoned-save.png](/private/tmp/paired-parent-cutoff-tuscmy6k/latest-poisoned-save.png).

## Verification and resolved findings

Initial implementation: **23 kit/session tests passed**. An isolated copy of the CLI E2E test also passed. It retained grading and results at `/private/tmp/paired-parent-e2e-d3kljmel/artifacts/e2e/paired/`. Those 24 passes describe the initial implementation, not the final hashes.

Final kit/session snapshot command, run inside the temporary copy:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests /Users/koval/dev/prc/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_paired_kit.py tests/test_paired_session.py tests/test_paired_regressions.py --basetemp=/private/tmp/paired-parent-cutoff-pytest
```

Result: **25 passed, 5 failed**. The five session tests still use the previous start contract without a trial ID. Log: [tests.log](/private/tmp/paired-parent-cutoff-tuscmy6k/tests.log). The later assets update does not alter those HTTP helpers. The new browser test was read but not run.

Initial safe probes confirmed uncovered questions/metadata/assignment, server seal bypass, concurrent `session.tmp` replacement failures, and stale-tab writes into the next reading. Initial browser probes also lost one simultaneous answer and an immediate-abort draft. The original CSP disabled the generated PRC map; direct viewing of the same bytes rendered its graph.

Final source checks show these changes: the seal now covers study data and assignment; loading compares frozen fields and artifact hashes. Server initialization and start verify the study. HTTP handling is serial. Requests and artifact URLs bind to trial IDs. Lens state JSON is parsed. The page retains controls and includes the current draft at completion. These earlier defects are excluded from current blockers.

Duplicate completion is rejected rather than idempotently acknowledged. The trial ID check prevents a stale request from completing the next trial. Pending outcomes remain unknown in grading. Export requires closure and omits explicit condition, timing, and assignment fields. Content-derived condition inference remains an acknowledged limitation.

No real GitHub reading or genuine Lens presentation was driven. The revised CSP was inspected, but the revised actual PRC map was not re-tested. Fixture browser checks do not establish real-study readiness. Full lint, typecheck, build, and full-suite verification were outside this bounded review.

## Decision and claim audit

**Two unsupported claims were identified.**

- [.audit/paired-evaluation.tsv:5](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/.audit/paired-evaluation.tsv:5) states the writer produced no runnable code after eleven minutes. Its cited source directory does not establish that elapsed time or the dispatch history. Treat this historical rationale as uncorroborated by the cited evidence, not disproved.
- [docs/design/paired-evaluation-v2.md:31](/Users/koval/dev/prc/.claude/worktrees/paired-evaluation/docs/design/paired-evaluation-v2.md:31) claims content-addressed SVG files. The validator checks a 32-hex filename and a separate byte hash. It never compares the filename with the hash prefix. Renaming fixture SVGs to `00000000000000000000000000000000.svg`, while retaining their correct hashes, still passed preparation.

TSV rows 2–4 record the selected size, local-server design, and external contamination limitation. Their cited plan/design/materials sources support those decisions. They do not establish implementation verification. The TSV has no implementation-completion or real-browser-pass claim; its implementation result remains open.

The no-comments lens found no material comment blocker. Public contracts and HTTP method naming suppressions explain necessary interfaces. Section banners and test narration do not warrant correctness findings. No comment or code edits were made.

**Next step:** Complete a reliable paired-study reading feature: verified Lens delivery, recoverable answer persistence, and key-based MC grading. Verify both real tool presentations, duplicate tabs, failure recovery, closure, and blinded export before starting scored readings.
