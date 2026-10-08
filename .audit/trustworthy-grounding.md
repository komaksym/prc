# Grounding for trustworthy PR explanations

Summary. The public CLI captures a PR, builds inventory and a change map, checks an optional board, then renders local files.
The assessment report at docs/launch/READINESS-2026-10-08.md defines D1 to D17.
The main feature plan is PLANS.md. The parent edits facts, parsing, acquisition errors and map presentation.

Facts path. github_source.py supplies the PR metadata, per-file diff and pinned Git objects.
capture.py records SourceError as capture gaps; pipeline.py can then ask repo_path after acquisition failed.
snapshot.py and inventory.py classify files and count lines. Opaque inputs can be skipped before counting.
brief.py owns test and sensitivity classification. codegraph.py recognizes named functions but misses object-literal callbacks.
changemap.py owns diff-line attribution to parsed symbols. Decorator spans and line ownership must be tested separately.
presentation/card.py currently defines compute_stats. comment.py reuses it. map_assets/map.js recomputes different statistics.
render_map.py serializes ChangeMap into the browser page. Consistent stats need one computed source and one definition per label.

Render path. cli.py dispatches board tools through explainer/boards.py.
check.verify_board checks receipts. render.render_board later fills timing, highlights code, runs join_gate and encodes video.
doc.uncovered marks files or symbols covered when a receipt touches them. It does not prove changed-line coverage.
engine.js renders the board. It can print undefined for missing outro fine and place notes over code.
The installed guide uses prototype commands. The installed skill emits separate Claude and Codex instructions.
The package test installs the wheel offline even though its fresh cache may lack a pinned dependency.

Boundary constraints. Keep existing CLI commands and map schema compatible. New fields may be additive when needed.
Use accurate wording for unsupported parsing and direct-call test evidence. No dependency or language backend is added.
Coverage counts distinct changed lines actually displayed, on the correct base or head side, not touched files.
Board validation and render preflight must agree on accepted inputs. A preview must avoid full video encoding.
The user is the only human reviewer. Do not push, open PRs, change licensing or rename the package.

