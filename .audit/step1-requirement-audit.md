# Step 1 requirement audit

Summary. Implementation, installation, machine checks and the three review packages are complete. Direct listening remains unverified.

| Requirement | Current evidence | Result |
| --- | --- | --- |
| Fix the voice lock and use installed Kokoro. | 38174a4, be2e7fa, run-NYgULN/doctor.log, wheel install and smoke, all three run.json files, sampled soundtrack correlations. | Verified for the installed source and sampled voice identity. |
| Fail release verification when Kokoro is missing. | tests/test_voice_gate.py, the forced --voice kokoro verifier, 855-case JUnit including missing-backend regressions. | Verified. |
| Add baoyu infographics with PRC words and the OCR gate. | Each case's infographic-work prompt, generation-rounds.json, immutable candidate records, preview brief, published PNG hash and four successful readings. All originals were viewed directly. | Verified. OCR's limits remain explicit. |
| Rebuild the map on PR Lens. | Pinned MIT bundle, runtime and vendor tamper regressions, five maintainer CLI checks, converter tests and actual browser map/drawer/tour screenshots. | Verified. All changed files remain navigable. |
| Rebuild three real acceptance PRs with original diffs at matching revisions and infographics inline. | acceptance/verification.json, render-identity.json, github-current-step1.json, original Git object comparisons, installed-wheel commands and doc/hash checks. | Verified at be2e7fa. |
| Verify actual browser and video outputs. | Three browser-check.json records, 41 successful agent-browser link checks and screenshots, visual-final.md with 44 images and 39 additional caption samples. | Verified within the stated surfaces and sample times. |
| Verify by listening to the videos. | Audio streams, complete ASR transcripts and sampled voice comparisons exist. Direct audio input is unsupported in this runtime. Transcripts have technical-name ambiguities. | Not verified. The review page and worksheet preserve this open requirement. |
| Keep accurate facts, honest coverage and publication boundaries. | Original diff/numstat and quoted-line checks, shared Facts, explicit unsupported-Go disclosures and partial-line counts, claims-final.md, D21. | Machine facts verified. Human acceptance and publication remain separate. |

Current source is be2e7fa. The final archive comparison covers 281 checkout paths and 75 included archive inputs. The package cache started empty. Chromium and Kokoro weights were reused.

Visual limitations are retained. The cards abbreviate analysis warnings and paths. Embedded scene citations are small. Some tertiary text has weak visual contrast. Main titles, code and active captions have no observed destructive clipping or overlap.

The automatic approval reviewer temporarily rejected one audio-check command because its account usage check could not run. A later read-only usage check reported ordinary usage allowed. The same escalation path then approved the retry, and both remaining soundtrack checks completed. No approval was bypassed.

The parent accepted the independent claims and visual reports within their stated scopes. Neither supplies human acceptance. A transcript difference is not automatically an audible defect.

The goal remains active. Do not claim all step 1 requirements are complete or mark the goal achieved while direct listening is missing. Do not push, open a PR or publish without explicit approval under D21.

Next step. The sole human reviewer listens at the worksheet's named times and records the three acceptance judgments.
