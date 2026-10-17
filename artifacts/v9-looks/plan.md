# Round 9 light looks: how they were made

Brief: more light looks on the Control on paper layout. Same three moments of linkedin-mdp pull request 5, same motion, same colour meanings (amber status, green kept, red removed, blue markers and links, dashed slot). Light mode only. Method: Anshu Chimala, "How to turn your AI into a world-class designer", Lenny's Newsletter, 2026-09-01.

## Technique 1: seed strings

A shell script made four random strings. Each look takes its direction from one string.

| Seed | What I read in it | Look |
|---|---|---|
| D3c7UbDdzquYUcAGWeqJ96YVYBQNRnvP6XLIszHH | D3C7 as a pale stone hex, "zqu" as quiet | Stone |
| RiIVcjuWmvdjdnbXrp5ycDPj0Ymrp6xWH0rK5U5N | I and IV as Roman numerals, xWH0 as white with zero radius | Gallery |
| d0cui40wwmRFpdXko9g7SMill78SD5kVdW1yCPiJ | "SMill" as a paper mill, "d0cu" as a printed document | Cotton |
| ufSdiBrSztHBYw1xTW4oZHW39PR6o9va78uZkf78 | "oZH" as soft, W39 as a warm hue near 39 degrees | Cream |

## Technique 2: a concrete inspiration per look

- Cream: wondering.app. Its CSS gives #FFFCF0 cream, #261312 brown ink, Inter and Public Sans, 16 to 24 px radii.
- Gallery: a white gallery wall with framed prints and numbered captions.
- Cotton: a letterpress memo on cotton rag paper.
- Stone: the quiet product surfaces of current YC tools (Geist type, flat rows, hairline borders).

## Technique 3: a critic with screenshots only

A fresh critic subagent sees only screenshots: the reference look, the wondering.app screenshots and the new looks. It never sees code or earlier critiques. It ranks the looks by polish and taste and gives each a score out of 10. I fix its top gaps and run it again with the same prompt. Results are below.

## Technique 4: image generation

Planned: a generated cotton rag texture for Cotton. Image generation was blocked by the account quota during this round, so Cotton uses an SVG noise grain for now.

## Techniques 6 and 7: subtract and remove AI tells

All four new looks drop the tracked capital labels ("MERGED PULL REQUEST", "COMPLETE SCENARIO") for sentence case. Cream drops all outlines. Gallery drops shadows and corner radii.

## Critic rounds

Each round used a fresh critic subagent (Dispatch role: strongest judgment, inherited model). It saw only screenshots: the paper reference, one wondering.app screenshot taken in a Cua space, and each look at 1440 px and 800 px. It never saw code or the earlier critique. The prompt is the same file in both rounds: /private/tmp/prc-v9/critic-prompt.txt. Round 2 adds Ivory to the candidate list.

| Look | Round 1 | Round 2 | Beats paper (round 2) |
|---|---|---|---|
| Ivory (new in round 2) | none | 7.5 | Yes |
| Stone | 7 | 7 | Yes |
| Gallery | 6 | 6.5 | No, it is too literary |
| Cream | 5.5 | 6 | Barely |
| Cotton | 4.5 | 5 | No |

Round 1 fixes:

- Stone: removed the zebra rows, inset the row tints to the label edge, set the summary to weight 500 at 28 px, used ink-blue links and gave each section more space.
- Gallery: put the numerals on the heading line, used one grey hairline everywhere, warmed the wall and balanced the title.
- Cream: changed to 8 px rows and white cards with a warm hairline, boxed every row and lightened the summary.
- Cotton: changed to JetBrains Mono, roman sans captions and solid hairlines, and added space under the eyebrow.
- Ivory: new. It is the critic's suggested mix of Stone's structure, Cream's page, paper's tracked eyebrows and a quieter headline.

Round 2 fixes:

- Ivory: softer page (#fbf8f1), bigger and darker capital labels, no section rules, and card footers on the card floor.
- Stone: looser title tracking.
- Gallery: no numerals.
- Cream: the callout now matches the cards.
- Stone and Cream: card footers sit on the card floor.

No look reached the article's stop mark of 9. The top score is 7.5. The critic named three shared gaps that are still open:

- The code highlight bar runs to the card edge.
- The callout does not align with the code block.
- The 800 px layout keeps the desktop spacing.
