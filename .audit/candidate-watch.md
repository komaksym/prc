# candidate-watch - reveal-candidate run

Verdict: PASS - candidate complete. PR16 is present. No rebuild needed.

Done vs missing (rebuild.json):
- Rebuilt check_passed true (8): pr5, pr7, pr8, pr10, pr13, pr15, pr16, pr19.
- Reused from release-check (4): pr11, pr12, pr14, pr17.
- Missing: none. All 12 PR dirs exist under outputs/.

PR16 board - reveal cues present:
- Old release-check pr16: stats cues None, outro cues None.
- Candidate pr16: stats 2 card cues, outro l1 at 0.0, l2 at 0.5, cmd at 0.9.
- Candidate board SHA matches rebuild.json 37b29b3be228c3c3c9b1a428c0ad2368a86200865a117d73ba50b49af42a3407.
- Transform matches rebuild-reveal-candidate.py logic.

outputs/pr16 state - complete:
- board.json, run.json check passed true, duration 51.72s.
- video.mp4 2.1M, narration.wav 4.7M, map.json, map.html, doc.html.
- card.html, card.png, comment.md, phrases.json 6 phrases, player.html, tokens_s3.json.
- keys 14 png, audio empty same as pr10 and pr11.
- logs/pr16.json check_passed true, stored_head_sha df74ac34650a049fd1feb4a081adb3ace5f3e0cf.

Board SHAs rebuilt:
- pr5 603737530a6090778dab6ec2fef62b3db1265d7791a85e2c68e4cafa19e1b55e
- pr7 80dfca280ab60f3a5eebe0192749211639335b7021faca0f14e107f900cf23ef
- pr8 bc0a698d8faf0219ddbeb7d6370d40917e08ec8a56d852c565be3c573bb66d76
- pr10 9a537138689273a1cc2b3fcd7dad21e223b1c2266433711b658caaa21fe85a6f
- pr13 383b63a7ff1e2a88d0133ef6f4a6598c97174b2e232e117b487ea434a9a78583
- pr15 f7ae5a0f3e3dc562c70498324e14685a7a8b408392edb9f360b49c1da3d1d5fa
- pr16 37b29b3be228c3c3c9b1a428c0ad2368a86200865a117d73ba50b49af42a3407
- pr19 24a7e4b3a7c559dec3873d486147f028dde870d890eeb4eded9bbd791800b451

Rebuild command for parent - no-op, safe, script skips recorded PRs:
- python3 artifacts/release/rebuild-reveal-candidate.py
- Run from repo root. Do not run per-PR prc explain manually.
- Script asserts boards unchanged and refuses to replace outputs.
- This run did NOT execute the rebuild, per scope, avoids 40s per PR race.

Notes:
- Expectation PR16 missing is stale. PR16 finished at 11:38 UTC, wall 39.01s.
- rendered dir is empty. Outputs moved after build. This is normal.
- Principles: prove-it-works, laziness-protocol, foundational-thinking. Verified real artifacts, smallest read-only check, checked shapes first.
