# Direction 2 · "Yours" — the review sheet (arena candidate 3)

## Token plan

Paper #FAFAF8, ink #17181C, hairlines #E7E7E3. Six meaning-bearing colours, each pinned to one job everywhere on the page and in the clip:

| Token | Hex | Fixed meaning |
| --- | --- | --- |
| cobalt | #2E5CE6 rail / #2340B8 text | the Google Doc, the text the reporter owns, the line-36 check, focus |
| complete-green | #E8F5EE fill / #146C43 text | COMPLETE, unchanged notes, the merged chip |
| blocked-amber | #FCF1DC fill / #8A5300 text | BLOCKED, and line 44 |
| failed-red | #FCEBE8 fill / #B3261E text | FAILED, and the removed "old" line |
| keyword-violet | #8250DF | Python keywords in code |
| number-orange | #953800 | numbers in code |

Type roles: **Schibsted Grotesk** for display and UI — tight tracking on the 42px headline and the summary, crisp at 13px labels; it is not Inter, not Source Serif, none of the round-6 faces. **IBM Plex Mono** for every technical token: file paths, line numbers, scenario names, markers, and the code itself. Two families, no third.

Layout sketch:

    merged   linkedin-mdp / pull 5          (left-set kicker)
    Daily reconciliation report in a Google Doc   (grotesk 700, tight)
    ------------------------------------------------------------
    [1] The Google Doc report
        [ This run: scenario control, big      [ Google Doc after the run:
          status word, six-count table,          operator note | cobalt-owned
          exit code ]                            region: struck "old" + report |
                                                 end marker | kept note ]
    ------------------------------------------------------------
    [2] The order of work in run()    scripts/report_connections_doc.py
        light buffer, gutter numbers link to GitHub, line 36 on the cobalt rail
        three notes: 36 Google first / 44 BLOCKED / 51 FAILED
    ------------------------------------------------------------
    [3] Summary — 28px line, then the Review tip on a cobalt rail

Everything is left-set; hairlines do the separating. The panels are not interchangeable cards: the run sheet is a status board, the Doc panel is a document with one owned region, the code is a buffer. Three different objects, one system.

## What changed after reviewing the plan against the brief

- First plan was cream paper, serif display, one warm accent. Discarded during the plan review: it is the exact slop cluster the frontend-design skill names, and it would have read as round-6 B again.
- Second plan used dark editor buffers. Discarded: that is option C, one of the four looks he rejected.
- Planned reviewer comments absolutely positioned beside code lines, like GitHub side comments. Demoted to the note row under the buffer: nothing may cover code, and 800 px would break the alignment.
- Planned tracked ALL-CAPS mono section labels. Replaced with plain 1/2/3 chips: the moments are a real sequence, so the numbers carry information; the caps were decoration.
- Set code on a light buffer with violet/blue/amber/orange tokens. All-grey code was called unreadable in round 6; light keeps the sheet calm while every token class keeps its own hue.
- Coloured the status words inside the string literals ("BLOCKED", "FAILED") with the status colours. The code now speaks the same colour language as the rest of the sheet.

## Alternatives considered and rejected

- A dark IDE skin: the nearest existing look is rejected round-6 C, and it fights the "clearer than GitHub" job rather than serving it.
- Six counts as dashboard tiles: numbers without the Doc context around them, and the card kit in disguise.
- A run timeline graphic: it would restate the order the buffer already shows, with invented chrome.

## Why it is not AI slop

Three structurally different panels on hairlines instead of a stack of identical rounded cards; sentence-case labels; no gradient washes, no spaced em-dash fragments, no middle-dot meta rows, no arrow glyphs appended to links; mono appears only where the subject is genuinely technical. One bold element carries the design — the cobalt-owned Doc region — and everything else stays quiet.

## YC-polish addendum

This direction is the YC register end to end: near-white paper, precise 1px hairlines, generous whitespace, tight-tracked grotesk headlines, flat white panels with one subtle shadow token, mono reserved for technical tokens, and one short eased reveal per moment in clip mode — nothing on the page exists for decoration.
