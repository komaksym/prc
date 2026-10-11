# Paired evaluation — candidate sketch (glm)

Candidate for the matched-pair pilot in PLANS.md, "Matched PR evaluation, 2026-10-11". Grounded in `src/prc/evaluation/{protocol,scoring,analysis,io}.py`, `src/prc/cli.py`, `docs/design/evaluation-protocol.md`, and `.audit/paired-evaluation-failures.md` (failure cases cited as F1–F16). One candidate; synthesis happens at the parent.

## Problem

The paired pilot has five invariants no existing artifact enforces: each PR is read once (F1, F9); only one arm's output is ever exposed per PR (F7); the reading clock survives refresh and process restart (F8); answer keys and future PRs never reach the browser before closure; scoring is blind to assignment, interface, timing, and failure status. The existing `prc.evaluation` engine is pure and hard-wired to the frozen 12-pair protocol; the paired pilot runs 3 pairs in one session. The shape must add one small ownership layer without touching the engine.

## Usage (caller's view)

CLI first; four commands, one job each:

```
prc paired-prepare manifest.toml --kit artifacts/paired/<study-id>
# validates roster and assets (F1–F5), draws randomization, copies asset bytes, seals;
# refuses to write a kit on any failure

prc paired-serve artifacts/paired/<study-id> --port 8737
# human reads at http://127.0.0.1:8737 in a real browser; closes with responses.json

prc paired-grade artifacts/paired/<study-id> responses.json --graded graded.json --out results.json
# prints blinded sheet (human scorer fills anchors), then unblinds into results.json

prc eval-analyze artifacts/paired/results.json --pair-count 3
```

Browser flow: the dashboard lists six trials in drawn order with states (unstarted/open/stopped/closed). Opening a trial starts the server-side clock exactly once; replay or a duplicate tab is a no-op (F9). The trial page shows the assigned arm (GitHub opened live by pinned URL, plus the prebuilt arm view) and the three frozen questions; answers save per item; refresh re-renders remaining time computed from the server (F8, F16). Stop (submit or abort) freezes elapsed; the 20-minute deadline does it automatically and flags censored (F10, F11). A stopped trial never serves content again (no same-PR reread).

## Shape

New package `prc/paired/`, three modules. Public surface: three functions plus one server class; internals are `_`-private and not re-exported.

```python
# kit.py — pure, stdlib only
@dataclass(frozen=True)
class Asset: snapshot_id: str; arm: Condition; source_kind: AssetSource; kit_path: Path; sha256: str
@dataclass(frozen=True)
class Question: snapshot_id: str; index: int; kind: ItemKind; prompt: str
@dataclass(frozen=True)
class TrialManifest: pairs: tuple[PrePair, ...]; seed: int; github_urls: Mapping[str, str]
                    assets: Mapping[str, PreparedAsset]; protocol: Protocol
@dataclass(frozen=True)
class TrialKit: root: Path; sealed: SealedKit; assignment: ExperimentAssignment
                assets: tuple[Asset, ...]; questions: tuple[Question, ...]; keyfile: Path
def prepare(manifest, kit_root) -> TrialKit   # F1–F5 checks; copies bytes; seals
def load_kit(kit_root) -> TrialKit            # re-verifies digest and keys digest (F6)

# session.py — the only writer of mutable state (session.sqlite)
class PairedServer:
    def __init__(self, kit, port): ...
    def serve_forever(self) -> SessionSummary
# GET /, GET /trial/<id>, POST /answer, POST /stop, POST /close -> responses.json
# tables: trials(pair_id, snapshot_id, arm, opened_at, stopped_at, reason, censored)
#         answers(snapshot_id, index, answer, confidence, saved_at)

# grade.py — pure
def blinded_sheet(kit, responses) -> BlindedSheet      # HMAC tokens from keyfile; no arm, timing, or interface
def apply_grades(kit, responses, graded, results_path) -> Path  # validates F12; writes io.load_pairs shape
```

Load-bearing decisions:

