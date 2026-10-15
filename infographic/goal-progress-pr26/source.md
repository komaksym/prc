# Source: progress during the PR #26 review goal



TITLE: PR REVIEW TOOL: WHAT WAS WRONG AND WHAT WE FIXED
SUBTITLE: Progress on the review of linkedin-mdp PR #26

MOD-1 | THE ROOT PROBLEM | icon: one stamp printing identical pages
"One template built all 8 study videos."
"It picked 1 file, 3 to 4 lines, and 2 boxes."
"PR #26 changed 76 lines. The video showed only 5."

MOD-2 | VIDEO GLITCH FIXED | icon: film frame with a box moving between two boxes
"At 0:19 a name flew into the wrong box and spilled out."
"Now the name changes halfway and stays inside the box."
"A test failed first, then passed after the fix."

MOD-3 | REFERENCES NOW CLICKABLE | icon: cursor clicking a link
"Each file:line reference opens that exact line on GitHub."
"Commits, file names, and the PR number are links too."

MOD-4 | NEW GLOBAL RULE: CLICK EVERYTHING | icon: shield with a check mark
"A script now clicks every link and button on a page."
"Agents cannot say 'ready' without a fresh passing check."
"Rule tests: 31 of 31 pass."

MOD-5 | REVIEW MADE SIMPLE | icon: one page with a notes box
"Removed: questions, scores, timer, grading, PR pairs."
"Now: one PR, its video, page, and infographic, and one notes box."
"6,481 lines of old study code deleted."

MOD-6 | CHECKED END TO END | icon: browser window with check marks
"All 8 PRs rebuilt with the Kokoro voice."
"Voice check 8 of 8. Browser click pass 50 of 50."
"929 tests pass. Lint and type checks are clean."

FOOTER: "Status: fixed and verified on 8 PRs. Notes hub is live with 0 notes so far."




TITLE: PR REVIEW TOOL: WHAT IS STILL OPEN
SUBTITLE: Gaps found in the PR #26 review and the next decisions

MOD-1 | INFOGRAPHIC IS STILL WEAK | icon: blank picture frame with a warning mark
"The tool still makes a plain words-only diagram."
"Next: make each PR infographic with the baoyu skill, like your example."

MOD-2 | VIDEOS SKIP IMPORTANT FILES | icon: folder with missing files
"The template shows only a few lines from one file."
"Next: cover every core file, such as the CI workflow file in PR #3."

MOD-3 | NARRATION IS TOO HARD TO READ | icon: speech bubble with tangled lines
"Lines like 'a shorter page ends acquisition' are unclear."
"Next: write narration in short plain sentences and check it."

MOD-4 | NO FACT CHECK YET | icon: magnifying glass over a document
"Nothing checks that each spoken claim matches the code."
"Next: a second model checks every claim against the diff."

MOD-5 | HOW TO SHIP THE FIRST VERSION | icon: two paths, one marked recommended
"Option A: hosted GitHub app. We pay for every video."
"Option B: free tool plus GitHub Action. Users bring their own model key."
"Recommended: Option B. Zero hosting cost, ships fastest."

MOD-6 | COST PER PR (ESTIMATE) | icon: price tag with a bar chart
"Opus 5.5: about $0.90"
"DeepSeek V4.1 Flash: about $0.06"
"GLM 5.3 Flash: about $0.03"
"Estimates only. Not measured yet."

FOOTER: "Next feature: full-coverage storyboards with plain narration, a claim check, and a baoyu infographic per PR."

