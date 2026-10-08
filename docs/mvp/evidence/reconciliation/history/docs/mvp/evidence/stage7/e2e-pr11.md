# Stage 7 skill-driven E2E: PR 11, 2026-10-06

A fresh run through the installed skill text only (`skills/prc-explain/SKILL.md`
from `prc skill install claude --dest`, bundled in the worktree wheel rebuilt
after 7097762). No repo access: clean folder `/tmp/stage7-e2e/work`, the
`prc` binary from the clean-install venv (`/tmp/stage7-clean2/.venv`),
GITHUB_TOKEN unset.

## Wall time: 8m12s (13:20:41 - 13:28:53 CEST)

- skill install + `prc doctor` (all ok, say backend): ~1 min
- step 1 `prc explain --source .../pull/11`: live acquisition worked with no
  token; head 306ff5a26ca6 matches the stored map's head, so no `--map` needed
- step 2 `prc board guide`: read, shaped 6 scenes (title, groups, groups,
  diff, list, outro), 45-75 s target
- step 3 `board show` (full + path-filtered) and `board find "created_at"`:
  the PR is a 1-line collector projection change (`created_at` added to the
  prospects `TABLE_COLUMNS`) plus a 177-line synthetic E2E, evidence JSON,
  docs and infographic inputs
- step 4 wrote `board.json` (before/after prospect-row pictures grounded on
  the removed/added projection line; diff scene of lines 18-20; list of 3
  evidence receipts; outro handing off to `TABLE_COLUMNS`)
- step 5 `prc board check`: **passed on the first try, 16 receipts verified**
- step 6 `prc board coverage`: files 2/12, code symbols 3/6. Left out: docs
  (PLANS.md, README, infographic prompts), `e2e-evidence.json`, and the
  negative-case machinery (`entry main`, `callee exercise`,
  `exercise.database`). Told the user exactly that.
- step 7 `prc explain --source ... --board board.json --voice say
  --out <absolute>`: 1m22s render, 52.81 s video vs 46.57 s predicted
  (13% over, inside the skill's ~15% voice note), `check_passed: true`
- step 8 stills at 800 px: every scene type appears and reads cleanly;
  `layout_warnings` empty. Two timing notes, both already in the skill:
  the t=0 still is blank (title fades in) and the diff step fires 10% into
  sentence 2, so a still at the sentence start still shows old code; a still
  2 s later shows the red/green step. No board fix needed.
- step 9 outputs in `out/komaksym-linkedin-mdp-11-306ff5a26ca6/`: `map.json`
  (100 KB), `map.html`, `board.json`, `video.mp4` (2.7 MB, 1920x1080, 30 fps,
  52.8 s), `run.json`. prc posted nothing.

## Skill defects found

None blocking. The run confirmed the three 7097762 fixes (absolute `--out`,
blank t=0, voice duration tolerance) instead of adding new ones.
