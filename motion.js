/* Mouvement — Think'UP. Zéro dépendance.
   Fait quatre choses : ombre de l'en-tête et barre de progression au
   défilement, apparition progressive des blocs, compteurs animés, et rien
   d'autre. Voir motion.css pour le principe de sécurité : seuls les éléments
   encore sous la ligne de flottaison sont masqués, jamais ceux déjà visibles. */
(function () {
  'use strict';

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var header = document.querySelector('header.site');
  var pending = [];   /* éléments masqués qui attendent leur tour */
  var ticking = false;
  var bar = null;
  var portrait = document.querySelector('.portrait-frame');
  var narrow = window.matchMedia('(max-width: 880px)');

  if (!reduce) {
    bar = document.createElement('div');
    bar.className = 'mo-progress';
    bar.setAttribute('aria-hidden', 'true');
    document.body.appendChild(bar);
  }

  /* Un élément qu'on a dépassé d'un coup (lien d'ancre vers le bas de page)
     ne déclenche jamais l'observateur : on le révèle ici, hors écran, pour
     qu'il ne reste pas invisible quand on remonte. */
  function flushAbove() {
    for (var i = pending.length - 1; i >= 0; i--) {
      if (pending[i].getBoundingClientRect().bottom < 0) reveal(pending[i], true);
    }
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      var y = window.pageYOffset || document.documentElement.scrollTop;
      if (header) header.classList.toggle('is-scrolled', y > 8);
      if (portrait) portrait.style.setProperty('--py', (narrow.matches ? 0 : Math.min(y * 0.12, 90)) + 'px');
      if (bar) {
        var max = document.documentElement.scrollHeight - window.innerHeight;
        bar.style.transform = 'scaleX(' + (max > 0 ? Math.min(1, y / max) : 0) + ')';
      }
      flushAbove();
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();

  if (reduce || !('IntersectionObserver' in window)) return;

  /* ── Apparition au défilement ──────────────────────────────────────────── */
  function reveal(el, instant) {
    var i = pending.indexOf(el);
    if (i === -1) return;
    pending.splice(i, 1);
    io.unobserve(el);
    if (instant) el.style.transition = 'none';
    el.classList.add('is-in');
    /* Une fois posé, on retire le marquage : les transitions de survol
       reprennent la main sur `transform`. */
    window.setTimeout(function () {
      el.removeAttribute('data-mo');
      el.classList.remove('is-in');
      el.style.removeProperty('transition');
      el.style.removeProperty('--mo-d');
    }, instant ? 50 : 1200 + (parseInt(el.style.getPropertyValue('--mo-d'), 10) || 0));
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) reveal(e.target, false);
      else if (e.boundingClientRect.bottom < 0) reveal(e.target, true);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });

  /* Blocs isolés, puis groupes dont les enfants arrivent en cascade. */
  var singles = [
    'main section:not(.hero) > .wrap > .eyebrow',
    'main section:not(.hero) h2',
    '.sec-lede', '.refs-lede', '.method-after', '.refs-suite',
    '.invite .row > div', '.pullquote', '.close-grid > div:first-child'
  ];
  var groups = [
    '.obs-list > li', '.offer-grid > .offer', '.refs-grid > .ref',
    '.faq-list > details', '.creds-row > .cred', '.berg > .berg-half'
  ];

  function below(el) { return el.getBoundingClientRect().top >= window.innerHeight; }

  function mark(el, delay) {
    if (el.closest('[data-mo]') || !below(el)) return;
    el.setAttribute('data-mo', '');
    if (delay) el.style.setProperty('--mo-d', delay + 'ms');
    pending.push(el);
    io.observe(el);
  }

  singles.forEach(function (sel) {
    Array.prototype.forEach.call(document.querySelectorAll(sel), function (el) { mark(el, 0); });
  });
  groups.forEach(function (sel) {
    var counts = [], parents = [];
    Array.prototype.forEach.call(document.querySelectorAll(sel), function (el) {
      var k = parents.indexOf(el.parentNode);
      if (k === -1) { parents.push(el.parentNode); counts.push(0); k = parents.length - 1; }
      mark(el, Math.min(counts[k] * 130, 520));
      counts[k]++;
    });
  });

  /* ── Compteurs ─────────────────────────────────────────────────────────────
     « 35 ans », « 30 », « 20 % », « 80 % » : le nombre monte de 0 à sa valeur
     quand il entre à l'écran. La largeur finale est réservée d'avance pour que
     le texte voisin ne bouge pas. Le texte d'origine est rétabli à la fin. */
  var counters = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      counters.unobserve(e.target);
      count(e.target);
    });
  }, { threshold: 0.6 });

  function count(el) {
    var target = el.__moN, suffix = el.__moS, final = el.__moT, t0 = null, dur = 1000;
    function step(t) {
      if (t0 === null) t0 = t;
      var p = Math.min(1, (t - t0) / dur), eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased) + suffix;
      if (p < 1) window.requestAnimationFrame(step);
      else { el.textContent = final; el.style.removeProperty('min-width'); }
    }
    window.requestAnimationFrame(step);
  }

  Array.prototype.forEach.call(document.querySelectorAll('.cred .n, .berg-half .pct'), function (el) {
    var m = /^(\d+)([\s\S]*)$/.exec(el.textContent.trim());
    if (!m || +m[1] < 5 || !below(el)) return;
    el.__moN = +m[1]; el.__moS = m[2]; el.__moT = el.textContent;
    el.style.minWidth = el.getBoundingClientRect().width + 'px';
    el.textContent = '0' + m[2];
    counters.observe(el);
  });
})();
