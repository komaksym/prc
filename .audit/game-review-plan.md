# Game screen review

## Summary

Add Tuxemon #2370 as one light-mode PRC review. Reuse the existing board schema and renderer.
Show the PR author's labeled before and after images. Do not claim the game was run.
Keep existing reviews unchanged. Keep all work local under START-HERE.md's publication gate.

## Milestones

- [x] Validate the pinned map and both source images.
- [x] Author and check one storyboard with every changed unit in its reading path.
- [x] Generate a baoyu infographic, narrated video and labsheet page.
- [x] Verify links, screen layout, video transitions and narration on the exact outputs.
- [x] Commit the task files and record the local delivery state.

## Local review checkpoint

The page, video and infographic are generated. Exact-output checks cover the screenshot pair,
all nine scenes, code drawers, links, transitions and narration. The current narration check is
`/private/tmp/prc-battle-proof/listen-current.log`. The final handoff checks are collected in
`/private/tmp/prc-battle-proof/handoff-current/`.

The full test suite passes 1126 tests. Source lint and package build pass.
The verification cleanup adds strict test annotations and applies existing Ruff formatting.
The disposable release copy initializes Git so Ruff applies the source checkout's ignore rules.
A regression checks both ignored experiments and real source failures.
Final acceptance uses `bash scripts/verify-release.sh --offline`, including the installed wheel smoke test.
Release evidence is saved under `artifacts/release/verify/`. Publication still requires user approval.

## Throughput checkpoint

- Blocking first steps. Validate selection, pinned revisions and source images before board authoring.
- Independent workstreams. The board owner writes in game-review. The parent handles the infographic outside the checkout.
- Shared mutable state. One writer owns the checkout at a time. Parent integrates after the owner stops.
- Smallest safe decomposition. One board author and one independent visual reviewer. No application architecture changes are needed.

The artifact data shape is the existing board JSON, with scenes, reading entries, receipts and infographic panels.
The source screenshots are evidence, not generated reconstructions.

The earlier #3610 draft was rejected as too modest. #2370 shows separate monster pairs across the battle screen.
Its pinned base is e3317587bcb3a48dae551a52ae3b6022e28e5131.
Its pinned head is 4dc3b4fb0dd61dde22e89e18d1db7215eb929a65.
