# Reader packets do not implement the frozen viewing conditions

Type: task
Status: resolved

The current builder exposes source video and raw HTML instead of fixed reader payloads. It does not decode C3 frames or capture C4 and C5 screenshots. A reader can inspect more information than the frozen condition permits.

Finish local payload generation with exact recorded timing, hashes, answer-key exclusion, and failure preservation. Keep frozen packets unchanged. Save new CLI evidence under `artifacts/e2e/eval-packets`.

The isolated implementation is in `/private/tmp/prc-packet-work-20261007`.

## Answer

The captured `2026-10-08-release-check` run has 60 completed isolated reader packets with 339 matching payload hashes. The real packet builder and its E2E evidence are retained. See `docs/mvp/STATUS.md`. This resolves packet construction for that historical run. Current-source acceptance requires a new bound run after reconciliation fixes.
