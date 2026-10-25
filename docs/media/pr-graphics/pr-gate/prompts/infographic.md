---
layout: structural-breakdown
style: technical-schematic
aspect: 16:9
lang: en
---
Create a 16:9 landscape technical infographic in a clean blueprint "technical-schematic" style: off-white opaque canvas with a thin dark navy border, navy line work, one teal accent, crisp sans-serif labels, high contrast, ample whitespace. Every label must be spelled exactly as written below. Keep text short and legible.

Title at top: "One required check: gate"
Subtitle: "Reuse komaksym/pr-gate on any repo"

Center: a large hexagon node labeled "gate" with a small caption "the only check the ruleset requires".

Left side, a box labeled "Shared checks (pr-gate checks.yml)" containing five small rows with icons: "title", "actionlint", "zizmor", "secrets", "test (npm, optional)". An arrow goes from this box into the gate hexagon.

Below-left, a box labeled "Repo jobs" with two rows: "prc: ci on macOS" and "music-saver: e2e". An arrow goes from this box into the gate hexagon.

Right side, a box labeled "Ruleset pr-gate on main" with four rows: "require gate", "squash only", "threads resolved", "no up-to-date rule". A teal arrow goes from the gate hexagon to this box, labeled "blocks merge".

Bottom band, a numbered strip of three steps titled "Adopt in 3 steps":
"1  Add pr.yml: checks + your jobs + gate"
"2  Run apply-ruleset.sh OWNER/REPO"
"3  Disable old rulesets"

Top-right corner, a small dashed gray box labeled "Review bots: advisory, never required" with three tiny tags "CodeRabbit", "cubic", "Greptile".

No other text. No logos.
