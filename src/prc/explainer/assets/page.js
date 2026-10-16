// Clickable video. One scene at a time on the video engine's stage; the
// narration is the video's audio track, and window.PRC holds the same filled
// board the video rendered from.
(function () {
  var data = window.PRC;
  var board = data.board;
  var scenes = board.scenes;
  var el = function (id) { return document.getElementById(id); };
  var main = el('main'), stage = el('stage'), scale = el('scale'), audio = el('narr');
  var playBtn = el('play'), prevBtn = el('prev'), nextBtn = el('next');
  var counter = el('counter'), hint = el('hint'), strip = el('strip'), receipts = el('receipts');
  var panel = el('panel'), panelTitle = el('panel-title'), panelDiff = el('panel-diff'), panelGh = el('panel-gh');
  var cur = 0, seek = function () {}, frame = 0, regions = [];
  var hasAudio = !!audio.getAttribute('src');

  function fit() { stage.style.setProperty('--k', stage.clientWidth / 1920); }
  new ResizeObserver(fit).observe(stage);

  // Paused and idle views show this frame: the scene fully built, before its
  // fade. Only playback shows the timed reveal.
  function rest(s) { return (s.fade ? s.fade[0] : s.end) - 0.05; }
  function playing() { return hasAudio && !audio.paused && !audio.ended; }

  var opener = null, openerScene = 0;
  function closePanel(refocus) {
    var wasOpen = !panel.hidden;
    panel.hidden = true;
    main.classList.remove('has-panel');
    regions.forEach(function (r) { if (r) r.classList.remove('pg-on'); });
    if (wasOpen && refocus !== false && opener && opener.isConnected) {
      if (openerScene !== cur) { show(openerScene); }
      opener.focus();
    }
    opener = null;
  }

  function openHunk(k) {
    var t = data.targets[cur][k];
    panelTitle.textContent = t.label;
    panelDiff.innerHTML = t.hunk >= 0 ? data.hunks[t.hunk] : '<p class="hk-head">No local diff for this line.</p>';
    panelGh.href = t.url;
    regions.forEach(function (r, i) { if (r) r.classList.toggle('pg-on', i === k); });
    opener = regions[k] || document.activeElement;
    openerScene = cur;
    panel.hidden = false;
    main.classList.add('has-panel');
    el('panel-close').focus();
    var hit = panelDiff.querySelector('tr[data-k="' + t.key + '"]');
    if (hit) {
      hit.classList.add('hk-hit');
      var box = panelDiff.getBoundingClientRect();
      panelDiff.scrollTop += hit.getBoundingClientRect().top - box.top - box.height / 2;
    }
  }

  function mount(i) {
    scale.innerHTML = '';
    seek = window.prcMount(scale, board, i);
    var targets = data.targets[i];
    if (targets.length && targets[0].id) {
      // Group boxes: each target names the box it opens.
      regions = targets.map(function (t) { return scale.querySelector('.pill[data-id="' + CSS.escape(t.id) + '"]'); });
    } else {
      var found = scale.querySelectorAll('.drow:not(.gap)');
      regions = Array.prototype.slice.call(found.length ? found : scale.querySelectorAll('.item'));
      regions = regions.slice(0, targets.length);
    }
    regions.forEach(function (r, k) {
      if (!r) return;
      r.classList.add('pg-hit');
      r.setAttribute('role', 'button');
      r.setAttribute('tabindex', '0');
      r.setAttribute('aria-label', 'Open hunk for ' + targets[k].label);
      r.addEventListener('click', function () { openHunk(k); });
      r.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); openHunk(k); } });
    });
    hint.textContent = !regions.length ? '' : targets[0].id ? 'Click a box to open its hunk.' : 'Click a code line to open its hunk.';
    var links = (data.receipts || [])[i] || [];
    receipts.innerHTML = '';
    receipts.hidden = !links.length;
    if (links.length) receipts.appendChild(document.createTextNode('Receipts: '));
    links.forEach(function (l, k) {
      if (k) receipts.appendChild(document.createTextNode(' · '));
      var a = document.createElement('a');
      a.href = l.url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = l.label;
      receipts.appendChild(a);
    });
  }

  function update() {
    counter.textContent = 'Scene ' + (cur + 1) + ' of ' + scenes.length;
    prevBtn.disabled = cur === 0;
    nextBtn.disabled = cur === scenes.length - 1;
    playBtn.textContent = playing() ? 'Pause' : 'Play';
    Array.prototype.forEach.call(strip.children, function (b, i) {
      b.classList.toggle('on', i === cur);
      if (i === cur) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
    });
  }

  function show(i) {
    if (i < 0 || i >= scenes.length) return;
    var keep = playing();
    cur = i;
    closePanel(false);
    mount(i);
    if (keep) audio.currentTime = scenes[i].start;
    seek(keep ? scenes[i].start : rest(scenes[i]));
    update();
  }

  // While narration plays, the stage follows the audio clock; crossing a scene
  // end mounts the next scene, which is the video's own cut.
  function tick() {
    frame = 0;
    var t = audio.currentTime;
    if (t >= scenes[cur].end && cur < scenes.length - 1) {
      cur += 1;
      closePanel(false);
      mount(cur);
      update();
    }
    seek(t);
    if (playing()) frame = requestAnimationFrame(tick);
  }

  function play() {
    var s = scenes[cur];
    if (audio.currentTime < s.start || audio.currentTime >= s.end - 0.05) audio.currentTime = s.start;
    var p = audio.play();
    if (p && p.catch) p.catch(function () { update(); });
  }

  function toggle() {
    if (!hasAudio) return;
    if (playing()) audio.pause(); else play();
  }

  audio.addEventListener('play', function () { update(); if (!frame) frame = requestAnimationFrame(tick); });
  audio.addEventListener('pause', function () { cancelAnimationFrame(frame); frame = 0; seek(rest(scenes[cur])); update(); });

  prevBtn.addEventListener('click', function () { show(cur - 1); });
  nextBtn.addEventListener('click', function () { show(cur + 1); });
  playBtn.addEventListener('click', toggle);
  playBtn.disabled = !hasAudio;
  el('panel-close').addEventListener('click', closePanel);

  var infoBtn = el('info-open');
  if (infoBtn) infoBtn.addEventListener('click', function () { el('info').showModal(); });

  document.addEventListener('keydown', function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (el('info') && el('info').open) return;
    var tag = e.target.tagName;
    if (e.key === 'ArrowRight') { e.preventDefault(); show(cur + 1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); show(cur - 1); }
    else if (e.key === 'Escape') { closePanel(); }
    else if (e.key === ' ' && tag !== 'BUTTON' && tag !== 'A' && tag !== 'SUMMARY' && !e.target.closest('.pg-hit')) { e.preventDefault(); toggle(); }
  });

  scenes.forEach(function (s, i) {
    var b = document.createElement('button');
    b.type = 'button';
    var name = data.names[i];
    b.innerHTML = '<b>' + (i + 1) + '</b>';
    b.appendChild(document.createTextNode(name));
    b.title = name;
    b.setAttribute('aria-label', 'Go to scene ' + (i + 1));
    b.addEventListener('click', function () { show(i); });
    strip.appendChild(b);
  });

  fit();
  show(0);
  window.prcPage = { show: show, seek: function (t) { seek(t); }, scene: function () { return cur; } };
})();
