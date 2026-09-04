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

  function setOpen(open) {
    header.classList.toggle('menu-open', open);
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    burger.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
  }

  burger.addEventListener('click', function () {
    setOpen(!isOpen());
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
