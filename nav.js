/* Menu mobile.
   Sous 880 px les liens de navigation ne tiennent plus dans la barre. Ils
   etaient jusqu'ici simplement masques (`display: none`), sans rien pour les
   remplacer : au telephone, La methode / Les offres / Resultats / Ressources /
   Blog n'etaient atteignables que par un lien dans le corps de la page ou par
   le pied de page. Ils vivent desormais dans `.nav-more`, qui est une rangee
   de liens dans la barre au-dessus de 880 px et un panneau deroulant en
   dessous, ouvert par le bouton `.nav-burger`.

   « Me parler 30 min » reste hors du panneau : c'est le CTA principal, il doit
   rester visible en permanence, y compris menu ferme. */
(function () {
  var header = document.querySelector('header.site');
  if (!header) return;

  var burger = header.querySelector('.nav-burger');
  var panel = header.querySelector('.nav-more');
  if (!burger || !panel) return;

  var BREAKPOINT = 880;

  function isOpen() {
    return header.classList.contains('menu-open');
  }

  /* Le panneau se limite a la hauteur d'ecran restante pour rester defilable
     en paysage. Cette hauteur depend de la barre, qu'on mesure ici : la coder
     en dur dans le CSS la desynchronise du jour ou un CTA change de taille. */
  function measure() {
    header.style.setProperty('--nav-h', header.offsetHeight + 'px');
  }
  measure();
  window.addEventListener('resize', measure);

  function setOpen(open) {
    if (open) measure();
    header.classList.toggle('menu-open', open);
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    burger.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
  }

  /* Elements atteignables au clavier tant que le panneau est ouvert : tout ce
     qui est visible dans l'en-tete, donc le logo, les liens du panneau, les
     deux CTA et le burger. Les liens du panneau ferme ont `offsetParent` nul
     et sortent d'eux-memes de la liste. */
  function focusables() {
    var all = header.querySelectorAll('a[href], button:not([disabled])');
    return Array.prototype.filter.call(all, function (el) {
      return el.offsetParent !== null;
    });
  }

  burger.addEventListener('click', function () {
    var open = !isOpen();
    setOpen(open);
    if (open) {
      var first = panel.querySelector('a[href]');
      if (first) first.focus();
    }
  });

  /* Sans ce piege, Tab quitte l'en-tete des le dernier lien et le curseur part
     dans la page couverte par le panneau : au clavier on ne voit plus ou on
     est. Echap reste la sortie, et rend le focus au burger. */
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab' || !isOpen()) return;
    var f = focusables();
    if (f.length < 2) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });

  /* Naviguer referme : sur les ancres internes la page ne se recharge pas, le
     panneau resterait ouvert par-dessus la destination. */
  panel.addEventListener('click', function (e) {
    if (e.target && e.target.closest && e.target.closest('a')) setOpen(false);
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) {
      setOpen(false);
      burger.focus();
    }
  });

  document.addEventListener('click', function (e) {
    if (isOpen() && !header.contains(e.target)) setOpen(false);
  });

  /* Repasser en grand ecran avec le menu ouvert laisserait `menu-open` colle
     sur l'en-tete : sans effet visible, mais `aria-expanded` mentirait. */
  var wide = window.matchMedia('(min-width: ' + (BREAKPOINT + 1) + 'px)');
  function onWide(e) {
    if (e.matches) setOpen(false);
  }
  if (wide.addEventListener) wide.addEventListener('change', onWide);
  else if (wide.addListener) wide.addListener(onWide);
})();
