# Recherche et comparaison des prestations

## Ce que l'outil peut lire, et ce qu'il ne peut pas

Les prix de vols et d'hôtels pour des dates exactes viennent des connecteurs Kiwi.com et Trivago
quand ils sont actifs (`sources.md`). Sans eux, constat du 17/10/2026 :

- Les comparateurs de vols et d'hôtels (Google Flights, Skyscanner, Kayak, Booking, Expedia) se
  construisent en JavaScript ou bloquent les robots : WebFetch n'en lit pas les prix, et un navigateur
  sans interface n'y a pas obtenu de résultats. Ne pas s'acharner. Test élargi du 19/10/2026 à dix-neuf
  agences en ligne, discounters, ventes privées et comparateurs : aucun prix daté lisible ; huit pages
  d'accueil lisibles, avec des prix d'appel ou des bons plans datés. Le détail par site, et la manière
  de couvrir chacun, sont dans `sources.md` ; la procédure est la section « Balayage des sites de
  voyage » ci-dessous.
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
| Vol | connecteur Kiwi.com ; site de la compagnie pour vérifier le prix du même vol en achat direct | numéro de vol, aéroports et terminaux, durée, escales, bagages inclus, conditions de modification et de remboursement, compagnie qui opère le vol |
| Train | opérateur national ou régional (SNCF Connect, Trenitalia, Renfe, DB, CP, Eurostar…), revendeurs à défaut | gares exactes, réservation obligatoire ou non, échange et remboursement |
| Car, bateau | opérateur | lieu de départ précis, bagages, fréquence en basse saison |
| Hébergement | connecteur Trivago (par destination, ou autour du lieu de rendez-vous) ; site de l'établissement pour les conditions et un éventuel meilleur prix direct | adresse et quartier, distance à pied ou en transport du programme, petit-déjeuner, taxe de séjour, heure d'arrivée et de départ, annulation gratuite jusqu'à quand, avis récents |
| Transferts | transports publics officiels, puis taxis et navettes | durée réelle à l'heure prévue, fréquence la nuit et le week-end |
| Location | loueurs ; vérifier franchise, carburant, kilométrage, conducteur additionnel, permis international | lieu et heure de prise et de restitution |
| Activité | site officiel du lieu, billetterie officielle | jours de fermeture, réservation obligatoire, créneau, durée |
| Assurance | d'abord la notice de la carte bancaire du payeur ; puis contrats annulation et assistance | plafonds de frais médicaux et de rapatriement, franchise, exclusions |

Les prix en devise étrangère portent `devise`, `taux_eur` (valeur d'une unité en euros) et
`taux_source` (source et date du taux : BCE via Frankfurter, voir `sources.md`).

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

## Balayage des sites de voyage

Les connecteurs donnent les meilleurs prix datés, pas tous les vendeurs. Avant de présenter une
proposition, passer en revue les agences en ligne, discounters, dénicheurs de bons plans, ventes
privées et comparateurs listés dans `sources.md`, pour le transport principal et l'hébergement (les
activités et les transferts n'en relèvent pas).

1. **Après les connecteurs**, quand la meilleure option de chaque formule est connue : c'est elle que
   le balayage cherche à battre, à périmètre égal.
2. **Site par site, selon son mode** (`sources.md`) :
   - `lu` : WebSearch `site:<domaine> <destination> <mois> <année>` (pour VoyagesPirates, ajouter la
     ville de départ), puis WebFetch des pages trouvées ; relever toute offre de vol, d'hôtel ou de
     vol + hôtel pour la destination, la période et le nombre de voyageurs ;
   - `connecteur` : dans les résultats Trivago de l'hôtel retenu, relever le prix de chaque site de la
     liste qui y figure comme vendeur ;
   - `mail` : avec l'accord de Patrick, lire dans sa messagerie les mails d'alerte des sites auxquels il
     est inscrit (`profils.json`), selon les règles de `sources.md` ; ne jamais ouvrir un lien de ces
     mails ;
   - `patrick` : écrire le lien de recherche prérempli, ou la page d'accueil et les critères.
3. **Tout consigner** dans `journal.md`, tableau « Balayage » : site, mode, résultat (offre avec prix,
   nature et lien ; « rien de mieux » ; « non lu » et la raison), heure. Chaque site de la liste a sa
   ligne, même vide : un site passé sous silence est un site non vérifié.
4. **Une offre qui bat la meilleure option** à périmètre égal (prix final, bagages, annulation,
   petit-déjeuner, temps porte à porte) entre dans `prestations` avec la nature de son prix ; une offre
   moins bonne n'y entre pas, sa ligne au journal suffit.
5. **Remettre à Patrick, avec la proposition**, la liste des sites `patrick` avec leurs liens et
   critères, et lui demander de coller ce qu'il voit : un prix collé pour les dates et les voyageurs
   exacts devient `constate`. Une vente repérée dans un mail lui est donnée par son nom, à ouvrir
   lui-même. Les ventes privées se consultent avec son propre compte ; l'outil n'en crée aucun et ne
   s'y connecte pas (règle 3 du skill).

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
Balayage des sites de voyage : oui (sites et modes de sources.md)
Date et heure du relevé : 2026-10-15T11:00 (Europe/Paris)
```

L'agent renvoie des prestations au format de `dossier-json.md`, prêtes à coller ; pour un poste de
vols ou d'hébergement, il fait aussi le balayage de son poste et rend son tableau, à reporter dans
`journal.md`, avec les liens à transmettre à Patrick. Les relire avant de les intégrer : une source
qui ne mène pas à la page du prix, ou un prix `constate` sans dates exactes, se requalifie.
