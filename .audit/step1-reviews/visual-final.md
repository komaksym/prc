# Step 1 visual artifact inspection

**TL;DR.** I viewed all 44 inventory images with `view_image` at original detail. All image hashes match, and all 41 derived crops or frames match their current sources pixel for pixel. The em card truncates its unsupported-language reason. The swarm card truncates the affected-file list but retains a meaningful warning. This is an artifact inspection, not human acceptance or a release verdict.

## Scope and method

Worktree: `/Users/koval/dev/prc/.claude/worktrees/readiness`.

HEAD: `be2e7fa167ffd45cbc5d5e3d5ce6320927df3e60`.

Final binding time: `2026-10-10T14:12:47.267249+00:00`.

Inventory: `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/images.json`.

Inventory SHA-256: `49c31521bbf0b401327f93aeb8a15c86b3a185da56064ad066c46fd40d4b3983`.

I inspected 3 cards, 22 walkthrough crops, and 19 decoded video frames. I read each current output/board.json for narration text and sentence timing. I read each acceptance/browser-check.json for the listed frame times. I compared the prose, scene content, card summary, and limitation disclosures. I did not listen to audio.

The user limited this task to existing artifacts. I opened no browser, generated no replacement project artifacts, and made no external writes or messages. I did not edit project files or existing images. Only local inspection tooling and this report were written under /private/tmp.

I followed poteto mode, the project verify skill, Prove It Works, and Unslop. Prove It Works changed the method: I viewed actual pixels and decoded the current videos again. The project verify skill limited the conclusion to inspected artifacts. I did not infer a product or release verdict from screenshots.

Throughput checkpoint: n/a, read-only investigation.

I did not duplicate the parent's direct inspection of accepted infographic originals. The walkthrough crops naturally contain their embedded versions. This report does not certify their original artwork, publication mode, or publication hash audit.

## Concrete findings

1. **Incomplete em card reason.** Inventory image 30 shows the analysis warning ending at `unsupported lan...`. The statement that one file is incomplete remains readable. The exact reason is truncated. Its dependency patch path is visible in the risk column. The title, metrics, entry points, and remaining test-evidence caveats are complete.

2. **Swarm card drops affected paths.** Inventory image 44 says analysis is incomplete for seven files. It shows one complete .go path with `unsupported language`, then truncates the remaining list. This warning is meaningful, but the card cannot show all affected paths. Its zero parsed-symbol and call counts must be read with that warning.

3. **Small embedded scene details.** At the captured 800 px walkthrough width, prose and separate receipt links are readable. The embedded video test citations and fine-print warnings are much smaller. Images 11, 26, and 38 are concrete examples. Full 1920 px video frames expose those details more clearly. No text was missing because of a horizontal page crop.

4. **Weak tertiary contrast.** The video receipt footers and some citations use faint gray text on dark backgrounds. Main headings, code, diagram labels, and active captions have stronger contrast. This is a visual observation, not a measured accessibility contrast result.

No inspected main title, diagram box, selected code row, or active subtitle has visible clipping or destructive overlap. The long LibrarySync append row and em dispatch row wrap completely. Crop edges split some lines vertically. The adjacent 80 px overlaps recover those lines. These seams are inspection crops, not page-layout clipping.

The cards and scenes agree on their main story. LibrarySync shows s1e1 before and s2e3 after watching s2e2. em shows the sheet closing on touch and points to onComplete. Swarm separates the three Compose error types and points to fileLoader.Load. The em card's lack of direct static test-call evidence can coexist with the story's added E2E tests. I compared their displayed wording without auditing the underlying source claims.

## Captions and Go disclosure

All 19 inventory video samples occur 0.5 seconds before their scene ends. None shows a separate subtitle at that time. These samples establish settled scene layout. They do not establish active-caption completeness.

To close that gap, I decoded 39 additional samples from the current MP4s in memory. Each sample time is `sentence.start + (sentence.on + sentence.off) / 2`. I viewed each lower frame region, y=820 through y=1080, at the original 1920 px width. The tool displayed these in-memory samples as JPEG images. No existing image was edited.

Thirty-five samples show complete, readable subtitles that match the board text. Inline code appears without the board's Markdown backticks. Four LibrarySync/em outro samples show no separate subtitle. Their corresponding main outro text appears complete in the inventory frames. I do not count those four blank subtitle regions as proof that a subtitle exists.

I also viewed the full swarm outro frame at 55.205 seconds. Its second subtitle is complete and separated from the large summary. The command and unsupported-Go fine print appear later in the settled 58.950-second frame. This inspection does not establish every animation transition.

The swarm title subtitle at 8.205 seconds explicitly states that PRC can quote the Go diff but cannot build its symbol or call graph. Walkthrough image 36 repeats that statement in full prose. The settled outro at 58.950 seconds explicitly says Go symbol and call analysis is unsupported and directs review to the original diff. Thus the Go disclosure is substantive and readable in the inspected video and walkthrough. The card gives a meaningful incomplete-analysis warning, with the list truncation noted above.

