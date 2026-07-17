const clarityId = 'wg2wwqst2s';
const consentKey = 'thinkup_analytics_consent';

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
  if(localStorage.getItem(consentKey) === 'yes') loadClarity();
  buildConsentBanner();
});
