# Gestion du risque

## Le plancher : ce qu'il est, ce qu'il n'est pas

`seuil_perte_max` = 0,75 : si la valeur d'une stratégie tombe à 25 % de la mise, tout est vendu et
rien n'est réinvesti sans décision de Patrick. C'est un seuil de ruine, pas une gestion du risque :
après -75 %, il faut +300 % pour revenir à la mise. Le script l'applique dans chaque simulation et
refuse toute stratégie dont la probabilité de l'atteindre dépasse `proba_max_plancher` (5 %), en
retenant la plus défavorable de trois mesures : tirage par blocs à dérive neutre, tirage par blocs à
dérive historique, rejeu de toutes les fenêtres réelles de l'historique.

Le risque se pilote bien avant le plancher, par trois leviers :

1. **Le budget de risque par ligne** (`risque_max_par_ligne`) : poids × distance du stop ≤ 2 % du
   budget en court terme, 5 % en moyen terme. Une ligne de 25 % avec un stop à 8 % risque 2 %.
2. **La diversification** : au-delà de la moitié du budget sur une seule action, le script alerte.
3. **La taille minimale** : un ordre dont les frais dépassent 1 % est trop petit pour le budget.

## Produits

| Autorisé | Conditions |
|---|---|
| Actions, ETF, fonds, obligations, matières premières via ETC, devises via ETF | aucune |
| Crypto-actifs au comptant | volatilité forte : budget de risque appliqué strictement |
| Produits à levier à perte limitée à la mise (turbos, warrants, ETF à levier) | court terme seulement, 10 % du budget au plus, stop obligatoire |

Interdits, parce que la perte peut dépasser la mise : CFD, contrats à terme, vente d'options, vente à
découvert, change sur marge. Une ligne marquée `perte_illimitee` est refusée quel que soit son type.

## Stops et objectifs

- Court terme : stop entre 2 et 3 fois la variation quotidienne moyenne (fournie par `analyser`) ;
  plus serré, le bruit le déclenche ; plus large, le budget de risque impose une ligne minuscule. Gain
  visé au moins 1,5 fois le risque, 2 fois de préférence.
- Moyen terme : stop suiveur de 10 à 20 % selon la volatilité, ou invalidation fondamentale écrite.
- Long terme : pas de stop sur un cœur diversifié (il ferait vendre au creux d'une crise) ; le risque
  se tient par l'allocation, le rééquilibrage annuel et le plancher.
- Un stop simulé s'exécute à la clôture qui le franchit : un écart d'ouverture est compté. Chez le
  courtier, un ordre stop ne garantit pas le prix, sauf stop garanti payant.

## Lire les simulations

- **Dérive neutre** (cas central de la note) : la tendance de l'instrument est ramenée au taux sans
  risque ; seule la forme du risque passé est conservée. Hypothèse prudente.
- **Dérive historique** : prolonge la tendance passée. Optimiste pour un gagnant d'hier.
- **Rejeu** : les fenêtres réelles, crises comprises, dans leur ordre. Ne contient aucune crise plus
  grave que celles déjà vécues par la série : un historique court qui ignore 2008 sous-estime le risque.
- Les blocs s'allongent avec l'horizon (jusqu'à 126 séances) pour garder la durée des crises.

## Ce qui reste hors modèle

Faillite de l'émetteur, suspension de cotation, défaut du courtier (garantie des titres et des
espèces, à vérifier chez le courtier), risque de change d'un actif hors euro (compté dans le cours s'il
est converti, à vérifier), liquidité d'une petite valeur. Les signaler dans le pré-mortem quand ils
s'appliquent.
