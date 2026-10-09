# Grounding for the caption-rule design (D23, D24)

Worktree: /Users/koval/dev/prc/.claude/worktrees/readiness (branch feat/trustworthy-pr-explanations, HEAD 07e8596 plus an uncommitted D18 to D22 fix). Read code there. Do not edit it.

## What the user sees

PRC renders one checked board (JSON written by an agent, format in src/prc/explainer/assets/BOARD.md) into five outputs: video (player.html driven by assets/engine.js, encoded to MP4), walkthrough doc.html (src/prc/explainer/doc.py), card.png (src/prc/presentation/card.py plus assets/card.html), comment.md (src/prc/presentation/comment.py) and map.html.

## Traced facts

- engine.js:15 `esc` escapes & < > ". engine.js:16 `fmt = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>')`.
- The engine uses fmt for captions (engine.js:630, text from scene sentences), group subtitles (:308), notes (:347, :429, :538), claims (:458) and diff labels (:500). It uses esc only for group titles (:308), claim numbers (:458) and outro l1/l2 (:485).
- timing.py:178 builds each engine sentence text as `line if isinstance(line, str) else line["show"]`.
- doc.py:40 `captions(scene)` returns the shown text of each say entry: a string, or a dict's "show" (else "speak"). The uncommitted D19 fix adds doc.py `_prose_html(line)` = `re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(line))` for doc prose. Nothing checks that it stays equal to engine fmt.
- card.py:88 `headline(m, board)` returns the outro l1 when present, else `str(scene["say"][0])` of the first title scene, else the PR title. card.py:383 puts it into the HEADLINE token through xml.sax.saxutils.escape, so backticks stay raw. card.html:43 clamps the headline to two lines at 42px bold.
- comment.py:185 writes `# {span(headline(m, board))}`. render_brief.py:15-20 `span()` turns backticks into apostrophes, collapses whitespace and wraps the whole headline in one Markdown code span.
- check.py:325-328 requires outro l1 and l2 to be strings. check.py:329-340 allows a say entry to be a string or a dict with a string "show". No rule mentions backticks. No rule requires an outro scene.
- BOARD.md:26 says text in backticks shows as code in the caption and is read without the backticks. BOARD.md:153 says l1 states what changed in one plain sentence.
- Layering: prc.presentation and prc.explainer do not import each other. Both import core modules such as prc.facts and prc.brief. prc.pipeline imports both packages.
- The three real acceptance boards all have an outro. Their l1 and l2 contain no backticks, so their cards take the headline from l1.

## Reproduced defects

- D23. A board without an outro whose title caption is "`select_next_episode` now finds the last watched episode." gives a card headline with raw backticks, while the video caption shows code. An outro l1 or l2 with backticks shows raw backticks in the video outro and in the card.
- D24. A board without an outro whose first title say entry is {"show": "The `AI` step is new.", "speak": "The A.I. step is new."} gives the card headline "{'show': 'The `AI` step is new.', 'speak': 'The A.I. step is new.'}". The comment uses the same headline() and prints the same dict.

## Constraints

- No new dependencies. Keep the board format, the CLI and the comment's code-span headline.
- Boards without backticks must render byte-identical card, doc, comment and video frames. The acceptance package depends on this.
- The card must still fit its two-line headline clamp.
- Tests must reach the behavior through public entry points: build_card_html, render_comment, render, render_doc and a real Chromium page.

## Open design questions

1. Where does the one Python rule for "say entry to shown text" and "shown text to HTML" live, given the layering?
2. Outro l1 and l2: render backtick pairs as code like captions, reject backticks in the board checker, or keep them plain?
3. What keeps the Python rule and engine.js fmt from drifting apart?
4. Should timing.py:178 and doc.captions() move to the shared rule in the same change?
