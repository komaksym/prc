# Source: paired-eval hub handoff repair (2026-10-13)

Operator report: "familiar PR retained as unknown; timed reading refused". The hub refused a
reading at the familiarity gate and gave no recovery guidance. Operator correction: the hub was
verified by API checks and screenshots, but never by clicking the buttons.

Subagent Halley clicked every hub button in real Chromium and found six defects:
1. Familiar or explained-PR refusal gave no guidance.
2. A stale preview dead-ended the hub (two-tab start).
3. Close while a reading ran hid its reason.
4. Prepare while a reading ran showed a misleading message.
5. Mid-way close was impossible from the landing page.
6. A deadline timeout silently replaced the reading with the landing page.

Fixes: src/prc/evaluation/session.py (close reason, preview states) and
src/prc/evaluation/assets.py (guided refusal, stale-preview recovery, timeout notice,
confirm-guarded Close study now). Ten new regression tests in tests/test_paired_hub.py pass,
and the driver PA S S run closes, grades, and analyzes six trials with zero page errors.

Subagent Huygens enforced the practice: scripts/verify_paired_hub.py drives every button path
and writes checks.json plus screenshots; .agents/skills/verify/features/paired.md requires it
for hub changes; tests/test_verify_paired_hub.py and tests/test_dispatch_collection.py fail when
the requirement is missing; one AGENTS.md rule row records it. The routing guard now reads the
live override sheet and fails loudly on drift with the stale mirror.

Study state after reseal: six readings pending, fresh seal, superseded seals kept.
