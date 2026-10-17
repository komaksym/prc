# Direction 1 · "Wondering" — rationale (arena candidate 3)

## Token plan

The base is wondering.app's exact pair: paper #FFFCF0 for the page, ink #261312 for text. On top sit six meaning-bearing colours, each pinned to one job everywhere on the page and in the clip:

| Token | Hex | Fixed meaning |
| --- | --- | --- |
| doc-blue | #7ACEFF fill / #315F79 text | the Google Doc, the text the reporter owns, the line-36 check |
| kept-green | #5BBEA5 fill / #2F6B55 text | COMPLETE, and the Doc notes that stay unchanged |
| blocked-amber | #E3B33C fill / #7E5F12 text | BLOCKED, and line 44 |
| failed-coral | #FF7361 fill / #BE3B26 text | FAILED, and the removed "old" line |
| keyword-violet | #6D4FC2 | Python keywords in code |
| number-orange | #C46A16 | numbers in code |

Neutrals between them: panel #F6F0E1, sheet #FFFEF8, hairlines #E8E0CC / #F0E9D8, muted text #6E6459.

Type roles: **Young Serif** carries display (page title, moment titles, the closing summary) — wondering's friendly, chunky voice. **Public Sans** carries body, labels and the Doc text. **JetBrains Mono** carries code, markers, line numbers and scenario names. **Instrument Serif italic** appears once, on "Review tip" — wondering's occasional-italic accent.

Layout sketch:

    merged · linkedin-mdp / pull 5              (centered kicker)
    Daily reconciliation report in a Google Doc  (Young Serif, 46)
    What the report wrote, the order of work, where to start.

    1  The Google Doc report
       [ This run: scenario pills, status pill,      [ Google Doc after the run:
         six counts, exit code, source link ]          operator note | markers |
                                                       struck "old" + written report |
                                                       "Keep this note." ]
    2  The order of work in run()   scripts/report_connections_doc.py
       numbered buffer, line 36 banded blue
       three note chips: 36 Google first / 44 BLOCKED / 51 FAILED
    3  Summary — Young Serif takeaway, then the Review tip card

Left-aligned moments under a centered header. The Doc sheet is the hero object; everything else stays quiet. No sidebars, no card grid.

## What changed after reviewing the plan against the brief

- Cut a planned soft gradient wash in the header. It was decoration, and the YC addendum plus the slop checklist both reject gradient washes; warmth now comes from paper, pastel fills and the rounded Doc sheet only.
- Moved the "Google checks run first" callout from a floating note beside the code into the chip row under the buffer. No overlay may touch code, and a floating note breaks at 800 px.
- Kept the removed "old" line visible with a strike-through instead of deleting the row. The removal is part of the story; hiding it would lose what the reporter does.
- Dropped the compass glyph from the "Operator note" row: no emoji per the standing note.
- Replaced Share Tech Mono with JetBrains Mono. Share Tech Mono has one weight and thin joins; the brief demands readable, colourful code first.
- Kept the scenario switch (the B pattern he did not object to) and pinned it to "complete" in clip mode so the video tells one story.

## Alternatives considered and rejected

- A full Google-Docs mock with toolbar and tabs: more chrome, less truth. The Doc's text is what the reviewer must check, so the sheet shows only text.
- A dark mode from wondering's #261312: doubles the work for one reviewer; light reads calmer and warmer here.
- B's five prose steps under the Doc: the run panel already carries the numbers, and the page must stay a two-minute read.

## Why it is not AI slop

No cream-plus-terracotta pairing, no gradient washes, no ALL-CAPS eyebrows, no middle-dot meta rows, no arrow glyphs on links, no identical card kit — the three panels differ in shape because their jobs differ (status board, document, code buffer). Colour appears only where a meaning is fixed, and the one memorable object is the Doc sheet, not decoration around it.

## YC-polish addendum

Applied by pairing wondering's warmth with product discipline: 1px #E8E0CC hairlines, a ~1120px measure with generous breathing room, tight-set display type, one short eased reveal per moment in clip mode, hover states only where they answer an action, and zero decorative elements.
