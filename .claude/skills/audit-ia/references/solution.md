# Conception de la solution

But : pour chaque constat, la réponse la plus simple qui produit le résultat, vérifiée sur pièces, et
décrite de façon que Patrick puisse la mettre en place sans poser de question. Une solution qui ne se
rattache à aucun constat n'a pas sa place, même si elle est séduisante.

## Démarche, constat par constat (par ordre de priorité)

1. **Résultat attendu.** Une phrase mesurable : « Un devis standard produit en 15 minutes au lieu d'une
   heure, sans erreur de prix. » Si on ne sait pas l'écrire, le constat est mal compris : revenir aux faits.
2. **Au moins trois options**, dans cet ordre de préférence :
   1. non-IA : organisation, règle de gestion, meilleur usage d'un outil déjà payé ;
   2. l'IA déjà disponible chez le client (Copilot dans Microsoft 365, Gemini dans Google Workspace,
      fonctions IA de l'ERP ou du CRM en place) ;
   3. automatisation no-code avec appel à un modèle de langage (Make, n8n, Zapier, Power Automate) ;
   4. développement spécifique (freelance).
   Retenir la plus simple qui atteint le résultat. Consigner chaque option écartée avec sa raison
   (`alternatives_ecartees`). Conclure « pas d'IA ici » est une réponse valable, et souvent la plus utile.
3. **Vérifier sur le web, à la date du jour** (WebSearch, puis WebFetch de la page officielle) pour chaque
   outil proposé : la fonction existe dans l'offre visée, le prix public et l'offre minimale requise,
   l'hébergement des données (UE ou non), l'existence d'un DPA, la non-réutilisation des données pour
   l'entraînement et le réglage qui la garantit. Renseigner `verifie_le` et `source`. **Jamais un prix ou
   une fonctionnalité de mémoire** : les offres IA changent tous les trimestres.
4. **La part humaine.** Où la machine propose et où l'humain décide ; qui valide, à quel moment, sur
   quel critère. Aucun envoi automatique à un client ou à un salarié sans validation, sauf justification.
5. **Conformité.** Si le skill `compliance-rgpd-ia-act` est disponible, l'appliquer. Sinon :
   - RGPD : données personnelles traitées, base légale, minimisation, sous-traitants (DPA, art. 28),
     transferts hors UE, analyse d'impact si les critères sont réunis ;
   - IA Act : pratique interdite ? système à haut risque (annexe III : recrutement et gestion RH,
     accès au crédit, etc.) ? obligations de transparence (agent conversationnel, contenu généré) ?
     obligation de maîtrise de l'IA (art. 4) pour le client déployeur. **Le calendrier d'application a
     bougé : vérifier l'état en vigueur sur une source officielle** (EUR-Lex, Commission, CNIL) et citer
     la date de vérification.
   - Ce qui relève d'un avocat est dit comme tel, pas tranché.
6. **Business case.** Renseigner `business_case` avec des références H ; si aucun gain ne se chiffre
   honnêtement, `gains_qualitatifs` à la place. Un outil partagé par deux solutions n'est compté qu'une
   fois (l'autre porte `cout_mensuel: 0` et `note: "compté en S1"`). Les licences déjà payées comptent zéro.
7. **Réalisation et effort.** Pour chaque étape : qui (Patrick en no-code, freelance avec le profil
   précis, client) et combien de jours. Réévaluer l'effort du constat (barème d'extraction.md). Prévoir
   une marge d'aléa explicite sur les étapes nouvelles pour Patrick ou dépendant d'un tiers.

## Garde-fous

- **Partir de l'existant du client.** Un outil qu'il paie déjà et maîtrise bat un meilleur outil à
  acheter, installer et faire adopter.
- **Pas de surdimensionnement.** Une PME de 20 personnes n'a pas besoin d'une plateforme ; un tableur
  bien structuré et un scénario no-code suffisent souvent.
- **Commencer petit.** Un pilote sur un périmètre restreint, des critères de passage à l'échelle, puis
  la généralisation. Le devis peut suivre ce découpage (lot pilote ferme, généralisation en option).
- **Les données d'abord.** Si la solution suppose des données propres qui n'existent pas, le premier
  lot est leur préparation, chiffrée comme telle.
- **Le savoir-faire d'une seule personne** (chiffrage, réglage, relation client) relève de l'offre
  « Formalisation de savoir-faire » : entretiens de rétro-ingénierie avant tout outil.
- **Mesure trop fragile ?** Si les volumes sont trop incertains pour décider, recommander d'abord un
  Diagnostic Index Iceberg (offre catalogue) plutôt que de bâtir sur du sable.
- **Pas de promesse.** Gains = estimations ; écrire « devrait », « estimé », jamais « garanti ».

## Écrire le dossier de solution (`02-dossier-solution.md`)

Le lecteur est Patrick : consultant expérimenté, pilote de projets, pas développeur. Le test : pourrait-il
ouvrir le dossier chez le client, lundi matin, et dérouler chaque étape sans chercher ailleurs ?

- Chaque étape au niveau du clic : noms exacts des menus, des champs, des réglages ; pas « configurer
  l'intégration » mais la suite d'actions qui la configure. Si l'interface d'un éditeur est susceptible
  d'avoir changé, donner le lien de sa documentation officielle en plus.
- Les prompts sont complets, prêts à coller, avec les variables entre crochets et un exemple rempli.
- Le jeu de tests utilise des cas réalistes tirés de l'échange (anonymisés), dont des cas limites.
- Chaque terme technique est dans le glossaire, avec l'exemple du projet.
- Si une partie dépasse ce que Patrick peut faire seul, le dire et rédiger le brief du freelance.

## Contrôle de sortie de passe

Chaque constat a une réponse (solution ou `hors_perimetre` motivé) ; chaque outil a `verifie_le` et
`source` ; `audit.py verifier $A` ne signale plus d'erreur sur les blocs solutions.
