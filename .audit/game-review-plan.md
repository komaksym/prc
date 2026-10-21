# Game screen review

## Summary

Add Tuxemon #2370 as one light-mode PRC review. Reuse the existing board schema and renderer.
Show the PR author's labeled before and after images. Do not claim the game was run.
Keep existing reviews unchanged. Keep all work local under START-HERE.md's publication gate.

## Milestones

- [x] Validate the pinned map and both source images.
- [x] Author and check one storyboard with every changed unit in its reading path.
- [ ] Generate a baoyu infographic, narrated video and labsheet page.
- [ ] Verify links, screen layout, video transitions and narration on the exact outputs.
- [ ] Commit the task files and record the local delivery state.

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
