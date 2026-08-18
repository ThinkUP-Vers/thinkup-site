const clarityId = 'wg2wwqst2s';
const consentKey = 'thinkup_analytics_consent';

/* Pages sans aucune mesure d'audience, meme si le visiteur a consenti
   ailleurs sur le site.

   Les diagnostics de conformite affichent que les reponses ne quittent pas
   le navigateur. Clarity rejoue les clics et le DOM : il capterait donc les
   reponses au questionnaire — absence de base legale, conservation illimitee,
   transfert hors UE — et les enverrait chez Microsoft, hors Union europeenne.
   Une page qui explique le regime des transferts ne peut pas en realiser un
   a l'insu du visiteur. L'engagement affiche doit rester litteralement vrai.

   Aucun traceur n'etant depose ici, aucune banniere de consentement n'est
   requise sur ces pages (article 82 de la loi Informatique et Libertes). */
const noTrackPages = ['ai-act.html', 'rgpd.html'];

function isNoTrackPage(){
  const path = location.pathname.replace(/\/+$/, '');
  return noTrackPages.some(function(page){
    return path.endsWith('/' + page) || path.endsWith('/' + page.replace('.html', ''));
  });
}

function loadClarity(){
  if(window.__thinkupClarityLoaded) return;
  window.__thinkupClarityLoaded = true;
  (function(c,l,a,r,i,t,y){
    c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
    t=l.createElement(r);t.async=1;t.src='https://www.clarity.ms/tag/'+i;
    y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
  })(window, document, 'clarity', 'script', clarityId);
}

function buildConsentBanner(){
  if(localStorage.getItem(consentKey)) return;

  const banner = document.createElement('div');
  banner.className = 'cookie-banner visible';
  banner.setAttribute('role','dialog');
  banner.setAttribute('aria-label','Choix des cookies de mesure');
  banner.innerHTML =
    '<p>Think\'UP utilise une mesure d\'audience sobre pour comprendre les pages utiles. Vous pouvez accepter ou refuser.</p>'+
    '<div class="cookie-actions">'+
    '<button class="cookie-btn" type="button" data-consent="no">Refuser</button>'+
    '<button class="cookie-btn primary" type="button" data-consent="yes">Accepter</button>'+
    '</div>';

  banner.addEventListener('click',function(e){
    const choice = e.target && e.target.getAttribute('data-consent');
    if(!choice) return;
    localStorage.setItem(consentKey,choice);
    banner.classList.remove('visible');
    if(choice === 'yes') loadClarity();
  });

  document.body.appendChild(banner);
}

document.addEventListener('DOMContentLoaded',function(){
  if(isNoTrackPage()) return;
  if(localStorage.getItem(consentKey) === 'yes') loadClarity();
  buildConsentBanner();
});
