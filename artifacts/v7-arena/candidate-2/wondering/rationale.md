# Direction 1 - Wondering - rationale

## Token plan

Colour - six named, each with one fixed meaning, used nowhere else:

- Paper #FFFCF0 - page ground. From the wondering.app live CSS.
- Ink #261312 - prose text only. From wondering.app dark step.
- Sky #0F6FD6 - every place to read on GitHub. Links, markers, line numbers.
- Leaf #1D7A4F - kept notes and COMPLETE. Never used for links.
- Coral #F0506E - removed old text only. Code wash uses the same hue.
- Sun #F5B301 - new report wash only. Status stamps tint from the same ramp.
- Amber #B45309 marks BLOCKED and Red #B3261E marks FAILED. Both extend the ramp above, never reused.

Type - four faces, each with one role:

- Young Serif - headlines only. Friendly chunky display from wondering.app.
- Public Sans - body, labels, counts. UI voice.
- Instrument Serif italic - the dek accent line only. One moment of warmth.
- Share Tech Mono - code, line numbers, markers. Never body labels.

Layout sketch - calm lesson path, centred 1080 column:

- Masthead: star, kicker, serif title, italic dek, colour key on a hairline.
- Moment: left prose column 380 wide, right figure column fluid.
- Moment 1 figure: two sheets side by side on wide screens, stacked at 800.
- Moment 2 figure: three stop flow rail above one dark code island.
- Moment 3: centred serif summary, one tip card with a blue edge.

ASCII: [prose 380 | figure fluid] x2, then [centred summary + tip].
Wire: +-- key on hairline --+ / | 1/3 prose | run + doc | / | 2/3 prose+rail | code | / | centred 3/3 |.

## Plan review against the brief

- First plan used all caps eyebrows and dot joined meta strings. Both are listed template tells. Changed to sentence case kickers and a plain key list.
- First plan washed the code panel in the same cream as the page. The reviewer called all grey code unreadable. Changed to the wondering dark ink island with five distinct token hues.
- First plan floated a callout tag over line 36. The brief bans overlays on code. Changed to a sidenote row below the code, outside the pre element.
- First plan showed only the COMPLETE path. The brief allows the four test scenarios. Added a scenario switch that rewrites moment 1, as B did.

## Alternatives considered and rejected

- Star field night canvas in wondering violet. Rejected: dark ground would repeat round 6 option A, which the reviewer rejected.
- Scrolly prose that dims as the figure steps, as B did. Rejected: B palette was liked but its scrolly form was not picked. A static lesson path reads faster in two minutes.
- One dull two colour scheme, cream plus brown. Rejected directly by the brief. Six fixed meanings stay.

## Why it is not AI slop

- One memorable device only: the warm lesson sheets on a grain wash. Everything else is quiet hairlines, no shadows, no gradient buttons.
- No SaaS card kit: sheets carry two different radii and borders, the code island is full dark, the tip has a single blue edge. No shared soft shadow, no wash decoration.
- No template chrome: sentence case labels, no dot joined meta, no WORD dash fragments, no arrow on links, mono only where code lives.
- Copy follows plain style: short sentences, each under twenty words, active voice.

## YC addendum

- Applied the sleek minimal polish inside the warmth: tight tracked serif title, 1px hairlines, no shadows beyond one soft sheet lift, one orchestrated reveal on scroll and in clip with a single ease curve, generous whitespace, nothing decorative beyond the grain wash.

## Clip contract

- Page view shows the finished state with no autoplay. Clip mode at ?clip=1 frames 1280 by 720, one moment at a time.
- window.__ready turns true when fonts load. window.startClip plays moments 1 to 3, pushes elapsed seconds into window.__marks, sets window.__clipDone true. Total about fifteen seconds.
