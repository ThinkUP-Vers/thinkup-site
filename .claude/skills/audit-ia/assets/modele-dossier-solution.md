<!-- Gabarit du dossier de mise en œuvre : document INTERNE, écrit pour Patrick.
Objectif : pouvoir tout mettre en place chez le client sans avoir à poser une seule question.
Règles : references/solution.md. -->

# Résumé en dix lignes

<!-- consigne : pour qui ; quel problème ; quelle solution ; combien (devis {{devis.total}}, budget hors devis
{{devis.budget_tiers_min}} à {{devis.budget_tiers_max}} s'il y en a un) ; quel gain ({{bc.global.gain_annuel.central}}
par an en central, {{bc.global.gain_annuel.prudent}} en prudent) ; en combien de temps ; qui fait quoi
(Patrick, freelance, client) ; le risque principal et sa parade ; la première action lundi matin. -->

# 1. Traçabilité constat → solution → devis

{{TABLEAU:tracabilite}}

# 2. Solutions

<!-- consigne : une partie « ## S1 — {{sol.S1.titre}} » par solution retenue ou en option, avec TOUTES
les sous-parties ci-dessous, dans cet ordre. Une sous-partie sans objet porte une ligne qui dit pourquoi.

### Le problème traité
Constats P#, faits marquants (avec la citation), résultat attendu en une phrase mesurable.

### Le principe, simplement
Cinq lignes maximum, compréhensibles sans culture technique. Une analogie si elle aide.

### Ce qui a été écarté, et pourquoi
Les options étudiées (non-IA, outil existant, no-code, développement) et la raison de chaque rejet.

### Architecture et flux
Tableau : Déclencheur | Étape | Outil | Donnée en entrée → en sortie | Contrôle humain.
Puis les accès et droits nécessaires (qui, quel compte, quel niveau).

### Outils et coûts
Chaque outil : offre exacte, prix public relevé (date + lien), hébergement des données, DPA disponible,
réglage « pas d'entraînement sur vos données ». Préférer ce que le client paie déjà.

### Prérequis côté client
Accès, licences, données (où, quel format, quelle qualité), personnes à mobiliser et combien de temps.

### Mise en œuvre pas à pas
Étapes numérotées. Chacune commence par [Patrick], [Freelance] ou [Client], puis :
- Quoi : l'action ;
- Pourquoi : ce qu'elle permet ;
- Comment : au niveau du clic ou de la commande, menus et noms de champs compris ;
- Vérifier : comment savoir que c'est bon ;
- Si ça ne marche pas : la cause la plus probable et quoi faire ;
- Durée estimée.

### Prompts et paramétrages
Les prompts complets, prêts à coller, dans des blocs de code ; les réglages exacts (modèle, température
si exposée, variables, colonnes d'un tableur, règles d'un scénario).

### Jeu de tests et critères d'acceptation
Au moins cinq cas tirés du contexte réel, dont deux cas limites : entrée → sortie attendue → critère
réussi / raté. Puis le seuil d'acceptation qui déclenche la généralisation.

### Indicateurs
Tableau : indicateur | point de départ (fait ou hypothèse) | cible | méthode et fréquence de mesure.

### Conformité RGPD et IA Act
Données personnelles traitées, base légale, sous-traitants et DPA, transferts hors UE, AIPD oui/non et
pourquoi ; qualification IA Act et obligations qui en découlent, vérifiées à la date du jour (sources).
Ce qui relève d'un avocat.

### Risques et parades
Tableau : risque | probabilité | conséquence | parade | qui surveille.

### Exploitation et maintenance
Qui fait quoi après la mise en service, à quelle fréquence ; que faire si l'outil change de prix ou
de comportement ; plan B si l'éditeur disparaît.

### Formation et conduite du changement
Qui former, combien de temps, sur quoi ; comment présenter l'outil aux équipes (ce qui ne change pas
pour elles, ce qui change) ; les objections probables et la réponse.

### Brief prestataire
Si un freelance intervient : cahier des charges métier prêt à envoyer (contexte, objectif, périmètre,
livrables, critères d'acceptation, contraintes techniques et RGPD, délai, budget cible, profil recherché).
Sinon : « Sans objet, réalisé par Patrick ». -->

# 3. Planning et répartition des rôles

<!-- consigne : semaines numérotées depuis la commande ; jalons de décision (go / no-go après pilote) ;
tableau RACI simple (Patrick, freelance, dirigeant, référent métier, informatique). -->

# 4. Outils, coûts et rentabilité de la mission

{{TABLEAU:outils}}

{{TABLEAU:rentabilite}}

<!-- consigne : commenter en trois lignes : la mission est-elle au bon prix pour Think'UP ? Quel lot est
le plus exposé à un dépassement, et quelle est la contingence prévue ? -->

# 5. Questions à régler avant de démarrer

{{TABLEAU:questions_internes}}

# 6. Glossaire technique

<!-- consigne : chaque terme technique employé dans ce dossier, expliqué en une ou deux lignes, avec
l'exemple concret de ce projet. -->
