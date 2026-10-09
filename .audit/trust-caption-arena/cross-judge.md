# Arena cross-judge: caption rule (D23/D24) — candidate 2 vs candidate 3

## Verdict
Base: candidate 3 (src/prc/captions.py, `shown` + `shown_html`). Reject candidate 2 plain-text card headline: red tests require card <code> spans, and plain stripping breaks card/video/doc agreement.

## Scores (0-5)

| Criterion | C2 (boardtext) | C3 (captions) |
|---|---|---|
| 1. Correctness: str/show-speak + paired/unpaired backticks | 2 — `shown()` fixes D24, `prose_html`+fmt fixes video/doc/outro, but card `plain_text` strips paired markers (zero <code> spans), contradicts BOARD.md:26 | 5 — `shown()` + `shown_html` everywhere (caption, outro l1/l2 via fmt, doc prose, card HEADLINE); unpaired literal in both twins; escape-then-span |
| 2. Presentation/explainer layering | 5 — new core module, stdlib only, no cross-import | 5 — same core placement, stdlib only, checker stays validation boundary |
| 3. Smallest maintainable API | 3 — three fns split one concept into two policies (HTML vs plain); HEADLINE stays escaped | 5 — two fns, one HTML policy; deletes doc `_prose_html`; timing.py:178 + doc.captions() move together |
| 4. Backtick-free preservation + comment syntax | 4 — byte-identical claim + `span()` untouched, no quote-char analysis | 5 — html.escape matches doc today; card bytes identical when headline has no quote char (true for acceptance); comment `span()` untouched; mdp12/14/17b test |
| 5. Real browser coverage (doc/card/outro, escaping, layout) | 3 — Chromium caption+outro <code> assertions but card oracle asserts plain (wrong), doc path thin | 5 — render(keys_only=True)+Chromium player.html window.seek for outro, caption innerHTML equals shown_html with apostrophe normalization, render_doc + build_card_html/render_comment via public entries |

## Why C2 fails the contract
tests/test_card_comment.py::test_card_headline_sets_backticked_names_as_code expects headline_parts() == (plain text, [select_next_episode]): one <code> span, unpaired backtick literal, angle brackets escaped. C2 `plain_text` yields zero <code> spans — red stays red. C3 HEADLINE=`shown_html(headline)` with HEADLINE out of `_escape` branch keeps card/video/doc identical. D24 fixed by both via `shown()`, but only C3 carries it to code card + unchanged comment `span()`.

## Card/outro default code styling: adequate, no geometry
Card card.html:43 clamps .headline to 2 lines at 42px bold with overflow hidden; no code rule. Browser-default <code> (monospace, inherited size) preserves clamp; worst case is ellipsis, not breakage. No template-byte change keeps backtick-free byte-identity. Outro engine.css l1/l2 are 84px serif; code inherits monospace via global code rule and l2 gold color; captions already prove the pattern (ecap code 0.84em gold). Sufficient for trust milestone. _FIT governs look/risky/evidence only. Optional follow-up only if E2E screenshots show weak contrast: add headline-code/outro-code gold rule with screenshot proof.

## Recommended grafts (C2 into C3 base)
- Pinned corpus breadth from C2: amp/lt/gt/quot + paired + unpaired backticks, shared by Python unit + Chromium assertions, with pointer comments naming engine.js `fmt` on both sides.
- SayEntry str-or-dict alias and note that check.spoken() (voice) stays separate from shown text.
- Single-token engine diff framing (esc to fmt at outro :485 only, all other fmt/esc sites stay).

## Rejections
- Reject C2 `plain_text` + HEADLINE-stays-escaped: fails red card-code contract, splits card from video/doc.
- Reject checker-rejects-backticks (both designs rightly reject): invents author burden, breaks boards, leaves render path undecided.
- Reject rule-in-explainer, pre-rendered-HTML-in-board-JSON, typed-HTML-wrapper (C3 alternatives list governs).
- Reject checker-rejects-odd-backtick-count: literal-unpaired parity is the tested behavior, unneeded for D23/D24.
- Accept C3 PR-title fallback through `shown_html` (consistent); confirm only if a backticked PR title appears in review.
