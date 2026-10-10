# Step 1 vendor-fixes report (isolated clone /private/tmp/step1-vendor-fixes @ a6b0e62)

## TL;DR

Without --update, scripts/vendor-prlens.mjs now compares the rebuilt bundle sha256 and the recomputed golden hashes against prlens.lock.json before either file is written, and exits with a clear error while leaving both files byte-identical. A test-first regression (tests/test_prlens_vendor.py, 5 tests) recorded red under the old code and green after the fix, and a real no-update re-vendor of the clone reproduced the exact pinned bundle bytes. Tarball version and hash checks continue to pass against the offline inputs.

## Files changed (uncommitted)

- scripts/vendor-prlens.mjs — added the no-update write gate (bundle_sha256 and validated_goldens), merged the duplicate node:fs import, replaced the dead "esbuild" default with an unconditional resolve (modulesDir is always set by then).
- tests/test_prlens_vendor.py — new regression suite driving the real vendor CLI end to end.

## Defect and fix

The script verified tarball hashes when no --update was given, but then rebuilt the bundle and wrote prlens.bundle.js plus prlens.lock.json unconditionally, so a stale or wrong bundle pin was silently overwritten. Now, after the build, smoke, and golden validation, and before any write, the no-update path throws on either a bundle_sha256 mismatch or any validated_goldens mismatch, and the scratch dir is removed first. --update keeps the intentional pin change. Checks are guarded by presence of the respective pin, so a first-time bootstrap (empty lock) still works like the tarball check always did.

## Red/green

- Red (log: /private/tmp/step1-vendor-fixes-red.log): 2 failed, 3 passed. test_revendoring_without_update_rejects_bundle_mismatch and ..._rejects_golden_mismatch failed with returncode 0, proving both files were written despite the tampered pin. The tarball gate and byte-reproduction tests already passed pre-fix.
- Commands: PYTHONDONTWRITEBYTECODE=1 /Users/koval/dev/prc/.venv/bin/pytest tests/test_prlens_vendor.py --noconftest -q (each test builds an isolated repo layout under pytest tmp, then runs node scripts/vendor-prlens.mjs --tarballs /private/tmp/prlens --node-modules /private/tmp/prlens/bundle/node_modules; no network, no clone writes).
- Green (log: /private/tmp/step1-vendor-fixes-green.log): 5 passed — patched-bundle mismatch rejected with both assets untouched, golden mismatch rejected untouched, update mode rewrites the bundle pin, tarball mismatch rejects untouched, and a plain no-update re-vendor is byte-identical.
- Repo neighbors: tests/test_graphdoc.py under the clone tree — 12 passed (read-only guard of pin/golden equality). The parent checkout was never written.

## Real no-update rebuild (log: /private/tmp/step1-vendor-fixes-revendor.log)

- Command: node scripts/vendor-prlens.mjs --tarballs /private/tmp/prlens --node-modules /private/tmp/prlens/bundle/node_modules in the clone.
- All 5 goldens passed safeParseGraphDoc from the pinned schema (VALID lines), smoke passed (SMOKE w=436 h=180), and the CLI exited 0.
- sha256 before == after for prlens.bundle.js (036f2ae251209bf7649b09afcd6d8ac4ace457d2b6023ad9fa4ab83d6f1f80b4) and prlens.lock.json (1d2c39e45da78bbd3780f59d37fa2625f9bf89c0e0681d14dedd06e38709fc10). git status shows only scripts/vendor-prlens.mjs and tests/test_prlens_vendor.py.
- Version/hash checks: the extracted packages report 0.3.2 and 0.7.0 from package.json, esbuild 0.25.10 and zod 4.6.5 from /private/tmp/prlens/bundle/node_modules, matching the lock pins.

## Exact pin evidence

- shasum -a 256 /private/tmp/prlens/*.tgz: renderer c6c7ca978643392574cde90bddaf3031a3bb3d7cf664f86b8a8819e1731638a1, schema 540133ec9b8196a10bb578fe8692e17641dd84161fc3b47800fc207ff523e8b5 — equal to the lock's tarball_sha256 for 0.3.2 / 0.7.0.
- All five lock.validated_goldens hashes recomputed from tests/data/graphdoc today: em-5756, grouped, librarysync-98, shop, swarm-116 — all OK; bundle_sha256 recomputed from the committed bundle — OK.

## Manifest shim review (pinned upstream)

- Upstream renderer dist/index.js re-exports exactly seven manifest names: CONTENT_HASH_LENGTH, contentHash, canonicalJson, graphContentHash, renderAssetId, renderAssetFileName, buildManifest; dist/render.js imports those helpers from ./manifest.js and render.js itself uses no node:crypto. The shim covers all seven, so the bundle graph is closed.
- Upstream schema dist/index.js re-exports exactly RenderAsset and RenderManifest from ./manifest.js; the shim provides both. Nothing else in the schema surface is stubbed.
- Why the browser does not need the integrity APIs: the manifest chain exists to name and persist render assets by content hash on surfaces that publish them (GitHub action writing files, hosted app uploading). The PRC page calls prcLens.render(doc, {lens, theme}) and consumes out.svg (inlined as a data URL) and out.atlas (hit targets); it never writes or addresses render assets, so contentHash/graphContentHash/renderAssetId/buildManifest are unused by design on that surface and stubbed to drop node:crypto from a browser bundle.
- Why the shims do not weaken graph-schema validation: golden validation runs before the shim files are written (the validate.mjs step precedes both writeFileSync calls), so safeParseGraphDoc from the pinned zod schema validates the real upstream code. The schema shim only replaces the renderer-asset inventory schemas (RenderAsset/RenderManifest), not graph validation; render.js imports only assertNever and MAX_RENDER_ASSETS from the schema, which stay real. The page contract stays checked in Python at build time by validate_contract, and this change adds the missing no-update gate that keeps lock.validated_goldens honest.

## Slop removed

- Merged the second import { rmSync } from "node:fs" line into the existing node:fs import.
- Removed the always-true if (modulesDir) around the esbuild resolve and the dead "esbuild" fallback default; modulesDir is set unconditionally before that point (npm install fills it when --node-modules is absent).

## Logs saved

- /private/tmp/step1-vendor-fixes-red.log
- /private/tmp/step1-vendor-fixes-green.log
- /private/tmp/step1-vendor-fixes-revendor.log
- /private/tmp/step1-vendor-fixes-baseline-sha.log
- /private/tmp/step1-vendor-fixes.patch
