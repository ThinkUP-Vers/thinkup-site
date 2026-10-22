---
name: visibilite-site
description: >
  Lance l'agent visibilite-site : audit du référencement (Google, Bing) et de la visibilité dans les
  réponses des IA pour think-up.fr, puis plan d'actions priorisé avec outils gratuits ou open source.
  Déclencher sur : « /visibilite-site », « booster la visibilité du site », « audit SEO », « GEO ».
  Ne pas déclencher pour : l'écriture d'un seul article ou post demandé tel quel.
---

# Visibilité du site

1. Lance l'agent `visibilite-site` avec la consigne de Patrick telle quelle (par défaut : « audit complet puis
   10 actions prioritaires »). Précise-lui s'il s'agit d'un audit seul ou d'un audit suivi des corrections
   applicables au dépôt.
2. Au retour, vérifie par `git diff --stat` ce qui a été modifié, relance
   `python3 -I .claude/skills/visibilite-site/scripts/controle_seo.py` et les contrôles de `CLAUDE.md`
   (`?v=`, `nav-burger`) avant d'annoncer quoi que ce soit.
3. Les envois (candidatures, posts, mails) restent à Patrick : l'agent ne fournit que des brouillons.

Le script `scripts/controle_seo.py` ne modifie rien. Il sert aussi de contrôle de non-régression :
il doit rester sans constat de gravité haute.
