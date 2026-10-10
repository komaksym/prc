**TL;DR:** The stated step 1 machine claims are supported at `be2e7fa167ffd45cbc5d5e3d5ce6320927df3e60`. Direct byte comparisons and saved execution records support the release run and all three acceptance packages. Human acceptance, subjective listening, and D21 approval remain open. No introduced regression was found in the two-line decode fix within this review's scope.

**Scope.** This was an independent, read-only claims review in `/Users/koval/dev/prc/.claude/worktrees/readiness`. HEAD matched the requested source. I read the specified documentation, closure report, release logs, combined verification, and each case's records. I wrote only this report. I ran no suite, browser, external write, message, visual inspection, or audio listening session. The parent's hub clicks and image inspection are outside this review.

The pstack Prove It Works principle led me to compare actual bytes against Git and the recorded hashes. Test Behavior, Not Implementation led me to check the CLI failure, fallback assertions, and red/green proof. Poteto and unslop judgment kept machine results separate from human conclusions. Throughput checkpoint is n/a for this read-only investigation.

**Release verification is supported.** `tests.log` reports 855 passed in 381.64 seconds. I independently counted 855 JUnit cases and zero failure, error, or skipped elements. Both binary-Tesseract regression cases are present and successful. `lint.log` passes. `format.log` reports 599 formatted files. `typecheck.log` passes on 109 source files. `build.log` records successful sdist and wheel builds.

The installed-wheel smoke is also supported. `wheel-check.json` identifies the installed package and records no browser errors. `wheel-cli.json` records a successful explanation. The saved verifier asserts map interaction, drawer opening, walkthrough readiness, and video properties before writing its success record. `/private/tmp/step1-final-release.log` records completion. My read-only `ffprobe` check confirms 1920×1080 video and a 41.775-second audio stream. The smoke's `run.json` records `kokoro` and a passed check. Doctor reports Kokoro, Chromium, Tesseract, and ffmpeg available.

Evidence is [the release run](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/release/verify/run-NYgULN/tests.log), [JUnit](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/release/verify/run-NYgULN/tests.xml), [wheel check](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/release/verify/run-NYgULN/wheel-check.json), and [verifier](/Users/koval/dev/prc/.claude/worktrees/readiness/scripts/verify-release.sh:100).

**Source identity is independently confirmed.** I enumerated the fixed Git tree and compared every relevant file with the isolated checkout. All 281 source, test, script, and build metadata paths match. All 75 listed sdist inputs match that Git revision. The archive contains only one additional generated file, `PKG-INFO`. Its SHA-256 matches the recorded archive hash.

I also compared all 70 package files in the wheel with `src/` at the fixed revision. All match. Those same 70 installed package files match the wheel. The wheel SHA-256 is `003d02db8184e05805491a4de639d7bd5e7a599b0a1776dc76e3bd5e69f6cc48`.

The counts have explicit boundaries. The 281-path comparison excludes working audit, plan, and documentation files. The sdist intentionally excludes tests and maintainer scripts. The package cache started empty according to the saved record. Chromium and Kokoro weights were reused. This supports an empty package-cache claim, not an entirely fresh machine claim. Evidence is [source-archive-compare.json](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/release/verify/run-NYgULN/source-archive-compare.json).

**All three acceptance identities are supported.** Each render identity names `be2e7fa`, the same verified wheel hash, and its installed `wheel-env/bin/prc` command. Each command requests Kokoro and runs outside the source package directory. Saved completion logs and combined verification confirm installed-wheel execution.

| Case | Frozen base | Frozen head | Current duration | Hash checks |
| --- | --- | --- | --- | --- |
| librarysync-98 | e3742c159512078753c40da9226cb5fd72de5444 | d24bcde9cfb3b1bb93dc77147d0d31f7598a264c | 73.600 s | 20 match |
| em-5756 | 9e2db120d3ea98e1e37fe939972ef364ab4508a9 | 3755cd396c0075e29d3ea6638e0fd2e572f3ed3b | 63.550 s | 20 match |
| swarm-116 | 3dafc39698bafd42172a7a19230153d4127dc8e1 | 2f7696dda0342ae9d5b2bfdf76bc57d64dc890a5 | 59.450 s | 19 match |

The 59 checks cover recorded inputs, outputs, and supplied candidates. None mismatches. Each original diff and numstat also matches a fresh comparison of its retained Git objects. Captured maps, rendered maps, provenance, combined verification, and saved GitHub metadata agree on the pairs. The GitHub record describes its check time, `2026-10-10T13:09:22.364Z`. It does not freeze the live PR page or establish its later state.

Evidence is [verification.json](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/verification.json), [GitHub snapshot](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/github-current-step1.json), and the [librarySync](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/render-identity.json), [em](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/em-5756/render-identity.json), and [swarm](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/render-identity.json) render identities.

**The correct gated PNG bytes are published locally.** Each published image matches its accepted candidate and the gate's SHA-256. Each `doc.html` embeds those exact PNG bytes. Each comment links to `infographic.png` with the AI disclosure. The frozen candidate copies also have recorded hashes, checked by the retained acceptance verifier.

| Case | Selected candidate | Published SHA-256 | Successful OCR word counts |
| --- | --- | --- | --- |
| librarysync-98 | candidate-04.png | 4954efd2e4db8f73577b430b291c28637211e23808ca2595038d0c16b96db19e | 72 in each mode |
| em-5756 | candidate-04.png | deec5ea51249e74523dc1832eeb1e6d1d2a4d2b85fcbae0fad0be13faedf14b3 | 76 in each mode |
| swarm-116 | candidate-02.png | 78497407b0cbacbf5d16ff4112da755b29702687cc36202657d6b642ec76c45a | 60 in each mode |

