(() => {
  "use strict";

  const MAP = JSON.parse(document.getElementById("map-data").textContent);
  const SVGNS = "http://www.w3.org/2000/svg";
  const STATUSES = new Set(["added", "modified", "deleted", "context"]);
  const EDGE_STATUSES = new Set(["added", "removed", "kept"]);
  const GLYPH = { function: "f", method: "m", class: "C" };
  const PILL = { added: "new", modified: "modified", deleted: "deleted" };
  const LANE_LABEL = {
    files: "Other changed files",
    callers: "Callers",
    changed: "Changed code",
    callees: "Callees",
    tests: "Tests",
  };
  const MINUS = "\u2212";
  const DOT = " \u00b7 ";
  const STEP_SECONDS = { overview: 4, risky_file: 3.4, entry: 3.8, callee: 3.4, test: 3.2, summary: 4.6 };
  const MAX_TOUR = 60;
  const MIN_STEP = 1.6;
  const MOVE = 1.0;
  const DIM_NODE = 0.13;
  const DIM_EDGE = 0.05;
  const BEHIND_SUMMARY = 0.35;
  const LEGIBLE = 0.55;
  const NO_TEST = "no direct test";
  const GITHUB_PR = /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/[0-9]+$/;

  const $ = (id) => document.getElementById(id);
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  const status = (s) => (STATUSES.has(s) ? s : "context");
  const edgeStatus = (s) => (EDGE_STATUSES.has(s) ? s : "kept");
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const basename = (path) => path.slice(path.lastIndexOf("/") + 1) || path;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function add(parent, ...children) {
    for (const child of children) if (child) parent.appendChild(child);
    return parent;
  }

  function svg(tag, cls) {
    const node = document.createElementNS(SVGNS, tag);
    if (cls) node.setAttribute("class", cls);
    return node;
  }

  /* Model */

  const nodes = [];
  const symbolNode = new Map();
  const fileNode = new Map();
  const fileByPath = new Map(MAP.files.map((f) => [f.path, f]));
  const briefFile = new Map(MAP.brief.files.map((f) => [f.path, f]));

  MAP.symbols.forEach((sym, i) => {
    const box = LAYOUT.symbols[i];
    if (!box || symbolNode.has(sym.id)) return;
    const node = {
      key: `s${i}`, kind: "symbol", sym, status: status(sym.status), name: sym.qualname,
      path: sym.path, lane: box[0], x: box[1], y: box[2], w: box[3], h: box[4],
      out: [], in: [], near: new Set(),
    };
    nodes.push(node);
    symbolNode.set(sym.id, node);
  });

  MAP.files.forEach((file, i) => {
    const box = LAYOUT.files[i];
    if (!box || fileNode.has(file.path)) return;
    const node = {
      key: `f${i}`, kind: "file", file, status: file.status === "modified" ? "modified" : status(file.status),
      name: basename(file.path), path: file.path, lane: box[0], x: box[1], y: box[2], w: box[3], h: box[4],
      out: [], in: [], near: new Set(),
    };
    nodes.push(node);
    fileNode.set(file.path, node);
  });

  const edges = [];

  MAP.edges.forEach((edge, i) => {
    const src = symbolNode.get(edge.source);
    const dst = symbolNode.get(edge.target);
    const route = LAYOUT.edges[i];
    if (!src || !dst || typeof route !== "string") return;
    const item = { key: `e${i}`, src, dst, route, status: edgeStatus(edge.status), byName: edge.resolution === "name" };
    edges.push(item);
    src.out.push(item);
    dst.in.push(item);
    src.near.add(dst);
    dst.near.add(src);
  });

  const isTest = (node) => node.lane === "tests";
  const live = (edge) => edge.status !== "removed";

  for (const node of nodes) {
    node.untested =
      node.lane === "changed" && node.status !== "deleted" && !node.in.some((e) => isTest(e.src) && live(e));
  }

  const changed = nodes.filter((n) => n.kind === "symbol" && n.status !== "context");
  const changedCode = changed.filter((n) => n.lane === "changed");
  const testsTouched = changed.filter(isTest);
  const untested = changedCode.filter((n) => n.untested);
  const callSites = changedCode.reduce((sum, n) => sum + (n.sym.call_sites || 0), 0);
  const added = edges.filter((e) => e.status === "added").length;
  const removed = edges.filter((e) => e.status === "removed").length;
  const risky = MAP.brief.files.filter((f) => f.sensitive);

  function ciState() {
    const checks = MAP.brief.checks;
    const failed = checks.filter((c) => c.state === "failed");
    if (!checks.length) return { cls: "none", label: "no CI", word: "none" };
    if (failed.length) return { cls: "bad", label: "CI failed", word: "failed", failed };
    if (checks.some((c) => c.state === "pending")) return { cls: "warn", label: "CI pending", word: "pending" };
    return { cls: "good", label: "CI passed", word: "passed" };
  }

  const ci = ciState();

  /* Header */

  document.title = `${MAP.title} \u00b7 PR map`;
  $("title").textContent = MAP.title;

  (() => {
    const meta = $("meta");
    const sep = () => el("span", "sep", "\u00b7");
    add(meta, sep(), el("span", "", MAP.pr), sep(), el("span", "", `by ${MAP.author}`), sep(),
      el("span", "mono", `${MAP.base_sha.slice(0, 7)} \u2192 ${MAP.head_sha.slice(0, 7)}`));
    if (typeof MAP.url === "string" && GITHUB_PR.test(MAP.url)) {
      const link = el("a", "", "Open on GitHub");
      link.setAttribute("href", MAP.url);
      link.setAttribute("rel", "noopener noreferrer");
      link.setAttribute("target", "_blank");
      add(meta, sep(), link);
    }

    const stats = $("stats");
    const stat = (value, label, cls, dot) => {
      const box = el("div", `stat ${cls || ""}`);
      const val = el("div", "stat-value");
      if (dot) val.appendChild(el("span", "dot"));
      val.appendChild(el("span", "", value));
      return add(box, val, el("div", "stat-label", label));
    };
    add(stats,
      stat(MAP.files.length, MAP.files.length === 1 ? "file" : "files"),
      stat(changed.length, changed.length === 1 ? "symbol changed" : "symbols changed"),
      stat(callSites, "call sites affected"),
      stat(testsTouched.length, testsTouched.length === 1 ? "test touched" : "tests touched",
        testsTouched.length ? "" : "warn"),
      stat(ci.word, "CI on head", ci.cls, true),
      stat(risky.length, risky.length === 1 ? "risky surface" : "risky surfaces", risky.length ? "warn" : ""));
  })();

  /* Canvas */

  const viewport = $("viewport");
  const world = $("world");
  world.style.width = `${LAYOUT.w}px`;
  world.style.height = `${LAYOUT.h}px`;

  if (LAYOUT.dense) world.classList.add("dense");

  for (const band of LAYOUT.bands) {
    const box = el("div", "band");
    box.style.left = `${band[1]}px`;
    box.style.top = `${band[2]}px`;
    box.style.width = `${band[3]}px`;
    box.style.height = `${band[4]}px`;
    box.appendChild(el("div", "band-label", LANE_LABEL[band[0]] || ""));
    world.appendChild(box);
  }

  for (const group of LAYOUT.groups) {
    const sym = MAP.symbols[group[5]];
    if (!sym) continue;
    const label = add(el("div", "group"), el("span", "", sym.path));
    label.style.left = `${group[1]}px`;
    label.style.top = `${group[2]}px`;
    label.style.width = `${group[3]}px`;
    label.style.height = `${group[4]}px`;
    label.setAttribute("title", sym.path);
    world.appendChild(label);
  }

  if (!MAP.symbols.length) {
    viewport.appendChild(el("div", "empty", "No function or class changed in a parsed file."));
  }

  const edgeLayer = svg("svg", "edges");
  edgeLayer.setAttribute("width", String(LAYOUT.w));
  edgeLayer.setAttribute("height", String(LAYOUT.h));
  edgeLayer.setAttribute("viewBox", `0 0 ${LAYOUT.w} ${LAYOUT.h}`);
  const defs = svg("defs");

  for (const kind of EDGE_STATUSES) {
    const marker = svg("marker");
    marker.setAttribute("id", `arrow-${kind}`);
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "9");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "8");
    marker.setAttribute("markerHeight", "8");
    marker.setAttribute("markerUnits", "userSpaceOnUse");
    marker.setAttribute("orient", "auto");
    const tip = svg("path", `arrow-${kind}`);
    tip.setAttribute("d", "M1 1L9 5L1 9z");
    marker.appendChild(tip);
    defs.appendChild(marker);
  }

  edgeLayer.appendChild(defs);
  world.appendChild(edgeLayer);

  const round = (v) => Math.round(v * 10) / 10;

  const drawOrder = { kept: 0, removed: 1, added: 2 };

  for (const edge of [...edges].sort((p, q) => drawOrder[p.status] - drawOrder[q.status])) {
    const path = svg("path", `e e-${edge.status}${edge.byName ? " e-name" : ""}`);
    path.setAttribute("d", edge.route);
    path.setAttribute("marker-end", `url(#arrow-${edge.status})`);
    path.setAttribute("data-edge", edge.key);
    edge.el = path;
    edgeLayer.appendChild(path);
  }

  function pathLine(path) {
    const box = el("div", "path");
    box.appendChild(el("span", "", path));
    return box;
  }

  function rowCard(node) {
    add(node.el, el("div", "bar"), el("span", "glyph", GLYPH[node.sym.kind] || "f"), el("span", "name", node.name));
    if (PILL[node.status]) node.el.appendChild(el("span", "pill", PILL[node.status]));
    if (node.untested) node.el.appendChild(el("span", "flag", "!"));
    node.el.setAttribute("title", node.untested ? `${node.name} · ${NO_TEST}` : node.name);
  }

  function symbolCard(node) {
    if (LAYOUT.dense) return rowCard(node);
    const sym = node.sym;
    const card = node.el;
    const head = el("div", "n-row");
    add(head, el("span", "glyph", GLYPH[sym.kind] || "f"), el("span", "name", node.name));
    if (PILL[node.status]) head.appendChild(el("span", "pill", PILL[node.status]));
    if (node.status === "context") {
      const sub = add(el("div", "n-row"), pathLine(node.path));
      if (sym.call_sites) sub.appendChild(el("span", "sites", plural(sym.call_sites, "call site", "call sites")));
      add(card, el("div", "bar"), head, sub);
      return;
    }
    add(card, el("div", "bar"), head, pathLine(node.path));
    const foot = el("div", "n-foot");
    const delta = el("span", "delta");
    add(delta, el("span", "plus", `+${sym.added}`), document.createTextNode(" "), el("span", "minus", `${MINUS}${sym.removed}`));
    add(foot, delta);
    if (node.status !== "deleted" && !isTest(node)) foot.appendChild(el("span", "sites", plural(sym.call_sites, "call site", "call sites")));
    if (node.untested) foot.appendChild(el("span", "badge", NO_TEST));
    card.appendChild(foot);
  }

  function fileCard(node) {
    const card = node.el;
    add(card, el("div", "bar"), el("span", "name", node.name));
    if (node.file.sensitive) card.appendChild(el("span", "risk", node.file.sensitive));
    card.setAttribute("title", node.path);
  }

  for (const node of nodes) {
    const card = el("div", `node ${node.kind === "file" ? "chip" : "sym"} st-${node.status}`);
    card.setAttribute("data-node", node.key);
    card.setAttribute("tabindex", "0");
    card.setAttribute("role", "button");
    card.style.left = `${node.x}px`;
    card.style.top = `${node.y}px`;
    card.style.width = `${node.w}px`;
    card.style.height = `${node.h}px`;
    node.el = card;
    if (node.kind === "symbol") symbolCard(node);
    else fileCard(node);
    world.appendChild(card);
  }

  /* Camera */

  const cam = { x: 0, y: 0, k: 1 };
  const all = { x: 0, y: 0, w: LAYOUT.w, h: LAYOUT.h };
  let userMoved = false;

  function applyCamera() {
    world.style.transform = `translate(${round(cam.x)}px, ${round(cam.y)}px) scale(${cam.k.toFixed(4)})`;
    viewport.style.backgroundPosition = `${round(cam.x)}px ${round(cam.y)}px`;
    viewport.style.backgroundSize = `${round(24 * cam.k)}px ${round(24 * cam.k)}px`;
    world.classList.toggle("far", cam.k < 0.55);
  }

  function bounds(list) {
    if (!list.length) return all;
    const x = Math.min(...list.map((n) => n.x));
    const y = Math.min(...list.map((n) => n.y));
    return { x, y, w: Math.max(...list.map((n) => n.x + n.w)) - x, h: Math.max(...list.map((n) => n.y + n.h)) - y };
  }

  function fitTo(box, area, maxK) {
    const pad = 32;
    const k = clamp(Math.min(area.w / (box.w + 2 * pad), area.h / (box.h + 2 * pad)), 0.12, maxK);
    return {
      k,
      x: area.x + area.w / 2 - (box.x + box.w / 2) * k,
      y: area.y + area.h / 2 - (box.y + box.h / 2) * k,
    };
  }

  function viewArea() {
    const w = viewport.clientWidth;
    const h = viewport.clientHeight;
    const drawer = drawerOpen() ? Math.min(520, w * 0.92) : 0;
    return { x: 16, y: 16, w: Math.max(200, w - 32 - drawer), h: Math.max(200, h - 88) };
  }

  function fit() {
    Object.assign(cam, fitTo(all, viewArea(), 1.1));
    applyCamera();
  }

  function open() {
    const area = viewArea();
    const whole = fitTo(all, area, 1.1);
    const band = LAYOUT.bands.find((b) => b[0] === "changed");
    if (whole.k >= LEGIBLE || !band) {
      Object.assign(cam, whole);
    } else {
      const box = { x: band[1], y: band[2], w: band[3], h: band[4] };
      const lane = fitTo(box, area, 1.1);
      if (lane.k >= LEGIBLE) Object.assign(cam, lane);
      else Object.assign(cam, {
        k: LEGIBLE,
        x: box.w * LEGIBLE <= area.w ? area.x + area.w / 2 - (box.x + box.w / 2) * LEGIBLE : area.x - box.x * LEGIBLE,
        y: area.y - box.y * LEGIBLE,
      });
    }
    applyCamera();
  }

  let flight = 0;

  function flyTo(target) {
    const from = { ...cam };
    const start = performance.now();
    const id = ++flight;
    const step = (now) => {
      if (id !== flight) return;
      const p = ease(clamp((now - start) / 420, 0, 1));
      const k = from.k * Math.pow(target.k / from.k, p);
      const cx = lerp(centreX(from), centreX(target), p);
      const cy = lerp(centreY(from), centreY(target), p);
      Object.assign(cam, { k, x: viewport.clientWidth / 2 - cx * k, y: viewport.clientHeight / 2 - cy * k });
      applyCamera();
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  const lerp = (a, b, p) => a + (b - a) * p;
  const centreX = (c) => (viewport.clientWidth / 2 - c.x) / c.k;
  const centreY = (c) => (viewport.clientHeight / 2 - c.y) / c.k;

  function zoomAt(factor, sx, sy) {
    const k = clamp(cam.k * factor, 0.12, 2.5);
    cam.x = sx - ((sx - cam.x) * k) / cam.k;
    cam.y = sy - ((sy - cam.y) * k) / cam.k;
    cam.k = k;
    userMoved = true;
    applyCamera();
  }

  let drag = null;
  let dragged = false;

  viewport.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || $("drawer").contains(event.target) || event.target.closest(".zoom")) return;
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY, cx: cam.x, cy: cam.y, captured: false };
    dragged = false;
  });

  viewport.addEventListener("pointermove", (event) => {
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (!drag.captured && Math.hypot(dx, dy) < 4) return;
    if (!drag.captured) {
      drag.captured = true;
      dragged = true;
      viewport.setPointerCapture(event.pointerId);
      viewport.classList.add("dragging");
      pause();
    }
    flight++;
    cam.x = drag.cx + dx;
    cam.y = drag.cy + dy;
    userMoved = true;
    applyCamera();
  });

  const endDrag = () => {
    drag = null;
    viewport.classList.remove("dragging");
  };
  viewport.addEventListener("pointerup", endDrag);
  viewport.addEventListener("pointercancel", endDrag);

  viewport.addEventListener("wheel", (event) => {
    if ($("drawer").contains(event.target)) return;
    event.preventDefault();
    flight++;
    pause();
    const rect = viewport.getBoundingClientRect();
    if (event.ctrlKey || event.metaKey) {
      zoomAt(Math.exp(-event.deltaY * 0.01), event.clientX - rect.left, event.clientY - rect.top);
    } else {
      cam.x -= event.deltaX;
      cam.y -= event.deltaY;
      userMoved = true;
      applyCamera();
    }
  }, { passive: false });

  viewport.addEventListener("click", (event) => {
    if (dragged || touring) return;
    if (event.target === viewport || event.target === world || event.target.classList.contains("band")) {
      select(null);
    }
  });

  $("zoom-in").addEventListener("click", () => zoomAt(1.25, viewport.clientWidth / 2, viewport.clientHeight / 2));
  $("zoom-out").addEventListener("click", () => zoomAt(0.8, viewport.clientWidth / 2, viewport.clientHeight / 2));
  $("zoom-fit").addEventListener("click", () => {
    userMoved = false;
    fit();
  });

  /* Hover and selection */

  let selected = null;

  function light(node) {
    world.classList.toggle("hovering", Boolean(node));
    for (const n of nodes) n.el.classList.toggle("lit", Boolean(node) && (n === node || node.near.has(n)));
    for (const e of edges) e.el.classList.toggle("lit", Boolean(node) && (e.src === node || e.dst === node));
  }

  for (const node of nodes) {
    node.el.addEventListener("pointerenter", () => {
      if (!touring && !drag) light(node);
    });
    node.el.addEventListener("pointerleave", () => {
      if (!touring) light(selected);
    });
    node.el.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.stopPropagation();
      select(node);
    });
    node.el.addEventListener("click", (event) => {
      event.stopPropagation();
      if (dragged) return;
      select(node);
    });
  }

  const drawer = $("drawer");
  const drawerOpen = () => drawer.getAttribute("aria-hidden") === "false";

  function select(node, centre) {
    if (touring) exitTour();
    if (selected) selected.el.classList.remove("selected");
    selected = node;
    light(node);
    if (!node) {
      drawer.setAttribute("aria-hidden", "true");
      return;
    }
    node.el.classList.add("selected");
    fillDrawer(node);
    drawer.setAttribute("aria-hidden", "false");
    if (centre) {
      const area = viewArea();
      const k = Math.max(cam.k, 0.8);
      flyTo({ k, x: area.x + area.w / 2 - (node.x + node.w / 2) * k, y: area.y + area.h / 2 - (node.y + node.h / 2) * k });
    }
  }

  function section(title, body) {
    return add(el("section", "d-section"), el("h3", "d-title", title), body);
  }

  function diffView(hunks) {
    if (!hunks.length) return el("div", "d-empty", "No line changes recorded for this item.");
    const box = el("div", "diff");
    const rows = el("div", "diff-rows");
    for (const hunk of hunks) {
      rows.appendChild(el("div", "hunk-head", `@@ ${MINUS}${hunk.old_start} +${hunk.new_start} @@`));
      for (const line of hunk.lines) {
        const kind = line.op === "+" ? "add" : line.op === "-" ? "del" : "ctx";
        add(rows, add(el("div", `dl ${kind}`),
          el("span", "ln", line.old === null ? "" : line.old),
          el("span", "ln", line.new === null ? "" : line.new),
          el("span", "sg", kind === "add" ? "+" : kind === "del" ? MINUS : ""),
          el("span", "code", line.text)));
      }
    }
    return add(box, rows);
  }

  const EDGE_TAG = { added: "new call", removed: "removed call", kept: "call" };

  function linkList(items, empty) {
    if (!items.length) return el("div", "d-empty", empty);
    const list = el("div", "links");
    for (const { node, tag, tagClass } of items) {
      const row = el("button", `link st-${node.status}`);
      row.setAttribute("type", "button");
      const text = el("span", "link-text");
      add(text, el("span", "link-name", node.name), el("span", "link-path", node.path));
      add(row, el("span", "bar"), text, tag ? el("span", `etag ${tagClass || ""}`, tag) : null);
      row.addEventListener("click", () => select(node, true));
      list.appendChild(row);
    }
    return list;
  }

  const edgeItem = (edge, other) => ({
    node: other,
    tag: `${EDGE_TAG[edge.status]}${edge.byName ? " \u00b7 by name" : ""}`,
    tagClass: edge.status,
  });

  function fillDrawer(node) {
    drawer.replaceChildren();
    drawer.className = `drawer st-${node.status}`;
    const head = el("div", "d-head");
    const tags = el("div", "d-tags");
    if (PILL[node.status]) tags.appendChild(el("span", "pill", PILL[node.status]));
    tags.appendChild(el("span", "d-kind", node.kind === "file" ? `${node.file.kind} file` : node.sym.kind));
    const close = el("button", "d-close", "\u00d7");
    close.setAttribute("type", "button");
    close.setAttribute("aria-label", "Close");
    close.addEventListener("click", () => select(null));
    add(head, el("div", "bar"), tags, el("div", "d-name", node.kind === "file" ? node.path : node.name),
      node.kind === "file" ? null : el("div", "d-path", node.path), close);

    const facts = el("div", "d-facts");
    const body = el("div", "d-body");

    if (node.kind === "file") {
      const file = node.file;
      add(facts, el("span", "fact", `+${file.added} ${MINUS}${file.removed}`));
      if (file.sensitive) facts.appendChild(el("span", "fact bad", file.sensitive));
      const brief = briefFile.get(file.path);
      if (file.sensitive && brief && !brief.named) facts.appendChild(el("span", "fact warn", "not mentioned in the description"));
      if (file.language === null && file.kind === "code") facts.appendChild(el("span", "fact", "not parsed"));
      add(body, section("Diff", diffView(file.hunks)));
      const inside = file.symbols.map((id) => symbolNode.get(id)).filter(Boolean);
      if (inside.length) body.appendChild(section("Symbols", linkList(inside.map((n) => ({ node: n })), "")));
    } else {
      const sym = node.sym;
      if (node.status !== "context") add(facts, el("span", "fact", `+${sym.added} ${MINUS}${sym.removed}`));
      facts.appendChild(el("span", "fact", plural(sym.call_sites, "call site", "call sites")));
      if (sym.span) facts.appendChild(el("span", "fact", `lines ${sym.span[0]}\u2013${sym.span[1]}`));
      else if (sym.base_span) facts.appendChild(el("span", "fact", `was lines ${sym.base_span[0]}\u2013${sym.base_span[1]}`));
      if (node.untested) facts.appendChild(el("span", "fact warn", `${NO_TEST}: no test in this map calls it`));
      const callers = node.in.filter((e) => !isTest(e.src));
      const tests = node.in.filter((e) => isTest(e.src));
      add(body,
        section("Diff", node.status === "context" ? el("div", "d-empty", "Unchanged. Shown because it calls or is called by changed code.") : diffView(sym.hunks)),
        section("Callers", linkList(callers.map((e) => edgeItem(e, e.src)), "No caller in the map.")),
        section("Callees", linkList(node.out.map((e) => edgeItem(e, e.dst)), "Calls nothing in the map.")),
        isTest(node) ? null : section("Tests", linkList(tests.map((e) => edgeItem(e, e.src)), "No test calls this directly.")));
    }

    head.appendChild(facts);
    add(drawer, head, body);
  }

  /* Tour */

  const names = (list) => {
    const shown = list.slice(0, 2).map((n) => n.name);
    return list.length > 2 ? `${shown.join(", ")} +${list.length - 2} more` : shown.join(" and ");
  };

  function focusNodes(ids) {
    const found = [];
    for (const id of ids) {
      const node = symbolNode.get(id) || fileNode.get(id);
      if (node) found.push(node);
      else if (fileByPath.has(id)) {
        for (const sid of fileByPath.get(id).symbols) if (symbolNode.has(sid)) found.push(symbolNode.get(sid));
      }
    }
    return found;
  }

  function symbolFacts(node) {
    const sym = node.sym;
    const parts = [node.path, `+${sym.added} ${MINUS}${sym.removed}`];
    if (node.status !== "deleted" && !isTest(node)) parts.push(plural(sym.call_sites, "call site", "call sites"));
    if (node.untested) parts.push(NO_TEST);
    return parts.join(DOT);
  }

  function describe(step, index, total) {
    const count = `${index + 1} / ${total}`;
    const focus = focusNodes(step.focus);
    const node = focus[0];
    const via = step.via ? symbolNode.get(step.via) : null;

    if (step.kind === "overview") {
      return {
        kicker: "Overview", count, main: MAP.title,
        sub: [plural(MAP.files.length, "file", "files"), plural(changed.length, "symbol changed", "symbols changed"),
          plural(added, "call added", "calls added"), `${removed} removed`].join(DOT),
      };
    }

    if (step.kind === "risky_file") {
      const path = step.focus[0] || "";
      const file = fileByPath.get(path);
      const brief = briefFile.get(path);
      const reason = (file && file.sensitive) || (brief && brief.sensitive) || "Sensitive file";
      const unnamed = brief && !brief.named ? `${DOT}not mentioned in the description` : "";
      return { kicker: "Risky surface", count, main: `${reason} changed${unnamed}`, sub: path };
    }

    if (step.kind === "summary") return { kicker: "Summary", count, main: "", sub: "" };

    if (!node || node.kind !== "symbol") return { kicker: step.kind, count, main: step.focus.join(", "), sub: "" };

    const word = node.sym.kind;
    const name = node.name;

    if (step.kind === "test") {
      const targets = node.out.filter(live).map((e) => e.dst);
      const covers = targets.length ? `${DOT}covers ${names(targets)}` : "";
      const main = node.status === "added" ? `New test ${name}${covers}`
        : node.status === "deleted" ? `Deleted test ${name}` : `Test ${name} changed${covers}`;
      return { kicker: "Test", count, main, sub: symbolFacts(node) };
    }

    if (step.kind === "callee" && via) {
      const link = node.in.find((e) => e.src === via);
      let main;
      if (node.status === "deleted") main = `Deleted ${name}${DOT}${via.name} no longer calls it`;
      else if (node.status === "added") main = `New ${word} ${name}${DOT}called by ${via.name}`;
      else if (link && link.status === "added") main = `${via.name} now calls ${name}`;
      else if (link && link.status === "removed") main = `${via.name} no longer calls ${name}`;
      else main = `${name} changed${DOT}called by ${via.name}`;
      return { kicker: `Called from ${via.name}`, count, main, sub: symbolFacts(node) };
    }

    const callers = node.in.filter((e) => live(e) && !isTest(e.src)).map((e) => e.src);
    let main;
    if (node.status === "deleted") {
      const former = node.in.filter((e) => !isTest(e.src)).map((e) => e.src);
      main = `Deleted ${name}${former.length ? `${DOT}${names(former)} no longer ${former.length === 1 ? "calls" : "call"} it` : ""}`;
    } else if (node.status === "added") {
      main = `New ${word} ${name}${callers.length ? `${DOT}called by ${names(callers)}` : `${DOT}nothing calls it yet`}`;
    } else {
      main = `${name} changed${callers.length ? `${DOT}called by ${names(callers)}` : ""}`;
    }
    return { kicker: step.kind === "entry" ? "Entry point" : "Changed", count, main, sub: symbolFacts(node) };
  }

  const timeline = (() => {
    const base = MAP.tour.map((s) => STEP_SECONDS[s.kind] || 3);
    const fixed = MAP.tour.reduce((sum, s, i) => sum + (s.kind === "overview" || s.kind === "summary" ? base[i] : 0), 0);
    const middle = base.reduce((sum, v) => sum + v, 0) - fixed;
    const scale = middle > 0 && fixed + middle > MAX_TOUR ? Math.max((MAX_TOUR - fixed) / middle, 0) : 1;
    let start = 0;
    return MAP.tour.map((step, i) => {
      const plain = step.kind === "overview" || step.kind === "summary";
      const duration = Math.round((plain ? base[i] : Math.max(base[i] * scale, MIN_STEP)) * 1000) / 1000;
      const focus = focusNodes(step.focus);
      const via = step.via ? symbolNode.get(step.via) : null;
      const lit = new Set(focus);
      if (via) lit.add(via);
      if (step.kind !== "risky_file") for (const n of focus) for (const m of n.near) lit.add(m);
      const item = {
        kind: step.kind, focus: step.focus, via: step.via, start: Math.round(start * 1000) / 1000, duration,
        caption: describe(step, i, MAP.tour.length), nodes: focus, viaNode: via, lit, plain: plain || !focus.length,
      };
      start += duration;
      return item;
    });
  })();

  const duration = Math.round(timeline.reduce((sum, s) => sum + s.duration, 0) * 1000) / 1000;

  function tourCamera(step) {
    const w = viewport.clientWidth;
    const h = viewport.clientHeight;
    const area = { x: 48, y: 32, w: Math.max(200, w - 96), h: Math.max(160, h - 32 - 176) };
    if (step.plain) return fitTo(all, step.kind === "summary" ? { x: 16, y: 16, w: w - 32, h: h - 32 } : area, 1.1);
    const core = step.viaNode ? [...step.nodes, step.viaNode] : step.nodes;
    const wide = fitTo(bounds([...step.lit]), area, 1.25);
    return wide.k >= 0.62 ? wide : fitTo(bounds(core), area, 1.25);
  }

  let cameras = null;

  function camerasFor() {
    const size = `${viewport.clientWidth}x${viewport.clientHeight}`;
    if (!cameras || cameras.size !== size) cameras = { size, list: timeline.map(tourCamera) };
    return cameras.list;
  }

  const plainLevel = (step) => (step.kind === "summary" ? BEHIND_SUMMARY : 1);
  const nodeLevel = (step, node) => (step.plain ? plainLevel(step) : step.lit.has(node) ? 1 : DIM_NODE);
  const hidden = LAYOUT.dense ? 0 : DIM_EDGE;
  const edgeLevel = (step, edge) => {
    if (step.plain) return LAYOUT.dense ? 0 : plainLevel(step);
    return step.nodes.includes(edge.src) || step.nodes.includes(edge.dst) ? 1 : hidden;
  };

  const caption = $("caption");
  const summary = $("summary");
  let captionFor = -1;

  function fillCaption(index) {
    if (captionFor === index) return;
    captionFor = index;
    const text = timeline[index].caption;
    const kicker = add(el("div", "cap-kicker"), el("span", "", text.kicker), el("span", "cap-count", text.count));
    caption.replaceChildren(kicker, el("div", "cap-main", text.main), el("div", "cap-sub", text.sub));
  }

  function fillSummary() {
    summary.replaceChildren();
    const cell = (num, label, cls) => add(el("div", `sum-cell ${cls || ""}`), el("div", "sum-num", num), el("div", "sum-label", label));
    const grid = add(el("div", "sum-grid"),
      cell(changed.length, changed.length === 1 ? "symbol changed" : "symbols changed"),
      cell(added ? `+${added}` : "0", added === 1 ? "call added" : "calls added", added ? "good" : ""),
      cell(removed ? `${MINUS}${removed}` : "0", removed === 1 ? "call removed" : "calls removed", removed ? "bad" : ""),
      cell(callSites, "call sites affected"),
      cell(untested.length, `changed ${untested.length === 1 ? "symbol" : "symbols"} with ${NO_TEST}`, untested.length ? "warn" : "good"),
      cell(ci.word, ci.failed ? `CI failed: ${ci.failed.map((c) => c.name).join(", ")}` : "CI on the head commit", ci.cls));
    const toured = new Set(MAP.tour.flatMap((step) => step.focus));
    const skipped = changedCode.filter((n) => !toured.has(n.sym.id)).length;
    const note = skipped ? el("div", "sum-note", `${plural(skipped, "more changed symbol", "more changed symbols")} on the map, not in this tour`) : null;
    add(summary, el("div", "sum-kicker", "What this PR rewired"), el("div", "sum-title", MAP.title), grid, note,
      el("div", "sum-brand", "PR map \u00b7 computed from the code, no AI drew this"));
  }

  fillSummary();

  let touring = false;

  function enterTour() {
    if (touring) return;
    select(null);
    light(null);
    touring = true;
    document.body.classList.add("touring");
  }

  function exitTour() {
    pause();
    if (!touring) return;
    touring = false;
    document.body.classList.remove("touring");
    for (const n of nodes) {
      n.el.style.opacity = "";
      n.el.classList.remove("focus");
    }
    for (const e of edges) {
      e.el.style.opacity = "";
      e.el.style.strokeDashoffset = "";
    }
    captionFor = -1;
  }

  function stepAt(t) {
    let index = 0;
    while (index + 1 < timeline.length && timeline[index + 1].start <= t) index++;
    return index;
  }

  function seek(time) {
    if (!timeline.length) return;
    const t = clamp(Number(time) || 0, 0, duration);
    enterTour();
    const index = stepAt(t);
    const step = timeline[index];
    const prev = timeline[Math.max(index - 1, 0)];
    const u = t - step.start;
    const p = index === 0 ? 1 : ease(clamp(u / MOVE, 0, 1));
    const cams = camerasFor();
    const from = cams[Math.max(index - 1, 0)];
    const to = cams[index];
    const k = from.k * Math.pow(to.k / from.k, p);
    const vw = viewport.clientWidth / 2;
    const vh = viewport.clientHeight / 2;
    const cx = lerp((vw - from.x) / from.k, (vw - to.x) / to.k, p);
    const cy = lerp((vh - from.y) / from.k, (vh - to.y) / to.k, p);
    Object.assign(cam, { k, x: vw - cx * k, y: vh - cy * k });
    applyCamera();

    for (const n of nodes) {
      n.el.style.opacity = String(round(lerp(nodeLevel(prev, n), nodeLevel(step, n), p) * 100) / 100);
      n.el.classList.toggle("focus", !step.plain && step.nodes.includes(n));
    }
    const offset = String(-round((t * 28) % 28));
    for (const e of edges) {
      e.el.style.opacity = String(round(lerp(edgeLevel(prev, e), edgeLevel(step, e), p) * 100) / 100);
      if (e.status === "added") e.el.style.strokeDashoffset = offset;
    }

    const last = index === timeline.length - 1;
    const fadeIn = clamp((u - 0.25) / 0.45, 0, 1);
    const fadeOut = last ? 1 : clamp((step.duration - u) / 0.35, 0, 1);
    fillCaption(index);
    caption.style.opacity = step.kind === "summary" ? "0" : String(round(Math.min(fadeIn, fadeOut) * 100) / 100);
    summary.style.opacity = step.kind === "summary" ? String(round(clamp((u - 0.3) / 0.6, 0, 1) * 100) / 100) : "0";
    $("progress-bar").style.width = `${round((t / duration) * 1000) / 10}%`;
  }

  /* Playback */

  const player = { t: 0, playing: false, until: null, last: 0 };

  function setPlaying(on) {
    player.playing = on;
    document.body.classList.toggle("playing", on);
    $("play-label").textContent = on ? "Pause" : player.t >= duration && touring ? "Replay" : "Play tour";
  }

  function frame(now) {
    if (!player.playing) return;
    player.t = Math.min(duration, player.t + (now - player.last) / 1000);
    player.last = now;
    if (player.until !== null && player.t >= player.until) player.t = player.until;
    seek(player.t);
    if (player.t >= duration || (player.until !== null && player.t >= player.until)) setPlaying(false);
    else requestAnimationFrame(frame);
  }

  function run(from, until) {
    flight++;
    player.t = from;
    player.until = until;
    player.last = performance.now();
    seek(from);
    setPlaying(true);
    requestAnimationFrame(frame);
  }

  function pause() {
    if (player.playing) setPlaying(false);
  }

  function goto(index) {
    const i = clamp(index, 0, timeline.length - 1);
    const step = timeline[i];
    run(step.start, step.start + Math.min(step.duration - 0.4, MOVE + 0.6));
  }

  function next() {
    if (!touring) return goto(0);
    goto(stepAt(player.t) + 1);
  }

  function prev() {
    if (!touring) return goto(0);
    goto(stepAt(player.t) - 1);
  }

  $("play").addEventListener("click", () => {
    if (player.playing) return pause();
    const from = touring && player.t < duration ? player.t : 0;
    run(from, null);
  });

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const key = event.key;
    if (key === "Escape") {
      if (drawerOpen()) select(null);
      else if (touring) exitTour();
    } else if (key === "ArrowRight" || key === " " || key === "PageDown") {
      next();
    } else if (key === "ArrowLeft" || key === "PageUp") {
      prev();
    } else if (key === "f" || key === "F") {
      if (touring) exitTour();
      userMoved = false;
      fit();
    } else if (key === "+" || key === "=") {
      zoomAt(1.25, viewport.clientWidth / 2, viewport.clientHeight / 2);
    } else if (key === "-" || key === "_") {
      zoomAt(0.8, viewport.clientWidth / 2, viewport.clientHeight / 2);
    } else {
      return;
    }
    event.preventDefault();
  });

  window.addEventListener("resize", () => {
    if (touring) seek(player.t);
    else if (!userMoved) open();
  });

  open();

  window.prcTour = Object.freeze({
    duration,
    steps: timeline.map((s) => Object.freeze({
      kind: s.kind, focus: [...s.focus], via: s.via, start: s.start, duration: s.duration,
      caption: Object.freeze({ ...s.caption }),
    })),
    seek: (t) => {
      pause();
      player.t = clamp(Number(t) || 0, 0, duration);
      seek(player.t);
    },
  });
})();
