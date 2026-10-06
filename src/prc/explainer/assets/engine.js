(() => {
  const B = window.BOARD;
  const W = 1920, H = 1080;
  const C = { blue: '#58C4DD', green: '#83C167', red: '#FC6255', gold: '#F0AC5F', grey: '#8A93A6', text: '#ECEFF4', dim: '#5B6475', bg: '#0E1320' };
  const STATUS = { modified: C.blue, added: C.green, context: C.grey, removed: C.red, kept: C.grey };
  const TONE = { bad: C.red, good: C.green, info: C.gold };
  const clamp = x => Math.max(0, Math.min(1, x));
  const smooth = x => { x = clamp(x); return x * x * x * (x * (x * 6 - 15) + 10); };
  const prog = (t, a, d = 0.6) => smooth((t - a) / d);
  const easeOut = x => 1 - Math.pow(1 - clamp(x), 3);
  // Flashes attack instantly and decay convexly, so the eye reads them as an impact, not a fade.
  const decay = (t, a, d) => { const q = (t - a) / d; return q >= 0 && q <= 1 ? (1 - q) * (1 - q) : 0; };
  const lerp = (a, b, k) => a + (b - a) * k;
  const rgba = (hex, a) => `rgba(${parseInt(hex.slice(1, 3), 16)},${parseInt(hex.slice(3, 5), 16)},${parseInt(hex.slice(5, 7), 16)},${a.toFixed(3)})`;
  const measure = (() => { const cx = document.createElement('canvas').getContext('2d'); return (text, font) => { cx.font = font; return cx.measureText(text || '').width; }; })();
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = s => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
  const NS = 'http://www.w3.org/2000/svg';
  const S = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs || {}) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const D = (cls, html, parent) => { const d = document.createElement('div'); if (cls) d.className = cls; if (html != null) d.innerHTML = html; if (parent) parent.appendChild(d); return d; };
  const cueT = (s, pred) => { const c = (s.cues || []).find(pred); return c ? c.t : Infinity; };

  const MAKERS = {};

  MAKERS.title = (s, root) => {
    const wrap = D('title-wrap', null, root);
    const kicker = D('kicker', esc(s.kicker), wrap);
    const tl = D('ptitle', null, wrap);
    const chars = [];
    const segs = s.segments || [{ text: s.title }];
    segs.forEach(seg => {
      const span = document.createElement('span');
      if (seg.claim) span.className = 'claim';
      for (const ch of seg.text) { const c = document.createElement('span'); c.textContent = ch; span.appendChild(c); chars.push(c); }
      if (seg.claim) {
        seg.badge = document.createElement('span'); seg.badge.className = 'badge'; seg.badge.textContent = seg.claim; span.appendChild(seg.badge);
        seg.at = cueT(s, c => c.claim === seg.claim);
      }
      seg.span = span; tl.appendChild(span);
    });
    const meta = D('meta', s.meta, wrap);
    const t0 = s.start + 0.5, typing = 1.5;
    return t => {
      kicker.style.opacity = prog(t, s.start + 0.15, 0.5);
      chars.forEach((c, i) => { c.style.opacity = prog(t, t0 + i * typing / chars.length, 0.2); });
      meta.style.opacity = prog(t, t0 + typing, 0.5);
      segs.forEach(seg => {
        if (!seg.claim) return;
        const k = prog(t, seg.at, 0.6);
        seg.span.style.backgroundSize = `${k * 100}% 0.1em`;
        seg.badge.style.opacity = k;
        seg.badge.style.transform = `translateX(-50%) scale(${lerp(1.6, 1, k)})`;
      });
    };
  };

  MAKERS.graph = (s, root) => {
    D('legend', ['new', 'changed', 'existing'].map((l, i) => { const c = [C.green, C.blue, C.grey][i]; return `<span><i style="border-color:${c};background:${c}33"></i>${l}</span>`; }).join(''), root);
    const svg = S('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, style: 'position:absolute;inset:0' }, root);
    S('defs', {}, svg).innerHTML = `<filter id="glow${s.i}" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`;
    const cam = S('g', {}, svg);
    const gE = S('g', {}, cam), gN = S('g', {}, cam), gT = S('g', {}, cam), gX = S('g', {}, cam);
    const byId = {};

    s.nodes.forEach(n => {
      const color = STATUS[n.status];
      const g = S('g', {}, gN);
      S('rect', { width: n.w, height: n.h, rx: 18, fill: color + '22', stroke: color, 'stroke-width': 3 }, g);
      S('text', { x: n.w / 2, y: 45, 'text-anchor': 'middle', class: 'nlabel' }, g).textContent = n.label;
      S('text', { x: n.w / 2, y: 74, 'text-anchor': 'middle', class: 'nsub' }, g).textContent = n.sub;
      const ring = S('rect', { width: n.w, height: n.h, rx: 18, fill: 'none', stroke: color, 'stroke-width': 4, opacity: 0 }, g);
      const mark = S('g', { opacity: 0 }, g);
      const mc = S('circle', { r: 23, fill: C.bg, stroke: C.red, 'stroke-width': 3 }, mark);
      const mt = S('text', { y: 11, 'text-anchor': 'middle', class: 'mark', fill: C.red }, mark);
      byId[n.id] = { n, g, ring, mark, mc, mt, show: Infinity, pulses: [], markAt: Infinity };
    });

    const edges = {};
    s.edges.forEach(e => {
      const a = byId[e.s].n, b = byId[e.t].n;
      const x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x - 16, y2 = b.y + b.h / 2;
      const dx = Math.max(50, (x2 - x1) * 0.5);
      const color = STATUS[e.status];
      const p = S('path', { d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`, fill: 'none', stroke: color, 'stroke-width': e.status === 'added' ? 4.5 : 3.5, 'stroke-linecap': 'round' }, gE);
      const L = p.getTotalLength();
      p.style.strokeDasharray = `${L} ${L}`;
      p.style.strokeDashoffset = L;
      const end = p.getPointAtLength(L), pre = p.getPointAtLength(Math.max(0, L - 3));
      const ang = Math.atan2(end.y - pre.y, end.x - pre.x) * 180 / Math.PI;
      const head = S('path', { d: 'M-2,-10 L16,0 L-2,10 Z', fill: color, opacity: 0, transform: `translate(${end.x},${end.y}) rotate(${ang})` }, gE);
      edges[e.s + '>' + e.t] = { e, p, L, head, at: Infinity };
    });

    const AREA = { x: 80, y: 120, w: 1760, h: 700 };
    const fit = ids => {
      const ns = ids.map(id => byId[id].n);
      const x0 = Math.min(...ns.map(n => n.x)) - 40, x1 = Math.max(...ns.map(n => n.x + n.w)) + 40;
      const y0 = Math.min(...ns.map(n => n.y)) - 70, y1 = Math.max(...ns.map(n => n.y + n.h)) + 100;
      return { k: Math.min(1.25, AREA.w / (x1 - x0), AREA.h / (y1 - y0)), cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
    };

    const walks = [], flashes = [], notes = [], cams = [{ t: -1e9, v: fit(s.nodes.map(n => n.id)) }];
    const shown = new Set();

    (s.cues || []).forEach(c => {
      if (c.do === 'show') c.ids.forEach((id, i) => { byId[id].show = Math.min(byId[id].show, c.t + i * 0.18); shown.add(id); });
      else if (c.do === 'draw') c.edges.forEach((k, i) => { edges[k[0] + '>' + k[1]].at = c.t + i * 0.2; });
      else if (c.do === 'pulse') byId[c.id].pulses.push(c.t);
      else if (c.do === 'focus') cams.push({ t: c.t, v: fit(c.ids) });
      else if (c.do === 'walk') {
        const per = c.per || 0.9;
        const segs = c.path.slice(1).map((id, i) => edges[c.path[i] + '>' + id]);
        c.path.slice(1).forEach((id, i) => byId[id].pulses.push(c.t + (i + 1) * per));
        const g = S('g', { opacity: 0 }, gT);
        S('circle', { r: 15, fill: C.gold, filter: `url(#glow${s.i})` }, g);
        let card = null;
        if (c.card) {
          const src = byId[c.path[0]].n;
          card = S('g', { opacity: 0, transform: `translate(${src.x + src.w / 2},${src.y - 30})` }, gT);
          const txt = S('text', { 'text-anchor': 'middle', class: 'cardt' }, card);
          txt.textContent = c.card;
          const bb = txt.getBBox();
          card.insertBefore(S('rect', { x: bb.x - 16, y: bb.y - 9, width: bb.width + 32, height: bb.height + 18, rx: 10, fill: C.gold }), txt);
        }
        walks.push({ c, segs, g, per, card });
      } else if (c.do === 'flash') {
        c.edges.forEach((k, i) => {
          const E = edges[k[0] + '>' + k[1]];
          const dot = S('circle', { r: 11, fill: C.gold, filter: `url(#glow${s.i})`, opacity: 0 }, gT);
          const at = c.t + i * 0.15;
          flashes.push({ E, dot, at });
          const target = byId[k[1]];
          target.markAt = at + 0.6; target.mt.textContent = c.mark || '✗';
          const tone = TONE[c.tone || 'bad'];
          target.mc.setAttribute('stroke', tone); target.mt.setAttribute('fill', tone);
        });
      } else if (c.do === 'note') {
        const n = byId[c.id].n, color = TONE[c.tone || 'info'];
        const g = S('g', { opacity: 0 }, gX);
        const txt = S('text', { class: 'note-t', fill: color, 'text-anchor': 'middle' }, g);
        txt.textContent = c.text;
        const bb = txt.getBBox();
        g.insertBefore(S('rect', { x: bb.x - 20, y: bb.y - 12, width: bb.width + 40, height: bb.height + 24, rx: 12, fill: C.bg, stroke: color, 'stroke-width': 2.5 }), txt);
        let x = n.x + n.w / 2, y = n.y + n.h + 62;
        if (c.side === 'above') y = n.y - 34;
        if (c.side === 'right') { x = n.x + n.w + 44 + bb.width / 2; y = n.y + n.h / 2 + 9; }
        g.setAttribute('transform', `translate(${x},${y})`);
        notes.push({ g, at: c.t, until: c.until != null ? c.until : Infinity });
      }
    });

    Object.entries(byId).forEach(([id, N]) => { if (!shown.has(id)) N.show = s.start + 0.2; });
    Object.values(edges).forEach(E => { if (E.at === Infinity) E.at = Math.max(byId[E.e.s].show, byId[E.e.t].show) + 0.3; });

    return t => {
      let i = 0;
      cams.forEach((c, j) => { if (t >= c.t) i = j; });
      let v = cams[i].v;
      if (i > 0) { const a = cams[i - 1].v, k = prog(t, cams[i].t, 1.0); v = { k: lerp(a.k, v.k, k), cx: lerp(a.cx, v.cx, k), cy: lerp(a.cy, v.cy, k) }; }
      cam.setAttribute('transform', `translate(${AREA.x + AREA.w / 2},${AREA.y + AREA.h / 2}) scale(${v.k}) translate(${-v.cx},${-v.cy})`);

      Object.values(byId).forEach(N => {
        const o = prog(t, N.show, 0.5), sc = lerp(0.8, 1, o), n = N.n;
        N.g.setAttribute('opacity', o);
        N.g.setAttribute('transform', `translate(${n.x + n.w / 2},${n.y + n.h / 2}) scale(${sc}) translate(${-n.w / 2},${-n.h / 2})`);
        let ro = 0, rs = 1;
        N.pulses.forEach(pt => { const q = (t - pt) / 0.9; if (q >= 0 && q <= 1) { ro = 1 - q; rs = 1 + 0.2 * smooth(q); } });
        N.ring.setAttribute('opacity', ro);
        N.ring.setAttribute('transform', `translate(${n.w / 2},${n.h / 2}) scale(${rs}) translate(${-n.w / 2},${-n.h / 2})`);
        N.mark.setAttribute('opacity', t >= N.markAt ? 1 : 0);
        N.mark.setAttribute('transform', `translate(${n.w - 4},4) scale(${lerp(1.7, 1, easeOut((t - N.markAt) / 0.3))})`);
      });

      Object.values(edges).forEach(E => {
        const k = prog(t, E.at, 0.8);
        E.p.style.strokeDashoffset = E.L * (1 - k);
        E.head.setAttribute('opacity', clamp((k - 0.8) / 0.2));
      });

      walks.forEach(w => {
        const total = w.segs.length * w.per, u = (t - w.c.t) / total;
        if (w.card) w.card.setAttribute('opacity', Math.min(prog(t, w.c.t - 0.3, 0.3), 1 - prog(t, w.c.t + total + 0.6, 0.5)));
        if (u < 0 || t > w.c.t + total + 1.2) { w.g.setAttribute('opacity', 0); return; }
        const q = Math.min(clamp(u) * w.segs.length, w.segs.length - 1e-6), j = Math.floor(q), f = u >= 1 ? 1 : smooth(q - j);
        const E = w.segs[j], pt = E.p.getPointAtLength(E.L * f);
        w.g.setAttribute('transform', `translate(${pt.x},${pt.y})`);
        w.g.setAttribute('opacity', Math.min(prog(t, w.c.t, 0.25), 1 - prog(t, w.c.t + total + 0.6, 0.5)));
      });

      flashes.forEach(F => {
        const q = (t - F.at) / 0.6;
        if (q < 0 || q > 1.3) { F.dot.setAttribute('opacity', 0); return; }
        const pt = F.E.p.getPointAtLength(F.E.L * smooth(q));
        F.dot.setAttribute('cx', pt.x); F.dot.setAttribute('cy', pt.y);
        F.dot.setAttribute('opacity', 1 - clamp((q - 1) / 0.3));
      });

      notes.forEach(N => N.g.setAttribute('opacity', Math.min(prog(t, N.at, 0.4), 1 - prog(t, N.until, 0.35))));
    };
  };

  MAKERS.calc = (s, root) => {
    const wrap = D('calc', null, root);
    const h = D('calc-h', esc(s.heading), wrap);
    const row = D('chips', null, wrap);
    const items = s.chips.map((c, i) => {
      const arrow = i > 0 ? D('arrow', '→', row) : null;
      const chip = D('chip' + (c.tone ? ' ' + c.tone : ''), `<div class="v">${esc(c.text)}</div><div class="n">${esc(c.note || '')}</div>`, row);
      return { chip, arrow, at: cueT(s, q => q.do === 'chip' && q.i === i) };
    });
    return t => {
      h.style.opacity = prog(t, s.start + 0.2, 0.5);
      items.forEach(it => {
        const k = prog(t, it.at, 0.5);
        it.chip.style.opacity = k;
        it.chip.style.transform = `translateY(${lerp(26, 0, k)}px)`;
        if (it.arrow) it.arrow.style.opacity = k;
      });
    };
  };

  MAKERS.timeline = (s, root) => {
    const svg = S('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, style: 'position:absolute;inset:0' }, root);
    const toMin = hhmm => { const [a, b] = hhmm.split(':').map(Number); return a * 60 + b; };
    const [r0, r1] = s.range.map(toMin);
    const X0 = 330, X1 = 1590;
    const X = hhmm => X0 + (toMin(hhmm) - r0) / (r1 - r0) * (X1 - X0);
    const axisY = 590;
    const axis = S('g', {}, svg);
    S('line', { x1: X0, x2: X1, y1: axisY, y2: axisY, stroke: C.dim, 'stroke-width': 2 }, axis);
    for (let m = r0; m <= r1; m += 60) {
      const hh = String(m / 60).padStart(2, '0') + ':00', x = X(hh);
      S('line', { x1: x, x2: x, y1: axisY - 8, y2: axisY + 8, stroke: C.dim, 'stroke-width': 2 }, axis);
      S('text', { x, y: axisY + 42, 'text-anchor': 'middle', class: 'tick' }, axis).textContent = hh;
    }
    S('text', { x: X0, y: 200, class: 'tl-room' }, axis).textContent = s.room;
    const [o0, o1] = s.overlap;
    const ov = S('rect', { x: X(o0), y: 244, width: X(o1) - X(o0), height: 272, rx: 12, fill: C.red + '30', stroke: C.red, 'stroke-width': 3, opacity: 0 }, svg);
    const ovT = S('text', { x: (X(o0) + X(o1)) / 2, y: 232, 'text-anchor': 'middle', class: 'tl-ov', opacity: 0 }, svg);
    ovT.textContent = 'overlap';
    const rows = s.rows.map((r, i) => {
      const y = 260 + i * 140, x = X(r.from), w = X(r.to) - X(r.from);
      const color = r.status === 'confirmed' ? C.blue : C.grey;
      const g = S('g', { opacity: 0 }, svg);
      const rect = S('rect', { x, y, width: w, height: 100, rx: 16, fill: color + (r.status === 'confirmed' ? '33' : '14'), stroke: color, 'stroke-width': 3, 'stroke-dasharray': r.status === 'confirmed' ? 'none' : '12 9' }, g);
      S('text', { x: x + 24, y: y + 44, class: 'tl-l' }, g).textContent = r.label;
      S('text', { x: x + 24, y: y + 78, class: 'tl-s' }, g).textContent = `${r.from}–${r.to} · ${r.status}`;
      return { g, rect, w, at: cueT(s, q => q.do === 'bar' && q.id === r.id) };
    });
    const ask = S('text', { x: X(s.rows[0].from) - 26, y: 320, 'text-anchor': 'end', class: 'tl-ask', opacity: 0 }, svg);
    ask.textContent = s.ask + ' →';
    const stamp = S('text', { 'text-anchor': 'middle', class: 'tl-stamp', opacity: 0 }, svg);
    stamp.textContent = s.stamp;
    const sx = X(s.rows[1].to) + 150, sy = 420;
    const msg = D('tl-msg', `<span class="k">admin queue</span><span class="t">${esc(s.message)}</span>`, root);
    const at = name => cueT(s, q => q.do === name);
    return t => {
      rows.forEach(r => { const k = prog(t, r.at, 0.7); r.g.setAttribute('opacity', Math.min(1, k * 2)); r.rect.setAttribute('width', Math.max(1, r.w * k)); });
      ask.setAttribute('opacity', prog(t, at('ask'), 0.4));
      const o = prog(t, at('overlap'), 0.5), beat = 0.75 + 0.25 * Math.cos(Math.max(0, t - at('overlap')) * 5);
      ov.setAttribute('opacity', o * beat); ovT.setAttribute('opacity', o);
      const k = prog(t, at('stamp'), 0.35);
      stamp.setAttribute('opacity', k);
      stamp.setAttribute('transform', `translate(${sx},${sy}) rotate(-10) scale(${lerp(2.2, 1, k)})`);
      msg.style.opacity = prog(t, at('message'), 0.45);
    };
  };

  const PAD = 24, IH = 90, GAP = 18;
  const groupHead = (s, g) => s.head || (g.sub ? 124 : 82);
  const groupH = (s, g) => { const n = Math.max(1, g.items.filter(it => !it.outside).length); return g.row ? groupHead(s, g) + IH + PAD : groupHead(s, g) + n * (IH + GAP) - GAP + PAD; };

  // Groups without x/y are placed by column (`col`, default 0), stacked and centred, so a board never authors pixels.
  const autoLayout = s => {
    const cols = [];
    s.groups.forEach(g => {
      const inside = Math.max(1, g.items.filter(it => !it.outside).length), out = g.items.length - g.items.filter(it => !it.outside).length;
      const iw = Math.max(g.row ? 150 : 220, ...g.items.map(it => Math.max(measure(it.text, '500 40px ui-monospace, Menlo, monospace') + (g.row ? 40 : 54),
        it.label ? measure(it.label.toUpperCase(), '700 17px system-ui') + it.label.length * 1.7 + 40 : 0)));
      g.w = g.w || Math.ceil(Math.max(g.row ? 2 * PAD + inside * iw + (inside - 1) * GAP : 2 * PAD + iw,
        measure(g.title.toUpperCase(), '700 24px system-ui') + g.title.length * 24 * 0.16 + 2 * PAD + 6, measure(g.sub, '31px system-ui') + 2 * PAD + 6));
      const iwF = g.row ? (g.w - 2 * PAD - (inside - 1) * GAP) / inside : g.w - 2 * PAD;
      g.fw = g.w + (g.row && out ? 18 + out * (iwF + GAP) - GAP : 0);
      g.fh = groupH(s, g) + (!g.row && out ? 18 + out * (IH + GAP) - GAP : 0);
      (cols[g.col || 0] = cols[g.col || 0] || []).push(g);
    });
    const list = cols.filter(Boolean), colW = list.map(c => Math.max(...c.map(g => g.fw)));
    const sumW = colW.reduce((a, b) => a + b, 0);
    const gap = list.length > 1 ? Math.max(90, Math.min(300, (1720 - sumW) / (list.length - 1))) : 0;
    let x = (W - sumW - gap * (list.length - 1)) / 2;
    list.forEach((c, j) => {
      const colH = c.reduce((a, g) => a + g.fh, 0) + 56 * (c.length - 1);
      let y = Math.max(130, 480 - colH / 2);
      c.forEach(g => { g.x = Math.round(c.length > 1 ? x : x + (colW[j] - g.fw) / 2); g.y = Math.round(y); y += g.fh + 56; });
      x += colW[j] + gap;
    });
  };

  MAKERS.groups = (s, root) => {
    const groups = {}, items = {}, flies = [], marks = [], notes = [];
    const tones = t => ({ bad: C.red, good: C.green, info: C.gold, blue: C.blue }[t] || C.blue);
    if (s.groups.some(g => g.x == null)) autoLayout(s);

    s.groups.forEach(g => {
      const HEAD = groupHead(s, g);
      const inside = Math.max(1, g.items.filter(it => !it.outside).length);
      const iw = g.row ? (g.w - 2 * PAD - (inside - 1) * GAP) / inside : g.w - 2 * PAD;
      const h = groupH(s, g);
      const el = D('grp', `<div class="gt">${esc(g.title)}</div>${g.sub ? `<div class="gs">${fmt(g.sub)}</div>` : ''}`, root);
      Object.assign(el.style, { left: g.x + 'px', top: g.y + 'px', width: g.w + 'px', height: h + 'px' });
      const G = groups[g.id] = { el, x: g.x, y: g.y, w: g.w, h, show: Infinity, tone: [], flash: [] };
      let k = 0, o = 0;
      g.items.forEach(it => {
        const n = it.outside ? o++ : k++, w = iw;
        const x = !g.row ? g.x + PAD : it.outside ? g.x + g.w + 18 + n * (iw + GAP) : g.x + PAD + n * (iw + GAP);
        const y = g.row ? g.y + HEAD : it.outside ? g.y + h + 18 + n * (IH + GAP) : g.y + HEAD + n * (IH + GAP);
        const pel = D('pill' + (it.kind === 'slot' ? ' slot' : '') + (g.row ? ' seat' : ''), `<span class="pt">${esc(it.text)}</span>${it.label ? `<span class="plabel">${esc(it.label)}</span>` : ''}`, root);
        Object.assign(pel.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: IH + 'px' });
        const label = pel.querySelector('.plabel');
        if (label) label.style.color = tones(it.labelTone || it.tone || 'bad');
        items[it.id] = { it, el: pel, label, x, y, w, h: IH, G, k: k + o, show: Infinity, fill: it.kind === 'slot' ? Infinity : -Infinity, tone: it.tone ? [{ t: -Infinity, v: it.tone }] : [], strike: Infinity, flash: [] };
      });
    });

    const box = id => groups[id] || items[id];
    (s.cues || []).forEach(c => {
      if (c.do === 'show') c.ids.forEach((id, i) => { box(id).show = Math.min(box(id).show, c.t + i * (c.step || 0.12)); });
      else if (c.do === 'tone') (c.ids || [c.id]).forEach(id => box(id).tone.push({ t: c.t, v: c.tone }));
      else if (c.do === 'fill') c.ids.forEach((id, i) => { items[id].fill = Math.min(items[id].fill, c.t + i * (c.step || 0.12)); });
      else if (c.do === 'strike') items[c.id].strike = c.t;
      else if (c.do === 'fly') {
        const a = items[c.from], b = items[c.to], dur = c.dur || 0.9;
        // The clone slides its text from where the source shows it to where the target will, so the landing never doubles letters.
        const tw = measure(a.it.text, '500 40px ui-monospace, Menlo, monospace');
        const inset = I => I.el.classList.contains('seat') ? Math.max(0, (I.w - tw) / 2 - 3) : 24;
        const el = D('pill fly', `<span class="pt">${esc(a.it.text)}</span>`, root);
        Object.assign(el.style, { height: a.h + 'px', paddingRight: '0px', whiteSpace: 'nowrap' });
        flies.push({ a, b, el, t: c.t, dur, fade: !!c.fade, arc: c.arc || 60, pa: inset(a), pb: inset(b) });
        if (!c.fade) { b.fill = Math.min(b.fill, c.t + dur); b.flash.push({ t: c.t + dur }); if (b.it.kind !== 'slot') b.show = Math.min(b.show, c.t + dur); }
      } else if (c.do === 'mark') {
        const B = box(c.id), tone = tones(c.tone || 'bad');
        const el = D('gmark', `${esc(c.text || '✗')}<i class="ring"></i>`, root);
        Object.assign(el.style, { left: B.x + B.w - 30 + 'px', top: B.y - 20 + 'px', color: tone, borderColor: tone });
        marks.push({ el, ring: el.querySelector('.ring'), t: c.t });
        B.flash.push({ t: c.t, color: tone });
      } else if (c.do === 'note') {
        const B = box(c.id), tone = tones(c.tone || 'info');
        const el = D('gnote', fmt(c.text), root);
        el.style.color = tone; el.style.borderColor = tone;
        if (c.side === 'right') Object.assign(el.style, { left: B.x + B.w + 24 + 'px', top: B.y + B.h / 2 + 'px', transform: 'translateY(-50%)' });
        else if (c.side === 'above') Object.assign(el.style, { left: B.x + B.w / 2 + 'px', top: B.y - 20 + 'px', transform: 'translate(-50%,-100%)' });
        else Object.assign(el.style, { left: B.x + B.w / 2 + 'px', top: B.y + B.h + 20 + 'px', transform: 'translateX(-50%)' });
        notes.push({ el, t: c.t, until: c.until != null ? c.until : Infinity });
      }
    });

    Object.values(groups).forEach(G => { if (G.show === Infinity) G.show = s.start + 0.2; });
    Object.values(items).forEach(I => {
      if (I.show === Infinity && I.fill === -Infinity) I.show = I.G.show + 0.2 + I.k * 0.12;
      if (I.it.kind === 'slot') I.show = Math.min(I.show, I.G.show + 0.2 + I.k * 0.12);
    });

    const toneAt = (list, t) => { let v = null; list.forEach(x => { if (t >= x.t) v = x.v; }); return v; };
    const glow = (el, list, t, color) => {
      let a = 0, c = color;
      list.forEach(f => { const k = decay(t, f.t, 0.7); if (k > a) { a = k; c = f.color || color; } });
      el.style.boxShadow = a > 0 ? `0 0 ${36 * a}px ${10 * a}px ${rgba(c, 0.6 * a)}` : '';
    };
    return t => {
      Object.values(groups).forEach(G => {
        const k = prog(t, G.show, 0.5);
        G.el.style.opacity = k;
        G.el.style.transform = `translateY(${lerp(20, 0, k)}px)`;
        const v = toneAt(G.tone, t);
        G.el.style.borderColor = v ? tones(v) : '';
        glow(G.el, G.flash, t, v ? tones(v) : C.blue);
      });
      Object.values(items).forEach(I => {
        const k = Math.min(prog(t, I.show, 0.4), prog(t, I.G.show, 0.5));
        const filled = t >= I.fill;
        I.el.style.opacity = I.it.kind === 'slot' && !filled ? k * 0.9 : k;
        I.el.classList.toggle('slot', I.it.kind === 'slot' && !filled);
        const struck = prog(t, I.strike, 0.35);
        const v = struck > 0 ? 'bad' : toneAt(I.tone, t);
        const col = v ? tones(v) : C.blue;
        if (!I.el.classList.contains('slot')) { I.el.style.borderColor = col; I.el.style.background = col + (struck > 0 ? '14' : '1f'); }
        else { I.el.style.borderColor = ''; I.el.style.background = ''; }
        glow(I.el, I.flash, t, col);
        I.el.querySelector('.pt').style.textDecoration = struck > 0.5 ? 'line-through' : 'none';
        I.el.querySelector('.pt').style.opacity = struck > 0 ? lerp(1, 0.6, struck) : 1;
        if (I.label) I.label.style.opacity = I.strike < Infinity ? struck : k;
      });
      flies.forEach(F => {
        const q = (t - F.t) / F.dur;
        // A landed clone lingers while its target fades in underneath, so the handoff never blinks.
        if (q < 0 || q > 1 + (F.fade ? 0.6 : 0.4 / F.dur)) { F.el.style.opacity = 0; return; }
        const e = smooth(Math.min(q, 1));
        F.el.style.left = lerp(F.a.x, F.b.x, e) + 'px';
        F.el.style.top = lerp(F.a.y, F.b.y, e) - Math.sin(Math.PI * Math.min(q, 1)) * F.arc + 'px';
        F.el.style.width = lerp(F.a.w, F.b.w, e) + 'px';
        F.el.style.paddingLeft = lerp(F.pa, F.pb, e) + 'px';
        F.el.style.opacity = q <= 1 || !F.fade ? 1 : 1 - (q - 1) / 0.6;
        F.el.style.transform = q > 1 && F.fade ? `scale(${lerp(1, 0.7, (q - 1) / 0.6)})` : '';
      });
      marks.forEach(M => {
        M.el.style.opacity = t >= M.t ? 1 : 0;
        M.el.style.transform = `scale(${lerp(1.7, 1, easeOut((t - M.t) / 0.3))})`;
        M.ring.style.opacity = decay(t, M.t, 0.6);
        M.ring.style.transform = `scale(${1 + 1.4 * easeOut((t - M.t) / 0.6)})`;
      });
      notes.forEach(N => { N.el.style.opacity = Math.min(prog(t, N.t, 0.4), 1 - prog(t, N.until, 0.35)); });
    };
  };

  MAKERS.bars = (s, root) => {
    const PAL = { blue: C.blue, green: C.green, grey: C.grey, gold: C.gold, red: C.red, good: C.green, bad: C.red, info: C.gold };
    const wrap = D('bars', null, root);
    const head = D('head', `<span class="big">${esc(s.big)}</span><span class="lbl">${esc(s.label)}</span>`, wrap);
    const max = Math.max(...s.bars.map(b => b.value));
    const c = (s.cues || []).find(q => q.do === 'bars'), step = (c && c.step) || 0.22;
    const rows = s.bars.map((b, i) => {
      const row = D('brow', `<div class="bl">${esc(b.label)}</div><div class="bt"><div class="bf"></div><div class="bv">+${b.value}</div><div class="bn"></div></div>`, wrap);
      const fill = row.querySelector('.bf'), val = row.querySelector('.bv'), note = row.querySelector('.bn');
      const color = PAL[b.tone || 'grey'];
      fill.style.background = color; val.style.color = color;
      return { b, row, fill, val, note, w: Math.max(6, (b.value / max) * 1040), at: (c ? c.t : s.start + 0.5) + i * step, dim: Infinity, noteAt: Infinity };
    });
    (s.cues || []).forEach(q => {
      if (q.do === 'dim') rows.forEach(r => { if (!q.keep.includes(r.b.id)) r.dim = q.t; });
      if (q.do === 'note') { const r = rows.find(r => r.b.id === q.id); r.note.innerHTML = fmt(q.text); r.note.style.color = TONE[q.tone || 'info']; r.noteAt = q.t; }
    });
    return t => {
      head.style.opacity = prog(t, s.start + 0.15, 0.5);
      rows.forEach(r => {
        const k = prog(t, r.at, 0.7);
        r.row.style.opacity = Math.min(1, k * 3) * lerp(1, 0.32, prog(t, r.dim, 0.5));
        r.fill.style.width = r.w * k + 'px';
        r.val.style.left = r.w * k + 18 + 'px';
        r.note.style.left = r.w + 150 + 'px';
        r.note.style.opacity = prog(t, r.noteAt, 0.4);
      });
    };
  };

  MAKERS.list = (s, root) => {
    const wrap = D('list', null, root);
    const head = D('head', `<span class="big" style="color:${TONE[s.tone || 'good']}">${esc(s.big)}</span><span class="lbl">${esc(s.label)}</span>`, wrap);
    const c = (s.cues || []).find(q => q.do === 'items'), step = c.step || 0.3;
    const items = s.items.map((it, i) => ({ el: D('item', `<span class="ok" style="color:${TONE[s.tone || 'good']}">${esc(s.mark || '✓')}</span><span>${s.code ? `<code>${esc(it.text)}</code>` : esc(it.text)}</span><span class="c">${esc(it.cite.split('/').pop())}</span>`, wrap), at: c.t + i * step }));
    if (s.more) items.push({ el: D('more', esc(s.more), wrap), at: c.t + items.length * step });
    return t => {
      head.style.opacity = prog(t, s.start + 0.15, 0.5);
      items.forEach(it => { const k = prog(t, it.at, 0.45); it.el.style.opacity = k; it.el.style.transform = `translateX(${lerp(-30, 0, k)}px)`; });
    };
  };

  MAKERS.receipt = (s, root) => {
    const rc = D('rc', null, root);
    const claim = D('claim', `<div class="num">${esc(s.n)}</div><div class="q">${fmt(s.claim)}</div>`, rc);
    const box = D('rows', null, rc);
    const c = (s.cues || []).find(q => q.do === 'rows'), step = c.step || 0.8;
    const rows = s.rows.map((r, i) => ({
      el: D('row', `<div class="kind">${esc(r.kind)}</div><div class="line"><div class="txt${r.prose ? ' prose' : ''}">${esc(r.text)}</div><div class="cite">${esc(r.line || '')}</div></div>`, box),
      at: c.t + i * step,
    }));
    const ver = D('verdict', esc(s.verdict[0]), claim);
    ver.style.color = TONE[s.verdict[1]]; ver.style.borderColor = TONE[s.verdict[1]];
    const vat = cueT(s, q => q.do === 'verdict');
    return t => {
      claim.style.opacity = prog(t, s.start + 0.15, 0.5);
      rows.forEach(r => { const k = prog(t, r.at, 0.45); r.el.style.opacity = k; r.el.style.transform = `translateY(${lerp(18, 0, k)}px)`; });
      const k = prog(t, vat, 0.35);
      ver.style.opacity = k;
      ver.style.transform = `rotate(-4deg) scale(${lerp(1.6, 1, k)})`;
    };
  };

  MAKERS.stats = (s, root) => {
    const wrap = D('stats', null, root);
    const cards = s.cards.map((c, i) => ({ el: D('stat', `<div class="v" style="color:${TONE[c.tone || 'good']}">${esc(c.value)}</div><div class="l">${esc(c.label)}</div>`, wrap), at: cueT(s, q => q.do === 'card' && q.i === i) }));
    return t => cards.forEach(c => { const k = prog(t, c.at, 0.5); c.el.style.opacity = k; c.el.style.transform = `translateY(${lerp(34, 0, k)}px)`; });
  };

  MAKERS.outro = (s, root) => {
    const wrap = D('outro', null, root);
    const l1 = D('l1', esc(s.l1), wrap), l2 = D('l2', esc(s.l2), wrap);
    const cmd = D('cmd', `<b>prc map</b> ${esc(s.url)}`, wrap);
    const fine = D('fine', esc(s.fine), wrap);
    const at = name => cueT(s, q => q.do === name);
    return t => {
      l1.style.opacity = prog(t, at('l1'), 0.5);
      l2.style.opacity = prog(t, at('l2'), 0.5);
      cmd.style.opacity = prog(t, at('cmd'), 0.5);
      fine.style.opacity = prog(t, at('cmd') + 0.5, 0.5);
    };
  };

  MAKERS.diff = (s, root) => {
    const wrap = D('diff', null, root);
    const cut = s.file.lastIndexOf('/') + 1;
    if (s.label) D('dlabel', fmt(s.label), wrap);
    D('dpath', `${esc(s.file.slice(0, cut))}<b>${esc(s.file.slice(cut))}</b>`, wrap);
    const box = D('code', null, wrap);
    const stepAt = {};
    (s.cues || []).forEach(c => { if (c.do === 'step') stepAt[c.n] = c.t; });
    // A step that replaces lines lets the removed rows tint red before the new lines open in their place.
    const swaps = new Set(s.rows.filter(r => r.op === '-').map(r => r.step));
    // Fewer, shorter lines get a bigger font; the block is centred in the space above the captions.
    const gutter = s.gutter || 0, GH = 30, TOP = 12;
    const wide = c => { const n = c.codePointAt(0); return (n >= 0x1100 && n <= 0x115F) || (n >= 0x2E80 && n <= 0xA4CF) || (n >= 0xAC00 && n <= 0xD7AF) || (n >= 0xF900 && n <= 0xFAFF) || (n >= 0xFE30 && n <= 0xFE4F) || (n >= 0xFF00 && n <= 0xFF60) || (n >= 0xFFE0 && n <= 0xFFE6) ? 2 : 1; };
    const tcols = t => [...t].reduce((a, ch) => a + wide(ch), 0);
    // Widest visual line in columns, counting the hanging indent on continuation lines.
    let longest = 0;
    s.rows.forEach(r => {
      if (r.gap || !r.tokens) { longest = Math.max(longest, (r.text || '').length); return; }
      let w = 0;
      r.tokens.forEach((tok, idx) => {
        if ((r.breaks || []).includes(idx)) { longest = Math.max(longest, w); w = r.hang || 0; }
        w += tcols(tok.text);
      });
      longest = Math.max(longest, w);
    });
    const widthBound = Math.floor(1560 / ((longest + gutter) * 0.6 + 2));
    const rowH = fs => Math.round(fs * 1.75);
    const tallAt = fs => s.rows.reduce((a, r) => a + (r.gap ? GH : rowH(fs) * (((r.breaks || []).length) + 1)), 2 * TOP) + (s.label ? 72 : 0) + 48;
    const topAt = tall => Math.max(118, Math.round(489 - tall / 2));
    let FS = Math.min(40, widthBound);
    while (FS > 22 && topAt(tallAt(FS)) + tallAt(FS) > 862) FS -= 1;
    FS = Math.max(22, FS);
    if (FS < 28) window.lint.push(`scene ${s.i}: diff font ${FS} px is small at GitHub width; show fewer or shorter lines`);
    const RH = rowH(FS);
    const digits = Math.max(1, ...s.rows.filter(r => r.num != null).map(r => String(r.num).length));
    const rows = s.rows.map((r, k) => {
      if (r.gap) return { r, k, el: D('drow gap', '<span class="sg"></span><span class="tx">⋯</span>', box), h: GH, t0: -Infinity, tin: -Infinity };
      const parts = [];
      (r.tokens || []).forEach((tok, idx) => {
        if ((r.breaks || []).includes(idx)) parts.push(`<br><span class="hang" style="display:inline-block;width:${r.hang || 0}ch"></span>`);
        parts.push(`<span class="mt ${tok.cls || ''}${tok.chg ? ' chg' : ''}">${esc(tok.text)}</span>`);
      });
      const el = D('drow', `<span class="ln" style="width:${digits + 1}ch;line-height:${RH}px">${r.num}</span><span class="sg">${r.op === '+' ? '+' : r.op === '-' ? '−' : ''}</span><span class="tx"><span class="ct">${parts.join('') || esc(r.text)}</span></span>`, box);
      const t0 = r.step ? stepAt[r.step] : -Infinity;
      return { r, k, el, h: RH * (((r.breaks || []).length) + 1), sg: el.querySelector('.sg'), tx: el.querySelector('.tx'), ct: el.querySelector('.ct'),
               t0, tin: r.op === '+' && swaps.has(r.step) ? t0 + 0.55 : t0, notes: [] };
    });
    const byRef = {};
    rows.forEach(R => { if (R.r.ref) byRef[R.r.ref] = R; if (R.ct) Object.assign(R.el.style, { fontSize: FS + 'px', lineHeight: RH + 'px' }); });
    const tallest = rows.reduce((a, R) => a + R.h, 2 * TOP) + (s.label ? 72 : 0) + 48;
    wrap.style.top = topAt(tallest) + 'px';
    rows.forEach(R => { if (R.ct) R.textW = Math.min(R.ct.offsetWidth, R.tx.clientWidth - 24); });
    // A note sits after the last visual line of its row, so it never covers wrapped text.
    const lastLineW = R => {
      const mts = [...R.el.querySelectorAll('.mt')], brs = R.r.breaks || [];
      const last = brs.length ? mts.slice(brs[brs.length - 1]) : mts;
      let w = last.reduce((a, el) => a + el.getBoundingClientRect().width, 0);
      const hangs = R.el.querySelectorAll('.hang');
      if (hangs.length) w += hangs[hangs.length - 1].getBoundingClientRect().width;
      return w;
    };
    const notes = (s.cues || []).filter(c => c.do === 'note').map(c => {
      const R = byRef[c.line], tone = TONE[c.tone || 'info'];
      const el = D('dnote', fmt(c.text), box);
      el.style.color = tone; el.style.borderColor = tone;
      const lnW = R.el.querySelector('.ln') ? R.el.querySelector('.ln').getBoundingClientRect().width : 0;
      const x = Math.min(lnW + 56 + lastLineW(R) + 32, 1700 - el.offsetWidth - 20);
      const N = { R, el, x, t: c.t, until: c.until != null ? c.until : Infinity, tone };
      R.notes.push(N);
      return N;
    });

    return t => {
      let y = TOP;
      rows.forEach(R => {
        let k = 1;
        if (R.r.op === '+') k = prog(t, R.tin, 0.45);
        const enter = prog(t, s.start + 0.25 + R.k * 0.035, 0.4);
        R.y = y; R.hk = k;
        R.el.style.top = y + 'px';
        R.el.style.height = R.h * k + 'px';
        // Removed rows stay on screen: their text dims to 0.85 and the row tints red. No strike, no close.
        R.el.style.opacity = enter * clamp(k * 2 - 1) * (R.r.op === '-' ? lerp(1, 0.85, prog(t, R.t0, 0.3)) : 1);
        y += R.h * k;
        if (!R.ct) return;
        if (!R.chg) R.chg = [...R.el.querySelectorAll('.mt.chg')];
        let bg = 0, color = C.green;
        if (R.r.op === '-') {
          const s0 = prog(t, R.t0, 0.3);
          R.sg.style.opacity = s0;
          R.sg.style.color = C.red;
          bg = 0.14 * s0; color = C.red;
          const mark = 0.40 * prog(t, R.t0 + 0.15, 0.3);
          R.chg.forEach(el => { el.style.background = mark > 0 ? rgba(C.red, mark) : ''; });
        }
        if (R.r.op === '+') {
          R.sg.style.color = C.green;
          R.el.style.transform = `translateX(${lerp(-24, 0, k)}px)`;
          bg = 0.10 + 0.42 * decay(t, R.tin + 0.45, 0.8);
          const mark = 0.34 * prog(t, R.tin + 0.3, 0.3);
          R.chg.forEach(el => { el.style.background = mark > 0 ? rgba(C.green, mark) : ''; });
        }
        let bar = 0, barColor = C.gold;
        R.notes.forEach(N => { const o = Math.min(prog(t, N.t, 0.3), 1 - prog(t, N.until, 0.3)); if (o > bar) { bar = o; barColor = N.tone; } });
        R.el.style.background = bg > 0 ? rgba(color, bg) : '';
        R.el.style.boxShadow = bar > 0 ? `inset 6px 0 0 ${rgba(barColor, bar)}` : '';
      });
      box.style.height = y + TOP + 'px';
      notes.forEach(N => {
        N.el.style.left = N.x + 'px';
        N.el.style.top = N.R.y + N.R.h * N.R.hk - RH / 2 + 'px';
        N.el.style.opacity = Math.min(prog(t, N.t, 0.3), 1 - prog(t, N.until, 0.3)) * clamp(N.R.hk * 2 - 1);
      });
    };
  };

  const stage = document.getElementById('stage');
  const cap = document.getElementById('cap'), foot = document.getElementById('foot'), bar = document.getElementById('bar');
  document.getElementById('header').innerHTML = B.header;
  const scenes = B.scenes.map(s => { const root = D('scene', null, stage); return { s, root, update: MAKERS[s.type](s, root) }; });
  const sentences = B.scenes.flatMap(s => (s.nocap ? [] : s.sentences));
  let lastCap, lastFoot;

  window.seek = t => {
    scenes.forEach(sc => {
      const o = Math.min(prog(t, sc.s.start, 0.45), 1 - prog(t, sc.s.end - 0.35, 0.35));
      sc.root.style.opacity = o;
      sc.root.style.visibility = o > 0.001 ? 'visible' : 'hidden';
      if (o > 0.001) sc.update(t);
    });
    const cur = sentences.find(x => t >= x.start - 0.15 && t < x.start + x.dur + 0.25);
    if (cur !== lastCap) { cap.innerHTML = cur ? fmt(cur.text).replace(/(\S+-\S+)/g, '<span style="white-space:nowrap">$1</span>') : ''; lastCap = cur; }
    cap.style.opacity = cur ? Math.min(prog(t, cur.start - 0.15, 0.15), 1 - prog(t, cur.start + cur.dur + 0.1, 0.15)) : 0;
    const sc = scenes.find(x => t >= x.s.start && t < x.s.end);
    const f = sc ? sc.s.footer || '' : '';
    if (f !== lastFoot) { foot.textContent = f; lastFoot = f; }
    foot.style.opacity = sc ? Math.min(prog(t, sc.s.start + 0.3, 0.5), 1 - prog(t, sc.s.end - 0.35, 0.35)) : 0;
    bar.style.width = `${(t / B.duration) * 100}%`;
  };
  // Layout lint: sample each scene after every cue and at its end, and report boxes that leave the safe frame.
  const SAFE = { left: 30, top: 96, right: W - 30, bottom: 862 };
  window.lint = [];
  scenes.forEach(({ s, root, update }) => {
    root.style.visibility = 'visible';
    const times = (s.cues || []).map(c => c.t + 0.8).concat([s.end - 0.4]);
    times.forEach(t => {
      update(t);
      root.querySelectorAll('.grp,.pill:not(.fly),.gnote,.gmark,.code,.dnote,.item,.item .c,.brow,.stat,.rc .rows').forEach(el => {
        if (parseFloat(getComputedStyle(el).opacity) < 0.05) return;
        const r = el.getBoundingClientRect();
        const edge = r.bottom > SAFE.bottom ? `bottom ${Math.round(r.bottom)}px (captions start at ${SAFE.bottom})` : r.right > SAFE.right ? `right edge ${Math.round(r.right)}px` : r.left < SAFE.left ? `left edge ${Math.round(r.left)}px` : r.top < SAFE.top ? `top ${Math.round(r.top)}px` : null;
        const msg = edge && `scene ${s.i}: ${el.className.split(' ')[0]} "${el.textContent.trim().slice(0, 32)}" leaves the frame at the ${edge}`;
        if (msg && !window.lint.includes(msg)) window.lint.push(msg);
      });
    });
  });
  window.prcTour = { duration: B.duration, seek: window.seek };
  window.seek(0);
  window.ready = true;
})();
