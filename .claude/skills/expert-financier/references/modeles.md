# Modèles : entraîner, tester, retenir

« Entraîner l'agent » ne modifie pas le modèle de langage : ses connaissances sont figées. Ce qui
s'entraîne, ce sont les modèles quantitatifs qu'il utilise, sur les données que Patrick ou l'agent
fournissent, et ce qui s'améliore, c'est la sélection de ces modèles et le calibrage de ses propres
prévisions (`references/auto-amelioration.md`).

## Le protocole de test

`finance.py backtest` découpe l'historique en fenêtres glissantes : les paramètres de chaque modèle
sont choisis sur trois ans (756 séances, meilleur ratio de Sharpe), puis appliqués tels quels à l'année
suivante, qui n'a pas servi au choix. Seules ces années de test comptent. Frais du plus petit budget
compris (le plus pénalisé par les frais fixes), liquidités rémunérées au taux sans risque, position
décidée à la clôture et appliquée à la séance suivante. Deux approximations, à garder en tête pour les
petits écarts : les frais fixes sont rapportés au budget de départ (pas à la valeur du moment), et le
changement de paramètres entre deux fenêtres n'est pas facturé.

Lecture :
- un modèle qui ne bat pas l'achat-conservation hors échantillon, en rendement ou en perte maximale à
  rendement comparable, n'apporte rien : le dire ;
- un Sharpe d'entraînement très supérieur au Sharpe de test signale le surajustement (alerte au-delà
  d'un écart de 0,5) ;
- un seul instrument ne prouve rien : un modèle devient « champion » dans le registre après trois
  instruments au moins, avec un gain de Sharpe médian supérieur à 0,1 et une perte maximale pas plus
  profonde de 5 points.

## Modèles intégrés

| Nom | Idée | Horizons |
|---|---|---|
| `achat_conservation` | référence | moyen, long |
| `tendance_mm` | investi si le cours dépasse sa moyenne mobile (100, 150, 200 jours) | moyen, long |
| `croisement_mm` | moyenne rapide au-dessus de la lente | moyen |
| `momentum_12_1` | performance passée hors dernier mois positive | moyen |
| `volatilite_cible` | exposition réduite quand la volatilité monte, ajustée par paliers | moyen, long |
| `rsi_court` | achat sur repli court (RSI 2) dans une tendance haussière | court |
| `cassure_donchian` | achat sur nouveau plus haut, sortie sur nouveau plus bas | court, moyen |

## Écrire un nouveau modèle (le développeur)

Un fichier Python dans `finance/modeles/` (essais) ou `$S/modeles/` (modèle éprouvé, versionné après
accord de Patrick), sur le patron de `$S/modeles/tendance_volatilite.py` :

```python
NOM = "mon_modele"                      # identifiant unique
LIBELLE = "Ce que fait le modèle, en une phrase"
HORIZONS = ["moyen"]
GRILLE = [{"n": 100}, {"n": 200}]        # trois à cinq jeux de paramètres, pas davantage

def expositions(prix, n):                # prix : numpy.ndarray des clôtures
    ...                                  # renvoie un tableau de même longueur, valeurs entre 0 et 1
```

Règles :
- l'exposition du jour t ne dépend que des cours jusqu'à t : le script le vérifie en recalculant le
  modèle sur des historiques tronqués et écarte tout modèle qui regarde l'avenir ;
- exposition entre 0 (liquidités) et 1 (investi) : ni levier ni vente à découvert ;
- une grille courte : chaque jeu de paramètres en plus augmente la chance de trouver un faux gagnant ;
- une idée économique avant le code (pourquoi l'effet existerait-il, pourquoi durerait-il ?).

## Tester un modèle entraîné ailleurs

Un modèle d'apprentissage automatique entraîné hors de l'outil (Python, tableur, plateforme) se
teste par ses signaux : un CSV `date,exposition` (0 à 1), produit en n'utilisant pour chaque date que
des données antérieures.

```bash
python3 $S/scripts/finance.py backtest $A --signaux signaux.csv
```

L'absence d'anticipation ne peut pas être contrôlée sur des signaux importés : le script le signale, et
Patrick doit confirmer comment ils ont été produits. Un modèle entraîné sur toute la période puis testé
sur cette même période ne prouve rien.

## Données d'entraînement

Toute série de cours passée par `donnees` ou `importer` sert de terrain. Pour juger un modèle,
plusieurs instruments et plusieurs régimes (hausse, krach, taux montants) valent mieux qu'un long
historique d'un seul titre. L'option `--aujourdhui` rejoue une analyse à une date passée sur les seules
données connues ce jour-là : valable pour les modèles du script, qui ne savent rien de la suite. Elle
ne mesure pas le jugement de l'agent : le modèle de langage connaît l'issue des épisodes antérieurs à
ses données d'entraînement (2008, 2020, 2022...) et ne peut pas l'oublier. Seules les prévisions faites
en temps réel et notées à l'échéance mesurent ce jugement.
