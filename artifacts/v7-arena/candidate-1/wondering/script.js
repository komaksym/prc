/* PRC page, direction "Wondering". Plain JS, no libraries. */
(function () {
  'use strict';

  /* ---------- content: from the pull request and its e2e test ---------- */
  var PR = 'https://github.com/komaksym/linkedin-mdp/pull/5';
  var F = PR + '/files#diff-';
  var RUN = F + 'ae4651b791554885691e5439c7e07983819af9ab95a7e822a05a376ed2ca5878R';
  var E2E = F + '611723ce987a2e3e568a3645b8623f2947dc1895aa75f817e07ea2dc45824c30R';
  var GDR = F + '997c7f526b66a84ac29be4c15cf342c0948e1accd92b45cf9196562aae7a805eR';

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
    complete: { exit: 0, status: 'COMPLETE', cap: 'The run is complete, so all six counts are known.' },
    later_404: { exit: 1, status: 'BLOCKED', cap: 'LinkedIn answers 404 on a later page, so the snapshot is not complete. The counts are unknown.' },
    supabase_timeout: { exit: 1, status: 'FAILED', cap: 'The Supabase write times out. The report warns that database writes may have happened.' },
    sharing: { exit: 2, status: null, cap: 'The Doc is shared with another account. The reporter stops before any LinkedIn or Supabase work and writes nothing.' }
  };
  var TONE = { COMPLETE: 'ok', BLOCKED: 'blk', FAILED: 'bad' };

  /* run() in scripts/report_connections_doc.py: [line, source, indent, tone, note] */
  var ROWS = [
    [36, 'await publisher.prepare()', 0, 'g', 'Google checks run first.'],
    ['fold', 5],
    [42, 'summary = await reconcile_connections(guarded_linkedin, supabase)', 1, '', 'Reads LinkedIn and writes to Supabase.'],
    [43, 'except LinkedInAPIError:', 0, 'b', ''],
    [44, 'result = ReportResult("BLOCKED", datetime.now(timezone.utc), None)', 1, 'b', 'A LinkedIn error gives BLOCKED.'],
    ['fold', 5],
    [50, 'except Exception:', 0, 'f', ''],
    [51, 'result = ReportResult("BLOCKED" if linkedin is None else "FAILED", \u2026)', 1, 'f', 'Other errors give FAILED, or BLOCKED if the LinkedIn client never started.'],
    ['fold', 14],
    [66, 'await publisher.publish(result)', 0, 'g', 'Publishes the status to the Doc.']
  ];
  /* clip step at which each code line lights up */
  var LIGHT = { 36: 3, 42: 4, 43: 5, 44: 5, 50: 6, 51: 6, 66: 7 };

  /* ---------- helpers ---------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function frame() { return new Promise(function (r) { requestAnimationFrame(function () { requestAnimationFrame(r); }); }); }

  var KW = { await: 1, async: 1, except: 1, try: 1, if: 1, else: 1, is: 1, not: 1, and: 1, or: 1, return: 1, def: 1, for: 1, in: 1 };
  function hl(src) {
    var out = '', re = /"[^"]*"|[A-Za-z_]\w*|\d+|\s+|./g, m;
    while ((m = re.exec(src))) {
      var t = m[0], nx = src.charAt(re.lastIndex);
      if (t.charAt(0) === '"') {
        var c = t === '"BLOCKED"' ? 's st-b' : t === '"FAILED"' ? 's st-f' : 's';
        out += '<span class="' + c + '">' + esc(t) + '</span>';
      } else if (t === 'None' || /^\d+$/.test(t)) out += '<span class="n">' + t + '</span>';
      else if (KW[t]) out += '<span class="k">' + t + '</span>';
      else if (/^[A-Z][a-z]/.test(t)) out += '<span class="t">' + t + '</span>';
      else if (/^[A-Za-z_]/.test(t) && nx === '(') out += '<span class="f">' + t + '</span>';
      else out += esc(t);
    }
    return out;
  }

  /* ---------- moment 1: this run + the Doc ---------- */
  function renderRun(key) {
    var sc = SCEN[key], tone = TONE[sc.status] || 'none', known = sc.status === 'COMPLETE';
    var h = '<div class="run-top"><h3>This run</h3><code class="scen-name">' + key + '</code></div>';
    h += '<p class="status s-' + tone + '">' + (sc.status || 'No status') + '</p>';
    h += '<p class="exit">Exit code ' + sc.exit + (sc.status ? '' : ', nothing written') + '</p>';
    h += '<dl class="counts">';
    COUNTS.forEach(function (c, i) {
      var v = known ? c[1] : sc.status ? 'unknown' : 'not counted';
      h += '<div data-b="3" style="--i:' + i + '"><dt>' + c[0] + '</dt><dd' + (known ? '' : ' class="unk"') + '>' + v + '</dd></div>';
    });
    h += '</dl>';
    h += '<p class="cap">The status and the six counts from the test run. Source: <a href="' + E2E + '247">e2e_doc_report.py:247</a></p>';
    $('#run').innerHTML = h;
  }

  function dl(cls, text, chip, step) {
    return '<div class="dl ' + cls + '" data-b="' + step + '"><span class="dt">' + text + '</span>' + (chip || '') + '</div>';
  }
  function renderDoc(key) {
    var sc = SCEN[key], wrote = !!sc.status, h = '';
    var kept = '<span class="chip c-keep" data-b="7">Kept</span>';
    h += dl('dl-keep', 'Operator note', kept, 4);
    h += dl('dl-mk', '[BEGIN AUTOMATED REPORT]', '', 4);
    h += '<div class="region" data-b="4">';
    if (wrote) {
      h += '<div class="dl dl-old" data-x="5"><span class="dt">old</span><span class="chip c-old">Removed</span></div>';
      report(sc.status).forEach(function (l, i) {
        var t = esc(l);
        if (i === 1) t = 'Status: <span class="sv s-' + TONE[sc.status] + '">' + sc.status + '</span>';
        h += '<div class="dl dl-new' + (i === 1 ? ' dl-status' : '') + '" data-b="6" style="--i:' + i + '"><span class="dt">' + t + '</span>' +
          (i === 0 ? '<span class="chip c-new">Written by this run</span>' : '') + '</div>';
      });
    } else {
      h += '<div class="dl dl-old same"><span class="dt">old</span><span class="chip c-same">Unchanged</span></div>';
      h += '<p class="stop">The run stopped before it wrote. Nothing between the markers changes.</p>';
    }
    h += '</div>';
    h += dl('dl-mk', '[END AUTOMATED REPORT]', '', 4);
    h += dl('dl-keep', 'Keep this note.', kept, 4);
    $('#docBody').innerHTML = h;
  }

  function setScen(key, animate) {
    $$('.seg button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.scen === key)); });
    renderRun(key);
    renderDoc(key);
    $('#scenCap').textContent = SCEN[key].cap;
    if (animate) {
      var g = $('.m1-grid');
      g.classList.remove('swap'); void g.offsetWidth; g.classList.add('swap');
    }
  }

  /* ---------- moment 2: order of work ---------- */
  function renderCode() {
    var h = '';
    ROWS.forEach(function (r) {
      if (r[0] === 'fold') {
        h += '<li class="fold"><span class="fold-ic" aria-hidden="true">\u22EF</span><span>' + r[1] + ' lines hidden</span></li>';
        return;
      }
      var n = r[0], step = LIGHT[n];
      h += '<li class="row' + (r[3] ? ' t-' + r[3] : '') + '" data-x="' + step + '">' +
        '<a class="ln" href="' + RUN + n + '" aria-label="Line ' + n + ' on GitHub">' + n + '</a>' +
        '<code class="src">' + new Array(r[2] + 1).join('    ') + hl(r[1]) + '</code>' +
        (r[4] ? '<p class="note" data-b="' + step + '">' + r[4] + '</p>' : '') + '</li>';
    });
    $('#lines').innerHTML = h;
  }

  /* ---------- boot ---------- */
  renderCode();
  setScen('complete', false);
  $$('.seg button').forEach(function (b) {
    b.addEventListener('click', function () { setScen(b.dataset.scen, true); });
  });

  var CLIP = document.documentElement.classList.contains('clip');
  var moments = [$('#m1'), $('#m2'), $('#m3')];

  /* ---------- clip mode: one moment at a time, 1280x720 ---------- */
  var PLAN = {
    1: [[1, 500], [2, 600], [3, 900], [4, 800], [5, 700], [6, 1200], [7, 900]],
    2: [[1, 500], [2, 700], [3, 1000], [4, 700], [5, 1000], [6, 1000], [7, 1000]],
    3: [[1, 500], [2, 1100], [3, 1500]]
  };
  var HOLD = 500, AVAIL = 656;

  function fit(m) {
    var st = $('.stage', m);
    st.style.transform = 'none';
    var h = st.scrollHeight, s = Math.min(1, (AVAIL - 48) / h);
    var off = Math.max(24, (AVAIL - h * s) / 2);
    st.style.transform = 'translateY(' + off.toFixed(1) + 'px) scale(' + s.toFixed(4) + ')';
  }
  function resetSteps(m) {
    $$('.in', m).forEach(function (e) { e.classList.remove('in'); });
    $$('.x', m).forEach(function (e) { e.classList.remove('x'); });
  }
  function show(i, prog) {
    moments.forEach(function (m, k) { m.classList.toggle('cur', k === i); });
    if (!prog) return;
    $$('.clip-prog i').forEach(function (bar, k) { bar.classList.toggle('done', k < i); bar.classList.toggle('now', k === i); });
  }
  async function playMoment(i) {
    var m = moments[i], plan = PLAN[i + 1];
    var total = plan.reduce(function (a, s) { return a + s[1]; }, 0) + HOLD;
    var bar = $$('.clip-prog i')[i];
    if (bar) bar.style.setProperty('--dur', total + 'ms');
    resetSteps(m);
    show(i, true);
    fit(m);
    await frame();
    for (var k = 0; k < plan.length; k++) {
      var step = plan[k][0];
      $$('[data-b="' + step + '"]', m).forEach(function (e) { e.classList.add('in'); });
      $$('[data-x="' + step + '"]', m).forEach(function (e) { e.classList.add('x'); });
      await sleep(plan[k][1]);
    }
    await sleep(HOLD);
  }

  if (CLIP) {
    show(0);
    window.startClip = async function () {
      window.__marks = [];
      window.__clipDone = false;
      var t0 = performance.now();
      for (var i = 0; i < moments.length; i++) {
        if (i > 0) { moments[i - 1].classList.add('out'); await sleep(320); moments[i - 1].classList.remove('out'); }
        await playMoment(i);
        window.__marks.push(Math.round(performance.now() - t0) / 1000);
      }
      window.__clipDone = true;
    };
  }

  var fontsReady = document.fonts
    ? Promise.all([
      document.fonts.load('400 40px "Young Serif"'),
      document.fonts.load('400 16px "Public Sans"'),
      document.fonts.load('600 16px "Public Sans"'),
      document.fonts.load('400 14px "IBM Plex Mono"'),
      document.fonts.load('500 14px "IBM Plex Mono"')
    ]).then(function () { return document.fonts.ready; }, function () { return document.fonts.ready; })
    : Promise.resolve();
  fontsReady.then(function () {
    if (CLIP) fit(moments[0]);
    window.__ready = true;
  });
})();
