(function () {
  var uid = 0;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function numberAttr(el, name, fallback) {
    var raw = parseFloat(el.getAttribute(name));
    return Number.isFinite(raw) ? raw : fallback;
  }

  function renderRing(el) {
    if (!el || el.getAttribute('data-graphify') !== 'ring') return;

    var value = clamp(numberAttr(el, 'data-value', 0), 0, 100);
    var display = el.getAttribute('data-display') || Math.round(value) + '%';
    var color = el.getAttribute('data-color') || 'purple';
    var size = clamp(numberAttr(el, 'data-size', 88), 44, 220);
    var stroke = clamp(numberAttr(el, 'data-stroke', 7), 3, 24);
    var radius = (size - stroke) / 2;
    var circumference = 2 * Math.PI * radius;
    var targetOffset = circumference * (1 - value / 100);
    var gradientId = 'graphify-grad-' + (++uid);

    el.classList.add('graphify-ring');
    el.style.setProperty('--graphify-size', size + 'px');
    el.style.setProperty('--graphify-stroke', stroke + 'px');
    el.setAttribute('data-color', color);
    el.setAttribute('role', 'img');
    el.setAttribute('aria-label', display);

    var strokePaint = color === 'grad' ? 'url(#' + gradientId + ')' : 'currentColor';
    var defs = color === 'grad'
      ? '<defs><linearGradient id="' + gradientId + '" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="var(--pink,#D020CC)"/><stop offset="52%" stop-color="var(--purple,#7B46E8)"/><stop offset="100%" stop-color="var(--cyan,#0096B8)"/></linearGradient></defs>'
      : '';

    el.innerHTML =
      '<svg viewBox="0 0 ' + size + ' ' + size + '" aria-hidden="true">' +
      defs +
      '<circle class="graphify-ring-track" cx="' + (size / 2) + '" cy="' + (size / 2) + '" r="' + radius + '" stroke-width="' + stroke + '"></circle>' +
      '<circle class="graphify-ring-value" cx="' + (size / 2) + '" cy="' + (size / 2) + '" r="' + radius + '" stroke-width="' + stroke + '" stroke="' + strokePaint + '" stroke-dasharray="' + circumference + '" stroke-dashoffset="' + circumference + '"></circle>' +
      '</svg>' +
      '<span class="graphify-ring-label">' + display + '</span>';

    var valueCircle = el.querySelector('.graphify-ring-value');
    requestAnimationFrame(function () {
      valueCircle.style.strokeDashoffset = String(targetOffset);
    });
  }

  function refresh(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-graphify="ring"]').forEach(renderRing);
  }

  function observe() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll('[data-graphify="ring"]'));
    if (!('IntersectionObserver' in window)) {
      nodes.forEach(renderRing);
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          renderRing(entry.target);
          io.unobserve(entry.target);
        }
      });
    }, { threshold: .15 });

    nodes.forEach(function (node) { io.observe(node); });
  }

  window.Graphify = { refresh: refresh };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observe);
  } else {
    observe();
  }
})();
