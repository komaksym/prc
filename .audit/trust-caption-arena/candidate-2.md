# Caption-text unification (candidate 2)

## Problem

Three renderers derive "shown text" from board sentences three ways: timing.py:178 inlines `line["show"]`, doc.py `captions()` repeats it with a different fallback, and card.py `headline()` calls `str()` on the raw entry. A fourth renderer, doc `_prose_html`, duplicates engine.js `fmt` without a parity guard, while the engine itself renders outro l1/l2 with `esc` instead of `fmt`. The result is D23 (raw backticks in card headline and video outro) and D24 (`str(dict)` headline). The layering constraint is load-bearing: `prc.presentation` and `prc.explainer` never import each other, so the single rule must live in core.

## Usage (caller's view)

Board authors change nothing. The board format, CLI, and comment code-span headline stay as-is.

```python
from prc.boardtext import plain_text, prose_html, shown

shown("says `hi`")
# -> "says `hi`"
shown({"show": "The `AI` step is new.", "speak": "The A.I. step is new."})
# -> "The `AI` step is new."
prose_html("uses `select_next_episode` & friends")
# -> 'uses <code>select_next_episode</code> &amp; friends'
plain_text("uses `select_next_episode` now")
# -> "uses select_next_episode now"
```

Call sites after the fix. `timing.py` builds sentence text as `shown(line)`. `doc.py` builds `captions()` as `[shown(s) for s in scene["say"]]` and prose as `prose_html(line)`. `card.py` `headline()` returns `plain_text(...)` of the outro l1 or the first title say entry via `shown()`, never `str(entry)`. `comment.py` keeps calling `span(headline(...))` unchanged. The engine renders outro l1/l2 with `fmt`, matching captions.

## Shape

New core module `src/prc/boardtext.py`, the only owner of two conversions: say-entry to shown text, and shown text to HTML or plain text. Both `prc.presentation` and `prc.explainer` already import core (`prc.facts`, `prc.brief`); both import `prc.boardtext` the same way, so the layering ban on presentation/explainer cross-imports stays intact (per boundary-discipline). `SayEntry` is `str | dict[str, str]`; validation of the dict shape stays in `check.py` at the boundary, and everything inside trusts the type. `check.spoken()` (voice spelling) stays where it is: voice selection is a different concern from shown text, and merging them would be temporal decomposition around one dict.

Interface depth: three public functions hide escaping order, the backtick regex, unmatched-backtick tolerance, and the show/speak fallback chain. Callers drop from inline conditionals to one call each. `timing.py:178` and `doc.captions()` both move in this change; leaving either inline keeps two ways to do one task and guarantees the next agent copies the wrong one.

Outro l1/l2 render as code through the same rule. BOARD.md:26 already promises backticks show as code and are read without backticks; l1/l2 are board prose read aloud, so "plain sentence" in BOARD.md:153 constrains tone, not markup. Rejecting backticks in the checker would invent author burden, break existing boards, and still leave the render path undecided.

Drift guard: the Python regex and engine `fmt` share one pinned corpus test (`tests/test_boardtext_parity.py`) covering `& < > "`, paired backticks, and unmatched backticks; both sides carry a pointer comment naming the other. The engine change is a single token (`esc` to `fmt`), so the drift surface is one regex, verified behaviorally by a Chromium test asserting `<code>` in caption and outro frames.

## Synthesis decision

Candidate. No synthesis performed; pending arena judging.

## Tradeoffs accepted

- We accept a new 30-line core module in exchange for deleting three inline copies and one duplicated regex.
- We accept `plain_text` stripping code markers in the card headline (no `<code>` styling; the HEADLINE token is XML-escaped) in exchange for card/video/doc agreement; comment `span()` keeps its apostrophe form per constraint.
- We accept corpus-pinned parity instead of generating one renderer from the other in exchange for zero toolchain changes and a one-token engine diff.

## Alternatives considered

