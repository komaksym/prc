import { render } from "./prlens-esm.mjs";
const doc = {
  schemaVersion: "0.2.0", kind: "graph",
  title: "PRC test", lenses: ["architecture"],
  provenance: { repo: { owner: "o", name: "n", host: "github.com" }, base: { sha: "0".repeat(40) }, head: { sha: "1".repeat(40) } },
  lanes: [ { id: "code", label: "Changed code" } ],
  nodes: [
    { id: "s0", label: "checkout", kind: "function", delta: "modified", lane: "code", badges: [], files: [{ path: "shop/cart.py", startLine: 1, endLine: 10, revision: "head" }] },
    { id: "s1", label: "apply_discount", kind: "function", delta: "added", lane: "code", subtitle: "called by checkout", badges: ["+18", "no direct test"], files: [{ path: "shop/cart.py", startLine: 11, endLine: 28, revision: "head" }] },
  ],
  edges: [ { id: "e0", from: "s0", to: "s1", kind: "call", delta: "added", emphasis: "hero", animated: false, files: [{ path: "shop/cart.py", startLine: 12, endLine: 12, revision: "head" }] } ],
  flows: [], views: [],
  walkthrough: { steps: [
    { id: "w0", heading: "What changed", body: "checkout now discounts orders.", focus: { kind: "all" } },
    { id: "w1", heading: "apply_discount", body: "New function called by checkout.", focus: { kind: "selection", lanes: ["code"], nodes: ["s1"], edges: [], flows: [] } },
  ] },
};
const out = render(doc, { lens: "architecture", theme: "dark" });
console.log("w", out.width, "h", out.height, "animated", out.animated);
console.log("atlas nodes", JSON.stringify(out.atlas.nodes));
console.log("atlas lanes", JSON.stringify(out.atlas.lanes));
console.log("atlas edges", JSON.stringify(out.atlas.edges));
console.log("svg bytes", out.svg.length, "smil", out.svg.includes("<animate"), "starts", out.svg.slice(0, 60));
