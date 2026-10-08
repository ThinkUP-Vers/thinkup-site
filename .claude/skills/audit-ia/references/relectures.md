# Passes de relecture croisée

Quatre relecteurs indépendants, chacun avec une seule grille, qui ne voient pas la conversation et
lisent les fichiers à froid. Leur unique production : des objections classées et prouvées. Ils ne
réécrivent rien.

## Lancement

Avec l'outil Agent : un seul message, quatre appels en parallèle à l'agent `relecteur-audit`, chacun
avec ce prompt (remplacer les crochets) :

```
Rôle : [R1 | R2 | R3 | R4]. Tour : [1 | 2].
Dossier d'audit : [chemin absolu de $A]
Grille : .claude/skills/audit-ia/references/relectures.md, section [R1…R4].
[Tour 2 uniquement : tes objections du tour 1 et le traitement annoncé pour chacune :
 <liste>. Vérifie qu'elles sont réellement levées, puis cherche les régressions
 introduites par les corrections.]
```

Sans outil Agent : faire les quatre passes soi-même, l'une après l'autre, en relisant les fichiers
depuis le disque (pas de mémoire de la rédaction) et en s'imposant une seule grille par passe.

Mode express : R1 et R4 seulement, un seul tour.

## Classement des objections

- **BLOQUANT** : erreur factuelle ; chiffre faux, non sourcé ou incohérent entre documents ; promesse de
  résultat ; risque juridique ou de conformité ; solution qui ne traite pas le constat ; étape non
  exécutable ; information interne dans un document client.
- **IMPORTANT** : ce qu'un dirigeant exigeant ou Patrick sur le terrain remarquerait : manque de clarté,
  trou dans le raisonnement, oubli d'un irritant, risque non traité, devis mal protégé.
- **MINEUR** : style, ordre, formulation.

Format de sortie obligatoire :

```
## R? — tour N — VALIDE | À CORRIGER | À REFAIRE
### Bloquant
1. [fichier, section] Constat. Preuve (citation, calcul, source web avec date). Correction attendue.
### Important
### Mineur
### Vérifications faites
Une ligne par vérification significative, y compris celles qui n'ont rien révélé.
```

Pas de critique vide : une objection sans preuve ne compte pas. Pas d'invention de problème : un
document solide reçoit VALIDE et quelques mineures réelles.

## R1 — Fidélité à la source

Lire `00-source.md` en entier, puis `dossier.json`, puis `livrables/*-compte-rendu.md` et
`livrables/*-devis.md`.
1. Chaque citation des faits F existe mot pour mot dans la source, à la localisation indiquée.
2. Chaque statut est juste : un « à peu près » n'est pas « déclaré », une estimation n'est pas « mesuré ».
3. Chaque affirmation du compte rendu sur l'entreprise remonte à un F ou à une H. Lister toute
   affirmation orpheline, y compris les généralités sectorielles présentées comme leur situation.
4. Chaque citation du compte rendu est fidèle et attribuée à la bonne fonction ; aucun salarié nommé.
5. Omissions : un irritant, une contrainte, une objection ou un objectif présent dans la source et
   absent des constats ou non traité. Signaler surtout ce que le dirigeant a répété ou dit avec force.
6. Les hypothèses à valider sont toutes visibles dans le compte rendu.

## R2 — Le dirigeant prospect

Se mettre dans la peau du dirigeant de cette entreprise (contexte dans `dossier.json`, bloc client) :
pressé, non technicien, sceptique, attentif à son argent et à ses équipes. Lire **seulement**
`livrables/*-compte-rendu.md` et `livrables/*-devis.md`, comme il les recevrait.
1. Est-ce que je reconnais mon entreprise et mes problèmes, ou un discours générique ?
2. Chaque recommandation : est-ce que je la comprends en trente secondes ? Qu'est-ce qui change pour
   mes équipes lundi ? Qu'est-ce que ça me demande, à moi et à elles ?
3. Les chiffres : est-ce que j'y crois ? Qu'est-ce qui me paraît gonflé ?
4. Le prix : est-il justifié par ce que je lis ? Puis-je commencer plus petit ?
5. Ce qui m'inquiète et n'est pas traité : mes données, la réaction des équipes, la dépendance à un
   outil, le temps que ça va me prendre.
