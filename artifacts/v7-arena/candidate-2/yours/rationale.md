# Direction 2 - Ledger - rationale

## Token plan

Colour - paper ledger ground with five signal hues, each fixed:

- Paper #FAFAF9 - page ground. Ink #0C0A09 - headlines only.
- Line #E7E5E4 - every 1px hairline. Muted #57534E - prose and counts.
- Signal blue #1D4ED8 - every GitHub line opening. Never prose emphasis.
- Signal green #15803D - kept notes and COMPLETE only.
- Removal coral #E11D48 - old text and error branch wash only.
- Amber #B45309 marks BLOCKED, red #B91C1C marks FAILED, yellow wash #FEF9C3 holds new text.

Type - two faces, hard split:

- Inter - all prose and UI, tight tracked headlines at minus three percent.
- IBM Plex Mono - code, line numbers, stamps, moment numbers. No mono labels on prose.

Layout sketch - diff ledger, left rail truthful to sequence:

- Crumbs bar: repo, PR, merged stamp, read time. No hero art.
- Moment: narrow left prose rail 340 wide, wide right evidence field.
- Moment 1 evidence: two ledger sheets, run table left, Doc right.
- Moment 2 evidence: three stop rail, then one black code block.
- Moment 3: centred statement, one tipped review row with a blue spine.

ASCII: [rail 340 | evidence fluid] x2, then [centred statement + tip].
Wire: +-- crumbs hairline --+ / | 01 rail+switch | run | doc | / | 02 rail+3 stops | code | / | 03 statement |.

The numbered rails 01, 02, 03 are a true sequence: report, then order, then start. Numbers mark sequence, not decoration.

## Plan review against the brief

- First plan used numbered section chips on every block plus all caps eyebrows. Both are listed template tells. Kept numbers only because the three moments are a true sequence, cut every eyebrow to sentence case.
- First plan gave code a light stone wash with one accent. The reviewer called single accent code unreadable. Changed to a black code island with four token hues plus muted folds.
- First plan floated a branch tag over lines 43 to 51. The brief bans overlays on code. Changed to a below code sidenote and a three stop rail beside the prose.
- First plan ended with a wide CTA band. Cut it. The review tip is the only close, as the baseline requires.

## Alternatives considered and rejected

- Broadsheet hairline newspaper with zero radius. Rejected directly by the frontend design guidance: zero radius dense columns are a known default, and the reviewer wants a shipped product, not a broadsheet.
- Dark acid canvas with one neon accent. Rejected directly by the brief history: single bright accent schemes read as AI defaults.
- Generic SaaS kit with equal cards, one radius, one soft shadow. Rejected directly by this brief. Sheets, code island, and tip each carry a different edge and depth.

## Why it is not AI slop

- One memorable device only: the ledger pairing of a tight prose rail with an evidence field. No gradient washes, no icon set, no mascot, no hero number.
- No template chrome: sentence case everywhere, no dot joined meta, no WORD dash labels, no arrow appended to links, mono only for code and stamps.
- Motion is one orchestrated reveal with a single ease curve, short and eased. Scroll and clip share the same sequence. Reduced motion shows the end state.
- Copy follows plain style: each sentence stays under twenty words, active voice, no emoji.

## YC addendum

- This direction leans fully into the sleek minimal product style: restrained palette, generous whitespace, Inter with tight tracking, precise 1px hairlines, one soft shadow on sheets, smooth purposeful motion with a single ease. Subject specificity comes from ledger devices built for review: the scenario switch, the run table, the three stop rail, and GitHub linked line numbers.

## Clip contract

- Page view shows the finished state with no autoplay. Clip mode at ?clip=1 frames 1280 by 720, one moment at a time.
- window.__ready turns true when fonts load. window.startClip plays moments 1 to 3, pushes elapsed seconds into window.__marks, sets window.__clipDone true. Total about fifteen seconds.
