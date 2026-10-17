/* PRC v7 · arena candidate 3 · direction "Wondering"
   Content is copied from the round-6 Control constants (picker.js):
   PR, RUN/E2E/GDR link bases, COUNTS, report(), SCEN. */
(function () {
  'use strict';

  var PR = 'https://github.com/komaksym/linkedin-mdp/pull/5';
  var RUN = PR + '/files#diff-ae4651b791554885691e5439c7e07983819af9ab95a7e822a05a376ed2ca5878R';

  var COUNTS = [
    ['Fetched rows', 4],
    ['Matched rows', 3],
    ['Unique matched connections', 2],
    ['Unmatched rows', 1],
    ['Newly inserted events', 1],
    ['Already-present events', 1]
  ];
  var RUNTIME = 'Run time: 2026-09-30 10:00:00 CEST';

  function report(status) {
    var L = ['LinkedIn CONNECTIONS reconciliation', 'Status: ' + status, RUNTIME];
    COUNTS.forEach(function (c) { L.push(c[0] + ': ' + (status === 'COMPLETE' ? c[1] : 'unknown')); });
    if (status === 'COMPLETE') L.push('Next action: review the aggregate counts; investigate unmatched rows if needed.');
    else if (status === 'BLOCKED') L.push('Next action: restore a complete LinkedIn CONNECTIONS snapshot, then rerun.');
    if (status === 'FAILED') {
      L.push('Database writes may have happened; their final state is unknown.');
      L.push('Next action: verify Supabase state before retrying reconciliation.');
    }
    return L;
  }

  var SCEN = {
    complete: { exit: 0, status: 'COMPLETE', cap: '<b>Exit 0.</b> The run is COMPLETE, so all six counts are known.' },
    later_404: { exit: 1, status: 'BLOCKED', cap: '<b>Exit 1.</b> LinkedIn answers 404 on a later page, so the snapshot is not complete. The status is BLOCKED and the counts are unknown.' },
    supabase_timeout: { exit: 1, status: 'FAILED', cap: '<b>Exit 1.</b> The Supabase write times out. The status is FAILED, and the report warns that database writes may have happened.' },
    sharing: { exit: 2, status: null, cap: '<b>Exit 2.</b> The Doc is shared with another account. The reporter stops before any LinkedIn or Supabase work and writes nothing.' }
  };

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  var KW = /^(await|async|except|try|if|else|is|None|return|def|import|from|for|in)$/;
  function hl(src) {
    var re = /("[^"]*"|\b[A-Za-z_]\w*\b|\b\d+\b|#.*$|[^"A-Za-z_\d#]+)/g, m, out = '';
    while ((m = re.exec(src))) {
      var t = m[0], next = src.charAt(re.lastIndex);
      if (t.charAt(0) === '"') {
        var word = t.slice(1, -1);
        if (word === 'BLOCKED') out += '<span class="tk-st st-blocked">' + esc(t) + '</span>';
        else if (word === 'FAILED') out += '<span class="tk-st st-failed">' + esc(t) + '</span>';
        else out += '<span class="tk-s">' + esc(t) + '</span>';
      }
      else if (t.charAt(0) === '#') out += '<span class="tk-c">' + esc(t) + '</span>';
      else if (KW.test(t)) out += '<span class="tk-kw">' + esc(t) + '</span>';
      else if (/^\d+$/.test(t)) out += '<span class="tk-n">' + t + '</span>';
      else if (/^[A-Za-z_]/.test(t) && next === '(') out += '<span class="tk-fn">' + esc(t) + '</span>';
      else out += esc(t);
    }
    return out;
  }

  var CODE_ROWS = [
    { ln: 36, ind: 0, t: 'await publisher.prepare()', hl: true },
    { fold: '5 lines' },
    { ln: 42, ind: 1, t: 'summary = await reconcile_connections(guarded_linkedin, supabase)' },
    { ln: 43, ind: 0, t: 'except LinkedInAPIError:' },
    { ln: 44, ind: 1, t: 'result = ReportResult("BLOCKED", datetime.now(timezone.utc), None)' },
    { fold: '5 lines' },
    { ln: 50, ind: 0, t: 'except Exception:' },
    { ln: 51, ind: 1, t: 'result = ReportResult("BLOCKED" if linkedin is None else "FAILED", \u2026)' },
    { fold: '14 lines' },
    { ln: 66, ind: 0, t: 'await publisher.publish(result)' }
  ];

  function renderCode() {
    var html = '';
    CODE_ROWS.forEach(function (r) {
      if (r.fold) {
        html += '<div class="crow fold"><span class="ln">\u22ef</span><span class="ct">' + esc(r.fold) + '</span></div>';
      } else {
        html += '<div class="crow' + (r.hl ? ' hl' : '') + '"><span class="ln"><a href="' + RUN + r.ln + '">' + r.ln + '</a></span><span class="ct">' + '    '.repeat(r.ind) + hl(r.t) + '</span></div>';
      }
    });
    document.getElementById('w-code').innerHTML = html;
  }

  function docRowHTML(l) {
    if (l === 'LinkedIn CONNECTIONS reconciliation') return '<p class="drow n-title"><span class="dt">' + esc(l) + '</span></p>';
    var m = /^([^:]+): (.*)$/.exec(l);
    if (m && /^Status/.test(l)) return '<p class="drow n-status"><span class="dt">' + esc(m[1]) + ': </span><span class="dv st-' + esc(m[2].toLowerCase()) + '">' + esc(m[2]) + '</span></p>';
    if (m && /^\d+$/.test(m[2])) return '<p class="drow"><span class="dt">' + esc(m[1]) + ': </span><span class="dv">' + m[2] + '</span></p>';
    return '<p class="drow n-note"><span class="dt">' + esc(l) + '</span></p>';
  }

  var scen = 'complete';
  var scenBtns = Array.prototype.slice.call(document.querySelectorAll('.scen button'));

  function setScen(s) {
    scen = s;
    scenBtns.forEach(function (b) {
      var on = b.dataset.scen === s;
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    var sc = SCEN[s], w = !!sc.status;
    var stat = document.getElementById('w-stat');
    stat.textContent = sc.status || 'none';
    stat.className = 'stat st-' + (sc.status ? sc.status.toLowerCase() : 'none');
    document.getElementById('w-counts').innerHTML = COUNTS.map(function (c) {
      var v = sc.status === 'COMPLETE' ? String(c[1]) : sc.status ? 'unknown' : 'none';
      return '<div class="crow"><span>' + esc(c[0]) + '</span><b' + (sc.status === 'COMPLETE' ? '' : ' class="n-unknown"') + '>' + v + '</b></div>';
    }).join('');
    document.getElementById('w-exit').textContent = 'Exit code ' + sc.exit + (w ? '' : ' \u00b7 nothing written');
    document.getElementById('w-scap').innerHTML = sc.cap;
    document.getElementById('w-docname').textContent = w ? 'Google Doc after the run' : 'Google Doc before the run';
    document.getElementById('w-news').innerHTML = w ? report(sc.status).map(docRowHTML).join('') : '';
    document.querySelector('.drow.old').classList.toggle('struck', w);
    document.querySelector('.region').classList.toggle('idle', !w);
    document.getElementById('w-stop').hidden = w;
  }

  scenBtns.forEach(function (b) {
    b.addEventListener('click', function () { setScen(b.dataset.scen); });
  });

  renderCode();
  setScen('complete');

  /* ---------- clip mode: one moment at a time, one build-up each ---------- */
  var CLIP = new URLSearchParams(location.search).get('clip');
  if (CLIP) document.body.classList.add('clip');
  var REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var moments = ['m1', 'm2', 'm3'].map(function (id) { return document.getElementById(id); });
  var STATES = [['s1-run', 's1-marks', 's1-old', 's1-news', 's1-kept'], ['s2-code', 's2-first', 's2-notes'], ['s3-sum', 's3-tip']];
  if (CLIP) moments[0].classList.add('live');

  window.__ready = false;
  window.__marks = [];
  window.__clipDone = false;

  function fontsReady() { window.__ready = true; }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fontsReady);
  else fontsReady();
  window.addEventListener('load', function () {
    setTimeout(function () { if (!window.__ready) fontsReady(); }, 1500);
  });

  function retire(i) {
    var m = moments[i];
    m.classList.add('out');
    setTimeout(function () { m.classList.remove('live', 'out'); }, 520);
  }

  function prep(i) {
    STATES[i].forEach(function (c) { moments[i].classList.remove(c); });
    moments[i].getBoundingClientRect();
  }

  var builds = [
    async function () {
      var m = moments[0];
      m.classList.add('s1-run'); await sleep(REDUCED ? 350 : 850);
      m.classList.add('s1-marks'); await sleep(REDUCED ? 250 : 550);
      m.classList.add('s1-old'); await sleep(REDUCED ? 300 : 650);
      m.classList.add('s1-news'); await sleep(REDUCED ? 350 : 1350);
      m.classList.add('s1-kept'); await sleep(REDUCED ? 300 : 750);
    },
    async function () {
      var m = moments[1];
      m.classList.add('s2-code'); await sleep(REDUCED ? 350 : 1250);
      m.classList.add('s2-first'); await sleep(REDUCED ? 250 : 850);
      m.classList.add('s2-notes'); await sleep(REDUCED ? 250 : 650);
    },
    async function () {
      var m = moments[2];
      m.classList.add('s3-sum'); await sleep(REDUCED ? 300 : 850);
      m.classList.add('s3-tip'); await sleep(REDUCED ? 250 : 750);
    }
  ];
  var HOLDS = [850, 900, 1100];
  var busy = false;

  window.startClip = async function () {
    if (busy) return;
    busy = true;
    setScen('complete');
    var t0 = performance.now();
    window.__marks = [];
    for (var i = 0; i < moments.length; i++) {
      if (i > 0) retire(i - 1);
      prep(i);
      moments[i].classList.add('live');
      await sleep(REDUCED ? 150 : 320);
      await builds[i]();
      await sleep(REDUCED ? 350 : HOLDS[i]);
      window.__marks.push(Math.round((performance.now() - t0) / 100) / 100);
    }
    await sleep(560);
    window.__clipDone = true;
  };
})();
