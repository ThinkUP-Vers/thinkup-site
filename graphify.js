/* graphify.js — animated SVG chart plugin for Think'UP
 * Usage: add data-graphify="ring" + data attributes to any element.
 * data-value   : numeric 0-100 (fill %)
 * data-display : text shown in ring centre (default: value + "%")
 * data-color   : pink | purple | cyan | grad (default: purple)
 * data-size    : SVG diameter in px (default: 88)
 * data-stroke  : arc stroke width in px (default: 7)
 */
;(function () {
  'use strict';

  var PALETTE = {
    pink:   '#D020CC',
    purple: '#7B46E8',
    cyan:   '#0096B8'
  };

  var GRAD_STOPS =
    '<stop offset="0%" stop-color="#D020CC"/>' +
    '<stop offset="55%" stop-color="#7B46E8"/>' +
    '<stop offset="100%" stop-color="#0096B8"/>';

  var gradIdCounter = 0;

  function buildRing(el) {
    var value   = Math.min(100, Math.max(0, parseFloat(el.dataset.value) || 0));
    var display = el.dataset.display || (value + '%');
    var color   = el.dataset.color  || 'purple';
    var size    = parseInt(el.dataset.size,   10) || 88;
    var sw      = parseInt(el.dataset.stroke, 10) || 7;

    var r    = (size - sw) / 2;
    var circ = 2 * Math.PI * r;
    var dash = circ - (value / 100) * circ;
    var cx   = size / 2;
    var cy   = size / 2;

    var gradId = 'gfyGrad' + (++gradIdCounter);
    var gradDef = '';
    var stroke;
    if (color === 'grad') {
      stroke  = 'url(#' + gradId + ')';
      gradDef = '<defs><linearGradient id="' + gradId + '" x1="0" y1="0" x2="1" y2="1">' +
                GRAD_STOPS + '</linearGradient></defs>';
    } else {
      stroke = PALETTE[color] || PALETTE.purple;
    }

    var svg =
      '<svg class="gfy-ring" width="' + size + '" height="' + size + '"' +
           ' viewBox="0 0 ' + size + ' ' + size + '" aria-hidden="true">' +
        gradDef +
        '<circle class="gfy-ring-track"' +
          ' cx="' + cx + '" cy="' + cy + '" r="' + r + '"' +
          ' fill="none" stroke="#E5E1F5" stroke-width="' + sw + '"' +
          ' transform="rotate(-90 ' + cx + ' ' + cy + ')"/>' +
        '<circle class="gfy-ring-arc"' +
          ' cx="' + cx + '" cy="' + cy + '" r="' + r + '"' +
          ' fill="none" stroke="' + stroke + '" stroke-width="' + sw + '"' +
          ' stroke-linecap="round"' +
          ' stroke-dasharray="' + circ + '" stroke-dashoffset="' + circ + '"' +
          ' transform="rotate(-90 ' + cx + ' ' + cy + ')"' +
          ' data-dash="' + dash + '"/>' +
        '<text class="gfy-ring-label"' +
          ' x="' + cx + '" y="' + cy + '"' +
          ' text-anchor="middle" dominant-baseline="middle">' +
          display +
        '</text>' +
      '</svg>';

    el.innerHTML = svg;
    el.classList.add('gfy-active', 'gfy-pending');
  }

  function animate(el) {
    el.querySelectorAll('.gfy-ring-arc').forEach(function (arc) {
      var target = parseFloat(arc.dataset.dash);
      requestAnimationFrame(function () {
        arc.style.transition = 'stroke-dashoffset 1.1s cubic-bezier(.25,.46,.45,.94)';
        arc.style.strokeDashoffset = target;
      });
    });
    el.classList.remove('gfy-pending');
    el.classList.add('gfy-done');
  }

  function init() {
    document.querySelectorAll('[data-graphify="ring"]').forEach(buildRing);

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { animate(e.target); io.unobserve(e.target); }
      });
    }, { threshold: 0.35 });

    document.querySelectorAll('.gfy-pending').forEach(function (el) {
      io.observe(el);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
