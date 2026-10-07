# Publishing prc: the operator checklist

Public writes require your explicit approval under decision D21.
Read-only checks and local preparation can run before approval.

1. **Check for private content.** Before any push:
   - `reports/` holds internal research and measurements. Keep it out, or
     review each file.
   - `prototypes/` is ignored by git, but check the working tree and the git
     history for anything copied out of it.
   - `eval/runs/` contains captured PR code and authored explanations.
     GitHub reports `komaksym/linkedin-mdp` as public on 2026-10-07.
     Review the captured content and media before publication. Media is ignored per `.gitignore`.
   - Run `git log --stat` over the full history and look for tokens, emails
     and private paths.
2. **Add a license.** You choose. MIT or Apache-2.0 fit a tool like this.
   Add the file and a `License` line in `README.md`.
3. **Choose the repo name.** It is your account. Suggested: `prc` or
   `prc-explain`.
4. **Publish to PyPI.** Build the wheel, check the metadata, then
   `uv publish` (or `twine upload`). You need a PyPI token.
5. **Push the repo.** `git push` to the approved new origin.
   Add README media only after its public URL resolves.
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
