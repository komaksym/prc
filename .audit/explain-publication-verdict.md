TL;DR: Use candidate A, staged directory publication with rollback and a short commit lock. Candidate B violates the required filesystem layout.

This verdict reviews the full `explain-publication-design.md` against the user's six criteria.
The scores assess proposed designs, not tested implementations. No product code changes belong to this review.

Scores use 2 for satisfies, 1 for partial, and 0 for fails. Criterion 1 is a compatibility gate.

| Criterion | Candidate A | Candidate B |
| --- | --- | --- |
| 1. No public API or path layout changes | **2.** Keeps signatures, result fields, public filenames, lexical paths, and real directories. Private siblings support publication. | **0.** Keeps lexical paths and signatures, but replaces the public directory with a symlink. Adds a generation store. Existing directories require refusal or migration. |
| 2. Keeps prior artifact on handled render failures | **2.** Rendering touches staging only. A handled render failure leaves the previous public directory and bytes untouched. | **2.** Rendering touches a new generation only. A handled render failure leaves the previous pointer and bytes untouched. |
| 3. Boardless success has no stale media | **2.** Publishes a fresh directory with this invocation's files only. No media deletion list is needed. | **2.** Selects a fresh generation with no board media. Historical media remains outside the selected public artifact. |
| 4. No dependencies | **2.** Uses standard-library filesystem tools. | **2.** Uses standard-library tools, including `os`. |
| 5. Minimal code and reader load | **2.** Redirects writes and adds one private publisher. Lock and rollback handling remain necessary complexity. | **1.** Adds pointer publication, generation retention, and a legacy-output policy. Safe migration also needs A's protocol. |
| 6. Rollback recovery bytes | **2.** Moves the previous directory without changing its bytes. A failed restoration retains the backup and reports its path. | **2.** Retains previous immutable generations. Failed pointer replacement needs no rollback. Safe legacy refusal also preserves bytes. |
| Total | **12/12** | **9/12** |

Candidate A wins on compatibility and scope. Candidate B has stronger steady-state publication semantics, but fails the compatibility gate.
The total does not establish that A is safer under process death.
Criterion 6 measures retained recovery bytes, not uninterrupted access through the public path.

Keep whole-artifact membership and separate staging paths from public result paths in the implementation.
Prepare the result before commit. Serialize public paths into metadata. Remove partial staged card images after nonfatal `CardError`.
The short lock must cover both renames and any rollback. Never steal an occupied lock automatically.
Reject public symlinks and unexpected files before moving the previous artifact.

A has a documented crash gap between moving the old directory and publishing staging.
Readers can see a missing public directory during that interval.
A killed process can leave the old artifact in `previous` and leave the commit lock occupied.
A failed restoration must preserve that backup, identify its path, and report both errors.
Recovery requires explicit inspection and restoration before lock removal. Do not promise automatic recovery or power-loss durability.
Document this behavior as "staged publication with rollback". Do not call the two-renames protocol atomic.

Cleanup must distinguish commit state. Before commit, remove only this invocation's staging and disposable empty containers.
Never delete a recovery backup after restoration fails.
After commit, backup or lock cleanup failures must warn without reporting publication failure or contaminating JSON stdout.
A retained lock can block later reruns even after successful publication. Report that cleanup condition clearly.
Candidate B retains old generations indefinitely under this proposal. It needs a separate retention policy before automatic cleanup.
B's pointer switch does not provide a snapshot across separate file opens. Its legacy conversion shares A's crash gap.

The parent should test prior filename and SHA-256 inventories after handled failures and successful boardless replacement.
Inject second-rename and restoration failures separately. Check preserved bytes, reported recovery paths, and occupied-lock refusal.
Check post-commit cleanup failure as successful publication with a warning. Check that metadata contains no private paths.
Product validation remains with the parent. This verdict does not claim lint, typecheck, tests, build, or GUI verification passed.

The available design record contains two sequential passes from one author.
The separate second-model attempt stopped without returning an artifact. It supplies no independent candidate evidence.
This review independently compares the two documented proposals. It does not treat them as two completed model submissions.

No further user decision is needed under the stated rubric. The parent can implement A within the documented failure guarantee.