6. Le ton : vendeur, condescendant, jargonneux, ou juste ? Repérer les tournures de texte généré.
7. Rien d'interne ne doit apparaître (taux, coûts de prestataires, rentabilité de Think'UP).
Terminer par : « Les trois questions que je poserais avant de signer » et « Ce qui me ferait signer ».

## R3 — Technique, conformité, exécutabilité

Lire `dossier.json`, `livrables/*-dossier-solution-INTERNE.md`, puis la section Recommandations du
compte rendu.
1. Chaque solution fonctionne avec les outils réellement en place chez le client (faits F « outil »),
   flux de données et droits d'accès compris.
2. Chaque outil, fonction et prix : vérifier sur le site de l'éditeur (WebSearch, WebFetch) ; citer
   l'URL et la date ; signaler tout écart ou toute affirmation invérifiable.
3. RGPD et IA Act : qualification juste, obligations correctes et en vigueur à la date du jour
   (vérifier sur une source officielle) ; DPA, hébergement, transferts ; ce qui relève d'un avocat est
   dit comme tel.
4. Exécutabilité par Patrick, consultant non développeur : prendre chaque étape et se demander si on
   peut la faire sans chercher ailleurs. Signaler étapes manquantes, instructions vagues (« configurer
   l'intégration »), prompts absents ou incomplets, jeu de tests ou critères d'acceptation manquants.
5. Estimations de charge réalistes ; dépendances et aléas identifiés ; plan B si un outil fait défaut.
6. Exploitation : qui maintient quoi après la mise en service.

## R4 — Cohérence commerciale et devis

Lire tout : `dossier.json`, `calculs.json`, les trois livrables `.md`, et `boutique-config.js` à la
racine du dépôt.
1. Traçabilité complète : chaque constat traité ou écarté avec raison ; chaque solution retenue chiffrée ;
   aucun lot sans constat qui le justifie.
2. Business case : hypothèses réalistes (taux d'automatisation dans les fourchettes ThinkUP, supervision
   déduite, montée en charge, temps interne du client compté) ; le scénario prudent tient-il ? Les
   gains sont-ils présentés comme des estimations ?
3. Chiffres identiques partout : synthèse, corps du compte rendu, devis, dossier interne, `calculs.json`.
   Tout chiffre écrit en dur dans un `.md` au lieu d'une balise est une objection.
4. Prix : offres du catalogue au prix public ; lots sur mesure cohérents avec les jours estimés dans le
   dossier interne ; rentabilité de la mission acceptable ; contingence présente sur les lots risqués.
5. Devis : objet clair, lots compréhensibles, livrables vérifiables, échéancier, validité, mention de TVA,
   renvoi aux CGV, hypothèses de chiffrage et exclusions qui protègent contre la dérive de périmètre.
6. La proposition offre une porte d'entrée (pilote) ; la prochaine étape est claire et datée ; les
   suites logiques (Pilotage, Formalisation de savoir-faire, Conformité) sont citées si elles répondent
   à un constat, jamais plaquées.

## Contrôle final (agent principal, après le dernier tour)

Lire les trois livrables `.md` d'une traite, puis cocher dans `journal.md` :

- [ ] `audit.py construire $A --final --pdf` : zéro erreur ; chaque alerte restante est justifiée
- [ ] La synthèse tient sur une page et se comprend seule
- [ ] Chaque constat a une réponse : solution, option, ou non-recommandation motivée
- [ ] Les chiffres de la synthèse, du corps, du devis et du dossier interne sont identiques
- [ ] Les hypothèses à valider et les questions ouvertes figurent dans le compte rendu
- [ ] Aucun élément interne dans le compte rendu ni dans le devis
- [ ] Chaque solution du dossier interne a : étapes au clic, prompts, tests, critères d'acceptation,
      indicateurs, conformité, maintenance, brief prestataire si besoin
- [ ] Le devis porte l'identité complète du client (SIREN, adresse), les dates, le total, l'échéancier
- [ ] Les objections non levées après deux tours sont listées pour Patrick, avec ma recommandation
