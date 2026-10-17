# PRC looks, round 10: seven looks from twelve YC startups

Summary: seven new light looks take their type, ink and surfaces from twelve YC startup homepages. Similar sites share one look. A screenshot-only critic scored three rounds. The final scores put BOND at 7.5, level with Ivory from round 9. Omanta, Belvedir and Audun score 7.0. No look clearly beats Ivory. The critic's remaining gap is structural: all looks keep Ivory's card, corner and border system.

Page: [v10-picker.html](../v10-picker.html). CSS: the `round 10` block at the end of [picker.css](../v6-styles/picker.css), made by `/private/tmp/prc-v10/gen.py` from `looks.json`.

## Sources

Each site was captured at 1440 px in the Cua space `local:prc-v8-clips` (Linux Chromium). The fonts and colours below come from computed styles on the live pages.

| Look | Source sites | What it carries over |
|---|---|---|
| Audun | [audun.co](https://audun.co/) | Warm paper #faf5f0, slate ink #161f28, a teal wash and a mint pill, large rounded cards, Instrument Sans (the site uses Ranade plus Instrument Sans) |
| Belvedir | [belvedir.ai](https://belvedir.ai/), [fabraix.com](https://fabraix.com/) | Stone white #fafaf9, a Georgia-style serif headline (Newsreader), Inter text, sentence-case labels |
| Omanta | [omanta.com](https://omanta.com/), [illumelabs.ai](https://www.illumelabs.ai/) | Blush cream #faf6f2, brown ink #2a1b18, a serif display headline (Libre Caslon Text; Bodoni Moda and Playfair were tried and dropped) |
| Speko | [speko.ai](https://speko.ai/), [meteoric.earth](https://meteoric.earth/) | Off-white #faf9f6, Hanken Grotesk and Geist, green-black ink #0e1512, a fading blue dot field from the Speko hero |
| Gumloop | [gumloop.com](https://www.gumloop.com/), [wondering.app](https://wondering.app/) | Light grey app shell, white cards with hairlines, a black pill like the Gumloop buttons, a Gellix-style sans (Figtree) |
| BOND | [bondapp.io](https://www.bondapp.io/) | Warm off-white #faf8f6, brown ink, a soft amber glow at the top, a soft serif headline (Fraunces, in place of Season Mix) |
| herdr | [herdr.dev](https://herdr.dev/), [pentagon.run](https://pentagon.run/) | Catppuccin Latte colours (herdr's dark site uses Catppuccin Mocha), a heavy Archivo headline, mono labels, Pentagon's electric blue #3d63ff for links |

Fixed in every look: amber is status, green is kept, red is removed, blue is markers and links, and a dashed outline is the slot the run writes. Code uses syntax colours.

## Critic rounds

The critic ran on the panel role "strongest judgment" (inherit-parent). It saw only screenshots at 1440 and 800 px, REF-paper, REF-ivory and the source homepages. Dispatches: `/private/tmp/prc-v10/dispatch-r{1,2,3}.json`.

| Look | Round 1 | Round 2 | Round 3 (final CSS) |
|---|---|---|---|
| BOND | 5.5 | 7.5 | **7.5** |
| Omanta | 6.5 | 6.0 | 7.0 |
| Belvedir | 5.5 | 7.0 | 7.0 |
| Audun | 6.5 | 7.0 | 7.0 |
| Speko | 7.0 | 6.5 | 6.5 |
| herdr | 6.5 | 6.5 | 6.0 |
| Gumloop | 6.0 | 6.5 | 6.0 |

Fixes after round 1: looser headline tracking in Audun, BOND and herdr, where words had fused. One job per colour, so the green dots, the blue card cap and the purple labels changed. Code paths moved out of the italic serif. A drawn serif for Belvedir and a wider serif for BOND. Flat rows for Gumloop. Signature surfaces: the Speko dot field, the BOND glow and the Audun teal.

Fixes after round 2: a stronger BOND glow and muted ink-blue links. No Belvedir dots, and a wider tip card. A stronger Audun wash. A lower-contrast Caslon for Omanta. White cards on a grey shell for Gumloop. The Speko dots moved from every card to one masked band at the top right. A lighter herdr title.

Open gaps from round 3, for the next round:

- All seven keep Ivory's cards, corners and borders. The critic says a typeface alone cannot carry a brand. Give each look one structural change as well, such as the card radius, the border style or the label system.
- BOND: anchor the glow behind the title, set the title weight to 300 to 350 and make the card labels stronger.
- Audun: choose one colour temperature and use deep navy for the title.
- herdr: the lilac page clashes with the amber code highlight.

## Clips

The clips were recorded in the same space with `rec9.py`, then cut and checked with `/private/tmp/prc-v10/post.py`. The checks found 0 black frames and 0 page errors in all seven clips. The results are in [clips/report.json](../v6-styles/clips/report.json), with contact sheets at `v6-styles/shots/clip-control-<look>-sheet.png`.

## Note on content

The page shows a compass emoji on "Operator note". It is quoted word for word from the pull request test data (`TEXT = "🧭 Operator note..."`, line 847 of the PR #5 diff). It is not design decoration.