## Per-image viewed status

All paths below are relative to the worktree. Every SHA-256 below is the actual file hash. It also matches the inventory value. VIEWED means the image tool returned the pixels and I inspected them. No listed image was unreadable.

| ID | Case | Kind | Image | Status and observation |
|---|---|---|---|---|
| 1 | librarysync-98 | video | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/screenshots/video-00-title.png` | VIEWED. Title wraps over two lines. Main text and metadata are complete. Footer is faint. No subtitle at this end-of-scene sample. |
| 2 | librarysync-98 | video | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/screenshots/video-01-groups.png` | VIEWED. Before state shows s2e2 watched and s1e1 up next. All boxes and labels fit. Receipt footer is faint. |
| 3 | librarysync-98 | video | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/screenshots/video-02-groups.png` | VIEWED. After state shows earlier gaps in red and s2e3 up next in green. Labels fit. Matches the card's summary. |
| 4 | librarysync-98 | video | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/screenshots/video-03-diff.png` | VIEWED. Helper diff shows complete quoted rows, including the long episode_key tuple. No clipping or overlap. Footer is faint. |
| 5 | librarysync-98 | video | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/screenshots/video-04-diff.png` | VIEWED. Bulk diff wraps append(episode) onto a continuation line. All selected rows remain visible. No clipping. |
| 6 | librarysync-98 | video | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/screenshots/video-05-list.png` | VIEWED. Three full test names fit beside citations. Check marks and count are clear. Citations are faint. |
| 7 | librarysync-98 | video | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/screenshots/video-06-outro.png` | VIEWED. Outro summary, review entry, command, and no-watch fallback omission are complete. No separate subtitle is visible. |
| 8 | librarysync-98 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/librarysync-98-doc-01-y0-1500.png` | VIEWED. Walkthrough header, video duration, embedded infographic, title prose and scene fit. Embedded small text needs closer viewing. |
| 9 | librarysync-98 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/librarysync-98-doc-02-y1420-2920.png` | VIEWED. Before and after diagrams match video states. Prose and receipt links fit. Bottom seam continues in the next crop. |
| 10 | librarysync-98 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/librarysync-98-doc-03-y2840-4340.png` | VIEWED. Helper prose and diff fit. Bulk scene begins below. Embedded code is smaller than the full video text. |
| 11 | librarysync-98 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/librarysync-98-doc-04-y4260-5760.png` | VIEWED. Bulk continuation, tests, and outro prose fit. Embedded test names and citations are very small at this 800 px page width. |
| 12 | librarysync-98 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/librarysync-98-doc-05-y5680-7180.png` | VIEWED. Outro and NOT COVERED section fit. The 16 of 79 disclosure is readable. Missing-line links stay within the page. |
| 13 | librarysync-98 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/librarysync-98-doc-06-y7100-8600.png` | VIEWED. Missing-line links fit within the page. Long list remains readable. Bottom footer continues in the next crop. |
| 14 | librarysync-98 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/librarysync-98-doc-07-y8520-8713.png` | VIEWED. Final footer and head hash fit. Footer has weak contrast. Page ends without visible clipping. |
| 15 | librarysync-98 | card | `artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/output/willtho89-librarySync-98-d24bcde9cfb3/card.png` | VIEWED. Card title wraps cleanly. Six metrics, two entry points and evidence caveats fit. Summary matches the scenes. |
| 16 | em-5756 | video | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/screenshots/video-00-title.png` | VIEWED. Title wraps cleanly. Complete PR metadata and title. Faint footer. No subtitle at this end-of-scene sample. |
| 17 | em-5756 | video | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/screenshots/video-01-groups.png` | VIEWED. Before state shows selection a, Note toolbar, open sheet and keyboard. The red covers-the-keyboard label fits. |
| 18 | em-5756 | video | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/screenshots/video-02-groups.png` | VIEWED. After state crosses out selection a and sheet. Green no-bullet and closed-on-touch labels fit. No overlap. |
| 19 | em-5756 | video | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/screenshots/video-03-diff.png` | VIEWED. onComplete diff fits, with the long dispatch row wrapped after the opening quote. Touch-only annotation clears the code. |
| 20 | em-5756 | video | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/screenshots/video-04-list.png` | VIEWED. Keyboard list rows fit. The long patch citation crowds the third row's right side but remains separate. Citation text is faint. |
| 21 | em-5756 | video | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/screenshots/video-05-list.png` | VIEWED. Three full test descriptions fit beside citations. No clipping. This diagram alone does not show the headless-keyboard caveat. |
| 22 | em-5756 | video | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/screenshots/video-06-outro.png` | VIEWED. Outro summary, entry point, command and follow-up file list fit. No separate subtitle is visible. |
| 23 | em-5756 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/em-5756-doc-01-y0-1500.png` | VIEWED. Walkthrough title, metadata, embedded infographic and title prose fit. Embedded metrics agree with the card. |
| 24 | em-5756 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/em-5756-doc-02-y1420-2920.png` | VIEWED. Before and after diagrams match the video. Prose and receipt links fit across the overlapping crop seam. |
| 25 | em-5756 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/em-5756-doc-03-y2840-4340.png` | VIEWED. Callback prose, wrapped code and keyboard-handling prose fit. Embedded patch citation is tiny at this width. |
| 26 | em-5756 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/em-5756-doc-04-y4260-5760.png` | VIEWED. Tests and outro prose fit. Headless Chrome keyboard limitation is readable in the prose. Embedded test citations are tiny. |
| 27 | em-5756 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/em-5756-doc-05-y5680-7180.png` | VIEWED. NOT COVERED discloses 3 of 112 lines and unavailable line references. Long patch paths fit. No horizontal clipping. |
| 28 | em-5756 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/em-5756-doc-06-y7100-8600.png` | VIEWED. Missing-line list fits. Top and bottom partial lines are crop seams, recovered by adjacent overlapping crops. |
| 29 | em-5756 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/em-5756-doc-07-y8520-9866.png` | VIEWED. Remaining references, opaque changed-file list and footer fit. No missing page tail. |
| 30 | em-5756 | card | `artifacts/trustworthiness/2026-10-09/acceptance/em-5756/output/cybersemics-em-5756-3755cd396c00/card.png` | VIEWED. Card metrics and entry points fit. Dependency patch path wraps. Analysis warning truncates at unsupported lan...; reason is incomplete. |
| 31 | swarm-116 | video | `artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/screenshots/video-00-title.png` | VIEWED. Title and metadata fit. No subtitle remains at this end-of-scene sample. Go limitation is absent from this particular static frame. |
| 32 | swarm-116 | video | `artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/screenshots/video-01-groups.png` | VIEWED. Read, YAML syntax and schema failure groups fit. All three full error type names are readable. |
| 33 | swarm-116 | video | `artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/screenshots/video-02-diff.png` | VIEWED. Go diff rows fit, including the long fmt.Errorf and structured-error returns. No clipping or overlap. |
| 34 | swarm-116 | video | `artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/screenshots/video-03-list.png` | VIEWED. Two complete test names and citations fit. Green marks are clear. Footer is faint. |
| 35 | swarm-116 | video | `artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/screenshots/video-04-outro.png` | VIEWED. Outro summary, fileLoader.Load entry and command fit. Complete Go unsupported-analysis disclosure is visible below the command. |
| 36 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-01-y0-1500.png` | VIEWED. Walkthrough title, metrics and title prose fit. Prose explicitly says PRC cannot build the Go symbol or call graph. |
| 37 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-02-y1420-2920.png` | VIEWED. Three error types match video groups. Diff prose and code fit. Receipt links continue over a crop seam. |
| 38 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-03-y2840-4340.png` | VIEWED. Test prose and outro fit. Go warning is complete inside the outro image but very small at this page width. |
| 39 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-04-y4260-5760.png` | VIEWED. NOT COVERED says 5 of 329 lines. Missing-line links fit in two columns. Bottom seam continues in the next crop. |
| 40 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-05-y5680-7180.png` | VIEWED. Missing references fit in two columns. No horizontal clipping. Partial edge rows are crop seams. |
| 41 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-06-y7100-8600.png` | VIEWED. Test and removed-line references fit. No horizontal clipping. Partial edge rows continue in adjacent crops. |
| 42 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-07-y8520-10020.png` | VIEWED. Compose and Git references fit. No horizontal clipping. Long paths use one column where needed. |
| 43 | swarm-116 | doc | `artifacts/trustworthiness/2026-10-09/inspection-be2e7fa/swarm-116-doc-08-y9940-11238.png` | VIEWED. Remaining references, five omitted files and final footer fit. No missing page tail. |
| 44 | swarm-116 | card | `artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/output/swarm-deploy-swarm-deploy-116-2f7696dda034/card.png` | VIEWED. Card summary and metrics fit. Warning says analysis is incomplete for 7 files and shows unsupported language for the first .go file. Remaining paths truncate. |

## Inventory hash and source binding

`python3 /private/tmp/step1-visual-read.py bind` passed twice. It found 44 of 44 image hash matches and 41 of 41 derived-image pixel matches. The inventory, image bytes, and all 36 recorded output hashes stayed unchanged between checks.

The 22 walkthrough crops match their case's screenshots/doc.png pixels at the stated y coordinates. Coverage extends from y=0 to the complete page bottom in each case. The 19 video frames match FFmpeg decodes of the current output/video.mp4 at the exact browser-check times. These comparisons use RGB pixels and no resize. The three cards are the current output/card.png files.

### librarysync-98

Output directory: `/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/librarysync-98/output/willtho89-librarySync-98-d24bcde9cfb3`.

Recorded renderer commit: `be2e7fa167ffd45cbc5d5e3d5ce6320927df3e60`.

Wheel SHA-256: `003d02db8184e05805491a4de639d7bd5e7a599b0a1776dc76e3bd5e69f6cc48`. The existing wheel matches the recorded value.

render-identity.json SHA-256: `b5873db98112b1334aeb00d701543be48cf37642c8a53e087685d3b34b8a3aac`.

browser-check.json SHA-256: `8acf4c9719a1fac1102339d378e672ea207f664e91a3ccc5f46454834810ece0`.

Full-page screenshot SHA-256: `6b2f6876279556b78e0c5425bd808ec44b5ac32274067d9477789a5e5d3cba2b`.

| Current output | Actual SHA-256 | Matches render identity |
|---|---|---|
| `map.json` | `4c0a403f0f50211be7bc1a6b220195854b5a3c0bdb8a9e0cbbc92bc8b4fbdb20` | YES |
| `map.html` | `887d710b86408ad811efda10976b4e06f21fffb75df8629478b1092a7fe8d00a` | YES |
| `board.json` | `47195e41ef1335b3132e9f06f2d1531ff767ae860cade6ba6198df10b4bf8cb5` | YES |
| `video.mp4` | `3a8a3d2b36c807534e48eb9e690fd09b473cc5848cd0cbeb305932beef508c35` | YES |
| `doc.html` | `52b759cc8b0b58f02c87a35a4cfd52de0a7cd400fbb24995940a14e62dea801f` | YES |
| `card.html` | `160c0595dabd77b5bf183a534296586768f12e2dfc746be780233fb8af7425ea` | YES |
| `card.png` | `395fe7f39629024ea2f36a4f4a0f1ffc5038e144fe0b35c32f190dd8c71a92d0` | YES |
| `comment.md` | `f3e597c4468178fdd7ee23577e29a51861ab09a14404d25a44d7d4eb9f1343a4` | YES |
| `run.json` | `e04a50280406692daccf7d1156ef7fe4b997b7051fca2694166b47e352f8a44d` | YES |
| `infographic/brief.json` | `9952b8dbfba72b05b9a797c18db53bb46a9b6c6279abbfd4870cf72c64029ff2` | YES |
| `infographic/check.json` | `5394603e7e1ed711f9cbc062bb75d02bb27fd0472e6bf1d248517ab04a3da876` | YES |
| `infographic.png` | `4954efd2e4db8f73577b430b291c28637211e23808ca2595038d0c16b96db19e` | YES |

### em-5756

Output directory: `/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/em-5756/output/cybersemics-em-5756-3755cd396c00`.

Recorded renderer commit: `be2e7fa167ffd45cbc5d5e3d5ce6320927df3e60`.

Wheel SHA-256: `003d02db8184e05805491a4de639d7bd5e7a599b0a1776dc76e3bd5e69f6cc48`. The existing wheel matches the recorded value.

render-identity.json SHA-256: `f8c0f7d8ca748206457c00b19d0e26536d82499a4adf25611bf974ef4e7bd205`.

browser-check.json SHA-256: `12e2452050ef64c9c4363c18800d3d0a9e32b8455504c7e47c5f4d5c8c683f69`.

Full-page screenshot SHA-256: `bfb791c33fae39bb11265826b2a156f1dbf4a20b678f2dacd6822de2e7a8c5db`.

| Current output | Actual SHA-256 | Matches render identity |
|---|---|---|
| `map.json` | `fe8e7e859e4b09af4f1337723a0397582e87226e3d6017af48c2efeb3cf38b09` | YES |
| `map.html` | `7656cac161bef3a0f9b390b258297915322779f62360a774d088d0b870ef14b3` | YES |
| `board.json` | `46098f85b81ce28299e8a30fe2c927734f480a52443a4fa13bbd38fa69de11cd` | YES |
| `video.mp4` | `c9f6fc2612b78766efda878c838f5845e6b7afab1e10873581bd7e84578c535e` | YES |
| `doc.html` | `f7653c1c7e33301319535ebe64fb789a0c4b12a225549234b5146d64dd3a5409` | YES |
| `card.html` | `084ba1dcf8c0c7cabeb7b44f45500e478bd6e31d8fc3b3005a244b27ff45f195` | YES |
| `card.png` | `a182e0543797a4661f590cf9a165770cb90f90747daed9ccf4e712c15503b00e` | YES |
| `comment.md` | `3ae975bda0849ffb7fc5ce134244f48dd4a173f38e70e37e8a1273742c3b2366` | YES |
| `run.json` | `259931d5c5f8fd1f362ffd3e5d4f451e39e52329d3948337b3d5b22ccb644263` | YES |
| `infographic/brief.json` | `37a81439fcfc53216ffbc5b2140b60d8864264351fa4b2272f33e32009ee29f7` | YES |
| `infographic/check.json` | `3545c783ad50748e0ac875307ac34cd05f77ea0947e925d3c3c4482516839d7b` | YES |
| `infographic.png` | `deec5ea51249e74523dc1832eeb1e6d1d2a4d2b85fcbae0fad0be13faedf14b3` | YES |

### swarm-116

Output directory: `/Users/koval/dev/prc/.claude/worktrees/readiness/artifacts/trustworthiness/2026-10-09/acceptance/swarm-116/output/swarm-deploy-swarm-deploy-116-2f7696dda034`.

Recorded renderer commit: `be2e7fa167ffd45cbc5d5e3d5ce6320927df3e60`.

Wheel SHA-256: `003d02db8184e05805491a4de639d7bd5e7a599b0a1776dc76e3bd5e69f6cc48`. The existing wheel matches the recorded value.

render-identity.json SHA-256: `94221b1b449eed896863786b374fa509f3bff5c293caa3d07253005c9ddd6aa9`.

browser-check.json SHA-256: `330d29ce5a642f5f2bbbdfc76ad4f01f1839de2031df7715f7ecd1734a6262a7`.

Full-page screenshot SHA-256: `f6772a29a9ce703b594c61b10a219e2aac2cd3792905e40fa201d3471a5f4d31`.

| Current output | Actual SHA-256 | Matches render identity |
|---|---|---|
| `map.json` | `53e5b9ccaa9b26f7289911fe7174245ebb9e14de60ed96937f6b40438518a6e8` | YES |
| `map.html` | `5a8959f8ae71ccda042f75f5f1fc3b34faceb74ee7494f6f300ece00eb70e0ae` | YES |
| `board.json` | `7a64b256a8156414527cfef518dc3ae20e371cc5d97773df2706d97a27be2368` | YES |
| `video.mp4` | `04e2b15e17ae881df45a75b426e37715a2dc020386c222da154212cec8963758` | YES |
| `doc.html` | `d197384342cf1a45d12424e39f70624a9b7cbe557ea3c3c611764d4be8be814c` | YES |
| `card.html` | `526e97dbb3e58c00bf9417ba9b9061dd1c9c5fe54423bf244de5ea621db882a7` | YES |
| `card.png` | `e153d45d4a9b751d27863022f6502b616331b343d95857686d60dddaf12aab2f` | YES |
| `comment.md` | `1df7593ea0c72aca49640226518d4351f0fdce52f830c6bc4d18dfb3aaffc557` | YES |
| `run.json` | `6f75fcb4765bfeb6133dde132eccf4b67b972529b12c30b275290147b15f1f4f` | YES |
| `infographic/brief.json` | `0f6f06dd7e181135f4ba4f51c8e8062cc10a66c039bee0e38e167f358fda5436` | YES |
| `infographic/check.json` | `3ba0a803c87845f917f96e379f63ac15bda11032196fd6d8868229dc1304944a` | YES |
| `infographic.png` | `78497407b0cbacbf5d16ff4112da755b29702687cc36202657d6b642ec76c45a` | YES |

### Image hashes and decoded-frame times

| ID | Dimensions | Actual SHA-256 | Binding |
|---|---|---|---|
| 1 | 1920 × 1080 | `cbab915b52c67fa9c5a4cda19275240e055af4cfa7b3bf52955fe64652a6a820` | Current MP4 pixel match at 9.075000 s, scene 0. |
| 2 | 1920 × 1080 | `190e7ef2c77ee17812143be2b9eb10713766bbc95d6123126ea5eb95c73f575c` | Current MP4 pixel match at 19.600000 s, scene 1. |
| 3 | 1920 × 1080 | `0fe1bb000cdf64b50d5bfa5e28012cf03c83a8fdd0ac36b74ddaf825a0aba898` | Current MP4 pixel match at 29.925000 s, scene 2. |
| 4 | 1920 × 1080 | `24fbe12ae210b04fffc8812655e8d188453bbf6fcc89d3c8cf59df4201f4659b` | Current MP4 pixel match at 41.200000 s, scene 3. |
| 5 | 1920 × 1080 | `327b8d8a1e7a8aabf803df7c02605f264d55a91cafc384294956c94080e0aeea` | Current MP4 pixel match at 49.175000 s, scene 4. |
| 6 | 1920 × 1080 | `ddb89c57538ca75cfb5efc7c33e55fb338109096905bdb924c45fbf26c320ce4` | Current MP4 pixel match at 61.525000 s, scene 5. |
| 7 | 1920 × 1080 | `24ccdf1f98a80409296b8776cc38159cf69097b0e53fef96d40059b741fbcff1` | Current MP4 pixel match at 73.100000 s, scene 6. |
| 8 | 800 × 1500 | `29d0e56286cacbab086b6877aeac62815dc00ec8ab858e27b82a3fe3033869a5` | Full-page screenshot crop pixel match. |
| 9 | 800 × 1500 | `66cf5bc9207601d2a7f703bc3776a3d396f2117c91f0deff99909261b35287e2` | Full-page screenshot crop pixel match. |
| 10 | 800 × 1500 | `f5a72180cfa6e41d5447fb1143548dc4b693dec2b19f8ce3b338b92d96c70cf9` | Full-page screenshot crop pixel match. |
| 11 | 800 × 1500 | `352566b0f16837f7f009d672b1e8dad0b670d0a9b56f8e1ce67e201b623e09a3` | Full-page screenshot crop pixel match. |
| 12 | 800 × 1500 | `3ac49db980c35cdbe8852de5b7dd8f679b7892fe0b93eeb4f7f9e1ab4e723c2d` | Full-page screenshot crop pixel match. |
| 13 | 800 × 1500 | `da3a0e9ef559bfd4cadf7b3ccbb7655efceab4447250b6209505b907876aaf60` | Full-page screenshot crop pixel match. |
| 14 | 800 × 193 | `25bd0a6fed008a3c38ffd1d74e0ce4a6b0bfa5cd37a2613697158549ca5218b9` | Full-page screenshot crop pixel match. |
| 15 | 2400 × 1260 | `395fe7f39629024ea2f36a4f4a0f1ffc5038e144fe0b35c32f190dd8c71a92d0` | Current card.png output hash match. |
| 16 | 1920 × 1080 | `e9e218e44cc4907adb1333c038067ae0a97efd5521953378291035b720df7763` | Current MP4 pixel match at 4.000000 s, scene 0. |
| 17 | 1920 × 1080 | `dfce16027b797117f7a00f9ff696dfb78fe6bccad1850ea70ac892eb5f3195d7` | Current MP4 pixel match at 12.975000 s, scene 1. |
| 18 | 1920 × 1080 | `8caee5bd3cf9f581cfb77f9a4ce5e00d3a25efd8b0a9b2bc3074b260f0e661f6` | Current MP4 pixel match at 19.950000 s, scene 2. |
| 19 | 1920 × 1080 | `b9e84ca5455630d02e395efea048a15207604a8ed5623de8b4cf239dcb7ff579` | Current MP4 pixel match at 30.450000 s, scene 3. |
| 20 | 1920 × 1080 | `f100fe81a48e8631db4b08812a20354ad0792f524806e9dabc9e5bf1df4c523a` | Current MP4 pixel match at 44.225000 s, scene 4. |
| 21 | 1920 × 1080 | `739ece6006f9ed5b682d2e58dccf328c75e30aa8c2c1404424bfa10a150a397d` | Current MP4 pixel match at 55.175000 s, scene 5. |
| 22 | 1920 × 1080 | `4071b9c950dfaf1325af32437e757cde0f68f61b106ad0467b4e13e136a44b23` | Current MP4 pixel match at 63.050000 s, scene 6. |
| 23 | 800 × 1500 | `0ef7c5c43fe65a88b531973c886dea2c6ff2a41b967cd1ba50170c8d0aa6f3a3` | Full-page screenshot crop pixel match. |
| 24 | 800 × 1500 | `8873482e35bb4849fdf1af2e6c164a0aaa621285f4cbe2260e1721b9b3ce50e0` | Full-page screenshot crop pixel match. |
| 25 | 800 × 1500 | `b2918c91b3666d564d4c1364687495f602497c7ed702594ed43ef04fe3cd3608` | Full-page screenshot crop pixel match. |
| 26 | 800 × 1500 | `6ee9ba118a37d3c87b7be53f5f8ebb98ee27af9400a345273d09897c691cc011` | Full-page screenshot crop pixel match. |
| 27 | 800 × 1500 | `a4e72166c7b39253e37e528b10b148d44e53be3c87b5deef2f488a8b0b524796` | Full-page screenshot crop pixel match. |
| 28 | 800 × 1500 | `14ea70874a4fd0dd7969e291d1406ac72b61f01fd6df0d160164132021246dab` | Full-page screenshot crop pixel match. |
| 29 | 800 × 1346 | `3c75e67d5d7fb88243d4aabbd8f62bce25bcbaddbbd13a5c3c1769077ead135a` | Full-page screenshot crop pixel match. |
| 30 | 2400 × 1260 | `a182e0543797a4661f590cf9a165770cb90f90747daed9ccf4e712c15503b00e` | Current card.png output hash match. |
| 31 | 1920 × 1080 | `97dc17ab4fd8f6e6cc989e78d5f58a2bd24ab41fe0ba36dd22e76e5c9b1be6ff` | Current MP4 pixel match at 11.100000 s, scene 0. |
| 32 | 1920 × 1080 | `928817d4d55a6687a5e6ef2d985203a0a06283de6e3fc6f6a96aae409c233ca1` | Current MP4 pixel match at 24.100000 s, scene 1. |
| 33 | 1920 × 1080 | `b57f2e41cae66c20b593d5e7503bca057fdd16976c4c5ccb285a93821f754fe0` | Current MP4 pixel match at 38.150000 s, scene 2. |
| 34 | 1920 × 1080 | `3b2e71f5845324885f084e58c2cac6b65991e49600eec810ee7e348d4baa606a` | Current MP4 pixel match at 48.050000 s, scene 3. |
| 35 | 1920 × 1080 | `2d201a9ba86a0194760f088f8a662c952933492567b8c9096584956b7c27e205` | Current MP4 pixel match at 58.950000 s, scene 4. |
| 36 | 800 × 1500 | `d7dbd30ea31fbf25740378391d56309ba47bbdd53686980cb52fd17cefa2e9cd` | Full-page screenshot crop pixel match. |
| 37 | 800 × 1500 | `46e0d2fa50db08ba0a72eb28dd8287b84db302a8f1c10dedcb438d653c948459` | Full-page screenshot crop pixel match. |
| 38 | 800 × 1500 | `db6a124779b4d102348512eef8046785e2b9b783b6701e693fb90ef4a660ef4f` | Full-page screenshot crop pixel match. |
| 39 | 800 × 1500 | `328fcd9ba8b94f28c36030e7a6358772a8a6bfb846fbce59ecbf0964075f76bd` | Full-page screenshot crop pixel match. |
| 40 | 800 × 1500 | `21c4227fe1e3bf95532f70ba69441a48a4e0297ea765cb2d1e1d346e0c0a35ea` | Full-page screenshot crop pixel match. |
| 41 | 800 × 1500 | `ee60c18fa5daeca46411b6062215b6f53f65f6ad24ae3e284706f9ec09daeeb3` | Full-page screenshot crop pixel match. |
| 42 | 800 × 1500 | `72a22859b739eaeea370636a8c0f443f31089e6bc651ab4a445a1c16ae1aa179` | Full-page screenshot crop pixel match. |
| 43 | 800 × 1298 | `55ca03206d899af7912688ae70efa924e10a4004a97962eaba73366c68d1100c` | Full-page screenshot crop pixel match. |
| 44 | 2400 × 1260 | `e153d45d4a9b751d27863022f6502b616331b343d95857686d60dddaf12aab2f` | Current card.png output hash match. |

## Additional caption samples viewed

Scene and sentence numbers are zero-based. These are in-memory video samples, outside the 44-image inventory.

| Case | Scene | Sentence | Time, seconds | Observed pixels and board text |
|---|---|---|---|---|
| librarysync-98 | 0 | 0 | 2.702500 | VIEWED. Complete subtitle, with no clipping. Board text: This pull request changes which episode up next suggests for a show. |
| librarysync-98 | 0 | 1 | 6.975000 | VIEWED. Complete subtitle, with no clipping. Board text: The dashboard and history routes use this lookup. |
| librarysync-98 | 1 | 0 | 11.890000 | VIEWED. Complete subtitle, with no clipping. Board text: A user has watched only s2e2 of six episodes. |
| librarysync-98 | 1 | 1 | 16.207500 | VIEWED. Complete subtitle, with no clipping. Board text: Up next used to pick the first unwatched one, s1e1. |
| librarysync-98 | 2 | 0 | 22.222500 | VIEWED. Complete subtitle, with no clipping. Board text: Now up next starts after the furthest watched episode. |
| librarysync-98 | 2 | 1 | 26.455000 | VIEWED. Complete subtitle, with no clipping. Board text: Earlier unwatched episodes are skipped, and the user gets s2e3. |
| librarysync-98 | 3 | 0 | 33.132500 | VIEWED. Complete subtitle, with no clipping. Board text: select_next_episode now finds the last watched episode in the list. |
| librarysync-98 | 3 | 1 | 38.232500 | VIEWED. Complete subtitle, with no clipping. Board text: Then it skips everything up to that episode and returns the next unwatched one. |
| librarysync-98 | 4 | 0 | 43.632500 | VIEWED. Complete subtitle, with no clipping. Board text: The bulk lookup had its own loop with the old rule. |
| librarysync-98 | 4 | 1 | 47.095000 | VIEWED. Complete subtitle, with no clipping. Board text: Now it calls select_next_episode for each show. |
| librarysync-98 | 5 | 0 | 52.607500 | VIEWED. Complete subtitle, with no clipping. Board text: The tests check the s2e2 case in the helper and through find_next_episode. |
| librarysync-98 | 5 | 1 | 58.287500 | VIEWED. Complete subtitle, with no clipping. Board text: If the newest episode is watched, nothing is suggested, even with earlier gaps. |
| librarysync-98 | 6 | 0 | 64.105000 | VIEWED. No separate subtitle in the lower region. Board text: Up next now follows the furthest watched episode. |
| librarysync-98 | 6 | 1 | 68.307500 | VIEWED. No separate subtitle in the lower region. Board text: Start review at select_next_episode in next_episode.py. |
| em-5756 | 0 | 0 | 1.957500 | VIEWED. Complete subtitle, with no clipping. Board text: Note now closes the Command Center on touch. |
| em-5756 | 1 | 0 | 6.672500 | VIEWED. Complete subtitle, with no clipping. Board text: A new test clicks thought a and opens the Command Center. |
| em-5756 | 1 | 1 | 10.637500 | VIEWED. Complete subtitle, with no clipping. Board text: Before, clicking Note left the sheet open over the keyboard. |
| em-5756 | 2 | 0 | 16.255000 | VIEWED. Complete subtitle, with no clipping. Board text: Now, on touch, Note closes the sheet, so thought a is no longer selected. |
| em-5756 | 3 | 0 | 22.802500 | VIEWED. Complete subtitle, with no clipping. Board text: Note's multicursor settings gain an onComplete callback. |
| em-5756 | 3 | 1 | 27.512500 | VIEWED. Complete subtitle, with no clipping. Board text: It runs after multicursors are restored, so they cannot reopen the sheet. |
| em-5756 | 4 | 0 | 33.490000 | VIEWED. Complete subtitle, with no clipping. Board text: From a note, opening the Command Center now dismisses the keyboard. |
| em-5756 | 4 | 1 | 37.667500 | VIEWED. Complete subtitle, with no clipping. Board text: The sheet lifts above the keyboard only while open. |
| em-5756 | 4 | 2 | 41.705000 | VIEWED. Complete subtitle, with no clipping. Board text: A library patch copies the scroll style before padding it. |
| em-5756 | 5 | 0 | 47.287500 | VIEWED. Complete subtitle, with no clipping. Board text: They cover closing the sheet, its padding, and opening from a note. |
| em-5756 | 5 | 1 | 52.210000 | VIEWED. Complete subtitle, with no clipping. Board text: Headless Chrome has no virtual keyboard, so one test checks padding instead. |
| em-5756 | 6 | 0 | 57.507500 | VIEWED. No separate subtitle in the lower region. Board text: Note closes the Command Center on touch. |
| em-5756 | 6 | 1 | 60.612500 | VIEWED. No separate subtitle in the lower region. Board text: Start at onComplete in note.ts. |
| swarm-116 | 0 | 0 | 2.937500 | VIEWED. Complete subtitle, with no clipping. Board text: This pull request separates Compose read, syntax, and validation failures. |
| swarm-116 | 0 | 1 | 8.205000 | VIEWED. Complete subtitle, with no clipping. Board text: PRC can quote this Go diff, but cannot build its symbol or call graph. |
| swarm-116 | 1 | 0 | 13.625000 | VIEWED. Complete subtitle, with no clipping. Board text: A read failure now returns ReadComposeError. |
| swarm-116 | 1 | 1 | 17.330000 | VIEWED. Complete subtitle, with no clipping. Board text: Invalid YAML returns ParseComposeError. |
| swarm-116 | 1 | 2 | 21.487500 | VIEWED. Complete subtitle, with no clipping. Board text: Decoded content failures return ValidateComposeError. |
| swarm-116 | 2 | 0 | 26.527500 | VIEWED. Complete subtitle, with no clipping. Board text: The old read path returned a formatted error. |
| swarm-116 | 2 | 1 | 30.647500 | VIEWED. Complete subtitle, with no clipping. Board text: The new path returns a type with the file path and original cause. |
| swarm-116 | 2 | 2 | 35.397500 | VIEWED. Complete subtitle, with no clipping. Board text: The YAML node is parsed first, then decoded into the schema. |
| swarm-116 | 3 | 0 | 41.112500 | VIEWED. Complete subtitle, with no clipping. Board text: The read-error test preserves ErrNotExist in the error chain. |
| swarm-116 | 3 | 1 | 45.555000 | VIEWED. Complete subtitle, with no clipping. Board text: The syntax-error test rejects the validation-error type. |
| swarm-116 | 4 | 0 | 50.612500 | VIEWED. Complete subtitle, with no clipping. Board text: Compose failures now have distinct error types. |
| swarm-116 | 4 | 1 | 55.205000 | VIEWED. Complete subtitle, with no clipping. Board text: The shared faults interface and repository wrappers remain in the original diff. |

## Limits

This inspection establishes only the pixels and times listed above. I did not replay each video continuously or listen to speech. I did not inspect every animation frame, mobile screenshot, map screenshot, or card browser viewport. I did not duplicate hub-link tests or Darwin's source/claim audit.

The walkthrough crop binding proves identity with the current retained full-page screenshots. Current HTML hashes match the render record. I did not independently recapture the HTML in a browser, so that final screenshot-to-HTML connection relies on the retained browser evidence.

All inventory images were readable. No listed inspection is incomplete. Captions have the four absent-outro-region observations stated above. Package lint, typecheck, tests, and build were not rerun because this task permits only artifact inspection.

**Next step.** Combine these visual findings with the separate hub-link and source/claim reports. Preserve the card truncation and small-text findings in that combined artifact review.

