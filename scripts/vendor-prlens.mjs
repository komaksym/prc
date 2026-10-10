#!/usr/bin/env node
// Node runs only during vendoring; the generated page must run offline.
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, readFileSync, symlinkSync, writeFileSync } from "node:fs";
import { rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ASSETS = join(ROOT, "src", "prc", "presentation", "map_assets");
const GOLDENS = join(ROOT, "tests", "data", "graphdoc");
const LOCK_PATH = join(ASSETS, "prlens.lock.json");
const BUNDLE_PATH = join(ASSETS, "prlens.bundle.js");
const RENDERER_PIN = "0.3.2";
const SCHEMA_PIN = "0.7.0";
const ZOD_PIN = "4.6.5";
const ESBUILD_PIN = "0.25.10";
const BUNDLE_BYTES_MAX = 100 * 1024;

const RENDERER_MANIFEST_SHIM = [
  "export const CONTENT_HASH_LENGTH = 32;",
  "export const contentHash = () => '';",
  "export const canonicalJson = (v) => JSON.stringify(v);",
  "export const graphContentHash = () => '';",
  "export const renderAssetId = () => '';",
  "export const renderAssetFileName = () => '';",
  "export const buildManifest = () => ({});",
  "",
].join("\n");

const SCHEMA_MANIFEST_SHIM = [
  "export const RenderAsset = undefined;",
  "export const RenderManifest = undefined;",
  "",
].join("\n");

function arg(name) {
  const i = process.argv.indexOf(name);
  return i === -1 ? null : process.argv[i + 1];
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function pkgVersion(dir, name) {
  const raw = readFileSync(join(dir, name, "package.json"), "utf8");
  return JSON.parse(raw).version;
}

function main() {
  const tarballsDir = arg("--tarballs");
  let modulesDir = arg("--node-modules");
  const update = process.argv.includes("--update");
  const scratch = mkdtempSync(join(tmpdir(), "prlens-vendor-"));
  const npmEnv = { ...process.env, npm_config_cache: join(scratch, "npm-cache") };
  const scope = join(scratch, "node_modules", "@coldtea");
  const rendererDir = join(scope, "pr-lens-renderer");
  const schemaDir = join(scope, "pr-lens-schema");
  let rendererTgz;
  let schemaTgz;
  if (tarballsDir) {
    rendererTgz = join(tarballsDir, "coldtea-pr-lens-renderer-" + RENDERER_PIN + ".tgz");
    schemaTgz = join(tarballsDir, "coldtea-pr-lens-schema-" + SCHEMA_PIN + ".tgz");
  } else {
    const out = execFileSync(
      "npm",
      ["pack", "@coldtea/pr-lens-renderer@" + RENDERER_PIN, "@coldtea/pr-lens-schema@" + SCHEMA_PIN],
      { cwd: scratch, encoding: "utf8", env: npmEnv },
    );
    const names = out.trim().split(/\s+/);
    rendererTgz = join(scratch, names.find((n) => n.includes("renderer")));
    schemaTgz = join(scratch, names.find((n) => n.includes("schema")));
  }
  if (!existsSync(rendererTgz) || !existsSync(schemaTgz)) {
    throw new Error("missing tarballs: " + rendererTgz + " " + schemaTgz);
  }
  const tarballSha = { renderer: sha256(rendererTgz), schema: sha256(schemaTgz) };
  let lock = {};
  if (existsSync(LOCK_PATH)) {
    lock = JSON.parse(readFileSync(LOCK_PATH, "utf8"));
  }
  const pinned = lock.tarball_sha256;
  if (pinned && !update) {
    if (pinned.renderer !== tarballSha.renderer || pinned.schema !== tarballSha.schema) {
      throw new Error("tarball hash mismatch against prlens.lock.json; rerun with --update");
    }
  }
  if (!modulesDir) {
    execFileSync("npm", ["install", "--prefix", scratch, "--no-save", "--no-audit", "--no-fund",
      "esbuild@" + ESBUILD_PIN, "zod@" + ZOD_PIN], { cwd: scratch, env: npmEnv, stdio: "inherit" });
    modulesDir = join(scratch, "node_modules");
  }
  for (const [name, pin] of [["esbuild", ESBUILD_PIN], ["zod", ZOD_PIN]]) {
    if (pkgVersion(modulesDir, name) !== pin) throw new Error("unpinned dependency: " + name);
  }
  execFileSync("mkdir", ["-p", rendererDir, schemaDir]);
  if (modulesDir !== join(scratch, "node_modules")) {
    symlinkSync(join(resolve(modulesDir), "zod"), join(scratch, "node_modules", "zod"));
  }
  execFileSync("tar", ["-xzf", rendererTgz, "-C", rendererDir, "--strip-components=1"]);
  execFileSync("tar", ["-xzf", schemaTgz, "-C", schemaDir, "--strip-components=1"]);
  const rendererVersion = JSON.parse(readFileSync(join(rendererDir, "package.json"), "utf8")).version;
  const schemaVersion = JSON.parse(readFileSync(join(schemaDir, "package.json"), "utf8")).version;
  if (rendererVersion !== RENDERER_PIN || schemaVersion !== SCHEMA_PIN) {
    throw new Error("unpinned package: " + rendererVersion + " / " + schemaVersion);
  }
  let esbuildModule = "esbuild";
  if (modulesDir) {
    esbuildModule = createRequire(import.meta.url).resolve("esbuild", { paths: [modulesDir] });
  }
  const { buildSync } = createRequire(import.meta.url)(esbuildModule);
  const goldens = readdirSync(GOLDENS).filter((n) => n.endsWith(".json")).sort();
  if (!goldens.length) {
    throw new Error("no goldens in " + GOLDENS);
  }
  const validateFile = join(scratch, "validate.mjs");
  writeFileSync(
    validateFile,
    "import { safeParseGraphDoc } from '@coldtea/pr-lens-schema';\n" +
      "import { readFileSync } from 'node:fs';\n" +
      "const [goldensDir, ...names] = process.argv.slice(2);\n" +
      "for (const name of names) {\n" +
      "  const doc = JSON.parse(readFileSync(goldensDir + '/' + name, 'utf8'));\n" +
      "  const parsed = safeParseGraphDoc(doc);\n" +
      "  if (!parsed.ok) {\n" +
      "    console.error('INVALID ' + name + ' ' + JSON.stringify(parsed.error.issues).slice(0, 2000));\n" +
      "    process.exitCode = 1;\n" +
      "  } else {\n" +
      "    console.log('VALID ' + name);\n" +
      "  }\n" +
      "}\n",
  );
  execFileSync("node", [validateFile, GOLDENS, ...goldens], {
    cwd: scratch,
    stdio: "inherit",
    env: { ...process.env, NODE_PATH: join(scratch, "node_modules") },
  });
  writeFileSync(join(rendererDir, "dist", "manifest.js"), RENDERER_MANIFEST_SHIM);
  writeFileSync(join(schemaDir, "dist", "manifest.js"), SCHEMA_MANIFEST_SHIM);
  const entry = join(scratch, "entry.mjs");
  writeFileSync(entry, "import { render } from '@coldtea/pr-lens-renderer';\nexport { render };\n");
  const rawBundle = join(scratch, "raw.bundle.js");
  buildSync({
    entryPoints: [entry],
    bundle: true,
    minify: true,
    format: "iife",
    globalName: "prcLens",
    outfile: rawBundle,
    logLevel: "warning",
    nodePaths: [join(scratch, "node_modules")],
  });
  let code = readFileSync(rawBundle, "utf8");
  if (/zod/i.test(code)) {
    throw new Error("bundle contains zod; expected renderer only");
  }
  if (code.includes("node:crypto")) {
    throw new Error("bundle contains node:crypto");
  }
  const license = readFileSync(join(rendererDir, "LICENSE"), "utf8").trim();
  const header = "/*! @coldtea/pr-lens-renderer " + RENDERER_PIN + " MIT\n" + license + "\n*/\n";
  code = header + code;
  if (Buffer.byteLength(code) > BUNDLE_BYTES_MAX) {
    throw new Error("bundle exceeds 100 KB: " + Buffer.byteLength(code));
  }
  const smoke = join(scratch, "smoke.js");
  writeFileSync(
    smoke,
    code +
      "\n;const doc = { schemaVersion: '0.2.0', kind: 'graph', title: 'smoke'," +
      " lenses: ['architecture']," +
      " provenance: { repo: { owner: 'o', name: 'n' }, base: { sha: 'a'.repeat(40) }, head: { sha: 'b'.repeat(40) } }," +
      " lanes: [{ id: 'code', label: 'Changed code' }]," +
      " nodes: [{ id: 's0', label: 'checkout', kind: 'function', delta: 'modified', lane: 'code'," +
      " files: [{ path: 'shop/cart.py', startLine: 1, endLine: 4, revision: 'head' }], badges: [] }]," +
      " edges: [], flows: [], views: [], walkthrough: { steps: [" +
      " { id: 'w0', heading: 'What changed', body: 'Two files changed.', focus: { kind: 'all' } }," +
      " { id: 'w1', heading: 'checkout', body: 'Changed.', focus: { kind: 'selection', nodes: ['s0'] } }] } };" +
      "\nconst out = prcLens.render(doc, { lens: 'architecture', theme: 'dark' });" +
      "\nif (!out || typeof out.svg !== 'string' || !out.svg.length) throw new Error('no svg');" +
      "\nif (!out.atlas || !out.atlas.nodes || !out.atlas.nodes.s0) throw new Error('no atlas node');" +
      "\nif (out.animated !== false) throw new Error('unexpected animation');" +
      "\nconsole.log('SMOKE w=' + out.width + ' h=' + out.height + ' svg=' + out.svg.length);\n",
  );
  execFileSync("node", [smoke], { stdio: "inherit" });
  const bundleSha = createHash("sha256").update(code).digest("hex");
  const validated = {};
  for (const name of goldens) {
    validated[name] = sha256(join(GOLDENS, name));
  }
  const modulesForVersions = modulesDir || join(scratch, "node_modules");
  const next = {
    bundle_sha256: bundleSha,
    esbuild: pkgVersion(modulesForVersions, "esbuild"),
    renderer: RENDERER_PIN,
    schema: SCHEMA_PIN,
    tarball_sha256: tarballSha,
    validated_goldens: validated,
    zod: pkgVersion(modulesForVersions, "zod"),
  };
  writeFileSync(BUNDLE_PATH, code);
  writeFileSync(LOCK_PATH, JSON.stringify(next, null, 2) + "\n");
  rmSync(scratch, { recursive: true, force: true });
  console.log("vendored " + BUNDLE_PATH + " (" + Buffer.byteLength(code) + " bytes)");

}

main();