- **Reused engine, no parallel protocol.** Randomization and sealing reuse `assign()` and `seal_digest()` with a scaled `Protocol(pair_count=3, pairs_per_session=3, session_days=(1,))`; grading reuses `deliver_product`, `deliver_baseline`, `score_item`, `SnapshotResult`, `PairOutcome`. `prc.evaluation` gains no edits; `--pair-count` is the only engine-CLI change.
- **Requests select an index, never a path.** URLs are `/trial/<n>/asset/<name>`; session.py maps names to absolute kit paths in memory for the current trial only. Traversal (F13) and future-PR exposure (F7) are impossible by construction: no request names a disk path, and the index contains only the active trial's assets. The keyfile is outside the served namespace.
- **Keys sealed but absent.** `keys.json` (per-item key, HMAC secret, token map) sits outside the index; the sealed payload records `keys_sha256`; grade refuses a changed keyfile — that is a new experiment with this experiment's records preserved (F6).
- **Arm identity sealed as data.** Per snapshot, exactly one arm's asset is prebuilt and hashed: genuine Coldtea PR Lens CI bytes for baseline, PRC review output for treatment, provenance checked against head/base revisions (F4, F5). A failed product build fails preparation before sealing; the runtime fallback machinery stays the engine's, deliberately unexercised in this pilot. A Lens asset that fails at serve time keeps the trial and records a visible delivery failure rather than degrading silently to GitHub alone (F14).
- **Timing is server-owned.** `opened_at` is written once per trial; elapsed is computed from state, never stored as a mutable counter; refresh or process restart recomputes it. Deadline and censoring come from `read_timer`.
- **One of everything.** One export path (server close), one grading entry (`paired-grade`), one analysis entry (`eval-analyze`). Question kinds and failure reasons are imported from `scoring`, never restated (no hand-synced lists).

Validation lives at the two boundaries: prepare (roster uniqueness, familiarity exclusion, matching rationale, asset provenance; F1–F5) and apply_grades (ids, anchors, conditions, complete pairs; F12). Between them the types make invalid states unrepresentable (`AssetSource`, `ItemKind`, `Condition` are enums; frozen dataclasses).

## Stdlib session server vs static kit

A static kit (pregenerated pages, file:// browsing) is simpler to build and audit, but cannot enforce any state invariant: filesystem browsing exposes both arms and keys by default, client timers reset on refresh, and viewed-once/deadline/abort bookkeeping would live outside code. Meeting F7–F13 statically re-creates server state in human discipline — the failure mode the audit exists to close. The stdlib `ThreadingHTTPServer` (~250 lines, localhost only, one sqlite session file) hides sqlite, threading, the allowlist, and timing behind one small surface. Verdict: stdlib server for scored sessions; the existing static hub stays for acceptance-only packets where those invariants do not apply.

## Tradeoffs accepted

- We accept a localhost server with no authentication in exchange for zero dependencies; exposure control, not auth, is the defense for keys.
- We accept that prebuilt assets leave the 120 s generation cap and runtime fallback unexercised here, in exchange for a reading window free of generation variance.
- We accept one session per kit run; multi-day scheduling returns only when the pilot justifies it.
- We accept sqlite as a file format, in exchange for atomic upserts and restart-safe state.

## Alternatives considered

- **Pure static kit with manual control** — lost: leaves F7–F13 unenforceable by construction and moves enforcement to operator discipline.
- **Extend the 12-pair `PROTOCOL` globals** — lost: couples two experiments' settings and mutates frozen assumptions; a scaled `Protocol` instance covers the pilot with zero engine changes.
- **Generate the treatment view at trial time via `prc review`** — lost: reintroduces generation failures into the timed window, which PLANS explicitly separates ("Prebuild both tools; record preparation separately from the 20-minute reading deadline").

## Open questions

1. Should the seed be a CLI argument on `paired-prepare` (reproducible, recorded in the sealed payload) or generated and printed? Assumed: CLI argument.
2. Is the baseline arm GitHub plus Lens only, or does it also carry one neutral inline artifact for parity? Assumed: GitHub plus Lens only, per PLANS.
3. Confidence (0–100) is collected in the browser; confirm it stays diagnostic-only in export and analysis.

## Next implementation step

Write the failing E2E first: prepare a 3-pair kit from a manifest, serve it, drive start → answer → reload → submit → close → grade → eval-analyze through the CLI, assert results.json matches the frozen expected analysis, and save a screenshot at each browser step (F16).
