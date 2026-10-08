# Complete current release evaluation evidence

Status: ready-for-agent
Type: task

The saved eight gates pass 96 cells. The full acceptance protocol additionally needs current public-corpus arrow precision, OCR at 800px, timing medians, output sizes, a fresh grounding audit bound to output hashes, and a planted-error judge check. Historical unbound audits cannot certify current output.

Use `docs/mvp/EVAL.md`. The baseline reader also authored questions, so its independence remains a separate limitation. The blank human responses cannot be supplied by agents.

## Current status, 2026-10-08

Historical offline timing has 48 successful samples, including 12 warmups. Its fingerprint predates the current source. Recorded OCR is 25/31 at 800 pixels. Current artifact-bound grounding remains absent. The reconciliation source review found four defects; fixes are under final independent recheck. Human evidence remains blank. See `docs/mvp/STATUS.md`. This ticket stays open.
