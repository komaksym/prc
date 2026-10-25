# Contributing

Thanks for helping improve prc. The project explains pull requests through
local maps, videos, walkthroughs, cards, and comment drafts.

## Set up

prc requires Python 3.12 or later, Git, and
[uv](https://docs.astral.sh/uv/).

1. Fork the repository and clone your fork.
2. Create a branch: `git switch -c feat/your-feature`.
3. Install the development environment:

   ```sh
   uv sync --extra video
   uv run playwright install chromium
   ```

Video rendering also needs `ffmpeg` and `ffprobe` on `PATH`. Run
`uv run prc doctor` to check the local toolchain.

## Before opening a pull request

- Add or update tests for changed behavior.
- Update user-facing and developer-facing documentation when behavior changes.
- Keep generated output out of commits unless it is deliberate test or release
  evidence.
- Run the narrowest relevant test during development.
- Run the repository checks before you ask for review:

  ```sh
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy
  uv run pytest
  ```

For release-sensitive changes, run the complete gate:

```sh
bash scripts/verify-release.sh
```

The pull request template asks for the command, result, evidence path, and
limitations. Do not describe an older run as proof for the current commit.

## Issues and labels

Use the issue forms for bugs, feature requests, and questions. Apply a
`P0`–`P3` priority when you can judge urgency, and add one or more
`area:` labels. Readers use the labels to triage work, so keep them accurate.

## Commit style

Use Conventional Commits with the smallest accurate scope:

```
feat(map): show directly linked tests
fix(render): keep the prior successful folder on failure
docs(contributing): add the release verification command
```

Common types are `feat`, `fix`, `refactor`, `perf`, `test`, `docs`,
`build`, `ci`, and `chore`.

## Code style

Follow the configuration in `pyproject.toml`. Keep UI, domain logic, and data
access separate. Prefer the existing module boundaries and naming patterns.

## Security

Do not open a public issue for a suspected vulnerability. Follow
[SECURITY.md](SECURITY.md). Never commit credentials, tokens, private
repository data, or proprietary source.
