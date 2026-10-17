# Format de dossier.json

Exemple complet : `exemple/dossier.json` (voyage fictif). Dates au format `AAAA-MM-JJ`, horaires au
format `AAAA-MM-JJTHH:MM` à l'heure locale du lieu, accompagnés de leur fuseau IANA
(`Europe/Paris`, `America/New_York`). Les montants sont des nombres, sans symbole.

## meta

| Champ | Contenu |
|---|---|
| `reference` | `AAAA-MM-JJ-objet`, posé par `init` |
| `objet` | une ligne : « Lisbonne, séminaire puis week-end » |
| `nature` | `pro`, `perso` ou `mixte` |
| `statut` | `brief` → `proposition` → `reservation` → `pret` → `en_cours` → `clos` ; il fixe l'étape des contrôles (`pret`, `en_cours` et `clos` valent `depart`) |
| `fuseau_reference` | fuseau du voyageur, `Europe/Paris` par défaut |

## voyageurs[]

`id` (`V1`…), `nom`, `categorie` (`adulte`, `enfant`, `bebe`), `age` (enfants seulement, à la date du
voyage), `nationalite` (code ISO), `document` : `{type: passeport | cni, expire_le}`, `fidelite[]`,
`preferences[]`, `contraintes[]`.

Interdits, refusés par le script : numéro de passeport ou de carte d'identité, numéro de carte
bancaire, cryptogramme, code, mot de passe.

## brief

`depart`, `retour_a`, `etapes[]` (`{lieu, pays, du, au, fuseau}`, pays en code ISO à deux lettres),
`date_aller`, `date_retour`, `flexibilite`, `budget` (`{montant, devise: "EUR", base: total |
par_personne, plafond_strict}`), `objectif`, `rythme`, `hebergement`, `transport`,
`incontournables[]`, `a_eviter[]`, `notes` (hypothèses prises faute de réponse).

## variantes[]

`{id: "A", nom: "Essentiel", idee: "une phrase"}`. Les formules comparées dans la proposition.

## prestations[]

| Champ | Contenu |
|---|---|
| `id` | `P1`, `P2`… |
| `type` | `vol`, `train`, `bus`, `ferry`, `transfert`, `location`, `hebergement`, `activite`, `restaurant`, `assurance`, `formalite`, `autre` |
| `libelle`, `fournisseur`, `numero` | « Vol Paris-CDG → Lisbonne », la compagnie, le numéro de vol ou de train |
| `variantes[]` | formules auxquelles la prestation appartient |
| `voyageurs[]` | vide = tous les voyageurs |
| `debut`, `fin` | horaire pour un transport ou une activité ; dates d'arrivée et de départ pour un hébergement |
| `fuseau_debut`, `fuseau_fin` | obligatoires dès qu'il y a un horaire ; `fuseau_fin` vaut `fuseau_debut` s'il manque |
| `lieu_debut`, `lieu_fin`, `adresse` | aéroport et terminal, gare, adresse de l'hôtel |
| `prix` | voir ci-dessous |
| `conditions` | `{annulation, annulation_gratuite_jusqu_au, modification, bagages}` |
| `statut` | `proposee`, `retenue` (choisie, pas encore réservée), `reservee`, `ecartee`, `annulee` |
| `reservation` | `{reference, reserve_le, par, paye, reste_du, solde_avant}` |
| `notes` | motif d'un écart, précision utile |

`prix` : `{unitaire, unite, quantite, devise, taux_eur, taux_source, nature, source, releve_le, inclus}`.
Le montant vaut `unitaire × quantite`, converti en euros par `taux_eur` si `devise` n'est pas `EUR`.
`nature` : `constate`, `indicatif` ou `estime` (règle 1 du skill). `source` : l'adresse de la page,
suivie si besoin d'un commentaire (« https://… (tarif 2026) »), ou la base d'une estimation.
`releve_le` : date et heure du relevé. Gratuit ou déjà inclus : `unitaire: 0`.

## formalites[]

`{id: "F1", voyageurs[], pays, exigence, validite_min_mois, statut: ok | a_faire | bloquant |
sans_objet, echeance, source, verifie_le, notes}`. `validite_min_mois` : validité restante exigée
après le retour (0 = valable pendant tout le séjour) ; le script la compare à `expire_le`.

## conseils[]

`{pays, theme: securite | sante | meteo | argent | telephone | prises | usages | transport_local |
autre, texte, source, verifie_le}`. Un conseil `securite` par pays étranger au moins.

## programme[], contacts[], questions_ouvertes[], incidents[]

- `programme[]` : `{date, titre, deroule[]}`, un par jour.
- `contacts[]` : `{nom, role, telephone, email, adresse}`.
- `questions_ouvertes[]` : `{id: "Q1", question, pour, bloquante, reponse}` ; une question bloquante
  sans réponse empêche l'étape réservation.
- `incidents[]` : `{date, prestation, nature: retard | annulation | surreservation | bagage | autre,
  faits, droits, demarche, statut: ouvert | reclame | indemnise | clos, echeance}`.

## Ce que contrôle le script, par étape

| Étape | Contrôles |
|---|---|
| toutes | identifiants uniques, données interdites, dates lisibles |
| brief | voyageurs, dates, ville de départ, budget, étapes, expiration des documents |
| proposition | prix complets et sourcés, prix de plus de 72 h, horaires et fuseaux, chevauchements, battements courts, changement de lieu sans transfert, nuits sans hébergement, dépassement du budget, part non confirmée au-delà de 30 %, formalités et conseils sourcés, validité des documents |
| reservation | plan retenu non vide, prestations à réserver, références de réservation, soldes en retard, annulation sans frais dans les 72 h, questions bloquantes, formalité vérifiée pour chaque pays |
| depart | tout réservé, aucune formalité à faire ou bloquante, contacts et programme présents |
