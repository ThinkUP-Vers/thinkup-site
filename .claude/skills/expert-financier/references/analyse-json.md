# analyse.json

Un fichier par analyse, dans `finance/analyses/AAAA-MM-JJ-instrument/`. Exemple complet :
`exemple/analyse.json`. Les chemins de fichiers sont relatifs au dossier de l'analyse. Les taux et
poids s'écrivent en fraction (0,08 pour 8 %).

## meta

| Champ | Contenu |
|---|---|
| `reference` | `AAAA-MM-JJ-instrument`, écrit par `init` |
| `date` | date de l'analyse |
| `demande` | la demande de Patrick et les hypothèses prises à sa place |
| `statut` | `brouillon` puis `final` |

## parametres (facultatif)

Surcharge `config.json` et `finance/config.local.json` pour cette analyse seulement, clé par clé :
`enveloppe` (`PEA`, `CTO`, `AV`, `SOCIETE`), `budgets`, `courtier`, `fiscalite`... Les règles de risque
(`seuil_perte_max`, `proba_max_plancher`, `types_interdits`) ne se surchargent que sur demande
explicite de Patrick, consignée dans `meta.demande`.

## instrument

`nom`, `type` (`action`, `etf`, `fonds`, `obligation`, `matiere_premiere`, `devise`, `crypto`,
`produit_levier`, `indice`), `symbole`, `isin`, `place`, `devise`, `eligible_pea`, `fichier` (série
de cours), `prix`, `prix_date`, `prix_source`.

Obligation détenue en direct : ajouter
`"obligation": {"prix": 98.5, "coupon": 3.0, "echeance": "2034-05-25", "frequence": 1}` (prix pied de
coupon en % du nominal, coupon en %). Le script calcule rendement actuariel, duration, convexité et
sensibilité à un point de taux.

## reference_passive

`nom`, `fichier` et `classe` (par défaut `actions`) de l'ETF large auquel chaque stratégie est comparée (monde, ou indice du marché
étudié). Obligatoire en pratique : sans lui, la note ne dit pas si la stratégie vaut l'effort.

## analyse

| Champ | Contenu |
|---|---|
| `these` | la thèse en trois phrases au plus |
| `fondamental[]` | `{point, source, date}` |
| `valorisation[]` | `{indicateur, valeur, comparaison, source, date}` |
| `technique` | lecture de `analyser`, sans contredire ses chiffres |
| `premortem[]` | deux raisons au moins pour lesquelles la thèse échouerait |

## evenements[]

`{evenement, date (vide si non daté), type, probabilite, sens, ampleur_estimee, parade, source,
verifie_le}`. `type` : `banque_centrale`, `macro`, `resultats`, `politique`, `geopolitique`,
`reglementaire`, `sectoriel`, `climat`, `sanitaire`, `technologique`, `credit`, `autre`.
`probabilite` : `faible`, `moyenne`, `elevee`, `certaine`. La `parade` est décidée avant l'événement.

## scenarios[]

`{nom, probabilite, rendement, description}` ; probabilités sommant à 1 ; `rendement` sur l'horizon
moyen terme.

## strategies

Clés `court`, `moyen`, `long` (celles que la demande appelle). Pour chacune :

| Champ | Contenu |
|---|---|
| `objectif` | une phrase |
| `horizon_jours` | jours calendaires (défaut : 60, 365, 1826) |
| `enveloppe` | si différente de `parametres.enveloppe` |
| `entree`, `invalidation`, `sortie` | conditions écrites ; `invalidation` obligatoire |
| `reequilibrage_annuel` | `true` pour un portefeuille long terme à poids fixes |
| `lignes[]` | voir ci-dessous |
| `liquidites` | part laissée en liquidités ; poids + liquidités = 1 |

Ligne : `nom`, `type`, `fichier` (ou `proxy` : série de substitution déclarée), `poids`, `prix` (cours
de référence, pour les quantités et les niveaux), `stop` (perte depuis l'entrée qui déclenche la
sortie ; obligatoire en court et moyen terme), `stop_suiveur` (le stop suit le plus haut atteint),
`objectif` (gain qui déclenche la prise de bénéfice), `ttf` (`true` pour une action française de plus
d'un milliard de capitalisation), `fractionnable` (`true` si le courtier vend des fractions de part),
`classe` (`actions`, `obligations`, `immobilier`, `monetaire`, `matieres_premieres`, `devises`,
`crypto` ; obligatoire pour un ETF, un fonds ou un indice, déduite du type sinon : elle fixe la prime
de risque du cas central), `levier` (obligatoire pour un `produit_levier`, entre 1 et 20).

## previsions[]

`{id, horizon, enonce, symbole, fichier, echeance, condition: {type: au_dessus|en_dessous, seuil},
probabilite, strategie}`. `prix_reference` facultatif (par défaut, le dernier cours de la série) ;
`classe` facultative (par défaut, celle de la ligne ou de l'instrument qui partage le fichier).
L'énoncé doit être tranché à l'échéance sans discussion possible : un cours de clôture, un seuil, une
date. Probabilité entre 0,01 et 0,99.

## repartition (facultatif)

Répartition recommandée de chaque budget entre les horizons, parts sommant à 1 :
`{"1000": {"long": 1.0}, "5000": {"long": 0.8, "moyen": 0.2}}`. La note la présente en montants.
Chaque stratégie reste simulée sur la totalité du budget : pour une poche de 1 000 € dans un budget
de 5 000 €, lire la ligne 1 000 € de la stratégie concernée.

## recommandation, suivi[], lecons_appliquees[]

La recommandation dit quoi faire pour chaque budget, y compris ne rien faire. `suivi` : dates de
revue, alertes de cours à poser. `lecons_appliquees` : les leçons de `lecons.md` qui ont joué.

## Fichiers produits

- `calculs.json`, `analyse-quant.json`, `backtest.json` : calculs du script, à ne pas éditer.
- `donnees/sources.json` : origine de chaque série, écrite par `donnees` et `importer`.
- `livrables/<référence>-note.{md,html,docx}`.
- `journal.md` : ce qui a été fait, vérifié, décidé, et ce qui reste à faire.
