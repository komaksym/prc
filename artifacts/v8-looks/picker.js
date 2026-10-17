(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.tabs a'));
  var looks = Array.prototype.slice.call(document.querySelectorAll('.look'));
  function mark(v) { links.forEach(function (a) { a.setAttribute('aria-current', String(a.dataset.v === v)); }); }
  mark(looks[0].id);
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) mark(e.target.id); });
    }, { rootMargin: '-45% 0px -50% 0px' });
    looks.forEach(function (s) { io.observe(s); });
  }
  document.addEventListener('keydown', function (e) {
    var i = Number(e.key) - 1;
    if (e.metaKey || e.ctrlKey || e.altKey || !(i >= 0 && i < looks.length)) return;
    looks[i].scrollIntoView({ behavior: 'smooth' });
    mark(looks[i].id);
  });
})();
