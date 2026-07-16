# ThinkUP — Site vitrine

Site statique (HTML/CSS, sans framework ni build) de ThinkUP, cabinet de
conseil en adoption de l'IA pour dirigeants de PME. Contenu en français.
Chaque page est un fichier `.html` à la racine ; styles dans `style.css` et
`styles.css`.

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
