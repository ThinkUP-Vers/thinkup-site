# Gestion du risque

## Le plancher : ce qu'il est, ce qu'il n'est pas

`seuil_perte_max` = 0,75 : si la valeur d'une stratégie tombe à 25 % de la mise, tout est vendu et
rien n'est réinvesti sans décision de Patrick. C'est un seuil de ruine, pas une gestion du risque :
après -75 %, il faut +300 % pour revenir à la mise. Le script l'applique dans chaque simulation et
refuse toute stratégie dont la probabilité de l'atteindre dépasse `proba_max_plancher` (5 %), en
retenant la plus défavorable de quatre mesures : les trois hypothèses de tendance ci-dessous et le
rejeu de toutes les fenêtres réelles de l'historique.

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

Les trois hypothèses gardent le risque de l'historique (volatilité, queues de distribution,
corrélations entre lignes) et ne changent que la tendance médiane de chaque ligne :

- **Cas central** (tableaux de la note) : taux sans risque plus une prime prudente par classe d'actif
  (`primes_de_risque` dans `config.json` : 3 % pour les actions, 1 % pour les obligations, 0 pour les
  matières premières, devises et crypto-actifs). Ne pas supposer de prime reviendrait à dire que les
  actions ne rapportent pas plus qu'un livret, et pousserait toujours vers les liquidités.
- **Neutre** : aucune prime, chaque ligne croît au taux sans risque en valeur médiane. Test de
  résistance : la stratégie tient-elle si le marché ne rémunère pas le risque sur l'horizon ?
- **Historique** : prolonge la tendance passée de chaque ligne. Optimiste pour un gagnant d'hier.
- **Rejeu** : les fenêtres réelles, crises comprises, dans leur ordre. Ne contient aucune crise plus
  grave que celles déjà vécues par la série : un historique court qui ignore 2008 sous-estime le risque.
- Les blocs s'allongent avec l'horizon (jusqu'à 126 séances) pour garder la durée des crises.
- « Fait mieux que la référence » compare la stratégie et l'ETF de référence sous les mêmes
  hypothèses : le chiffre traduit l'effet du risque, des frais et des stops, jamais un avantage de
  l'analyse. L'avantage revendiqué se mesure ailleurs : dans les prévisions et leur score.
- Produit à levier : simulé comme un levier quotidien constant sur sa série sous-jacente (`levier`),
  perte bornée à la mise. Approximation : un turbo a un levier qui varie avec le cours et une barrière
  désactivante ; vérifier la fiche du produit.

## Ce qui reste hors modèle

Faillite de l'émetteur, suspension de cotation, défaut du courtier (garantie des titres et des
espèces, à vérifier chez le courtier), risque de change d'un actif hors euro (compté dans le cours s'il
est converti, à vérifier), liquidité d'une petite valeur. Les signaler dans le pré-mortem quand ils
s'appliquent.
