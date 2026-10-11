# Paired-eval cross-judge (readonly, xhigh ceiling)

Method: read parent and Muse end-to-end. No nested agents. GLM candidate arrived after first pass and is scored in the addendum below. Ceiling is xhigh; max is unavailable on this host.

Verdict: use parent local-server design as base. Graft Muse test and type details. Parent wins on leakage, state, and analysis wiring.

Scores (rubric from parent, 0-2 each):

- 1 Distinct unseen pair, exact two arms: parent 2, Muse 2. Both require distinct unseen PRs and one baseline plus one treatment per pair. Parent rejects duplicates even at new commits and exposed packets. Muse states arms clearly (GitHub+Lens vs GitHub+PRC).
- 2 Immutable evidence, honest readiness: parent 2, Muse 1. Parent seals manifest, hashes, questions, versions, and demands authentic Lens job/run at same head. It forbids vendored-renderer substitution. Muse validates SHAs and refuses key leaks, but claims directory hash equals seal.
- 3 Browser privacy, one-reading state, deadlines: parent 2, Muse 0. Parent enforces one active PR, server-side pending/active/submitted/aborted/timed_out, scoped artifact serve, traversal block, resume, 20-min timer that survives refresh. Static hub ships future pages, allows path peeking, and loses data across origins.
- 4 Existing analysis and missing outcomes: parent 2, Muse 0. Parent keeps legacy 12-pair constants, adds explicit 3-pair protocol, verifies trial IDs and anchors, and keeps unstarted trials unknown. Muse calls analyze unchanged for 2-3 pairs, but analyze rejects len != pair_count. Muse also rejects dropped pairs, so adverse/favorable scenarios cannot run.
- 5 Minimal deps, clear ownership: parent 1, Muse 1. Parent uses stdlib HTTPServer plus vanilla JS with explicit kit vs session ownership. Muse uses one paired.py module, but splits real state to browser storage.

Totals: parent 9/10, Muse 4/10.

Decisive points: static hub leaks by design. Server scope limits each reading to its assigned tree. Hardcoded 12-pair gate needs an explicit sealed protocol, not reuse unchanged. Unknowns must persist for scenario fills.

Graft from Muse: four-verb CLI names, frozen dataclass sketch (PairedKit, HubManifest, SessionCursor, ResponseRecord, BlindedResponse), single-PCG64 draw, forward-only with read-only review, two-pair fixture E2E plus unit list, and pilot-size-sim reuse.

Reality check: no frozen roster exists. No scored run exists. Parent is still prose. Next work must IMPLEMENT the runnable kit, server, export, grade, and analyze path.

GLM addendum (bounded, no full re-analysis): scores 8/10: 1:2 distinct unseen plus exactly one prebuilt arm per PR with provenance; 2:2 seal reuse plus keys-absent with keys_sha256 and serve-failure stays visible; 3:2 server-owned clock, one-trial asset scope, stopped trials never re-serve; 4:1 scaled Protocol plus --pair-count as sole engine change, but complete-pairs grade check risks unknowns; 5:1 stdlib server plus sqlite with single-writer session. Parent server choice stands.

Graft from GLM into parent base: sqlite atomic state with trials/answers tables and restart-safe elapsed; name-to-allowed-file map where /trial/<n>/asset/<name> resolves in memory to the active trial only; keys outside served namespace with digest check; HMAC blinded sheet; Lens serve failure recorded visibly, never silent GitHub fallback.
