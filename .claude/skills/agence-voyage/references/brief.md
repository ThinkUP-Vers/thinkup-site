# Entretien de découverte

Un bon agent pose peu de questions, mais les bonnes, et une seule fois. Ne demander que ce qui change
la recherche ; le reste se décide avec une hypothèse écrite.

## Ce qu'il faut savoir avant de chercher

| Thème | Questions | Champ |
|---|---|---|
| Qui | Combien de voyageurs, adultes, enfants (âge à la date du voyage) ; nationalité ; type de document et date d'expiration ; mobilité réduite, santé, régime alimentaire, si cela compte pour le voyage | `voyageurs` |
| Quand | Dates d'aller et de retour, flexibilité (± jours, jours de la semaine possibles) ; contraintes horaires fixes (rendez-vous, séminaire, rentrée) | `brief.date_aller`, `date_retour`, `flexibilite` |
| D'où, où | Ville de départ et de retour ; destination(s), ou envies si la destination est à conseiller (climat, distance maximale, type de séjour) | `brief.depart`, `retour_a`, `etapes` |
| Pourquoi | Professionnel : lieu et horaires imposés, facturation au nom de la société, politique de déplacement. Personnel : occasion, envies, ce qui ferait rater le voyage | `brief.objectif`, `meta.nature` |
| Budget | Montant, total ou par personne, ce qu'il couvre (transport, hébergement, activités, repas), souple ou plafond strict | `brief.budget` |
| Style | Rythme (dense, tranquille) ; hébergement (catégorie, quartier, chambre, cuisine) ; transport (direct ou moins cher, train plutôt qu'avion, horaires acceptables, bagages) | `brief.rythme`, `hebergement`, `transport` |
| Indispensable / à éviter | Ce qui doit absolument figurer ; ce qui est exclu | `brief.incontournables`, `a_eviter` |
| Déjà en main | Programmes de fidélité, avoirs ou bons, assurance annulation ou assistance (carte bancaire, contrat), permis de conduire | `voyageurs[].fidelite`, `brief.notes` |

## Manière de faire

- Un seul message, questions numérotées, regroupées par thème. Les choix fermés (formule de budget,
  vol direct ou non, rythme) passent par AskUserQuestion.
- Ce que `voyages/profils.json` dit déjà ne se redemande pas ; le rappeler en une ligne pour
  confirmation (« je pars sur : hublot, hôtel calme, Flying Blue »).
- Ne demander une information de santé que si elle change le voyage (vaccin, altitude, accessibilité),
  et ne garder que la conséquence (« éviter les escaliers »), pas le diagnostic.
- Une réponse manquante n'arrête pas le travail : écrire l'hypothèse dans `brief.notes`
  (« budget supposé hors repas ») ou une question dans `questions_ouvertes`, bloquante seulement si
  elle empêche de réserver.

## Contredire le projet quand il ne tient pas

À dire avant toute recherche, en commençant par le problème, puis la meilleure alternative :

- **Budget et saison** : vacances scolaires, ponts, grands salons et événements font monter les prix
  du transport et de l'hôtel ; vérifier le calendrier local avant de promettre une fourchette.
- **Durée et distance** : un long-courrier pour moins de cinq jours sur place laisse peu de temps
  utile une fois le décalage horaire compté ; le dire et proposer d'allonger ou de changer de cible.
- **Climat** : saison des pluies, cyclones, chaleur extrême, hiver austral ; vérifier sur une source
  climatologique, pas sur un souvenir.
- **Documents** : passeport à refaire, visa à délai long, autorisation électronique à demander ;
  comparer les délais annoncés à la date de départ.
- **Logistique** : correspondance trop courte, arrivée de nuit dans un lieu mal desservi, journée
  sans marge avant un rendez-vous important (prévoir l'arrivée la veille).
- **Sécurité** : zone déconseillée par le ministère ; voir la règle 6 du skill.
