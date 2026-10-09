# Final rendering contract

Summary. Validate the same code rows and reveal intervals that the engine consumes.

`diffrows.prepare` owns tab expansion, trailing-space removal and common indentation.
`jointest.document` constructs the join artifact for preflight and highlighted rendering.
`jointest.run` validates both artifacts. No second partial join contract remains.

`timing.row_motion` owns row entry, replacement delay and opening intervals.
Narration fitting stores these intervals on rows. The engine consumes the stored intervals.
`timing.visible_rows` checks complete row visibility at the settled frame, before scene fade.
Checks estimate silent cue stamps. Rendering repeats validation with actual narration stamps.
Coverage lists late or uncued rows as missing. Receipts alone do not display code.

Regression evidence: five failures before implementation in `join-reveal-red.log`.
The focused rendering, card, walkthrough and join suite passed 114 checks in real Chromium.
A replacement-row screenshot is produced by `test_replacement_is_visible_in_real_settled_frame`.

Next step: complete installed-wheel acceptance at three fixed PR revisions.
