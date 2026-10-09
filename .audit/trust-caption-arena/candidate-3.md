# Candidate 3 - one caption rule for D23 and D24

## Problem

The board author writes shown text with Markdown backticks. engine.js turns a backtick pair into a `<code>` span (fmt, engine.js:16). No Python renderer shares that rule. card.headline() returns the raw say entry (card.py:88), so the card shows raw backticks and a dict say entry becomes its repr (D24), and the comment prints the same. The outro uses esc, not fmt (engine.js:485), so backticked outro lines show raw backticks (D23). doc.py keeps a private copy of the code-span rule (_prose_html, doc.py:124). The design must honor: explainer and presentation never import each other, both import core modules; the board format, CLI and the comment's one-code-span headline stay; boards without backticks reproduce the acceptance package byte-identically; tests reach behavior through build_card_html, render_comment, render, render_doc and a real Chromium page.

## Usage (caller's view)

The board author is the only writer of shown text. These entries are legal today and all render surfaces must agree on them:

```json
{ "type": "title", "say": ["`select_next_episode` now finds the last watched episode."] }
{ "type": "title", "say": [{"show": "The `AI` step is new.", "speak": "The A.I. step is new."}] }
{ "type": "outro", "l1": "`select_next_episode` returns the last watched episode.", "l2": "Start at the finder in episodes.py." }
```

Video captions, outro lines, doc prose and the card headline show the identifier as code. The comment keeps its one code-span headline; span() already turns stray backticks into apostrophes, so it stays untouched.

Call sites:

```python
# prc/explainer/doc.py, _scene_section
prose = "\n".join(f'<p class="prose">{shown_html(line)}</p>' for line in captions(s))
# prc/presentation/card.py, build_card_html token table
("HEADLINE", shown_html(headline(m, board))),
# prc/explainer/timing.py, fit_sentences
"text": shown(line),
```

## Shape

New core module `src/prc/captions.py`. It owns two decisions: say entry to shown text, and shown text to HTML. Stdlib imports only, so both packages can import it and the layering holds. This is the single source of truth; the checker stays the validation boundary (explainer/check.py:325-340, unchanged).

```python
# src/prc/captions.py (new, core layer)
def shown(say: str | dict[str, Any]) -> str:
    """Shown text of a say entry: the string itself, else its "show" spelling.
    Raises ValueError on an entry the checker would reject."""
    raise NotImplementedError


def shown_html(text: str) -> str:
    """Shown text as HTML: html.escape, then each backtick pair becomes one <code> span."""
    raise NotImplementedError
```

Data flow: fit_sentences stores shown text per sentence (engine captions read it at :630). doc.captions(scene) maps a scene to shown texts and _prose_html is deleted; its one call site calls shown_html. card.headline() prefers outro l1, then the first title say entry via shown(), then the PR title; the HEADLINE token value becomes shown_html(headline(m, board)) and HEADLINE leaves the _escape branch (EYEBROW and FOOTER keep _escape). comment.render_comment is unchanged. engine.js: outro l1/l2 switch esc to fmt; every other fmt/esc site stays.

```js
// engine.js:485 before
const l1 = D('l1', esc(s.l1), wrap), l2 = D('l2', esc(s.l2), wrap);
// after
const l1 = D('l1', fmt(s.l1), wrap), l2 = D('l2', fmt(s.l2), wrap);
```

No CSS or card.html change. A template byte change would break byte-identity for every board; the card code span uses the browser default monospace.

Load-bearing decisions. The escape choice is html.escape, which doc.py uses today: doc.html stays byte-identical for every backtick-free board, card.html bytes stay identical whenever the headline has no quote character (true for every acceptance headline), and pixels never change for backtick-free boards. engine.js must stay standalone for the offline player page, so no code is shared across the language boundary; the invariant lives in a parity test instead. shown() raises on invalid entries, so an unchecked board fails loud instead of printing a dict repr. Interface depth: two small functions hide the show/speak fallback and the escape-plus-code-span policy; callers pass text and receive text or HTML. The refactor removes the two-ways problem: timing.py:178 and doc.captions() move onto the rule in this same change (question 4: yes; leaving either behind recreates a hand-synced copy).

### Tests

| Test (file) | Public entry | Catches |
|---|---|---|
| test_headline_uses_the_shown_text_of_a_spoken_caption (tests/test_card_comment.py, exists, red) | build_card_html, render_comment | D24 card and comment |
| test_card_headline_sets_backticked_names_as_code (same file, exists, red) | build_card_html | D23 card side, incl. unpaired backtick and angle brackets |
| test_outro_l1_l2_render_code_spans (new, tests/test_explainer_render.py) | render(keys_only=True) + real Chromium player.html, window.seek | D23 video outro side |
| test_caption_html_matches_engine_fmt (new, same file) | render(keys_only=True) + real Chromium player.html | Q3 drift guard: caption innerHTML equals shown_html, with the one known difference (apostrophe entity) normalized on both sides |
| test_doc_prose_matches_shared_rule (new, tests/test_explainer_doc.py) | render_doc | doc drift after the _prose_html redirect |
| test_backtick_free_boards_render_unchanged (new, tests/test_card_comment.py) | build_card_html, render_comment, render_doc over mdp12/mdp14/mdp17b | byte-identical constraint: every caption and l1/l2 gives shown_html(text) == html.escape(text) |

## Synthesis decision

Filled in by arena during synthesis.

## Tradeoffs accepted

- We accept that shown() raises where doc.captions() today returned an empty string; the checker prevents it, and a loud failure beats a blank caption.
- We accept html.escape semantics: card.html bytes change only for a headline containing a quote character; pixels stay identical and no acceptance headline has one.
- We accept the drift guard as a test, not shared code, because player.html must stay standalone.
- We accept parity coverage for captions only; notes, claims, group subtitles and labels stay video-only fmt sites.
- We accept the browser-default monospace for code spans in the card headline; no template bytes change.

## Alternatives considered

- Rule lives in explainer, presentation imports explainer: lost because it breaks the layering; card and comment would import the explainer package (voice, render) for one rule, and the change looks right only from one file.
- Checker rejects backticks in l1/l2, card stays plain: lost because it splits one concept into two policies, the l2 line most needs identifiers (file names to review), and the title-say path still needs conversion for the comment headline, so the card-side complexity survives anyway.
- Python pre-renders caption HTML into the board JSON the engine reads: lost because the board stays an author-written artifact and engine fmt also serves notes, claims and labels, so only captions would move and one JS rule splits into two sources.
- headline() returns a typed HTML-safe wrapper: lost because it adds a type across the package boundary to serve one render site; shown_html at the token is smaller.

## Implementation reconciliation

Nothing yet. Record accepted deviations here during implementation.

## Open questions and risks

- Unpaired backticks render literal in both twins. Should the checker reject an odd backtick count instead? One cheap rule, not needed for D23 or D24.
- The PR-title fallback goes through shown_html too, so backticks in a PR title render as code in the card. Confirm this is wanted.

## Next implementation step

Create src/prc/captions.py with shown and shown_html, make the two red card and comment tests pass, then move timing.py and doc.py onto the rule and run the suite.
