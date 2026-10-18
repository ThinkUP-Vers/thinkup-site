# Recherche et comparaison des prestations

## Ce que l'outil peut lire, et ce qu'il ne peut pas

Constat du 17/10/2026, à réévaluer si les outils de la session changent :

- Les comparateurs de vols et d'hôtels (Google Flights, Skyscanner, Kayak, Booking, Expedia) se
  construisent en JavaScript ou bloquent les robots : WebFetch n'en lit pas les prix, et un navigateur
  sans interface n'y a pas obtenu de résultats. Ne pas s'acharner.
- Se lisent souvent : pages tarifaires des hôtels indépendants, pages d'horaires des transporteurs
  régionaux, sites officiels des musées et sites (horaires, jours de fermeture, tarifs), offices de
  tourisme, pages des transports publics, conditions générales et pages bagages des compagnies.
- Quand un prix ne peut pas être lu pour les dates exactes : le noter `indicatif` (prix trouvé pour
  d'autres dates, avec la source) ou `estime` (calcul expliqué), et demander à Patrick de coller le
  résultat de sa recherche (texte ou capture) pour le passer en `constate`. Un agent qui demande au
  client de valider le tarif au moment de réserver ne perd pas la face ; un agent qui invente, si.

## Par poste : où chercher, quoi relever

| Poste | Sources à privilégier | À relever en plus du prix |
|---|---|---|
| Vol | site de la compagnie ; comparateurs à défaut, pour repérer les compagnies qui desservent la ligne | numéro de vol, aéroports et terminaux, durée, escales, bagages inclus, conditions de modification et de remboursement, compagnie qui opère le vol |
| Train | opérateur national ou régional (SNCF Connect, Trenitalia, Renfe, DB, CP, Eurostar…), revendeurs à défaut | gares exactes, réservation obligatoire ou non, échange et remboursement |
| Car, bateau | opérateur | lieu de départ précis, bagages, fréquence en basse saison |
| Hébergement | site de l'établissement ; plateformes pour les avis et pour repérer l'offre | adresse et quartier, distance à pied ou en transport du programme, petit-déjeuner, taxe de séjour, heure d'arrivée et de départ, annulation gratuite jusqu'à quand, avis récents |
| Transferts | transports publics officiels, puis taxis et navettes | durée réelle à l'heure prévue, fréquence la nuit et le week-end |
| Location | loueurs ; vérifier franchise, carburant, kilométrage, conducteur additionnel, permis international | lieu et heure de prise et de restitution |
| Activité | site officiel du lieu, billetterie officielle | jours de fermeture, réservation obligatoire, créneau, durée |
| Assurance | d'abord la notice de la carte bancaire du payeur ; puis contrats annulation et assistance | plafonds de frais médicaux et de rapatriement, franchise, exclusions |

Les prix en devise étrangère portent `devise`, `taux_eur` (valeur d'une unité en euros) et
`taux_source` (source et date du taux, par exemple la Banque centrale européenne).

## Comparer honnêtement

- **À périmètre égal** : un vol à 60 € sans bagage contre un vol à 95 € avec bagage n'est pas une
  économie de 35 € pour qui voyage avec une valise ; un hôtel loin du programme coûte en taxis et en
  temps.
- **Temps porte à porte**, pas seulement durée de vol : trajet vers l'aéroport, enregistrement,
  sûreté, arrivée en centre-ville. Un train de 4 h de centre à centre bat souvent un vol de 1 h 15.
- **Conditions** : non remboursable, modifiable avec frais, annulation gratuite jusqu'à une date ;
  une petite différence de prix achète parfois une vraie souplesse.
- **Avis** : récents (moins d'un an), en nombre suffisant, lus pour les motifs (bruit, propreté,
  wifi pour un déplacement professionnel), pas seulement pour la note.
- **Billets séparés** : deux vols sur deux réservations distinctes ne sont pas protégés en cas de
  correspondance manquée ; le signaler et prévoir une marge large, ou préférer un billet unique.
- **Forfait** : réserver transport et hébergement ensemble auprès d'un même professionnel peut
  constituer un forfait touristique, qui donne au voyageur une protection plus large (Code du tourisme,
  art. L211-1 et suivants) ; le mentionner quand l'écart de prix est faible.
- **Correspondances** : le script alerte sous des seuils génériques (60 min entre deux vols, 90 min
  avant un vol, 15 min avant un train) ; le temps minimum de correspondance publié par l'aéroport fait
  foi pour un changement d'avion.

## Formules

Deux formules par défaut (Essentiel, Confort), trois si le budget est large ou si Patrick hésite entre
deux philosophies (par exemple : tout en train, ou avion et voiture). Une prestation commune à
plusieurs formules porte toutes leurs lettres dans `variantes`. La recommandation se justifie en une
phrase par rapport au brief, pas par le prix seul.

## Déléguer à l'agent recherche-voyage (Claude Code seulement)

Là où l'agent `recherche-voyage` existe (Claude Code, dépôt du site), et pour plus de trois postes ou
un voyage à plusieurs étapes, lancer en parallèle un agent `recherche-voyage` par poste. Le cahier des
charges tient en quelques lignes et ne contient **aucun nom de voyageur, aucune référence de
réservation, aucun numéro** :

```
Poste : hébergement à Porto
Dates : arrivée le 2027-03-13, départ le 2027-03-15 (2 nuits)
Voyageurs : 2 adultes, une chambre double
Formules : A = 3 étoiles ou pension bien notée, 100 € la nuit au plus ; B = 4 étoiles, 180 € au plus
Contraintes : centre historique ou Ribeira, calme, annulation gratuite souhaitée
Programme à desservir : gare de Campanhã à l'arrivée, caves de Vila Nova de Gaia le 14
Date et heure du relevé : 2026-10-15T11:00 (Europe/Paris)
```

L'agent renvoie des prestations au format de `dossier-json.md`, prêtes à coller. Les relire avant de
les intégrer : une source qui ne mène pas à la page du prix, ou un prix `constate` sans dates exactes,
se requalifie.
