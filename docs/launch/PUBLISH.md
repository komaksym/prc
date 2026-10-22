# Publishing prc: the operator checklist

Public writes require your explicit approval under decision D21.
This checklist targets the existing [komaksym/prc](https://github.com/komaksym/prc) repository. Read-only checks and local preparation can run before approval.

1. **Check for private content.** Before any push:
   - `reports/` holds internal research and measurements. Keep it out, or
     review each file.
   - `prototypes/` is ignored by git, but check the working tree and the git
     history for anything copied out of it.
   - `eval/runs/` contains captured PR code and authored explanations.
     Review the captured content and media before publication. The
     [evidence retention policy](../HYGIENE-RETENTION.md) records which media is
     tracked and which new outputs are ignored. An ignore match does not hide
     edits to tracked files.
   - Run `git log --stat` over the full history and look for tokens, emails
     and private paths.
2. **Add a license.** You choose. MIT or Apache-2.0 fit a tool like this.
   Add the file and a `License` line in `README.md`.
3. **Use the existing repository.** Confirm that `git remote -v` has an `origin`
   that identifies the `komaksym/prc` repository and that `main` is the default
   branch. Publish approved work through a pull request against `origin/main`.
4. **Publish to PyPI.** Build the wheel, check the metadata, then
   `uv publish` (or `twine upload`). You need a PyPI token.
5. **Merge through the approved pull request flow.** Add README media only after
   its public URL resolves.
   The local example frame is `docs/media/explain-pr12-diff.png`.
6. **Post the promo.** The thread draft is `docs/launch/TWEET.md`; the cut
   video is `docs/launch/promo.mp4`.

## What is already checked

- `artifacts/release/privacy.json` records a regex scan of all local Git history blobs.
  No matched credential patterns or private path names were found. This does not replace manual content review.
- The wheel builds (`uv build`).
- `prc doctor` reports each dependency, its state and its install command.
- A clean install from the wheel works (Stage 7 recorded in `docs/mvp/LOG.md`).
- `eval/runs/2026-10-06-full/scoreboard.md` holds the release numbers.
