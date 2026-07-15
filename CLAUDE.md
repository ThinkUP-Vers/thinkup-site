# ThinkUP — Site vitrine

Site statique (HTML/CSS, sans framework ni build) de ThinkUP, cabinet de
conseil en adoption de l'IA pour dirigeants de PME. Contenu en français.
Chaque page est un fichier `.html` à la racine ; styles dans `style.css` et
`styles.css`.

## Méta-agent : évaluation systématique des demandes

À CHAQUE demande de l'utilisateur, avant de répondre, évalue silencieusement
sa complexité selon la grille de la Phase 0 du skill `meta-agent`
(multi-facettes, complexité, enjeu, ambiguïté productive, volume) :

- Demande simple (score 0–1) : réponds directement, n'invoque rien, ne
  mentionne pas le méta-agent.
- Demande complexe (score ≥ 2) : invoque le skill `meta-agent` et suis son
  protocole (conception d'agents sur mesure, challenge croisé via l'agent
  `challenger`, synthèse).

L'utilisateur peut aussi forcer l'activation avec `/meta-agent`, ou la refuser
en le disant explicitement.
