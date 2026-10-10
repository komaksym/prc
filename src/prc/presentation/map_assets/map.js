(() => {
  "use strict";
  const BLOCK = JSON.parse(document.getElementById("map-data").textContent);
  const MAP = BLOCK.map;
  const GRAPH = BLOCK.graph;
  const PSTEPS = BLOCK.steps;
  const GROUPS = MAP.groups;
  const FACTS = MAP.summary;
  const STATS = FACTS.stats;
  const MINUS = "\u2212";
  const DOT = " \u00b7 ";
  const STEP_SECONDS = { overview: 4, risky_file: 3.4, entry: 3.8, callee: 3.4, test: 3.2, summary: 4.6 };
  const MAX_TOUR = 60;
  const MIN_STEP = 1.6;
  const MOVE = 1.0;
  const LEGIBLE = 0.55;
  const NO_TEST = "no direct test evidence";
  const GITHUB_PR = /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/pull\/[0-9]+$/;
  const PILL = { added: "new", modified: "modified", deleted: "deleted" };
  const EDGE_TAG = { added: "new call", removed: "removed call", kept: "call" };
  const $ = (id) => document.getElementById(id);
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
  const lerp = (a, b, p) => a + (b - a) * p;
  const round = (v) => Math.round(v * 10) / 10;
  const plural = (n, one, many) => n + " " + (n === 1 ? one : many);
  const basename = (path) => path.slice(path.lastIndexOf("/") + 1) || path;
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function add(parent) {
    for (let i = 1; i < arguments.length; i++) if (arguments[i]) parent.appendChild(arguments[i]);
    return parent;
  }
  const symById = new Map(MAP.symbols.map((s) => [s.id, s]));
  const symIndex = new Map(MAP.symbols.map((s, i) => [s.id, i]));
  const fileByPath = new Map(MAP.files.map((f) => [f.path, f]));
  const fileIndex = new Map(MAP.files.map((f, i) => [f.path, i]));
  const briefFile = new Map(MAP.brief.files.map((f) => [f.path, f]));
  const testIds = new Set(FACTS.test_symbol_ids);
  const missingIds = new Set(FACTS.no_direct_test.map((entry) => entry.id));
  const graphById = new Map();
  if (GRAPH) for (const node of GRAPH.nodes) graphById.set(node.id, node);
  const mapIdOfGraph = new Map();
  const graphIdOfMap = new Map();
  if (GRAPH) {
    for (const node of GRAPH.nodes) {
      if (node.id.charAt(0) === "s") {
        const sym = MAP.symbols[Number(node.id.slice(1))];
        if (sym) {
          mapIdOfGraph.set(node.id, sym.id);
          graphIdOfMap.set(sym.id, node.id);
        }
      }
    }
  }
  const isTestId = (id) => testIds.has(id);
  const changed = MAP.symbols.filter((s) => s.status !== "context");
  const changedCode = changed.filter((s) => !testIds.has(s.id));
  const untested = FACTS.no_direct_test;
  const callSites = STATS.call_sites;
  const added = FACTS.edges_added;
  const removed = FACTS.edges_removed;
  const risky = MAP.brief.files.filter((f) => f.sensitive);
  const ci = {
    cls: { none: "none", failed: "bad", pending: "warn", passed: "good" }[FACTS.ci_state],
    label: FACTS.ci_state === "none" ? "no CI" : "CI " + FACTS.ci_state,
    word: STATS.ci_text,
    failed: MAP.brief.checks.filter((c) => c.state === "failed"),
  };
  document.title = MAP.title + " \u00b7 PR map";
  $("title").textContent = MAP.title;
  (() => {
    const meta = $("meta");
    const sep = () => el("span", "sep", "\u00b7");
    add(meta, sep(), el("span", "who", MAP.pr), sep(), el("span", "who", "by " + MAP.author), sep(),
      el("span", "mono", MAP.base_sha.slice(0, 7) + " \u2192 " + MAP.head_sha.slice(0, 7)));
    if (typeof MAP.url === "string" && GITHUB_PR.test(MAP.url)) {
      const link = el("a", "", "Open on GitHub");
      link.setAttribute("href", MAP.url);
      link.setAttribute("rel", "noopener noreferrer");
      link.setAttribute("target", "_blank");
      add(meta, sep(), link);
    }
    const stats = $("stats");
    const stat = (value, label, cls, dot) => {
      const box = el("div", "stat " + (cls || ""));
      const val = el("div", "stat-value");
      if (dot) val.appendChild(el("span", "dot"));
      val.appendChild(el("span", "", value));
      return add(box, val, el("div", "stat-label", label));
    };
    add(stats,
      stat(STATS.files, STATS.files === 1 ? "file" : "files"),
      stat(STATS.symbols_changed, STATS.symbols_changed === 1 ? "parsed symbol changed" : "parsed symbols changed"),
      stat(callSites, callSites === 1 ? "resolved call site" : "resolved call sites"),
      stat(STATS.tests_touched, STATS.tests_touched === 1 ? "test file touched" : "test files touched",
        STATS.tests_touched ? "" : "warn"),
      stat(ci.word, ci.label, ci.cls, true),
      stat(risky.length, risky.length === 1 ? "risky surface" : "risky surfaces", risky.length ? "warn" : ""));
    if (FACTS.limits.length) {
      const limit = stat(FACTS.limits.length,
        FACTS.limits.length === 1 ? "file without symbol analysis" : "files without symbol analysis", "warn");
      limit.setAttribute("title", FACTS.limits.map((entry) => entry.path + ": " + entry.reason).join("\n"));
      stats.appendChild(limit);
    }
  })();
  const viewport = $("viewport");
  const world = $("world");
  const drawer = $("drawer");
  const drawerOpen = () => drawer.getAttribute("aria-hidden") === "false";
  let diagramW = 960;
  let diagramH = 420;
  let atlas = { lanes: {}, nodes: {}, edges: {}, messages: {} };
  let renderFailed = false;
  if (!GRAPH || !GRAPH.nodes.length) {
    viewport.appendChild(el("div", "empty", "No function or class changed in a parsed file."));
  } else {
    const theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
    try {
      const out = prcLens.render(GRAPH, { lens: "architecture", theme: theme });
      diagramW = out.width;
      diagramH = out.height;
      atlas = out.atlas;
      const img = document.createElement("img");
      img.setAttribute("alt", "");
      img.setAttribute("width", String(out.width));
      img.setAttribute("height", String(out.height));
      img.setAttribute("src", "data:image/svg+xml;charset=utf-8," + encodeURIComponent(out.svg));
      img.className = "diagram";
      img.setAttribute("draggable", "false");
      world.appendChild(img);
    } catch (err) {
      renderFailed = true;
      viewport.appendChild(el("div", "fallback", "Diagram unavailable" + DOT + "the drawer still lists every change."));
      const files = el("div", "fallback-files");
      MAP.files.forEach((file, i) => {
        const link = el("button", "flink", file.path);
        link.setAttribute("type", "button");
        link.addEventListener("click", () => openNode("f" + i, false));
        files.appendChild(link);
      });
      viewport.appendChild(files);
    }
  }
  world.style.width = diagramW + "px";
  world.style.height = diagramH + "px";
  const ringLayer = el("div", "rings");
  world.appendChild(ringLayer);
  function labelOf(id) {
    const node = graphById.get(id);
    if (!node) return id;
    if (id.charAt(0) === "s") {
      const sym = MAP.symbols[Number(id.slice(1))];
      return sym ? sym.qualname : node.label;
    }
    if (id.charAt(0) === "f") {
      const file = MAP.files[Number(id.slice(1))];
      return file ? file.path : node.label;
    }
    const group = GROUPS[Number(id.slice(1))];
    return group ? group.label : node.label;
  }
  if (!renderFailed && GRAPH && GRAPH.nodes.length) {
    for (const id of Object.keys(atlas.nodes)) {
      if (!graphById.has(id)) continue;
      const box = atlas.nodes[id];
      const hit = el("button", "hit");
      hit.setAttribute("type", "button");
      hit.setAttribute("data-node", id);
      hit.setAttribute("aria-label", labelOf(id));
      hit.style.left = box.x + "px";
      hit.style.top = box.y + "px";
      hit.style.width = box.width + "px";
      hit.style.height = box.height + "px";
      hit.addEventListener("click", (event) => {
        event.stopPropagation();
        if (dragged) return;
        openNode(id, true);
      });
      world.appendChild(hit);
    }
  }
  const cam = { x: 0, y: 0, k: 1 };
  const all = { x: 0, y: 0, w: diagramW, h: diagramH };
  let userMoved = false;
  function applyCamera() {
    world.style.transform = "translate(" + round(cam.x) + "px, " + round(cam.y) + "px) scale(" + cam.k.toFixed(4) + ")";
    viewport.style.backgroundPosition = round(cam.x) + "px " + round(cam.y) + "px";
    viewport.style.backgroundSize = round(24 * cam.k) + "px " + round(24 * cam.k) + "px";
  }
  function boundsOf(ids) {
    const boxes = ids.map((id) => atlas.nodes[id]).filter(Boolean);
    if (!boxes.length) return all;
    const x = Math.min.apply(null, boxes.map((b) => b.x));
    const y = Math.min.apply(null, boxes.map((b) => b.y));
    return { x: x, y: y, w: Math.max.apply(null, boxes.map((b) => b.x + b.width)) - x, h: Math.max.apply(null, boxes.map((b) => b.y + b.height)) - y };
  }
  function fitTo(box, area, maxK) {
    const pad = 32;
    const k = clamp(Math.min(area.w / (box.w + 2 * pad), area.h / (box.h + 2 * pad)), 0.12, maxK);
    return {
      k: k,
      x: area.x + area.w / 2 - (box.x + box.w / 2) * k,
      y: area.y + area.h / 2 - (box.y + box.h / 2) * k,
    };
  }
  function viewArea() {
    const w = viewport.clientWidth;
    const h = viewport.clientHeight;
    const taken = drawerOpen() ? Math.min(520, w * 0.92) : 0;
    return { x: 16, y: 16, w: Math.max(200, w - 32 - taken), h: Math.max(200, h - 88) };
  }
  function fit() {
    const next = fitTo(all, viewArea(), 1.1);
    cam.x = next.x;
    cam.y = next.y;
    cam.k = next.k;
    applyCamera();
  }
  function open() {
    const area = viewArea();
    const whole = fitTo(all, area, 1.1);
    if (whole.k >= LEGIBLE) {
      cam.x = whole.x;
      cam.y = whole.y;
      cam.k = whole.k;
    } else {
      cam.k = LEGIBLE;
      cam.x = all.w * LEGIBLE <= area.w ? area.x + area.w / 2 - (all.x + all.w / 2) * LEGIBLE : area.x - all.x * LEGIBLE;
      cam.y = area.y - all.y * LEGIBLE;
    }
    applyCamera();
  }
  let flight = 0;
  function flyTo(target) {
    const from = { x: cam.x, y: cam.y, k: cam.k };
    const start = performance.now();
    const id = ++flight;
    const cx = (c) => (viewport.clientWidth / 2 - c.x) / c.k;
    const cy = (c) => (viewport.clientHeight / 2 - c.y) / c.k;
    const fx = cx(from);
    const fy = cy(from);
    const tx = cx(target);
    const ty = cy(target);
    const step = (now) => {
      if (id !== flight) return;
      const p = ease(clamp((now - start) / 420, 0, 1));
      const k = from.k * Math.pow(target.k / from.k, p);
      cam.k = k;
      cam.x = viewport.clientWidth / 2 - lerp(fx, tx, p) * k;
      cam.y = viewport.clientHeight / 2 - lerp(fy, ty, p) * k;
      applyCamera();
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
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
    if (event.target === viewport || event.target === world || event.target.className === "diagram") openNode(null);
  });
  $("zoom-in").addEventListener("click", () => zoomAt(1.25, viewport.clientWidth / 2, viewport.clientHeight / 2));
  $("zoom-out").addEventListener("click", () => zoomAt(0.8, viewport.clientWidth / 2, viewport.clientHeight / 2));
  $("zoom-fit").addEventListener("click", () => {
    userMoved = false;
    fit();
  });
  let selected = null;
  function openNode(id, centre) {
    if (touring) exitTour();
    selected = id;
    if (!id) {
      drawer.setAttribute("aria-hidden", "true");
      return;
    }
    fillDrawer(id);
    drawer.setAttribute("aria-hidden", "false");
    if (centre && atlas.nodes[id]) {
      const box = atlas.nodes[id];
      const area = viewArea();
      const k = Math.max(cam.k, 0.8);
      flyTo({ k: k, x: area.x + area.w / 2 - (box.x + box.width / 2) * k, y: area.y + area.h / 2 - (box.y + box.height / 2) * k });
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
      rows.appendChild(el("div", "hunk-head", "@@ " + MINUS + hunk.old_start + " +" + hunk.new_start + " @@"));
      for (const line of hunk.lines) {
        const kind = line.op === "+" ? "add" : line.op === "-" ? "del" : "ctx";
        add(rows, add(el("div", "dl " + kind),
          el("span", "ln", line.old === null || line.old === undefined ? "" : line.old),
          el("span", "ln", line.new === null || line.new === undefined ? "" : line.new),
          el("span", "sg", kind === "add" ? "+" : kind === "del" ? MINUS : ""),
          el("span", "code", line.text)));
      }
    }
    return add(box, rows);
  }
  function edgeTag(edge) {
    return EDGE_TAG[edge.status] + (edge.resolution === "name" ? " " + DOT + "by name" : "");
  }
  function symbolRow(id) {
    const sym = symById.get(id);
    if (!sym) return null;
    const row = el("button", "link st-" + sym.status);
    row.setAttribute("type", "button");
    const text = el("span", "link-text");
    add(text, el("span", "link-name", sym.qualname), el("span", "link-path", sym.path));
    add(row, el("span", "bar"), text);
    row.addEventListener("click", () => openSymbol(symIndex.get(id)));
    return row;
  }
  function linkList(ids, empty) {
    if (!ids.length) return el("div", "d-empty", empty);
    const list = el("div", "links");
    for (const id of ids) {
      const row = symbolRow(id);
      if (row) list.appendChild(row);
    }
    return list;
  }
  function openSymbol(mapIdx) {
    openNode("s" + mapIdx, true);
  }
  function drawerHead(kindLabel, title, path) {
    const head = el("div", "d-head");
    const close = el("button", "d-close", "\u00d7");
    close.setAttribute("type", "button");
    close.setAttribute("aria-label", "Close");
    close.addEventListener("click", () => openNode(null));
    add(head, el("div", "bar"), el("div", "d-kind", kindLabel), el("div", "d-name", title),
      path ? el("div", "d-path", path) : null, close);
    return head;
  }
  function fillDrawer(id) {
    const kind = id.charAt(0);
    if (kind === "g") return fillGroup(Number(id.slice(1)));
    if (kind === "f") return fillFile(Number(id.slice(1)));
    return fillSymbol(Number(id.slice(1)));
  }
  function fillSymbol(mapIdx) {
    const sym = MAP.symbols[mapIdx];
    if (!sym) return;
    drawer.replaceChildren();
    drawer.className = "drawer st-" + sym.status;
    const facts = el("div", "d-facts");
    const body = el("div", "d-body");
    if (sym.status !== "context") add(facts, el("span", "fact", "+" + sym.added + " " + MINUS + sym.removed));
    facts.appendChild(el("span", "fact", plural(sym.call_sites, "call site", "call sites")));
    if (sym.span) facts.appendChild(el("span", "fact", "lines " + sym.span[0] + "\u2013" + sym.span[1]));
    else if (sym.base_span) facts.appendChild(el("span", "fact", "was lines " + sym.base_span[0] + "\u2013" + sym.base_span[1]));
    if (missingIds.has(sym.id)) facts.appendChild(el("span", "fact warn", NO_TEST + ": no exact live test call appears in this map"));
    const callers = MAP.edges.filter((e) => e.target === sym.id && !isTestId(e.source));
    const tests = MAP.edges.filter((e) => e.target === sym.id && isTestId(e.source));
    const callees = MAP.edges.filter((e) => e.source === sym.id);
    const callerList = el("div", "links");
    for (const e of callers) {
      const src = symById.get(e.source);
      if (!src) continue;
      const row = el("button", "link st-" + src.status);
      row.setAttribute("type", "button");
      add(row, el("span", "bar"), add(el("span", "link-text"), el("span", "link-name", src.qualname), el("span", "link-path", src.path)),
        el("span", "etag " + e.status, edgeTag(e)));
      row.addEventListener("click", () => openSymbol(symIndex.get(e.source)));
      callerList.appendChild(row);
    }
    const calleeList = el("div", "links");
    for (const e of callees) {
      const dst = symById.get(e.target);
      if (!dst) continue;
      const row = el("button", "link st-" + dst.status);
      row.setAttribute("type", "button");
      add(row, el("span", "bar"), add(el("span", "link-text"), el("span", "link-name", dst.qualname), el("span", "link-path", dst.path)),
        el("span", "etag " + e.status, edgeTag(e)));
      row.addEventListener("click", () => openSymbol(symIndex.get(e.target)));
      calleeList.appendChild(row);
    }
    const testList = el("div", "links");
    for (const e of tests) {
      const src = symById.get(e.source);
      if (!src) continue;
      const row = el("button", "link st-" + src.status);
      row.setAttribute("type", "button");
      add(row, el("span", "bar"), add(el("span", "link-text"), el("span", "link-name", src.qualname), el("span", "link-path", src.path)),
        el("span", "etag " + e.status, edgeTag(e)));
      row.addEventListener("click", () => openSymbol(symIndex.get(e.source)));
      testList.appendChild(row);
    }
    if (!callerList.childNodes.length) callerList.appendChild(el("div", "d-empty", "No caller in the map."));
    if (!calleeList.childNodes.length) calleeList.appendChild(el("div", "d-empty", "Calls nothing in the map."));
    if (!testList.childNodes.length) testList.appendChild(el("div", "d-empty", "No test call appears in this map. This does not establish missing tests."));
    const head = drawerHead(sym.kind, sym.qualname, sym.path);
    if (PILL[sym.status]) head.appendChild(el("span", "pill", PILL[sym.status]));
    head.appendChild(facts);
    add(body,
      section("Diff", sym.status === "context"
        ? el("div", "d-empty", "Unchanged. Shown because it calls or is called by changed code.")
        : diffView(sym.hunks)),
      section("Callers", callerList),
      section("Callees", calleeList),
      isTestId(sym.id) ? null : section("Tests", testList));
    add(drawer, head, body);
  }
  function fillFile(mapIdx) {
    const file = MAP.files[mapIdx];
    if (!file) return;
    drawer.replaceChildren();
    drawer.className = "drawer st-" + file.status;
    const facts = el("div", "d-facts");
    add(facts, el("span", "fact", "+" + file.added + " " + MINUS + file.removed));
    if (file.sensitive) facts.appendChild(el("span", "fact bad", file.sensitive));
    const brief = briefFile.get(file.path);
    if (file.sensitive && brief && !brief.named) facts.appendChild(el("span", "fact warn", "not mentioned in the description"));
    if (file.language === null && file.kind === "code") facts.appendChild(el("span", "fact", "not parsed"));
    const head = drawerHead(file.kind + " file", file.path, null);
    head.appendChild(facts);
    const body = el("div", "d-body");
    add(body, section("Diff", diffView(file.hunks)));
    const inside = (file.symbols || []).filter((id) => symById.has(id));
    if (inside.length) body.appendChild(section("Symbols", linkList(inside, "")));
    add(drawer, head, body);
  }
  function fillGroup(groupIdx) {
    const group = GROUPS[groupIdx];
    if (!group) return;
    drawer.replaceChildren();
    drawer.className = "drawer";
    const total = group.added + group.modified + group.deleted;
    const sub = total + " changed: " + group.added + " added, " + group.modified + " modified, " + group.deleted + " deleted";
    const head = drawerHead(group.is_dir ? "folder" : "file", group.label, sub);
    add(drawer, head);
    const body = el("div", "d-body");
    const list = el("div", "links");
    for (const id of group.members) {
      const sym = symById.get(id);
      if (!sym) continue;
      const row = el("button", "link st-" + sym.status);
      row.setAttribute("type", "button");
      const lines = sym.span ? "lines " + sym.span[0] + "\u2013" + sym.span[1]
        : sym.base_span ? "was lines " + sym.base_span[0] + "\u2013" + sym.base_span[1] : "";
      add(row, el("span", "bar"),
        add(el("span", "link-text"), el("span", "link-name", sym.qualname), el("span", "link-path", sym.path)),
        el("span", "fact", "+" + sym.added + " " + MINUS + sym.removed + (lines ? DOT + lines : "")));
      row.addEventListener("click", () => openSymbol(symIndex.get(id)));
      list.appendChild(row);
    }
    body.appendChild(section("Members", list));
    drawer.appendChild(body);
  }
  const GW = GRAPH && GRAPH.walkthrough ? GRAPH.walkthrough.steps : [];
  const KICKER = { overview: "Overview", risky_file: "Risky surface", entry: "Entry point", callee: "Callee", test: "Test", summary: "Summary" };
  const timeline = (() => {
    const base = PSTEPS.map((s) => STEP_SECONDS[s.kind] || 3);
    const fixed = PSTEPS.reduce((sum, s, i) => sum + (s.kind === "overview" || s.kind === "summary" ? base[i] : 0), 0);
    const middle = base.reduce((sum, v) => sum + v, 0) - fixed;
    const scale = middle > 0 && fixed + middle > MAX_TOUR ? Math.max((MAX_TOUR - fixed) / middle, 0) : 1;
    let start = 0;
    return PSTEPS.map((step, i) => {
      const gw = GW[i] || { heading: step.kind, body: "", focus: { kind: "all" } };
      const plain = step.kind === "overview" || step.kind === "summary";
      const duration = Math.round((plain ? base[i] : Math.max(base[i] * scale, MIN_STEP)) * 1000) / 1000;
      const focus = gw.focus && gw.focus.kind === "selection" ? (gw.focus.nodes || []).filter((id) => graphById.has(id)) : [];
      const via = step.via ? graphIdOfMap.get(step.via) || null : null;
      const item = {
        kind: step.kind, via: step.via, start: Math.round(start * 1000) / 1000, duration: duration,
        focus: focus, viaNode: via, plain: plain || !focus.length,
        caption: { kicker: KICKER[step.kind] || step.kind, count: (i + 1) + " / " + PSTEPS.length, main: gw.heading, sub: gw.body },
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
    if (step.plain) {
      if (step.kind === "summary") return fitTo({ x: 16, y: 16, w: w - 32, h: h - 32 }, { x: 16, y: 16, w: w - 32, h: h - 32 }, 1.1);
      return fitTo(all, area, 1.1);
    }
    const core = step.viaNode ? step.focus.concat([step.viaNode]) : step.focus;
    const wide = fitTo(boundsOf(step.focus.concat(step.viaNode ? [step.viaNode] : [])), area, 1.25);
    return wide.k >= 0.62 ? wide : fitTo(boundsOf(core), area, 1.25);
  }
  let cameras = null;
  function camerasFor() {
    const size = viewport.clientWidth + "x" + viewport.clientHeight;
    if (!cameras || cameras.size !== size) cameras = { size: size, list: timeline.map(tourCamera) };
    return cameras.list;
  }
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
    const cell = (num, label, cls) => add(el("div", "sum-cell " + (cls || "")), el("div", "sum-num", num), el("div", "sum-label", label));
    const grid = add(el("div", "sum-grid"),
      cell(STATS.symbols_changed, STATS.symbols_changed === 1 ? "parsed symbol changed" : "parsed symbols changed"),
      cell(added ? "+" + added : "0", added === 1 ? "call added" : "calls added", added ? "good" : ""),
      cell(removed ? MINUS + removed : "0", removed === 1 ? "call removed" : "calls removed", removed ? "bad" : ""),
      cell(callSites, callSites === 1 ? "resolved call site" : "resolved call sites"),
      cell(untested.length, "changed " + (untested.length === 1 ? "symbol" : "symbols") + " with " + NO_TEST, untested.length ? "warn" : "good"),
      cell(ci.word, ci.failed.length ? "CI failed: " + ci.failed.map((c) => c.name).join(", ") : ci.label + " on the head commit", ci.cls));
    const toured = new Set(MAP.tour.flatMap((step) => step.focus));
    const skipped = changedCode.filter((n) => !toured.has(n.id)).length;
    const note = skipped ? el("div", "sum-note", plural(skipped, "more changed symbol", "more changed symbols") + " on the map, not in this tour") : null;
    const limits = FACTS.limits.map((entry) => entry.path + ": " + entry.reason).join("; ");
    add(summary, el("div", "sum-note", FACTS.test_note),
      limits ? el("div", "sum-note", "Symbol analysis limits: " + limits) : null);
    add(summary, el("div", "sum-kicker", "What this PR rewired"), el("div", "sum-title", MAP.title), grid, note,
      el("div", "sum-brand", "PR map \u00b7 computed from the code, no AI drew this"));
  }
  fillSummary();
  let touring = false;
  function enterTour() {
    if (touring) return;
    openNode(null);
    touring = true;
    document.body.classList.add("touring");
  }
  function exitTour() {
    pause();
    if (!touring) return;
    touring = false;
    document.body.classList.remove("touring");
    ringLayer.replaceChildren();
    captionFor = -1;
  }
  function stepAt(t) {
    let index = 0;
    while (index + 1 < timeline.length && timeline[index + 1].start <= t) index++;
    return index;
  }
  function drawRings(step) {
    ringLayer.replaceChildren();
    for (const id of step.focus) {
      const box = atlas.nodes[id];
      if (!box) continue;
      const ring = el("div", "ring");
      ring.style.left = box.x + "px";
      ring.style.top = box.y + "px";
      ring.style.width = box.width + "px";
      ring.style.height = box.height + "px";
      ringLayer.appendChild(ring);
    }
    if (step.viaNode && atlas.nodes[step.viaNode]) {
      const box = atlas.nodes[step.viaNode];
      const ring = el("div", "via");
      ring.style.left = box.x + "px";
      ring.style.top = box.y + "px";
      ring.style.width = box.width + "px";
      ring.style.height = box.height + "px";
      ringLayer.appendChild(ring);
    }
  }
  function seek(time) {
    if (!timeline.length) return;
    const t = clamp(Number(time) || 0, 0, duration);
    enterTour();
    const index = stepAt(t);
    const step = timeline[index];
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
    cam.k = k;
    cam.x = vw - cx * k;
    cam.y = vh - cy * k;
    applyCamera();
    if (captionFor !== index) drawRings(step);
    const last = index === timeline.length - 1;
    const fadeIn = clamp((u - 0.25) / 0.45, 0, 1);
    const fadeOut = last ? 1 : clamp((step.duration - u) / 0.35, 0, 1);
    fillCaption(index);
    caption.style.opacity = step.kind === "summary" ? "0" : String(round(Math.min(fadeIn, fadeOut) * 100) / 100);
    summary.style.opacity = step.kind === "summary" ? String(round(clamp((u - 0.3) / 0.6, 0, 1) * 100) / 100) : "0";
    $("progress-bar").style.width = String(round((t / duration) * 1000) / 10) + "%";
  }
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
      if (drawerOpen()) openNode(null);
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
    duration: duration,
    steps: timeline.map((s) => Object.freeze({
      kind: s.kind, focus: s.focus.slice(), via: s.via, start: s.start, duration: s.duration,
      caption: Object.freeze({ kicker: s.caption.kicker, count: s.caption.count, main: s.caption.main, sub: s.caption.sub }),
    })),
    seek: (t) => {
      pause();
      player.t = clamp(Number(t) || 0, 0, duration);
      seek(player.t);
    },
  });
})();
