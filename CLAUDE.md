# ThinkUP — Site vitrine

Site statique (HTML/CSS, sans framework ni build) de ThinkUP, cabinet de
conseil en adoption de l'IA pour dirigeants de PME. Contenu en français.
Chaque page est un fichier `.html` à la racine.

Feuilles de style réellement chargées : `style-v2.css` sur les 30 pages,
`style-legacy.css` sur 8 d'entre elles, `conformite.css` sur `ai-act.html`
et `rgpd.html`. `style.css` existe encore à la racine mais aucune page ne
le référence ; `styles.css` n'existe pas.

Chaque page porte aussi un bloc `<style>` en ligne, chargé APRÈS les
feuilles liées. À spécificité égale, c'est donc lui qui l'emporte : une
règle mutualisée dans `style-v2.css` doit monter d'un cran (par exemple
`.navlinks li.cta a` plutôt que `.navlinks .cta a`) pour passer devant.

## Cache : incrémenter le `?v=` à CHAQUE modification d'une feuille

`.htaccess` sert les fichiers `.css` et `.js` avec
`Cache-Control: public, max-age=31536000, immutable`. `immutable` signifie
que le navigateur ne revalide même pas au rechargement : tant que l'URL ne
change pas, un visiteur au cache tiède garde l'ancienne feuille pendant un
an.

Le HTML, lui, n'est mis en cache qu'une heure. Modifier une feuille sans
changer son `?v=` livre donc le nouveau balisage avec l'ancien CSS — c'est
exactement ce qui a cassé la navigation en production le 04/09/2026 (liens
empilés avec des puces, boutons sans style).

Donc, dès qu'on touche `style-v2.css`, `style-legacy.css` ou
`conformite.css` : incrémenter le `?v=` dans TOUTES les pages qui la
chargent, dans le même commit.

```
sed -i 's/style-v2\.css?v=[0-9]*/style-v2.css?v=4/' *.html
```

Attention : `curl` et un navigateur sans cache récupèrent toujours la
dernière version. Vérifier que le serveur sert le bon fichier ne prouve
donc rien sur ce que reçoivent les visiteurs. Le seul contrôle qui vaut
est de comparer le `?v=` des pages à celui du dernier changement de
feuille.

## Méta-agent : évaluation systématique des demandes

À CHAQUE demande de l'utilisateur, avant de répondre, évalue silencieusement
sa complexité selon la grille de la Phase 0 du skill `meta-agent`
(multi-facettes, complexité, enjeu, ambiguïté productive, volume) :

- Demande simple (score 0–1) : réponds directement, en commençant ta réponse
  par une seule ligne d'information — « *Méta-agent : score X/5 — réponse
  directe.* » — sans rien ajouter d'autre sur le méta-agent, puis la réponse.
- Demande complexe (score ≥ 2) : invoque le skill `meta-agent` et suis son
  protocole. Il présente son analyse (score, sous-problèmes, équipe d'agents
  envisagée) et demande confirmation à l'utilisateur AVANT de lancer
  l'orchestration (conception d'agents sur mesure, challenge croisé via
  l'agent `challenger`, synthèse).

L'utilisateur peut aussi forcer l'activation avec `/meta-agent`, ou la refuser
en le disant explicitement.
