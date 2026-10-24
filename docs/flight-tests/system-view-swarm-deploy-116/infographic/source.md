# Source: System View flight test report (2026-10-25)

The System View flight test on swarm-deploy#116 is done and is in draft PR #11. It explains the PR as named parts of the system, with no code on screen, in the same look as the game review. The release check passed on the final commit (48d3c40): 1129 tests, the build and a run of the built package. One gap is open: prc explain still exits with code 2 on this PR, because the step that makes the summary picture rejects a System View.

What you can watch: an 81-second narrated video and the matching page. Six scenes: title, the parts before the change, the parts after, a walk through the new error path, the tests the PR adds, and a close. Each part is a box: gitops/git, compose loader, init job check, shared/faults and compose errors. Every box and caption links to its exact line on GitHub.

How the layout was picked: three agents each drafted a different layout: a parts map with a walk-through, a sequence of runtime steps, and an operator's journey. A judge agent picked the parts map. Rule kept from the operator's journey: draw no arrow whose connection happens outside the PR's changes.

Gaps: the summary picture step rejects a System View; Go PRs show 0 tests added; arrows can only be straight lines.

Walk scene arrow: Load returns one type (compose loader to compose errors).
