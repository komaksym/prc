# Skill installation

A user installs PRC's board-writing guidance for Claude or Codex and inspects the resulting files.

## Sub-features

- `install-claude` creates Claude guidance.
- `install-codex` creates Codex guidance.
- `install-rerun` handles existing destinations safely.

## How to get to it (user POV)

Run `prc skill install claude` or `prc skill install codex`.
Use `--dest` for disposable verification destinations.

## Driving it with CLI and Playwright

Preconditions: choose scratch destinations beside `VERIFY_STORE`.

- Run `.venv/bin/python -m prc.cli skill install claude --dest "$(dirname "$VERIFY_STORE")/claude"`.
- Read the printed path and created SKILL.md. Copy guidance into `VERIFY_PROOF/install` before cleanup.
- Run `.venv/bin/python -m prc.cli skill install codex --dest "$(dirname "$VERIFY_STORE")/codex"`.
- Inspect created guidance and preserve command transcripts and copied files.
- For collision and rerun behavior, follow `tests/test_skill.py`. Require unrelated existing text to survive.

## Gotchas

- Default destinations can modify real agent configuration. Always pass `--dest` during verification.
- Global installation requires permission under `START-HERE.md`.
- This installs prc-explain. The verification skill stays in `.agents/skills/verify`.
