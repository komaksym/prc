# PRC looks, round 11: three looks that change the layout

Summary: round 10 changed only colours and fonts, so round 11 changes the page layout and the card structure. The code view and the reading order stay fixed. Six looks were built, and a screenshot-only critic scored them in two rounds. Three looks were cut because they changed only decoration. Essay (7), Lab sheet (6.5) and Workspace (6) remain, next to Control on paper (7).

Page: [v11-picker.html](../v11-picker.html). CSS: one file per look in [v6-styles/v11/](../v6-styles/v11/), plus the shared code view in [_code.css](../v6-styles/v11/_code.css).

## Method

The method follows Anshu Chimala, "How to turn your AI into a world-class designer" (Lenny's Newsletter):

- Ambitious, specific briefs. Each builder got one structural idea (an article, a sheet, a window, a tile board, a timeline, a launch page) and two YC source sites.
- Seed strings. Each builder took its open values (shades, spacing, type sizes, rule weights) from a random 40-character seed, to break the default AI look.
- A screenshot-only critic in a fresh context. It saw only shots at 1440 px, 800 px and three video frames, plus the source sites and paper. It scored each look out of 10 and named concrete gaps.
- Cut what adds no value. The critic named AI tells (glows, pill rows, decorative numerals, stock timeline nodes), and the fix rounds removed them.

Builders ran on the panel role "feature" (Muse Spark 1.3, xhigh). The critic ran on the panel role "strongest judgment" (the parent model). Each dispatch passed `check-dispatch-model.py` first.

## Fixed rules

- The code view is the same in every look. A checker compares its computed style with paper's. Workspace may drop the code's outer frame, so the code joins its pane. Text, colours and padding may not change.
- The visual order follows the DOM order. The checker measures every block.
- Colour meanings: amber is status, green is kept, red is removed, blue is markers and links, and a dashed outline is the slot the run writes.
- No sideways scroll at 800 px, no code cut off at 1440 px, the same link count as paper, and each video moment fits 1280x720.

## The six looks

| Look | Sources | Structure | Critic 1 | Critic 2 | Result |
|---|---|---|---|---|---|
| Essay | Belvedir, Fabraix | An article. Section names hang in a left margin. No cards. Ruled rows, colour ticks only on rows that carry a meaning, the tip as a pull quote. | 7.5 | **7** | Kept |
| Lab sheet | Omanta, Illume | One printed sheet on a light desk, with numbered sections. Figures are a top rule and a caption. One note style. | 6.5 | **6.5** | Kept |
| Workspace | Pentagon, herdr | One IDE window. Sections are panes joined by shared borders, with header strips. The code note is a side panel. | 6 | **6** | Kept |
| Spine | Audun, Meteoric | A vertical timeline with nodes beside paper's cards. | 6 | 6 | Cut. The critic found it was paper plus a stock stepper. |
| Bento | Gumloop, Wondering | A 12-column tile board. | 5 | 5 | Cut. Its one new element was an empty heading tile. The rest was paper's cards with more shadow. |
| Hero | BOND, Speko | A launch page with a hero band and a glow. | 4.5 | n/a | Cut after round 1. The glow is an AI tell, and the grid was decoration. |

Critiques: `/private/tmp/prc-v11/critic-1.md` and `critic-2.md`. Dispatches: `/private/tmp/prc-v11/dispatch-*.json`.

## Fixes per round

- After critic 1: essay starts its code at the content column and has no numerals. Lab sheet lost its black bands and double rules, and its figures now sit side by side. Workspace lost its empty rail and became one window. Bento was rebuilt as a tile board.
- After critic 2: essay has one left axis, quiet neutral rows, upright captions and a one-line code label in the margin. Lab sheet has transparent figures, one note style, a lighter desk and no "Fig." numbers. Workspace has a real headline row, a code pane with no double frame, a full-width slot row and plain footers.
- Shared: in the video, the third moment now starts at the top like the first two, so the summary does not jump. Paper's video is unchanged, because paper is the control.
- Final review: the Essay video froze on the flown status chip, which covered the "New status" label until moment 2. The recorder saves a frame only on a repaint, and Essay turns off the kept-row glow, so the chip removal made no new frame. The chip now fades out over 220 ms, and all three clips were recorded again. The Workspace text "Cards: none float." now reads "Cards: none."

## Open gaps

- Lab sheet: the six count rows are one text node each, so a CSS-only table with right-aligned numbers is not possible. A real table needs a change to the page markup.
- Essay: the code note sits under the code at 1440 px, because the reading column is too narrow to hold it beside the code.

## Checks

- `/private/tmp/prc-v11/check.py` checks paper, essay, workspace and lab sheet at 1440 px, at 800 px and in clip mode. The last run is in `/private/tmp/prc-v11/run-all.log`.
- The videos come from `build.py clips control-essay control-workspace control-labsheet`. The results are in [clips/report.json](../v6-styles/clips/report.json), with contact sheets at `v6-styles/shots/clip-control-<look>-sheet.png`.

