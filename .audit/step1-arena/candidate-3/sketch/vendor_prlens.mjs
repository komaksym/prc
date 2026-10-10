#!/usr/bin/env node
/* Sketch of tools/vendor-prlens.mjs (part B).
 * Maintainer-only. Node runs HERE, never inside prc. Writes a committed,
 * pinned browser bundle and records its hashes in prlens.lock.json.
 */
import { createHash } from "node:crypto"; // TODO: switch to WebCrypto; no reason to keep node:crypto in the tool

// TODO: read src/prc/presentation/map_assets/prlens.lock.json
//   { renderer: "0.3.2", schema: "0.7.0",
//     tarball_sha256: { renderer: "...", schema: "..." },
//     bundle_sha256: "..." }
// TODO: without --update, fail when a fetched version departs from the lock.
// TODO: npm pack --silent @coldtea/pr-lens-renderer@0.3.2 //       @coldtea/pr-lens-schema@0.7.0 into scratch/vendor/; sha256 each
//       tarball; compare with the lock (or write new values with --update).
// TODO: extract tarballs; replace BOTH packages' dist/manifest.js with
//   generated no-op shims (verified by experiment on 2026-10-09):
//     renderer shim: CONTENT_HASH_LENGTH = 32; contentHash, canonicalJson,
//       graphContentHash, renderAssetId, renderAssetFileName, buildManifest
//       as stubs.
//     schema shim: export const RenderAsset = undefined; RenderManifest same.
//   Their consumers only re-export those names; the browser calls none.
// TODO: esbuild bundle (bundled as a pinned vendoring devDependency):
//     entry: src/prc/presentation/map_assets/prlens.entry.mjs
//       import { render } from "@coldtea/pr-lens-renderer";
//       export { render };
//     --bundle --minify --format=iife --global-name=prcLens
//     --outfile=src/prc/presentation/map_assets/prlens.bundle.js
//   measured: about 54 KB minified with renderer only (zod stays out).
// TODO: smoke, exits nonzero on failure: run render() on a committed fixture
//   GraphDoc; require svg.length > 0 and atlas.nodes size == 2.
// TODO: write bundle_sha256 into the lock; print the tarball hashes.
