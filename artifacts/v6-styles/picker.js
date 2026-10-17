/* PRC v6 style picker, round 2. Throwaway prototype. */
(function () {
'use strict';
var PR = 'https://github.com/komaksym/linkedin-mdp/pull/5';
var F = PR + '/files#diff-';
var RUN = F + 'ae4651b791554885691e5439c7e07983819af9ab95a7e822a05a376ed2ca5878R';
var E2E = F + '611723ce987a2e3e568a3645b8623f2947dc1895aa75f817e07ea2dc45824c30R';
var GDR = F + '997c7f526b66a84ac29be4c15cf342c0948e1accd92b45cf9196562aae7a805eR';
var NS = 'http://www.w3.org/2000/svg';
function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
function $(s, r) { return (r || document).querySelector(s); }
function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

/* ---------- content, from the PR and its e2e test ---------- */
var COUNTS = [['Fetched rows', 4], ['Matched rows', 3], ['Unique matched connections', 2], ['Unmatched rows', 1], ['Newly inserted events', 1], ['Already-present events', 1]];
var RUNTIME = 'Run time: 2026-09-30 10:00:00 CEST';
function report(status) {
  var L = ['LinkedIn CONNECTIONS reconciliation', 'Status: ' + status, RUNTIME];
  COUNTS.forEach(function (c) { L.push(c[0] + ': ' + (status === 'COMPLETE' ? c[1] : 'unknown')); });
  if (status === 'COMPLETE') L.push('Next action: review the aggregate counts; investigate unmatched rows if needed.');
  else if (status === 'BLOCKED') L.push('Next action: restore a complete LinkedIn CONNECTIONS snapshot, then rerun.');
  if (status === 'FAILED') { L.push('Database writes may have happened; their final state is unknown.'); L.push('Next action: verify Supabase state before retrying reconciliation.'); }
  return L;
}
var SCEN = {
  complete: { exit: 0, status: 'COMPLETE', cap: '<b>Exit 0.</b> The run is COMPLETE, so all six counts are known.' },
  later_404: { exit: 1, status: 'BLOCKED', cap: '<b>Exit 1.</b> LinkedIn answers 404 on a later page, so the snapshot is not complete. The status is BLOCKED and the counts are unknown.' },
  supabase_timeout: { exit: 1, status: 'FAILED', cap: '<b>Exit 1.</b> The Supabase write times out. The status is FAILED, and the report warns that database writes may have happened.' },
  sharing: { exit: 2, status: null, cap: '<b>Exit 2.</b> The Doc is shared with another account. The reporter stops before any LinkedIn or Supabase work and writes nothing.' }
};

/* ---------- python-ish highlighter ---------- */
var KW = /^(await|async|except|try|if|else|is|None|return|def|import|from|for|in)$/;
function hl(src, pre) {
  pre = pre == null ? 'tk-' : pre;
  var out = '', re = /("[^"]*"|\b[A-Za-z_]\w*\b|\b\d+\b|#.*$|[^"A-Za-z_\d#]+)/g, m;
  while ((m = re.exec(src))) {
    var t = m[0], after = src.slice(re.lastIndex);
    if (t[0] === '"') out += '<span class="' + pre + 's">' + esc(t) + '</span>';
    else if (t[0] === '#') out += '<span class="' + pre + 'c">' + esc(t) + '</span>';
    else if (KW.test(t)) out += '<span class="' + pre + 'kw">' + t + '</span>';
    else if (/^\d+$/.test(t)) out += '<span class="' + pre + 'n">' + t + '</span>';
    else if (/^[A-Za-z_]/.test(t) && after[0] === '(') out += '<span class="' + pre + 'fn">' + t + '</span>';
    else out += esc(t);
  }
  return out;
}

/* =========================================================
   switcher
   ========================================================= */
var ORDER = ['control', 'a', 'b', 'c'];
var onShow = [];
function show(v) {
  ORDER.forEach(function (k) { $('#c' + k).classList.toggle('on', k === v); });
  $$('.sw button').forEach(function (b) { b.classList.toggle('on', b.dataset.v === v); });
  if (!CLIP && history.replaceState) history.replaceState(null, '', '#' + v);
  onShow.forEach(function (f) { f(v); });
}
$$('.sw button').forEach(function (b) { b.addEventListener('click', function () { show(b.dataset.v); }); });
document.addEventListener('keydown', function (e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  var t = e.target && e.target.tagName;
  if (t === 'INPUT' || t === 'TEXTAREA') return;
  var i = '1234'.indexOf(e.key);
  if (i >= 0) show(ORDER[i]);
});

/* =========================================================
   A: a tiny manim-style stage. Objects get keyframes; each frame
   transitions position, size, colour, opacity, write (clip) and draw (dash).
   ========================================================= */
function Stage(el, spec) {
  var self = this;
  this.el = el; this.o = {}; this.frames = spec.frames;
  var svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 1200 640');
  spec.objs.forEach(function (d) {
    var e;
    if (d.p) {
      e = document.createElementNS(NS, 'path');
      e.setAttribute('d', d.p); e.setAttribute('stroke', d.c); e.setAttribute('stroke-width', d.sw || 3);
      e.setAttribute('pathLength', '1'); e.style.strokeDasharray = '1';
      svg.appendChild(e);
    } else {
      e = document.createElement('div');
      e.className = 'o' + (d.mono ? ' mono' : '') + (d.r ? ' r' : '') + (d.wrap ? ' wrap' : '');
      e.innerHTML = d.t;
      e.style.left = d.x + 'px'; e.style.top = d.y + 'px'; e.style.fontSize = d.s + 'px';
      if (d.c) e.style.color = d.c;
      if (d.i) e.style.fontStyle = 'italic';
      if (d.w) e.style.width = d.w + 'px';
      if (d.ctr) { e.style.transform = 'translate(-50%,-50%)'; e.style.textAlign = 'center'; }
      el.appendChild(e);
    }
    self.o[d.id] = e;
  });
  el.appendChild(svg);
}
Stage.prototype.apply = function (f, instant) {
  var wait = 0;
  for (var id in f.s) {
    var e = this.o[id], p = f.s[id], t = p.t || f.t, dl = p.dl || 0;
    if (!e) continue;
    wait = Math.max(wait, t + dl);
    e.style.transition = instant ? 'none' : 'all ' + t + 'ms cubic-bezier(.45,0,.25,1) ' + dl + 'ms';
    var svgEl = e instanceof SVGElement;
    for (var k in p) {
      var v = p[k];
      if (k === 'x') e.style.left = v + 'px';
      else if (k === 'y') e.style.top = v + 'px';
      else if (k === 's') e.style.fontSize = v + 'px';
      else if (k === 'c') { if (svgEl) e.style.stroke = v; else e.style.color = v; }
      else if (k === 'o') e.style.opacity = v;
      else if (k === 'w') e.style.clipPath = 'inset(-30% ' + (100 - v * 100) + '% -30% -3%)';
      else if (k === 'dr') e.style.strokeDashoffset = String(1 - v);
      else if (k === 'd') e.style.d = 'path("' + v + '")';
    }
  }
  return wait;
};
Stage.prototype.reset = function () { this.apply(this.frames[0], true); this.el.getBoundingClientRect(); };
Stage.prototype.end = function () { var s = this; this.frames.forEach(function (f) { s.apply(f, true); }); };
Stage.prototype.play = async function () {
  if (this.busy) return; this.busy = true;
  this.reset(); await sleep(60);
  for (var i = 1; i < this.frames.length; i++) { var w = this.apply(this.frames[i], false); await sleep(w + (this.frames[i].hold || 0)); }
  this.busy = false;
};

var BLUE = '#58C4DD', GREEN = '#83C167', YEL = '#FFFF00', RED = '#FC6255', WHITE = '#ECE9E2', GRAY = '#8f8b84';
function brace(x, y1, y2) { var w = 12, m = (y1 + y2) / 2; return 'M' + (x + w) + ',' + y1 + ' Q' + x + ',' + y1 + ' ' + x + ',' + (y1 + w) + ' L' + x + ',' + (m - w) + ' Q' + x + ',' + m + ' ' + (x - w) + ',' + m + ' Q' + x + ',' + m + ' ' + x + ',' + (m + w) + ' L' + x + ',' + (y2 - w) + ' Q' + x + ',' + y2 + ' ' + (x + w) + ',' + y2; }
function braceR(x, y1, y2) { var w = 12, m = (y1 + y2) / 2; return 'M' + (x - w) + ',' + y1 + ' Q' + x + ',' + y1 + ' ' + x + ',' + (y1 + w) + ' L' + x + ',' + (m - w) + ' Q' + x + ',' + m + ' ' + (x + w) + ',' + m + ' Q' + x + ',' + m + ' ' + x + ',' + (m + w) + ' L' + x + ',' + (y2 - w) + ' Q' + x + ',' + y2 + ' ' + (x - w) + ',' + y2; }
function head(x, y, fx, fy) { var a = Math.atan2(y - fy, x - fx), L = 15, s = 0.45; return 'M' + (x - L * Math.cos(a - s)).toFixed(1) + ',' + (y - L * Math.sin(a - s)).toFixed(1) + ' L' + x + ',' + y + ' L' + (x - L * Math.cos(a + s)).toFixed(1) + ',' + (y - L * Math.sin(a + s)).toFixed(1); }
function hide(ids) { var s = {}; ids.forEach(function (i) { s[i] = { w: 0 }; }); return s; }
function merge() { var o = {}; for (var i = 0; i < arguments.length; i++) for (var k in arguments[i]) o[k] = arguments[i][k]; return o; }
function stag(ids, base, props) { var s = {}; ids.forEach(function (id, i) { s[id] = merge(props, { dl: base * i }); }); return s; }

function sceneDoc() {
  var RY = function (i) { return 190 + i * 34; };
  var objs = [
    { id: 'hl', t: 'complete scenario', x: 60, y: 150, s: 24, i: 1, c: GRAY },
    { id: 'st', t: 'Status: COMPLETE', x: 60, y: 200, s: 26, c: YEL },
    { id: 'hb', t: 'Google Doc before the run', x: 590, y: 62, s: 24, i: 1, c: GRAY },
    { id: 'ha', t: 'Google Doc after the run', x: 590, y: 62, s: 24, i: 1, c: GRAY },
    { id: 'note', t: '🧭 Operator note', x: 590, y: 110, s: 22 },
    { id: 'beg', t: '[BEGIN AUTOMATED REPORT]', x: 590, y: 150, s: 17, mono: 1, c: BLUE },
    { id: 'old', t: 'old', x: 590, y: 200, s: 22 },
    { id: 'end', t: '[END AUTOMATED REPORT]', x: 590, y: 250, s: 17, mono: 1, c: BLUE },
    { id: 'keep', t: 'Keep this note.', x: 590, y: 295, s: 22 },
    { id: 'lab', t: 'new status lands here', x: 532, y: 172, s: 19, i: 1, c: YEL, r: 1 },
    { id: 'r0', t: 'LinkedIn CONNECTIONS reconciliation', x: 590, y: RY(0), s: 17, c: GRAY },
    { id: 'r1', t: 'Status: COMPLETE', x: 60, y: 200, s: 26, c: YEL },
    { id: 'r2', t: RUNTIME, x: 590, y: RY(2), s: 17, c: GRAY },
    { id: 'r9', t: 'Next action: review the aggregate counts; investigate unmatched rows if needed.', x: 590, y: RY(9), s: 15, c: GRAY },
    { id: 'ck1', t: '✓ unchanged', x: 790, y: 110, s: 19, i: 1, c: GREEN },
    { id: 'ck2', t: '✓ unchanged', x: 790, y: 578, s: 19, i: 1, c: GREEN },
    { id: 'br', p: brace(558, 176, 224), c: YEL },
    { id: 'strike', p: 'M587,201 L627,201', c: RED },
    { id: 'arr', p: 'M372,318 C448,318 508,286 534,218', c: WHITE, sw: 2.5 },
    { id: 'arh', p: head(534, 218, 508, 286), c: WHITE, sw: 2.5 }
  ];
  var cs = [], cp = [];
  COUNTS.forEach(function (c, i) {
    objs.push({ id: 'c' + i, t: c[0] + ': ' + c[1], x: 60, y: 250 + i * 34, s: 22 });
    objs.push({ id: 'k' + i, t: c[0] + ': ' + c[1], x: 60, y: 250 + i * 34, s: 22 });
    cs.push('c' + i); cp.push('k' + i);
  });
  var copies = ['r1'].concat(cp);
  var f0 = merge(hide(['hl', 'st', 'hb', 'note', 'beg', 'old', 'end', 'keep', 'lab', 'r0', 'r2', 'r9', 'ck1', 'ck2'].concat(cs)), {
    ha: { o: 0, w: 1, y: 86 }, br: { dr: 0, d: brace(558, 176, 224), o: 1 }, strike: { dr: 0, o: 1 }, arr: { dr: 0, o: 1 }, arh: { dr: 0, o: 1 },
    old: { w: 0, o: 1, c: WHITE }, note: { w: 0, c: WHITE }, keep: { w: 0, c: WHITE, y: 295 }, end: { w: 0, y: 250 }, lab: { w: 0, y: 172 },
    st: { w: 0, o: 1 }, hb: { w: 0, o: 1, y: 62 }
  });
  copies.forEach(function (id, i) { f0[id] = { o: 0, w: 1, x: 60, y: i === 0 ? 200 : 250 + (i - 1) * 34, s: i === 0 ? 26 : 22 }; });
  cs.forEach(function (id) { f0[id].o = 1; });
  var fly = {};
  copies.forEach(function (id, i) { fly[id] = { x: 590, y: i === 0 ? RY(1) : RY(2 + i), s: i === 0 ? 22 : 20, dl: i * 45 }; });
  var dimL = {}; ['st'].concat(cs).forEach(function (id) { dimL[id] = { o: 0.35 }; });
  var appear = {}; copies.forEach(function (id) { appear[id] = { o: 1, t: 1 }; });
  return {
    objs: objs,
    frames: [
      { t: 1, s: f0 },
      { t: 650, s: stag(['hl', 'st'].concat(cs), 70, { w: 1 }) },
      { t: 650, s: stag(['hb', 'note', 'beg', 'old', 'end', 'keep'], 80, { w: 1 }) },
      { t: 550, s: { br: { dr: 1 }, lab: { w: 1, dl: 180 } } },
      { t: 450, s: { old: { c: RED }, strike: { dr: 1, dl: 120 } } },
      { t: 550, s: { arr: { dr: 1 }, arh: { dr: 1, dl: 420, t: 160 } } },
      { t: 1, s: appear },
      { t: 1100, s: merge(fly, dimL, { old: { o: 0 }, strike: { o: 0 }, end: { y: 536 }, keep: { y: 578 }, br: { d: brace(558, 172, 512) }, lab: { y: 156 }, arr: { o: 0 }, arh: { o: 0 }, hb: { o: 0, y: 40 }, ha: { o: 1, y: 62 } }) },
      { t: 550, s: stag(['r0', 'r2', 'r9'], 90, { w: 1 }) },
      { t: 550, s: { note: { c: GREEN }, keep: { c: GREEN }, ck1: { w: 1 }, ck2: { w: 1, dl: 120 } } }
    ]
  };
}

function sceneCode() {
  var CH = 11.4, X = 120;
  var rows = [
    [36, 'await publisher.prepare()', 0, 120], ['⋮', '', 0, 160],
    [42, 'summary = await reconcile_connections(guarded_linkedin, supabase)', 1, 200],
    [43, 'except LinkedInAPIError:', 0, 240],
    [44, 'result = ReportResult("BLOCKED", datetime.now(timezone.utc), None)', 1, 280], ['⋮', '', 0, 320],
    [50, 'except Exception:', 0, 360],
    [51, 'result = ReportResult("BLOCKED" if linkedin is None else "FAILED", …)', 1, 400], ['⋮', '', 0, 440],
    [66, 'await publisher.publish(result)', 0, 480]
  ];
  var objs = [{ id: 'fl', t: '<a href="' + RUN + '21">scripts/report_connections_doc.py</a> · run()', x: 60, y: 44, s: 18, mono: 1, c: GRAY }];
  var lines = [];
  rows.forEach(function (r, i) {
    var id = 'L' + i;
    if (r[0] === '⋮') objs.push({ id: id, t: '⋮', x: X + 4, y: r[3], s: 22, c: GRAY });
    else {
      objs.push({ id: 'n' + i, t: String(r[0]), x: 100, y: r[3], s: 17, mono: 1, c: '#6d6a64', r: 1 });
      objs.push({ id: id, t: esc(r[1]), x: X + r[2] * 4 * CH, y: r[3], s: 19, mono: 1 });
    }
    lines.push(id); if (r[0] !== '⋮') lines.push('n' + i);
  });
  objs.push(
    { id: 'co', t: 'Google checks run first', x: 560, y: 84, s: 30, c: BLUE },
    { id: 'ca', p: 'M552,94 C505,94 470,120 424,120', c: BLUE, sw: 2.5 },
    { id: 'cah', p: head(424, 120, 470, 120), c: BLUE, sw: 2.5 },
    { id: 'b1', p: braceR(975, 222, 298), c: WHITE, sw: 2.5 },
    { id: 'b1t', t: 'LinkedIn error<br>gives <span class="ky">BLOCKED</span>', x: 1000, y: 260, s: 21 },
    { id: 'b2', p: braceR(985, 342, 418), c: WHITE, sw: 2.5 },
    { id: 'b2t', t: 'other errors<br>usually <span class="ky">FAILED</span>', x: 1010, y: 380, s: 21 },
    { id: 'bt', t: 'The script <span class="kb">checks the Doc</span> before it reads LinkedIn or writes to Supabase.', x: 60, y: 572, s: 25 }
  );
  objs.forEach(function (o) { if (o.id === 'b1t' || o.id === 'b2t') { o.wrap = 1; o.w = 190; } });
  var f0 = merge(hide(['fl', 'co', 'b1t', 'b2t', 'bt'].concat(lines)), { ca: { dr: 0 }, cah: { dr: 0 }, b1: { dr: 0 }, b2: { dr: 0 }, L0: { w: 0, c: WHITE } });
  lines.forEach(function (id) { f0[id] = merge(f0[id], { o: 1 }); });
  var focus = function (keep) { var s = {}; ['L0', 'L2', 'L3', 'L4', 'L6', 'L7', 'L9'].forEach(function (id) { s[id] = { o: keep.indexOf(id) >= 0 ? 1 : 0.3 }; }); return s; };
  return {
    objs: objs,
    frames: [
      { t: 1, s: f0 },
      { t: 500, s: stag(['fl'].concat(lines), 45, { w: 1 }) },
      { t: 600, s: { L0: { c: BLUE }, co: { w: 1 }, ca: { dr: 1, dl: 250 }, cah: { dr: 1, dl: 750, t: 160 } } },
      { t: 550, s: merge(focus(['L3', 'L4']), { b1: { dr: 1 }, b1t: { w: 1, dl: 200 } }), hold: 350 },
      { t: 550, s: merge(focus(['L6', 'L7']), { b2: { dr: 1 }, b2t: { w: 1, dl: 200 } }), hold: 350 },
      { t: 700, s: merge(focus(['L0', 'L2', 'L3', 'L4', 'L6', 'L7', 'L9']), { bt: { w: 1 } }) }
    ]
  };
}

function sceneOutro() {
  var objs = [
    { id: 'l1', t: 'A daily workflow now writes reconciliation status<br>into a private Google Doc.', x: 600, y: 180, s: 44, ctr: 1 },
    { id: 'rc', p: 'M240,322 H960 V508 H240 Z', c: YEL, sw: 3 },
    { id: 'tl', t: '<span style="letter-spacing:.16em;text-transform:uppercase">Review tip</span>', x: 276, y: 360, s: 17, c: YEL },
    { id: 'tt', t: 'Start at <a class="mono" href="' + GDR + '139">publish</a> in <a href="' + GDR + '139">google_doc_report.py</a>. The tests use fake Google servers.', x: 276, y: 432, s: 27, wrap: 1, w: 650 }
  ];
  return {
    objs: objs,
    frames: [
      { t: 1, s: merge(hide(['l1', 'tl', 'tt']), { rc: { dr: 0 }, l1: { w: 0 } }) },
      { t: 1300, s: { l1: { w: 1 } }, hold: 200 },
      { t: 800, s: { rc: { dr: 1 }, tl: { w: 1, dl: 300 } } },
      { t: 700, s: { tt: { w: 1 } } }
    ]
  };
}

var STAGES = {};
function buildA() {
  STAGES.aDoc = new Stage($('#aDoc'), sceneDoc());
  STAGES.aCode = new Stage($('#aCode'), sceneCode());
  STAGES.aOutro = new Stage($('#aOutro'), sceneOutro());
  for (var k in STAGES) STAGES[k].end();
  $$('.a-play').forEach(function (b) { b.addEventListener('click', function () { STAGES[b.dataset.stage].play(); }); });
}
function fitStages() {
  $$('.a-wrap').forEach(function (w) { var s = w.clientWidth / 1200; if (s > 0) w.firstElementChild.style.transform = 'scale(' + s + ')'; });
}

/* =========================================================
   B: explorable models with steppers
   ========================================================= */
function Stepper(host, n, labels, go) {
  host.innerHTML = '<button type="button" class="nav prev" aria-label="Previous step">&#8592;</button><div class="b-dots"></div><button type="button" class="nav next" aria-label="Next step">&#8594;</button><span class="b-count"></span>';
  var dots = $('.b-dots', host);
  for (var i = 1; i <= n; i++) { var d = document.createElement('button'); d.type = 'button'; d.dataset.n = i; d.setAttribute('aria-label', 'Step ' + i + ': ' + labels[i - 1]); d.title = labels[i - 1]; dots.appendChild(d); }
  var cur = 1;
  function set(k) {
    cur = Math.max(1, Math.min(n, k));
    $$('button', dots).forEach(function (d) { var j = +d.dataset.n; d.classList.toggle('on', j === cur); d.classList.toggle('done', j < cur); });
    $('.prev', host).disabled = cur === 1; $('.next', host).disabled = cur === n;
    $('.b-count', host).textContent = 'Step ' + cur + ' of ' + n;
    go(cur);
  }
  $('.prev', host).addEventListener('click', function () { set(cur - 1); });
  $('.next', host).addEventListener('click', function () { set(cur + 1); });
  $$('button', dots).forEach(function (d) { d.addEventListener('click', function () { set(+d.dataset.n); }); });
  this.set = set; this.get = function () { return cur; };
}
function bindProse(chap, stepper) {
  $$('.b-step', chap).forEach(function (p) { p.addEventListener('click', function (e) { if (e.target.closest('a')) return; stepper.set(+p.dataset.step); }); });
}
function markProse(chap, k) { $$('.b-step', chap).forEach(function (p) { p.classList.toggle('on', +p.dataset.step === k); }); }

var BDOC = { step: 5, scen: 'complete' };
function buildBDoc() {
  var fig = $('#bDoc'), model = $('.b-model', fig);
  model.innerHTML =
    '<div class="b-run"><h4>This run</h4><div class="kvs"></div><div class="exit"></div></div>' +
    '<div class="b-sheet"><div class="doc-bar"><i></i><span class="dtitle"></span></div><div class="doc-body">' +
    '<div class="b-line" data-k="note">🧭 Operator note<span class="tag">unchanged ✓</span></div>' +
    '<div class="b-line mk">[BEGIN AUTOMATED REPORT]</div>' +
    '<div class="b-region"><span class="tab">Report slot · new status lands here</span><div class="b-line b-old">old</div><div class="news"></div></div>' +
    '<div class="b-line mk">[END AUTOMATED REPORT]</div>' +
    '<div class="b-line" data-k="keep">Keep this note.<span class="tag">unchanged ✓</span></div>' +
    '<div class="b-stop">Preflight refused the run: the Doc is shared with another account. Nothing between the markers changes.</div>' +
    '</div></div><svg class="b-link"><path d=""/></svg>';
  var lastScen = null;
  function render() {
    var sc = SCEN[BDOC.scen], st = BDOC.step, wrote = sc.status !== null;
    $$('.b-scen button', fig).forEach(function (b) { b.classList.toggle('on', b.dataset.scen === BDOC.scen); });
    var kv = '<div class="kv' + (st === 4 && wrote ? ' lit' : '') + '"><span>Status</span><span>' + (sc.status || 'none') + '</span></div>';
    COUNTS.forEach(function (c) { kv += '<div class="kv' + (st === 4 && wrote ? ' lit' : '') + '"><span>' + c[0] + '</span><span>' + (sc.status === 'COMPLETE' ? c[1] : sc.status ? 'unknown' : 'none') + '</span></div>'; });
    $('.kvs', model).innerHTML = kv;
    $('.exit', model).textContent = 'Exit code ' + sc.exit + (wrote ? '' : ' · nothing written');
    $('.b-run', model).classList.toggle('wait', st < 4);
    if (lastScen !== BDOC.scen) {
      $('.news', model).innerHTML = wrote ? report(sc.status).map(function (l, i) { return '<div class="b-line b-new' + (i === 1 ? ' st' : '') + '">' + esc(l) + '</div>'; }).join('') : '';
      lastScen = BDOC.scen; model.getBoundingClientRect();
    }
    $$('.b-line.mk', model).forEach(function (m) { m.classList.toggle('lit', st >= 2 && st <= 4); });
    $('.b-region', model).classList.toggle('lit', st >= 2 && st <= 4);
    var old = $('.b-old', model);
    old.classList.toggle('strike', wrote && st >= 3);
    old.classList.toggle('gone', wrote && st >= 4);
    $$('.b-new', model).forEach(function (n) { n.classList.toggle('in', st >= 4); n.classList.toggle('fresh', st === 4); });
    $$('[data-k="note"],[data-k="keep"]', model).forEach(function (n) { n.classList.toggle('kept', st >= 5); });
    $('.b-stop', model).classList.toggle('show', !wrote && st >= 3);
    $('.dtitle', model).textContent = 'Google Doc ' + (wrote && st >= 4 ? 'after' : 'before') + ' the run';
    $('.b-fcap', fig).innerHTML = sc.cap;
    markProse($('#bDocChap'), st);
    setTimeout(drawLink, st === 4 ? 520 : 0);
  }
  function drawLink() {
    var path = $('.b-link path', model), sc = SCEN[BDOC.scen];
    if (BDOC.step !== 4 || !sc.status) { path.setAttribute('d', ''); return; }
    var m = model.getBoundingClientRect(), a = $('.kvs', model).getBoundingClientRect(), r = $('.b-region', model).getBoundingClientRect();
    if (a.right > r.left - 8) { path.setAttribute('d', ''); return; }
    var x1 = a.right - m.left + 4, y1 = a.top + a.height / 2 - m.top, x2 = r.left - m.left - 2, y2 = r.top + r.height / 2 - m.top;
    path.setAttribute('d', 'M' + x1 + ',' + y1 + ' C' + (x1 + 20) + ',' + y1 + ' ' + (x2 - 20) + ',' + y2 + ' ' + x2 + ',' + y2);
  }
  var stepper = new Stepper($('.b-stepper', fig), 5, ['Before the run', 'Find the markers', 'Remove the old text', 'Write the report', 'Leave the notes alone'], function (k) { BDOC.step = k; render(); });
  $$('.b-scen button', fig).forEach(function (b) { b.addEventListener('click', function () { BDOC.scen = b.dataset.scen; render(); }); });
  bindProse($('#bDocChap'), stepper);
  stepper.set(5);
  window.addEventListener('resize', drawLink);
  onShow.push(function (v) { if (v === 'b') drawLink(); });
  return stepper;
}

var BCODE_ROWS = [
  [36, 'await publisher.prepare()', 0], ['fold', '5 lines'], [42, 'summary = await reconcile_connections(guarded_linkedin, supabase)', 1],
  [43, 'except LinkedInAPIError:', 0], [44, 'result = ReportResult("BLOCKED", datetime.now(timezone.utc), None)', 1], ['fold', '5 lines'],
  [50, 'except Exception:', 0], [51, 'result = ReportResult("BLOCKED" if linkedin is None else "FAILED", …)', 1], ['fold', '14 lines'],
  [66, 'await publisher.publish(result)', 0]
];
function buildBCode() {
  var fig = $('#bCode');
  $('.b-flow', fig).innerHTML = '<div class="b-node" data-n="1"><small>1 · Google</small>Check the Doc</div><div class="b-arrow">&#8594;</div><div class="b-node" data-n="2"><small>2 · LinkedIn and Supabase</small><span class="sub">Reconcile</span></div><div class="b-arrow">&#8594;</div><div class="b-node" data-n="3"><small>3 · Google</small>Publish the status</div><div class="b-out"></div>';
  var html = '';
  BCODE_ROWS.forEach(function (r) {
    if (r[0] === 'fold') html += '<div class="b-cl fold"><i></i>⋯ ' + r[1] + '</div>';
    else html += '<div class="b-cl" data-l="' + r[0] + '"><i>' + r[0] + '</i>' + '    '.repeat(r[2]) + hl(r[1], '') + (r[0] === 36 ? '<span class="b-side">  &#8592; Google checks run first · <a href="' + RUN + '36">report_connections_doc.py:36</a></span>' : '') + '</div>';
  });
  $('.b-codewrap', fig).innerHTML = html;
  var STEPS = {
    1: { lit: [36, 42, 66], n2: 'Reconcile', bad: false, out: 'Status: COMPLETE' },
    2: { lit: [43, 44, 66], n2: 'LinkedInAPIError', bad: true, out: 'Status: BLOCKED' },
    3: { lit: [50, 51, 66], n2: 'Any other error', bad: true, out: 'Status: FAILED' }
  };
  var stepper = new Stepper($('.b-stepper', fig), 3, ['Google first', 'LinkedIn fails', 'Something else fails'], function (k) {
    var s = STEPS[k];
    $$('.b-cl[data-l]', fig).forEach(function (c) { c.classList.toggle('on', s.lit.indexOf(+c.dataset.l) >= 0); });
    var n = $$('.b-node', fig);
    n[0].className = 'b-node ok' + (k === 1 ? ' lit' : '');
    n[1].className = 'b-node ' + (s.bad ? 'bad lit' : 'ok');
    n[2].className = 'b-node ok';
    $('.sub', fig).textContent = s.n2;
    $('.b-out', fig).textContent = s.out;
    markProse($('#bCodeChap'), k);
  });
  bindProse($('#bCodeChap'), stepper);
  stepper.set(1);
  return stepper;
}

/* =========================================================
   C: editor buffers whose rows move between steps
   ========================================================= */
function Editor(root, cfg) {
  var self = this;
  this.cfg = cfg; this.cur = cfg.start != null ? cfg.start : cfg.steps.length - 1;
  var tabs = cfg.tabs.map(function (t, i) { return '<div class="c-tab' + (i === 0 ? ' on' : '') + '">' + t + '</div>'; }).join('');
  var panes = cfg.panes.map(function (p, i) { return '<div class="c-pane">' + (p.title ? '<h5>' + p.title + '</h5>' : '') + '<div class="c-buf" data-p="' + i + '"></div></div>'; }).join('');
  var steps = cfg.steps.map(function (s, i) { return '<button type="button" data-i="' + i + '">' + (i + 1) + ' · ' + s.name + '</button>'; }).join('');
  root.innerHTML = '<div class="c-win ' + (cfg.cls || '') + '"><div class="c-tabs">' + tabs + '</div><div class="c-panes' + (cfg.panes.length === 1 ? ' one' : '') + '">' + panes + '</div>' +
    '<div class="c-bar"><button type="button" class="c-btn play">&#9654; Play</button><button type="button" class="c-btn prev" aria-label="Previous step">&#8592;</button><div class="c-steps">' + steps + '</div><button type="button" class="c-btn next" aria-label="Next step">&#8594;</button></div></div>' +
    '<p class="c-cap"></p>' + (cfg.after || '');
  this.rows = cfg.panes.map(function (p, pi) {
    var buf = $('.c-buf[data-p="' + pi + '"]', root), map = {};
    p.rows.forEach(function (r) {
      var e = document.createElement('div');
      e.className = 'c-row gone' + (r.fold ? ' fold' : '') + (r.ghost ? ' ghost' : '');
      e.innerHTML = '<span class="g"><span class="ln"></span><b></b></span><span class="t">' + r.h + '</span>' + (r.inlay ? '<span class="c-inlay ' + (r.inlayTone || 'mint') + ' hide">' + r.inlay + '</span>' : '');
      buf.appendChild(e); map[r.k] = { el: e, spec: r };
    });
    return { buf: buf, map: map, spec: p };
  });
  $('.play', root).addEventListener('click', function () { self.play(); });
  $('.prev', root).addEventListener('click', function () { self.go(self.cur - 1); });
  $('.next', root).addEventListener('click', function () { self.go(self.cur + 1); });
  $$('.c-steps button', root).forEach(function (b) { b.addEventListener('click', function () { self.go(+b.dataset.i); }); });
  this.root = root;
  this.go(this.cur, true);
}
Editor.prototype.go = function (i, instant) {
  var cfg = this.cfg, root = this.root;
  i = Math.max(0, Math.min(cfg.steps.length - 1, i)); this.cur = i;
  var st = cfg.steps[i];
  this.rows.forEach(function (pane, pi) {
    var s = st.panes[pi] || {}, vis = s.show || pane.spec.rows.map(function (r) { return r.k; });
    var probe = pane.map[pane.spec.rows[0].k].el, H = probe.offsetHeight || 30;
    var lit = s.lit || [], add = s.add || [], del = s.del || [], inl = s.inlay || [];
    var idx = 0;
    pane.spec.rows.forEach(function (r) {
      var o = pane.map[r.k], e = o.el, on = vis.indexOf(r.k) >= 0;
      if (instant) e.style.transition = 'none';
      if (on) {
        var entering = e.classList.contains('gone');
        e.style.top = (idx * H) + 'px';
        if (entering && !instant) { e.classList.add('enter'); e.style.transitionDelay = '0s,.32s'; e.getBoundingClientRect(); setTimeout(function (x) { x.style.transitionDelay = ''; }, 900, e); }
        e.classList.remove('gone');
        if (entering && !instant) requestAnimationFrame(function () { e.classList.remove('enter'); });
        idx++;
        $('.ln', e).textContent = r.fold || r.ghost ? '' : (r.ln != null ? r.ln : idx);
      } else {
        e.classList.add('gone'); e.classList.remove('enter');
      }
      e.classList.toggle('lit', lit.indexOf(r.k) >= 0);
      e.classList.toggle('dim', lit.length > 0 && lit.indexOf(r.k) < 0 && !r.fold);
      e.classList.toggle('add', add.indexOf(r.k) >= 0);
      e.classList.toggle('del', del.indexOf(r.k) >= 0);
      $('b', e).textContent = add.indexOf(r.k) >= 0 ? '+' : del.indexOf(r.k) >= 0 ? '−' : '';
      var ch = $('.c-inlay', e); if (ch) ch.classList.toggle('hide', inl.indexOf(r.k) < 0);
      if (instant) { e.getBoundingClientRect(); e.style.transition = ''; }
    });
    pane.buf.style.height = (Math.max(idx, s.minRows || 0) * H) + 'px';
  });
  $$('.c-steps button', root).forEach(function (b) { var j = +b.dataset.i; b.classList.toggle('on', j === i); b.classList.toggle('done', j < i); });
  $('.prev', root).disabled = i === 0; $('.next', root).disabled = i === cfg.steps.length - 1;
  $('.c-cap', root).innerHTML = st.cap;
};
Editor.prototype.play = async function (gap) {
  if (this.busy) return; this.busy = true;
  this.go(0); await sleep(gap || 1300);
  for (var i = 1; i < this.cfg.steps.length; i++) { this.go(i); await sleep(gap || 1300); }
  this.busy = false;
};
Editor.prototype.relayout = function () { this.go(this.cur, true); };

function docRow(l) {
  if (/^\[/.test(l)) return '<span class="tk-mk">' + esc(l) + '</span>';
  var m = /^([^:]+): (.*)$/.exec(l);
  if (m && /^Status/.test(l)) return esc(m[1]) + ': <span class="tk-h">' + esc(m[2]) + '</span>';
  if (m && /^\d+$/.test(m[2])) return esc(m[1]) + ': <span class="tk-n">' + m[2] + '</span>';
  return esc(l);
}
var EDITORS = {};
function buildC() {
  var rep = report('COMPLETE'), rk = rep.map(function (_, i) { return 'r' + i; });
  var left = [
    'result = ReportResult(', '    "COMPLETE",', '    datetime.now(timezone.utc),', '    ReportCounts(',
    '        fetched_rows=4,', '        matched_rows=3,', '        unique_matched=2,', '        unmatched_rows=1,', '        inserted=1,', '        already_present=1,',
    '    ),', ')'
  ].map(function (t, i) { return { k: 'a' + i, h: hl(t), ln: i + 1 }; });
  var right = [{ k: 'note', h: '🧭 Operator note', inlay: 'unchanged' }, { k: 'beg', h: docRow('[BEGIN AUTOMATED REPORT]') }, { k: 'old', h: 'old', inlay: 'new status lands here', inlayTone: 'blue' }]
    .concat(rep.map(function (l, i) { return { k: 'r' + i, h: docRow(l) }; }))
    .concat([{ k: 'end', h: docRow('[END AUTOMATED REPORT]') }, { k: 'keep', h: 'Keep this note.', inlay: 'unchanged' }]);
  var before = ['note', 'beg', 'old', 'end', 'keep'];
  var after = ['note', 'beg'].concat(rk, ['end', 'keep']);
  EDITORS.cDoc = new Editor($('#cDoc'), {
    tabs: ['Google Doc report <span class="badge">complete scenario</span>'],
    panes: [{ title: 'run() result, from the test run', rows: left }, { title: 'Google Doc text', rows: right }],
    steps: [
      { name: 'before', cap: 'Google Doc before the run. The reporter owns only the text between the two markers.', panes: [{}, { show: before, minRows: 15 }] },
      { name: 'find the markers', cap: 'It finds exactly one begin marker and one end marker. The new status lands between them.', panes: [{}, { show: before, lit: ['beg', 'end', 'old'], inlay: ['old'], minRows: 15 }] },
      { name: 'remove old', cap: 'One batch update removes <code>old</code> from between the markers …', panes: [{}, { show: before, lit: ['old'], del: ['old'], inlay: ['old'], minRows: 15 }] },
      { name: 'write the report', cap: '… and inserts the status, the run time, the six counts and a next action.', panes: [{ lit: ['a1', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9'] }, { show: ['note', 'beg', 'old'].concat(rk, ['end', 'keep']), lit: rk, add: rk, del: ['old'], minRows: 15 }] },
      { name: 'after', cap: 'Google Doc after the run. The notes outside the markers are unchanged; the test checks both ends at <a href="' + E2E + '237">e2e_doc_report.py:237</a>.', panes: [{}, { show: after, lit: ['note', 'keep'], inlay: ['note', 'keep'], minRows: 15 }] }
    ]
  });
  var R = function (k, ln, t, ind, extra) { return merge({ k: k, ln: ln, h: '    '.repeat(ind) + hl(t) }, extra || {}); };
  var runRows = [
    { k: 'ghost', h: '# This file is new in this pull request.', ghost: 1 },
    R('l36', 36, 'await publisher.prepare()', 0, { inlay: 'Google checks run first <a href="' + RUN + '36">report_connections_doc.py:36</a>' }),
    { k: 'f36', h: '⋯ 5 lines', fold: 1 },
    R('l42', 42, 'summary = await reconcile_connections(guarded_linkedin, supabase)', 1),
    { k: 'f42', h: '⋯ 23 lines', fold: 1 },
    R('l43', 43, 'except LinkedInAPIError:', 0),
    R('l44', 44, 'result = ReportResult("BLOCKED", datetime.now(timezone.utc), None)', 1, { inlay: 'status BLOCKED', inlayTone: 'blue' }),
    { k: 'f44a', h: '⋯ 21 lines', fold: 1 },
    { k: 'f44b', h: '⋯ 5 lines', fold: 1 },
    R('l50', 50, 'except Exception:', 0),
    R('l51', 51, 'result = ReportResult("BLOCKED" if linkedin is None else "FAILED", …)', 1, { inlay: 'usually FAILED', inlayTone: 'blue' }),
    { k: 'f51', h: '⋯ 14 lines', fold: 1 },
    R('l66', 66, 'await publisher.publish(result)', 0)
  ];
  var s1 = ['l36', 'f36', 'l42', 'f42', 'l66'], s2 = ['l36', 'f36', 'l42', 'l43', 'l44', 'f44a', 'l66'], s3 = ['l36', 'f36', 'l42', 'l43', 'l44', 'f44b', 'l50', 'l51', 'f51', 'l66'];
  EDITORS.cRun = new Editor($('#cRun'), {
    tabs: ['<a href="' + RUN + '21">scripts/report_connections_doc.py</a> <span class="badge">new file</span>'],
    panes: [{ title: 'def run() -> int:', rows: runRows }],
    steps: [
      { name: 'before', cap: '<code>scripts/report_connections_doc.py</code> does not exist before this pull request.', panes: [{ show: ['ghost'], minRows: 10 }] },
      { name: 'happy path', cap: 'Google checks run first. Then the script reconciles LinkedIn into Supabase and publishes the result.', panes: [{ show: s1, lit: ['l36', 'l42', 'l66'], add: ['l36', 'l42', 'l66'], inlay: ['l36'], minRows: 10 }] },
      { name: 'LinkedIn error', cap: 'A LinkedIn API error gives the status BLOCKED. The script still publishes that status.', panes: [{ show: s2, lit: ['l43', 'l44'], add: ['l43', 'l44'], inlay: ['l36', 'l44'], minRows: 10 }] },
      { name: 'other errors', cap: 'Other errors after the LinkedIn client starts usually give FAILED.', panes: [{ show: s3, lit: ['l50', 'l51'], add: ['l50', 'l51'], inlay: ['l36', 'l44', 'l51'], minRows: 10 }] },
      { name: 'read it whole', cap: 'The Doc check on line 36 runs before any LinkedIn or Supabase work.', panes: [{ show: s3, lit: ['l36'], inlay: ['l36', 'l44', 'l51'], minRows: 10 }] }
    ]
  });
  EDITORS.cSum = new Editor($('#cSum'), {
    cls: 'c-sumwin',
    tabs: ['SUMMARY.md'],
    panes: [{ rows: [{ k: 's0', h: '<span class="tk-p">## </span><span class="tk-h">What changed</span>', ln: 1 }, { k: 's1', h: '', ln: 2 }, { k: 's2', h: 'A daily workflow now writes reconciliation status', ln: 3 }, { k: 's3', h: 'into a private Google Doc.', ln: 4 }] }],
    steps: [
      { name: 'empty', cap: 'The summary of the pull request.', panes: [{ show: [], minRows: 4 }] },
      { name: 'heading', cap: 'The summary of the pull request.', panes: [{ show: ['s0'], minRows: 4 }] },
      { name: 'summary', cap: 'The summary of the pull request.', panes: [{ show: ['s0', 's1', 's2', 's3'], lit: ['s2', 's3'], minRows: 4 }] }
    ],
    after: '<aside class="c-tip"><span class="ic">!</span><div><b>Review tip</b>Start at <a href="' + GDR + '139">publish in google_doc_report.py</a>. The tests use fake Google servers.</div></aside>'
  });
  onShow.push(function (v) { if (v === 'c') for (var k in EDITORS) EDITORS[k].relayout(); });
}

/* =========================================================
   Control: animations for the clip
   ========================================================= */
function anim(el, kf, o) { return el.animate(kf, merge({ duration: 500, easing: 'cubic-bezier(.45,0,.25,1)', fill: 'both' }, o || {})); }
var CTL = {
  1: async function (m) {
    var rows = $$('.rowline', m), old = $('[data-k="old"]', m), sv = $('.slot-v', m), st = $('[data-k="st"]', m);
    rows.forEach(function (r, i) { anim(r, [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }], { delay: i * 55, duration: 380 }); });
    old.style.textDecoration = 'none'; sv.style.opacity = 0;
    $$('.keep', m).forEach(function (k) { k.style.boxShadow = 'none'; k.style.borderColor = PAPER ? '#e1d8c4' : '#3a4458'; });
    await sleep(1300);
    old.style.textDecoration = ''; anim(old, [{ opacity: 1 }, { opacity: .45 }], { duration: 400 });
    await sleep(500);
    var a = st.getBoundingClientRect(), b = sv.getBoundingClientRect(), c = st.cloneNode(true);
    c.style.cssText = 'position:fixed;margin:0;z-index:9;left:' + a.left + 'px;top:' + a.top + 'px;width:' + a.width + 'px';
    document.body.appendChild(c);
    await anim(c, [{ transform: 'none' }, { transform: 'translate(' + (b.left - a.left - 10) + 'px,' + (b.top - a.top - 6) + 'px)', width: b.width + 'px' }], { duration: 900 }).finished;
    c.remove(); sv.style.opacity = 1;
    await sleep(350);
    var G = PAPER ? '#2f7d4f' : '#009e73';
    $$('.keep', m).forEach(function (k) { k.style.boxShadow = ''; k.style.borderColor = ''; anim(k, [{ boxShadow: '0 0 0 0 ' + G }, { boxShadow: '0 0 0 6px rgba(0,158,115,.35)' }, { boxShadow: 'inset 0 0 0 1px ' + G }], { duration: 700 }); });
    await sleep(800);
  },
  2: async function (m) {
    $$('.cl', m).forEach(function (r, i) { anim(r, [{ opacity: 0 }, { opacity: 1 }], { delay: i * 70, duration: 300 }); });
    var co = $('.callout', m); co.style.opacity = 0;
    await sleep(900);
    anim($('.hl', m), [{ background: PAPER ? '#ffffff' : '#0e1320' }, { background: PAPER ? '#fff1d6' : '#3a2e1a' }], { duration: 500 });
    co.style.opacity = ''; anim(co, [{ opacity: 0, transform: 'translateX(20px)' }, { opacity: 1, transform: 'none' }], { duration: 600 });
    await sleep(1200);
  },
  3: async function (m) {
    anim($('.outro-l1', m), [{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'none' }], { duration: 700 });
    await sleep(900);
    anim($('.tipcard', m), [{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'none' }], { duration: 600 });
    await sleep(800);
  }
};

/* =========================================================
   boot and clip mode
   ========================================================= */
var params = new URLSearchParams(location.search), CLIP = params.get('clip');
// Flags come from the query (clip recording) or the hash (#control&solo&pal=paper, safe over file://).
function hashView() { return location.hash.slice(1).split('&')[0]; }
var flags = new URLSearchParams(location.search.slice(1) + '&' + location.hash.slice(1).split('&').slice(1).join('&'));
var PAPER = flags.get('pal') === 'paper';
if (PAPER) document.body.classList.add('pal-paper');
if (flags.has('solo')) document.body.classList.add('solo');
buildA(); var BD = buildBDoc(), BC = buildBCode(); buildC();
window.addEventListener('resize', fitStages);
window.addEventListener('hashchange', function () { var h = hashView(); if (ORDER.indexOf(h) >= 0) show(h); });
onShow.push(function (v) { if (v === 'a') fitStages(); });
var start = CLIP || hashView();
show(ORDER.indexOf(start) >= 0 ? start : 'control');
fitStages();

var PLAY = {
  control: function (m, i) { return CTL[i + 1](m); },
  a: function (m, i) { return STAGES[['aDoc', 'aCode', 'aOutro'][i]].play(); },
  b: async function (m, i) {
    if (i === 0) { BDOC.scen = 'complete'; for (var s = 1; s <= 5; s++) { BD.set(s); await sleep(s === 4 ? 1500 : 1150); } }
    else if (i === 1) { for (var k = 1; k <= 3; k++) { BC.set(k); await sleep(1300); } }
    else { anim($('.b-sum', m), [{ opacity: 0 }, { opacity: 1 }], { duration: 700 }); await sleep(600); anim($('.b-tip', m), [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }], { duration: 600 }); await sleep(900); }
  },
  c: function (m, i) { return EDITORS[['cDoc', 'cRun', 'cSum'][i]].play(i === 2 ? 700 : 1100); }
};
var PREP = {
  control: function () {},
  a: function (m, i) { STAGES[['aDoc', 'aCode', 'aOutro'][i]].reset(); },
  b: function (m, i) { if (i === 0) { BDOC.scen = 'complete'; BD.set(1); } if (i === 1) BC.set(1); },
  c: function (m, i) { EDITORS[['cDoc', 'cRun', 'cSum'][i]].go(0, true); }
};
if (CLIP) {
  document.body.classList.add('clip');
  fitStages();
  window.startClip = async function () {
    var ms = $$('#c' + CLIP + ' .moment'), t0 = performance.now();
    window.__marks = [];
    for (var i = 0; i < ms.length; i++) {
      PREP[CLIP](ms[i], i);
      ms[i].classList.add('live');
      if (i > 0) setTimeout(function (prev) { prev.classList.remove('live'); }, 650, ms[i - 1]);
      await sleep(400);
      await PLAY[CLIP](ms[i], i);
      window.__marks.push((performance.now() - t0) / 1000);
      await sleep(1000);
    }
    await sleep(500);
    window.__clipDone = true;
  };
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(function () { fitStages(); window.__ready = true; });
}
})();

