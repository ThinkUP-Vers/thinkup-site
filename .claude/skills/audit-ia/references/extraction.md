# Extraction : de la source aux faits

But : une base de faits dont chaque élément se retrouve mot pour mot dans `00-source.md`. Tout ce qui
suit (constats, solutions, chiffres, devis) s'appuie dessus. Une erreur ici se propage partout.

## Lire la source en entier, deux fois

1. Première lecture, sans rien noter : comprendre l'entreprise, le ton, ce qui préoccupe vraiment le
   dirigeant (souvent dit en fin d'échange, ou en passant).
2. Seconde lecture, crayon en main, avec la grille ci-dessous.

Une transcription automatique contient des erreurs (noms propres, chiffres, mots techniques). Citer tel
quel ; signaler une correction évidente dans `texte` (« transcription : "sage sang" = Sage 100 »).
Un chiffre douteux à l'oreille devient une question Q, pas un fait.

## Grille de lecture

| Rubrique | Ce qu'on cherche |
|---|---|
| Entreprise | activité, clients, effectif, CA, sites, organisation, saisonnalité |
| Système d'information | ERP, CRM, messagerie, bureautique (M365, Google), outils métier, fichiers Excel pivots, qui administre |
| Données | où elles vivent, format, qualité, doublons, données personnelles ou sensibles (RH, santé, clients) |
| Usages IA actuels | outils utilisés, officiellement ou non (ChatGPT perso = usage non encadré), résultats, craintes |
| Processus | pour chacun : étapes, rôles, volumes, fréquence, durée, outils, délais, erreurs |
| Partie visible | ce qui est décrit spontanément : réunions, devis, rapports, relances déclarées |
| Partie immergée | ce que révèlent les détails : re-saisies, recherches d'information, vérifications, corrections en boucle, consolidations, relances oubliées, savoir-faire détenu par une seule personne |
| Chiffres | tout nombre avec son unité et son périmètre, tel qu'énoncé |
| Objectifs | ce que le dirigeant veut obtenir, ses critères de réussite, son horizon |
| Contraintes | budget, délais, ressources internes, CSE, clients exigeants sur la sécurité, hébergement, réticences |
| Décision | qui décide, qui influence, calendrier, budget évoqué, prestataires déjà consultés |
| Objections | doutes, mauvaises expériences, peurs exprimées |
| Silences | ce qui aurait dû être dit et ne l'a pas été → question Q |

## Règles des faits (F)

- Un fait = une affirmation. « On fait 40 devis par mois et ça prend une heure chacun » = deux faits.
- `citation` : copier-coller exact de la source, assez long pour être retrouvé, assez court pour être lu.
- `localisation` : horodatage (Noota, audio) ou paragraphe (texte). Sans elle, le relecteur ne peut rien vérifier.
- `statut` : **mesuré** (compté, chronométré, extrait d'un outil), **déclaré** (affirmé comme un fait),
  **estimé** (« à peu près », « je dirais »), **déduit** (calculé par nous à partir d'autres F, à citer).
- Aucune interprétation dans un fait. L'interprétation va dans les constats.
- Les compléments apportés par Patrick après l'entretien sont des faits à part entière :
  `locuteur: "Patrick (complément du JJ/MM)"`, `localisation: "échange du JJ/MM"`.
- Les noms des salariés restent dans le dossier (interne) ; les livrables parlent de fonctions.

## Règles des constats (P)

- Un constat décrit un effet subi, jamais l'absence d'une solution. « Pas d'outil d'IA pour les devis »
  n'est pas un constat ; « Chaque devis demande une heure de recherche de prix dans trois fichiers » en est un.
- Chaque constat cite ses faits. Pas de fait, pas de constat.
- `cause_racine` : dite par le client, ou hypothèse de notre part (alors `certitude` au plus « probable »).
- `zone` : visible si le client l'a présenté comme un problème ; immergée si on l'a fait émerger.
- Fusionner les constats qui ont la même cause ; séparer ceux qui appellent des réponses différentes.

## Barème de priorisation (par défaut, à ajuster si le contexte l'exige)

| Note | Impact | Effort de mise en œuvre | Risque |
|---|---|---|---|
| 1 | confort, gêne marginale | réglage d'un outil déjà en place, moins de 2 jours | aucune donnée sensible, erreur sans conséquence |
| 2 | moins de 50 h/an ou gêne ponctuelle | outil standard à paramétrer, 2 à 5 jours | données internes non personnelles |
| 3 | 50 à 200 h/an, ou qualité visible en interne | intégration simple entre deux outils, 5 à 15 jours | données personnelles courantes, erreur visible d'un client |
| 4 | 200 à 500 h/an, ou effet direct sur le CA ou la marge | développement spécifique ou données à préparer, 15 à 40 jours | données sensibles (RH, santé), engagement contractuel |
| 5 | plus de 500 h/an, ou risque client, juridique, de continuité | refonte d'un processus ou du SI, plus de 40 jours | décision automatisée sur des personnes, haut risque IA Act, dépendance critique |

L'effort se note vraiment à la conception de la solution ; à l'extraction, noter une première
estimation, à corriger ensuite.

## Hypothèses (H) et questions (Q)

- Toute valeur nécessaire au business case et absente de la source devient une H : valeur, unité,
  origine précise, `a_valider: true`. Origines admises : un fait F (avec le calcul), une référence
  ThinkUP citée (l'article « Calculer le ROI de l'IA » : 45 000 € chargés / 1 600 h ≈ 28 €/h ; fourchettes
  d'automatisation par type de tâche), une réponse de Patrick. Jamais « estimation » sans base.
- Les fourchettes ThinkUP de taux d'automatisation (article ROI) : re-saisies 70–85 %, reporting et
  consolidation 60–80 %, premiers jets rédactionnels 40–65 %, relances sur règles 60–75 %, veille et
  synthèse 50–70 %. Le scénario prudent prend le bas de fourchette, le central le milieu.
- Une Q est **bloquante** si, sans réponse, on ne peut ni choisir la solution ni chiffrer le gain.
  Destinataire `Patrick` quand il peut savoir (il était dans la pièce), `client` sinon.

## Contrôle de sortie de passe

`python3 $S/scripts/audit.py verifier $A --etape extraction` sans erreur, puis relire la liste des
constats en se demandant : « Le dirigeant reconnaîtrait-il chacun d'eux comme le sien ? » et « Quel
irritant cité deux fois n'apparaît nulle part ? ».
