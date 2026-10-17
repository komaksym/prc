# Round 8 light looks: design plan

Subject: a review explainer for one merged pull request. Audience: one Python developer who reviews agent-written PRs and does not read code line by line. Job: make the change clear in 30 seconds, then hand off to GitHub.

Fixed by the brief: the Control layout and motion (the user likes "Control on paper"), light mode only, colourful syntax colours, one meaning per colour, links on every file:line.

Free axes: palette, type, how a row shows its meaning, code colours.

| Option | Palette (bg / ink / card / line / accent) | Type (title / UI / code) | Row meaning | The one memorable thing |
|---|---|---|---|---|
| Paper (reference) | #fbf8f1 / #26231e / #ffffff / #e4dccb / #1f5fbf | Source Serif 4 / Inter / JetBrains Mono | tinted boxes | unchanged, the baseline |
| Paper, coded | #fbf8f1 / #26231e / #ffffff / #e9e1cf / #1f5fbf | Newsreader / IBM Plex Sans / IBM Plex Mono | hairline rows, a 3 px colour bar on the left | syntax colours tuned to paper, rows quieter than boxes |
| Highlighter | #ffffff / #1d1d1b / #ffffff / #e6e4dd / #1d4ed8 | Literata / Atkinson Hyperlegible / IBM Plex Mono | marker swash behind the text, no boxes | the page reads like a printout marked by a reviewer |
| Index card | #e8edf3 / #1b2433 / #ffffff / #d6e2f3 / #2350b8 | IBM Plex Serif / IBM Plex Sans / IBM Plex Mono | ruled lines, red margin rule on each card | cool desk with white ruled cards |
| Notebook | #f6f7f1 grid / #1f2a24 / #ffffff / #1f2a24 / #23784a | Bricolage Grotesque / Atkinson Hyperlegible / Fira Code | ink outlines, solid fills for status | engineering grid paper and firm ink outlines |
| Doc suggestions | #eef0f3 / #202124 / #ffffff / #dadce0 / #1a73e8 | Lora / Roboto Flex / Roboto Mono | Google Docs suggestion colours: kept, removed, inserted | the explainer speaks the same visual language as the Doc it writes |

Colour meanings, all options: amber = status, green = kept, red with strike = removed, blue = markers and links, the written slot = inserted.

Review against the brief:
- First draft had a sixth option, a pale blueprint. It repeated Notebook (technical lines, one accent), so I cut it.
- First draft gave Highlighter a cream page. Cream plus serif is the generic default and duplicates Paper, so Highlighter moved to a white page.
- No option adds caps eyebrows, mono data labels, or arrow glyphs beyond what Control already has. The Control layout keeps its own small caps card titles because the user chose that layout.