- Reject backticks in outro l1/l2 via the checker. Lost: pushes cost to every board author, breaks boards that already use code voice, and fixes neither the card fallback nor the dict headline.
- Own the rule in `prc.explainer.check` and import it from presentation. Lost: violates the explicit layering invariant and aims the dependency the wrong way for a presentation need.
- Keep outro plain (`esc`) and strip backticks at the checker. Lost: preserves the D23 video/card divergence and contradicts the BOARD.md code promise.
- Duplicate strip logic separately in card.py and comment.py. Lost: split ownership of one invariant; the next edit fixes one copy (per separate-before-serializing-shared-state).

## Implementation reconciliation

No implementation performed. Design-only artifact.

## Open questions and risks

- Does the card HEADLINE slot accept inline `<code>` styling, which would let the card render code instead of stripping markers?
- Should `check.py` also warn (not error) on backticks in outro l1/l2 so authors notice the card shows them plain?
- Is `tests/test_boardtext_parity.py` an acceptable home for the shared corpus, or should the corpus live as a fixture both suites read?

## Next implementation step

Create `src/prc/boardtext.py` against the sketch below, then repoint `timing.py:178` and `doc.captions()` at it.

## Module map

- NEW `src/prc/boardtext.py`: owns `shown`, `prose_html`, `plain_text`. Imported by explainer and presentation; imports stdlib only.
- EDIT `src/prc/explainer/timing.py`: sentence text uses `shown`.
- EDIT `src/prc/explainer/doc.py`: `captions()` and `_prose_html` delegate to `shown` / `prose_html`.
- EDIT `src/prc/presentation/card.py`: `headline()` uses `shown` + `plain_text`, never `str(entry)`.
- EDIT `src/prc/explainer/assets/engine.js`: outro l1/l2 use `fmt`.
- EDIT `src/prc/presentation/comment.py`: none (inherits the fix through `headline`).
- NEW `tests/test_boardtext_parity.py`: pinned corpus for both renderers.

## Signature sketch

```python
from __future__ import annotations
from typing import Any
import html as _html
import re as _re

SayEntry = str | dict[str, str]
_CODE = _re.compile(r"`([^`]+)`")


def shown(entry: SayEntry) -> str:
    """Visible caption text: the string, or the dict's show (else speak)."""
    raise NotImplementedError


def prose_html(text: str) -> str:
    """Escape & < > quotes, then render paired backticks as <code>."""
    raise NotImplementedError


def plain_text(text: str) -> str:
    """Shown text with code markers removed for plain slots (card headline)."""
    raise NotImplementedError
```

```python
# card.py: headline keeps its selection order, changes only conversions
def headline(m: dict[str, Any], board: dict[str, Any] | None = None) -> str:
    raise NotImplementedError  # outro l1 -> plain_text(l1); title say[0] -> plain_text(shown(say[0])); else plain_text(title)
```

engine.js before/after (MAKERS.outro):

```js
// before
const l1 = D('l1', esc(s.l1), wrap), l2 = D('l2', esc(s.l2), wrap);
// after
const l1 = D('l1', fmt(s.l1), wrap), l2 = D('l2', fmt(s.l2), wrap);
```

No CSS change: `<code>` inside outro inherits the caption code style already in player CSS scope.

## Test list

- E2E via `render` + real Chromium page: board without outro, title caption "`select_next_episode` now finds the last watched episode." Catches D23 video half (caption frame must contain `<code>`) and D23 card half (`build_card_html` headline has no backticks). Artifact: rendered frame screenshot + card.html.
- E2E via `render` + Chromium: outro l1/l2 with backticks. Catches D23 outro half (outro frame `<code>`, card headline plain). Artifact: outro frame screenshot.
- Via `build_card_html` and `render_comment`: first title say entry `{"show": ..., "speak": ...}` with no outro. Catches D24 in both outputs (no `{'show':` text). Artifact: card.html + comment.md.
- Unit `tests/test_boardtext_parity.py`: corpus (`& < > "`, paired/unmatched backticks) asserting `prose_html` outputs. Catches Python/engine `fmt` drift alongside the Chromium `<code>` assertions.
- Regression: re-render the three acceptance boards; card, doc, comment, and video frames must be byte-identical (no-backtick path untouched). Catches over-broad conversion.
- Unit: `timing` sentence text equals `doc.captions()` on dict entries. Catches a future second copy of the rule.
