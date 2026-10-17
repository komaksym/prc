# Direction 2: Diff sheet

A quiet dark review surface in the style of Linear and Vercel. Every colour is a diff state or a run status, so the page reads like GitHub, but faster. The memorable element is the Google Doc shown as a unified diff, with before and after line numbers and a diffstat.

## Token plan

| Name | Hex | Fixed meaning |
| --- | --- | --- |
| Carbon | #0C0D0F | Page background; panels #121417, hairlines at 7.5% white |
| Jade | #3DD68C | Added by this run (+ lines, +10 diffstat) and the COMPLETE status |
| Rose | #FF6369 | Removed (- line, -1 diffstat) and FAILED: lines 50-51 |
| Amber | #F5B840 | BLOCKED: lines 43-44 |
| Azure | #5EA2FF | The Google Doc: the report region rail, the markers, the Google calls on lines 36 and 66 |
| Violet | #A98BFA | Merged, used once, as on GitHub |

Text is #EDEEF0, secondary text #9BA1AA, and line numbers #737A84. Jade, rose and amber follow GitHub's own diff and check colours, so a reviewer needs no key.

Syntax colours are lighter and differ in hue from the state colours: lavender keywords #C4A3FF, cyan functions #79C7FF, pink types #F2A7D0, sand strings #E8C27E, peach constants #F7A072. The literals "BLOCKED" and "FAILED" get the amber and rose tint, so the code carries the same status colours as the run card.

Type.

- Geist 600 for headlines, with -0.045em tracking on the title and -0.03em on section heads. Geist 400-500 for all UI and prose.
- Geist Mono only for things that are code: source lines, the Doc markers, file paths, scenario names, status values and the diffstat.

Layout sketch (1440 px, 1120 px column, left aligned):

    [PRC   komaksym/linkedin-mdp / Pull request 5                 (Open on GitHub)]

    (o) Merged
    Daily reconciliation report
    in a Google Doc
    What the change writes, the order of work, and the line to start at.
    o------------------------o------------------------o-----------------------
    The Google Doc report    Order of work in run()   Where to start
    status and six counts    Google checks run first  publish in google_doc_report.py

    The Google Doc report ...................... Each run replaces the text between two markers.
    ------------------------------------------------------------------------------------
    Test scenario [complete|later_404|supabase_timeout|sharing]
    +-- This run -------+  +-- Google Doc after the run ............ +10 -1 [#####] --+
    | (o) COMPLETE      |  | Before After                                               |
    | Exit code 0       |  |  1   1     Operator note                       Unchanged   |
    | Fetched rows   4  |  |  2   2     [BEGIN AUTOMATED REPORT]                        |
    | ...six counts     |  | |3      -  old                                   Removed   |
    +-------------------+  | |    3  +  LinkedIn CONNECTIONS ...    Written by this run |
                           | |    4  +  Status: COMPLETE ...                            |
                           |  4  13     [END AUTOMATED REPORT]                          |
                           |  5  14     Keep this note.                     Unchanged   |
                           +------------------------------------------------------------+

    Order of work in run() ..................... The script checks the Doc first.
    +-- scripts/report_connections_doc.py  run() -------------------------------------+
    | 36 |await publisher.prepare()                                                    |
    |      [Google] Google checks run first. A shared Doc stops ... report_...py:36     |
    |    ... 5 lines hidden                                                            |
    | 44 |    result = ReportResult("BLOCKED", ...)                                    |
    |      [BLOCKED] A LinkedIn error gives BLOCKED.                                   |
    | 51 |    result = ReportResult("BLOCKED" if linkedin is None else "FAILED", ...)  |
    |      [FAILED] Other errors give FAILED, or BLOCKED if ...                        |
    +----------------------------------------------------------------------------------+

    Where to start
    A daily workflow now writes reconciliation      +-- Review tip ------------------+
    status into a private Google Doc.               | Start at publish in google_... |
                                                    | The tests use fake Google ...  |

Explanations sit in rows below their code line, like GitHub review comments, so they never cover code. At 800 px the section heads stack, the run card becomes two columns above the diff, and the hero path stays three columns.

## What I changed after checking the plan against the brief

- First plan was a sticky left column with section titles beside the content (a docs layout). It squeezed the Doc to about 520 px and wrapped every report line, so section heads became a single row with a hairline.
- First plan used jade for "kept" and azure for "written". That fights the reviewer's reflex that green means added. Now jade means added, rose means removed, and unchanged lines stay neutral with an Unchanged tag. Azure marks only the region the script owns.
- First plan had a soft blue glow behind the hero. It was pure decoration, so I cut it. Depth comes from 1 px inner borders and one long, faint shadow.
- The video keeps the same layout but hides the neutral comment on line 42 and the file:line text inside comments, so the code stays above 12 px at 1280x720.

## How I applied the YC addendum

Restrained near-black surface, one family (Geist) with tight headline tracking, precise 1 px hairlines and inset borders, a white primary button, a frosted sticky bar, a segmented control with a lifted thumb, and one eased build-up per moment (opacity, 6 px rise, 3 px blur clearing). The page view has no autoplay motion.

## Alternatives I considered and rejected

- A light Vercel-white page. Direction 1 is already light, and the reader preferred the dark baseline.
- A git-graph diagram for run(). It adds a second picture of the same order. The code itself, lit in order, is clearer and is what he will review on GitHub.
- A hero stats strip with the six counts. That is the big-number SaaS default, and the counts belong to the Doc moment.

## Why it is not AI slop

- Its vocabulary is GitHub's own: unified diff, two line-number columns, the +/- gutter, the diffstat with five blocks, the Merged pill, inline review comments under a line. None of it is generic card chrome.
- Five colours, each with one meaning that holds across the run card, the diff, the code rows and the string literals.
- No all-caps eyebrows, no middle-dot meta, no arrows on links, no gradient washes. Mono appears only on code-like text.
- Every file and line reference links to GitHub: e2e_doc_report.py:247 and :237, every code line number, each comment's report_connections_doc.py:N, the file path, and publish at google_doc_report.py:139.

## Clip

index.html?clip=1 renders 1280x720 with a slim title bar and a three-part progress bar. Moment 1 (about 6 s): run card, counts in sequence, the diff frame, the "old" line turns into a rose deletion, the + lines write in, then the Unchanged tags. Moment 2 (about 7 s): the code appears dimmed, then lines 36, 42, 43-44, 50-51 and 66 light up in order as their comments arrive. Moment 3 (about 4 s): the summary, then the review tip. The measured total in jsdom is 16.9 s. window.__ready, window.startClip(), window.__marks and window.__clipDone follow the recorder contract.
