# Auto-amélioration

Une amélioration qui ne se mesure pas n'existe pas. La boucle repose sur quatre éléments, tous dans
`finance/journal/` (à sauvegarder sur Drive : sans eux, la mémoire repart de zéro).

| Fichier | Rôle |
|---|---|
| `previsions.jsonl` | chaque prévision chiffrée, sa probabilité, celle du modèle statistique, son issue |
| `registre-modeles.jsonl` | résultats hors échantillon de chaque modèle sur chaque instrument |
| `lecons.md` | leçons validées par Patrick, datées et prouvées |
| `bilan-AAAA-MM-JJ.{md,docx}` | bilans successifs |

## 1. Prévoir de façon vérifiable

Chaque horizon de chaque analyse porte au moins une prévision : un cours, un seuil, une date, une
probabilité. Le script calcule à côté la probabilité d'un modèle statistique simple (marche aléatoire
rééchantillonnée, dérive au taux sans risque). L'écart entre les deux est ce que l'analyse prétend
apporter.

## 2. Noter

`finance.py evaluer` tranche chaque prévision échue et calcule le score de Brier, (probabilité −
issue)², pour l'agent et pour le modèle. 0 est parfait, 0,25 est le score d'une pièce jetée à 50 %.
`finance.py annoter` qualifie chaque échec : `analyse` (thèse fausse), `evenement_exogene`, `timing`
(bonne thèse, mauvais moment), `hasard` (rien à corriger), `donnees` (source erronée ou périmée).

## 3. Mesurer

`finance.py bilan` donne :
- l'**apport de l'analyse** : 1 − Brier agent / Brier modèle ; positif, l'analyse fait mieux que le
  modèle ; négatif, elle fait moins bien et doit s'en rapprocher ;
- le **calibrage** : sur les prévisions annoncées à 70 %, combien se sont réalisées ? Un écart de plus
  de 10 points sur cinq prévisions ou plus signale une surconfiance ou une sous-confiance ;
- la ventilation par horizon et par type d'instrument, les causes d'échec, l'écart moyen avec la
  référence passive, le classement des modèles du registre.

Sous vingt prévisions évaluées, aucune conclusion statistique : le bilan le dit.

## 4. Apprendre, sous contrôle

Après chaque bilan, trois leçons au plus, chacune appuyée sur une ligne du bilan, soumises à Patrick.
Une leçon validée entre dans `lecons.md` :

```
- [2027-03-02] Sur les actions cycliques, ne pas annoncer plus de 65 % à un an (preuve : bilan du
  2027-03-02, 9 prévisions à 70-80 %, 4 réalisées).
```

Chaque analyse lit `lecons.md` à l'étape 0 et cite dans `lecons_appliquees` celles qui ont joué. Une
leçon de plus de six mois est réexaminée au bilan suivant : confirmée, reformulée ou retirée.

Ce qui ne change jamais par ce biais : le plancher, la probabilité maximale de l'atteindre, la liste
des produits interdits, l'absence d'ordre. Ces règles ne bougent que sur décision explicite de
Patrick, dans `config.json` ou `finance/config.local.json`.

## 5. Garde-fous contre la fausse amélioration

- Ne pas réécrire une prévision après coup : le script refuse de remplacer une prévision évaluée.
- Ne pas multiplier les prévisions faciles (à 95 % sur une évidence) pour embellir le score :
  l'apport se juge contre le modèle, qui les réussit aussi.
- Ne pas changer de modèle après une mauvaise année : le registre juge sur plusieurs instruments.
- Ne pas tirer de leçon d'un échec annoté `hasard`.

## Rythme

Évaluer à chaque séance (étape 0). Bilan mensuel, ou après dix nouvelles évaluations. Si Patrick le
souhaite, une tâche planifiée peut lancer l'évaluation et le bilan chaque mois ; la proposer, ne pas la
créer sans accord.
