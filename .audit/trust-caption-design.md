# Caption rendering contract

Summary. Select displayed text once and format paired backticks consistently across the generated outputs.
The board sentence is a string or a dictionary with a required `show` string and optional `speak` string.
The board checker owns validation. Speech selection remains in `check.spoken`.

## Usage and ownership

`prc.captions.shown(entry)` returns the string or its `show` field.
`prc.captions.shown_html(text)` escapes HTML before replacing paired backticks with code spans.
An unpaired backtick remains literal. The new core module uses only standard-library dependencies.
Timing, document prose and card headlines import it. Presentation and explainer do not import each other.
Delete the private document formatter when its caller moves.
The standalone JavaScript engine retains `fmt`. Its outro lines use that formatter.
The real-browser caption parity test detects drift between Python and JavaScript.
Comment headlines retain their existing single code span and apostrophe substitution.

## Synthesis decision

Candidate 3 is the base. The parent scored it 5, 5, 4, 4 and 3 on the five rubric criteria.
Candidate 2 scored 2, 5, 3, 3 and 2. Its plain card heading fails the required code-span result.
The independent muse-spark cross-judge also selected candidate 3.
Graft candidate 2's escaping corpus into the existing browser tests. Do not add pointer comments or a plain-text formatter.
Candidate 1 failed with HTTP 429 and produced no design. All candidate agents are closed.
The source designs and judge report are retained in `.audit/trust-caption-arena/`.

## Accepted decisions and implementation reconciliation

Use the existing required `show` field directly. An invalid unchecked dictionary raises `KeyError`.
This replaces the proposed extra `ValueError` guard. The checker already rejects that input.
The card applies code formatting to its selected headline, including the PR-title fallback.
HTML escaping can change quote entities in card source while retaining the same visible text.
Do not claim source-byte identity for every generated HTML file because the embedded engine changes.
Compare the three acceptance cards, comment files and video pixels after rebuilding.
The parent inspected the new card and outro screenshots. Default code typography fits those measured cases.
The delegated implementation worker returned no source patch and was closed. The parent implemented the saved contract.

## Verification

Before the fix, three new headline regressions failed with the predicted text and code-span differences.
The new browser test retains card PNGs and the settled video outro under `artifacts/e2e/caption-headlines`.
Existing real-browser caption tests retain all sentence screenshots under `artifacts/e2e/caption-parity`.
Run the targeted regressions, inspect screenshots, complete independent code review and run clean-cache verification.
Then rebuild and inspect all three acceptance cases from that installed wheel.