Every accepted record has the four expected modes, no failed modes, no missing text, and no invented words. Earlier librarySync and em candidates remain recorded as rejected. Four successful readings establish tool completion and the gate's decision. They do not prove every pixel or visual relationship is correct. Local output publication supplies no authorization for public publication.

**Saved browser execution supports the rendering and playback claim.** Each `browser-check.json` has zero page errors and zero remote requests. Playback records show 1920×1080 video, no media error, and time advancing beyond the selected frame. The saved driver explicitly awaits playback advancement. It also checks the map, drawer, tour, card, walkthrough, decoded infographic, and phone overflow before recording success.

The three playback times are 41.456382, 30.704905, and 38.4016 seconds. They exceed the selected frame times by more than 0.25 seconds. All 19 recorded frame files exist. Their scene types and times match the current rendered boards. Browser facts and coverage match combined verification. The completion log records successful browser checks for all three cases. These support the recorded execution claim. They do not substitute for the parent's visual inspection or human listening.

Evidence is [the browser driver](/Users/koval/dev/prc/.claude/worktrees/readiness/.audit/capture-trustworthy-browser.py), [rebuild completion log](/private/tmp/step1-acceptance-rebuild.log), and each case's `browser-check.json` beside its render identity.

**Voice matching supports Kokoro identity for the sampled lines.** The helper synthesizes one board line with Kokoro and say. It compares each reference against the video's audio by normalized waveform correlation.

| Case | Kokoro correlation | Say correlation | Transcript difference rate |
| --- | --- | --- | --- |
| librarysync-98 | 0.995 | 0.107 | 0.121 |
| em-5756 | 0.995 | 0.151 | 0.085 |
| swarm-116 | 0.994 | 0.103 | 0.147 |

Each matched line is the current board's first spoken line. Each audio record matches the copy retained in its render identity. The video hashes remain unchanged. The results strongly support Kokoro over the tested say reference for those samples. This is not a whole-video voice classification or a subjective quality judgment. Evidence is [voice-match.py](/private/tmp/voice-match.py) and each case's `voice-match.json`.

**Transcripts establish an unresolved listening limit.** I recomputed the recorded word counts, differences, and rates from each current board and saved transcript. All match. Ambiguities include `S2E3` versus `SE`, `onComplete` versus `on complete`, and `ErrNotExist` versus `earn not exist`. Other differences join or split technical names.

These are ASR differences. They cannot establish an audible pronunciation defect, and they cannot prove somebody listened. The transcript files do not literally match their boards. Any strict transcript-equality or completed-listening claim would overstate this evidence. I make no audible-defect finding. Evidence is [the transcript helper](/private/tmp/listen-transcript.py) and each case's `audio-transcript.json`.

**The decode correction has valid regression proof.** Commit `03d198a` adds two real `prc explain` cases before the fix. The fake external Tesseract emits invalid UTF-8 on stderr during version probing or OCR. Both saved red failures reach `UnicodeDecodeError` inside subprocess decoding. They are product failures, not missing-browser failures. The green log reports two passes. Both also pass in the 855-case release JUnit record.

The tests assert a tool verdict, failed-mode counts, no published infographic, and the retained card link. The release run retains both check JSON files and card PNGs. The version case records no readings. The OCR case records all four failed modes.

The executable production delta adds `UnicodeDecodeError` to the catches in `tesseract_version()` and `_read_mode()`. It returns their existing failure sentinels, `""` and `None`. `gate()` converts these into tool decisions and preserves fallback behavior. Other changes in the reviewed delta remove comments or rename the test's stylesheet variable without changing its bytes.

I ran a read-only boundary probe using those functions extracted from both Git revisions. It exercised valid output, nonzero exit, binary stdout, and binary stderr. Both old functions raised on binary output. Both corrected functions returned their failure sentinels. Successful and nonzero-exit behavior stayed unchanged. `git diff --check 03d198a..be2e7fa` also passed. No introduced regression was found. This probe is narrow evidence, not another suite or GUI run.

Evidence is [the source catches](/Users/koval/dev/prc/.claude/worktrees/readiness/src/prc/presentation/infographic.py:420), [CLI regression](/Users/koval/dev/prc/.claude/worktrees/readiness/tests/test_e2e_infographic.py:123), [red log](/private/tmp/step1-binary-red.log), [green log](/private/tmp/step1-binary-green.log), and the release run's `e2e/infographic/binary-*` records.

**Open gates and findings.** No unsupported core machine claim or blocking regression was found. No required artifact was missing. Three limits must remain explicit. Voice matching samples one line per video. OCR acceptance is a machine text gate. Browser execution and ASR do not supply visual acceptance or subjective listening.

At the reviewed documentation snapshot, S6, S7, and S8 remain unchecked. Launch documentation still describes acceptance rebuilding and future Kokoro videos. These are pending working sections, not completed claims. I did not infer their completion from newer artifacts. The plan's phrase about listening and its transcript-match predicate need evidence distinctions before closure.

All three worksheet decisions and usefulness scores remain pending. D21 requires explicit user approval for pushing, publication, and license choice. `START-HERE.md` also gates PR creation. No such approval is supplied by these artifacts. Evidence is [the worksheet](/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/acceptance.md), [D21](/Users/koval/dev/prc/.claude/worktrees/readiness/docs/mvp/DECISIONS.md:77), [PLANS.md](/Users/koval/dev/prc/.claude/worktrees/readiness/PLANS.md:22), and [closure.md](/Users/koval/dev/prc/.claude/worktrees/readiness/.audit/step1-reviews/closure.md).

**Next step.** Complete the parent-owned visual evidence and current documentation, then conduct the user's three-case acceptance and listening review. Keep release, push, PR creation, and public publication gated on explicit approval.
