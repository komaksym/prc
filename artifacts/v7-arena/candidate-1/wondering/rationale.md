# Direction 1: Wondering

A calm, warm review page. It borrows the paper, pastels and friendly serif from wondering.app. It keeps the baseline order: the Doc report, the order of work, then where to start.

## Token plan

Colour. Each colour has one meaning on the page and in the clip.

| Name | Hex | Fixed meaning |
| --- | --- | --- |
| Paper | #FFFCF0 | Page background (wondering.app background) |
| Ink | #261312 | All body text (wondering.app text) |
| Sky | #7ACEFF | Written by this run: the report region and the Google calls in run() (lines 36, 66) |
| Mint | #5BBDA5 | Kept unchanged, and the COMPLETE status |
| Marigold | #FFA51F | BLOCKED: line 43-44 and the BLOCKED status |
| Coral | #FF7361 | Removed, and FAILED: line 50-51 and the FAILED status |
| Violet | #7A97FF | Opens GitHub: link underline, focus ring, the review tip edge |

Text on tints uses the dark step of each hue (#2B6587, #2C6B5E, #8A4F00, #B3301E, #3A4FB0) so every label passes contrast. The warm neutral ramp (#F4F0E6, #E7E3DA, #D4CDC4, #7A6C65, #6B5752) carries panels, hairlines and secondary text.

Syntax colours use dark, ink-weight steps: plum keywords #9B2F6E, deep blue functions #1F6596, umber types #7A4E0E, moss strings #4F6E14, rust constants #B04F00. The string values "BLOCKED" and "FAILED" also get the marigold and coral tint, so the code shows the same status colours as the Doc.

Type.

- Young Serif: page title, moment headings, the summary sentence. Friendly and chunky, set with slight negative tracking.
- Public Sans: all UI and prose, 16-17.5 px, line height 1.5-1.6.
- IBM Plex Mono: code, the Doc markers, scenario names, status values.

Layout sketch (1440 px, 1120 px column, left aligned):

    [PR glyph PRC ...................................... Open the pull request on GitHub]
    +--------------------------------------------------------------------------------+
    | Merged  komaksym/linkedin-mdp, pull request 5                                  |
    | Daily reconciliation report                                                    |
    | in a Google Doc                     (painterly sky and hills, film grain)      |
    +--------------------------------------------------------------------------------+
    1 The Google Doc report   | 2 Order of work in run()   | 3 Where to start

    The Google Doc report
    Test scenario [complete|later_404|supabase_timeout|sharing]
    +-- This run --------+  +-- Google Doc after the run ---------------------------+
    | (o) COMPLETE       |  | Operator note                                  Kept   |
    | Exit code 0        |  | [BEGIN AUTOMATED REPORT]                              |
    | Fetched rows    4  |  | |old (struck)                               Removed   |
    | ...six counts      |  | |LinkedIn CONNECTIONS reconciliation  Written by run  |
    | e2e_doc_report:247 |  | |Status: COMPLETE ...                                 |
    +--------------------+  | [END AUTOMATED REPORT]                                |
                            | Keep this note.                                 Kept  |
                            +-------------------------------------------------------+

    Order of work in run()
    +-- scripts/report_connections_doc.py  run() ------------------------------------+
    | 36 |await publisher.prepare()                    (o) Google checks run first.   |
    |    ... 5 lines hidden                                                          |
    | 42     summary = await reconcile_connections(...) (o) Reads LinkedIn ...       |
    | 44 |   result = ReportResult("BLOCKED", ...)      (o) A LinkedIn error ...     |
    | 51 |   result = ReportResult(... "FAILED", ...)   (o) Other errors give ...    |
    | 66 |await publisher.publish(result)              (o) Publishes the status ...  |
    +--------------------------------------------------------------------------------+

    Where to start
    A daily workflow now writes reconciliation
    status into a private Google Doc.          [Review tip: Start at publish in ...]

At 800 px the code notes drop below their line, the run card turns into two columns above the Doc, and nothing overlaps code.

## What I changed after checking the plan against the brief

- First plan put a key (legend) above the Doc. The chips in the Doc margin already say Kept, Removed and Written by this run, so I cut the key.
- First plan used Share Tech Mono for code, as wondering.app does. It is condensed and techy, and it reads poorly at 13-14 px. The reader rejected unreadable code before, so code uses IBM Plex Mono.
- First plan used green for "written". The Doc already uses Google Docs suggestion vocabulary (struck text for removed), so Sky marks the report region the script owns and Mint stays for kept. The chips spell out each meaning, so no colour must be guessed.
- I removed the operator note emoji from the source content, because the brief bans emoji.
- Annotations sit in their own grid column, never on top of code. Margin chips in the Doc have their own column too.
- I dropped Instrument Serif. A third face for italic accents would be the "one italic word" tell.

## How I applied the YC addendum

I kept wondering.app's warmth (paper, pastels, Young Serif) and added the YC product polish: one painterly band only, 1 px warm hairlines, one soft shadow for the two sheets, a frosted sticky bar, a segmented control with a lifted white thumb, tight tracking on headlines, and one eased build-up per moment in the clip with no motion in the page view.

## Alternatives I considered and rejected

- A full-bleed blurred landscape behind the whole page. It is charming, but it lowers code contrast and turns the page into a mood piece.
- A star mascot like wondering.app. It would copy their brand, so the mark is the pull request glyph.
- Big numbered markers (01 / 02 / 03). The only numbers are in the small contents row, because the three moments are a reading order.

## Why it is not AI slop

- The meaning colours come from the subject: the Doc diff (kept, removed, written) and the run statuses (COMPLETE, BLOCKED, FAILED). The same five colours appear on the run card, the Doc, the code rows and the string literals.
- The Doc looks like a document, with margin chips, so it reads like Google Docs suggestion mode. A reviewer knows that view already.
- No all-caps eyebrows, no middle-dot meta strings, no arrows appended to links, no gradient on cards. The one decorative element is the hero band, and the brief asked for it.
- Every file and line reference is a GitHub link: e2e_doc_report.py:247 and :237, each code line number, the file path and publish at google_doc_report.py:139.

## Clip

index.html?clip=1 renders 1280x720 with a slim title bar and a three-part progress bar. Moment 1 (about 6 s): the run card, the counts in sequence, the Doc, "old" struck, the report written line by line, then the Kept chips. Moment 2 (about 7 s): the code dims, then lines 36, 42, 43-44, 50-51 and 66 light up in order with their notes. Moment 3 (about 4 s): the summary, then the review tip. The measured total in jsdom is 17.0 s. window.__ready, window.startClip(), window.__marks and window.__clipDone follow the recorder contract.
