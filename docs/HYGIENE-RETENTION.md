# PRC evidence retention policy

Tracked evaluation and review evidence stays available for inspection. A path in `.gitignore`, a local path string, or a `.codex` directory does not by itself justify deletion, establish a secret, or prove that publication is safe. Each category below has a separate purpose and review rule.

## Frozen evaluation packet images

The 243 tracked PNG files under `eval/runs/2026-10-08-release-check/packets/**/*.png` are frozen reader-capture evidence. They match the `eval/runs/*/packets/**/*.png` ignore rule because that rule keeps new or regenerated packet media out of ordinary changes. This curated set is tracked on purpose and stays published as historical evaluation evidence.

The exception applies to this frozen evidence set. Evaluation outputs and private evidence are not generally allowed. A new packet image needs a named evaluation purpose and review before it enters Git.

## Path-bearing text evidence

The retention audit identified 32 tracked text files whose content includes local absolute home paths. These files fall into three review groups: 10 audit and documentation files, 3 documentation evidence files, and 19 evaluation output or record files. A home-path string can disclose environment detail. It is neither a secret-plugin finding nor proof that the content is safe to publish.

Review these files before exposing the repository through a new distribution surface, archive, package, dataset, or history export. Check the surrounding content for credentials, personal data, private repository material, and other disclosure risk. Continue to keep publication decisions separate from Git retention decisions.

## PR review and provenance assets

Three tracked files under `.codex-pr-infographics/source-recovery-r4/` are retained PR review evidence:

- `infographic.png` is the rendered review visual.
- `prompts/infographic.md` records its source prompt.
- `provenance.json` binds the image and prompt to their hashes and purpose.

Keep the three files together. They support PR review and provenance; they are not runtime inputs or a cache. New agent-generated visual assets need a review purpose and provenance. Ephemeral outputs stay ignored and uncommitted, and a PR body uses a GitHub-hosted URL for an attached image.

## Existing cleanups and the hygiene guard

The earlier cleanup removed 24 generated run logs under `eval/runs/2026-10-08-release-check/logs/`. Those files remain in main's prior commit `7d61740108a0635871a3e131e92f92f0b01a85b8`. It kept `docs/mvp/evidence/reconciliation/history/stage6-log.md` as useful Markdown, and the file keeps its current main bytes. Do not restore the logs or remove the Stage 6 Markdown as part of retention work.

Curated evidence stays tracked, including `docs/mvp/evidence`, `docs/media`, the frozen packet set, path-bearing records, and the provenance assets above. Their tracked status is a retention decision; content and publication review still apply.

The release verifier runs `scripts/check-hygiene.sh` against the Git index before building. The guard rejects exact cache directory names, bytecode, root `dist` output, eval run logs, and `.private` directories. Real index tests cover forced additions, names containing newlines, and similarly named Markdown that must remain allowed. See [`.gitignore`](../.gitignore) for the ignore rules.

No tracked deletion or history rewrite follows from an ignore match or a local path string. A deletion needs a content-based retention decision and an explicit task that authorizes it.
