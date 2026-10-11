# Step 1 requirement audit

Summary. Implementation, installation, machine checks and the three review packages are complete. Listening is verified by calibrated speech recognizers, which the user chose on 2026-10-11 in place of direct listening.

| Requirement | Current evidence | Result |
| --- | --- | --- |
| Fix the voice lock and use installed Kokoro. | 38174a4, be2e7fa, run-NYgULN/doctor.log, wheel install and smoke, all three run.json files, sampled soundtrack correlations. | Verified for the installed source and sampled voice identity. |
| Fail release verification when Kokoro is missing. | tests/test_voice_gate.py, the forced --voice kokoro verifier, 855-case JUnit including missing-backend regressions. | Verified. |
| Add baoyu infographics with PRC words and the OCR gate. | Each case's infographic-work prompt, generation-rounds.json, immutable candidate records, preview brief, published PNG hash and four successful readings. All originals were viewed directly. | Verified. OCR's limits remain explicit. |
| Rebuild the map on PR Lens. | Pinned MIT bundle, runtime and vendor tamper regressions, five maintainer CLI checks, converter tests and actual browser map/drawer/tour screenshots. | Verified. All changed files remain navigable. |
| Rebuild three real acceptance PRs with original diffs at matching revisions and infographics inline. | acceptance/verification.json, render-identity.json, github-current-step1.json, original Git object comparisons, installed-wheel commands and doc/hash checks. Re-rendered at dae9737 with the run-Bkni85 wheel; map, card, comment and infographic files are byte-identical to the be2e7fa build. | Verified at dae9737. |
| Verify actual browser and video outputs. | be2e7fa: three browser-check.json records, 41 agent-browser link checks, visual-final.md. dae9737: hub-browser-dae9737 with 15 screenshots, 51 local references present, three infographics rendered, three videos playing at their new lengths, walkthroughs, map drawers and tours, and caption frames that keep code names. | Verified within the stated surfaces. |
| Verify by listening to the videos. | Each case's listening.json: Parakeet (muesli 0.8.5) heard 16 of 16 code-name mentions after its planted controls passed. listening/whisper-base-dae9737.json: Whisper base also heard 16 of 16. | Verified by machine listening, per the user's decision. Tone and pacing stay with the human reviewer. |
| S9, added 2026-10-11. Rewrite code names into speakable words before Kokoro, and gate every video on a calibrated recognizer (Parakeet first, Whisper fallback). | Commits 6736af2, ea3d1da, a864203, 012649e, dae9737. run-Bkni85: verify-release.sh from an empty cache, 884 passed, 0 skipped, wheel listening passed. All three acceptance videos pass `prc listen`. | Verified at dae9737. |
| Keep accurate facts, honest coverage and publication boundaries. | Original diff/numstat and quoted-line checks, shared Facts, explicit unsupported-Go disclosures and partial-line counts, claims-final.md, D21. | Machine facts verified. Human acceptance and publication remain separate. |

Current source is dae9737 (run-Bkni85). The package cache started empty. Chromium and Kokoro weights were reused. The be2e7fa archive comparison covered 281 checkout paths and 75 included archive inputs.

Visual limitations are retained. The cards abbreviate analysis warnings and paths. Embedded scene citations are small. Some tertiary text has weak visual contrast. Main titles, code and active captions have no observed destructive clipping or overlap.

The automatic approval reviewer temporarily rejected one audio-check command because its account usage check could not run. A later read-only usage check reported ordinary usage allowed. The same escalation path then approved the retry, and both remaining soundtrack checks completed. No approval was bypassed.

The parent accepted the independent claims and visual reports within their stated scopes. Neither supplies human acceptance. A transcript difference is not automatically an audible defect.

Every step 1 requirement now has current evidence. Human acceptance of the three PRs stays with the user. A release machine needs Muesli or openai-whisper, because the release run rejects the skipped E2E listening test. Do not push, open a PR or publish without explicit approval under D21.

Next step. The sole human reviewer listens at the worksheet's named times and records the three acceptance judgments.
