"""Modèle ajouté, patron des modèles écrits par l'agent (references/modeles.md).

Investi seulement en tendance haussière (cours au-dessus de sa moyenne mobile), avec une exposition
réduite quand la volatilité sur 20 séances dépasse la cible. Exposition ajustée par paliers de 25 %
pour limiter les frais.
"""
import numpy as np

NOM = "tendance_volatilite"
LIBELLE = "Tendance filtrée par la volatilité (moyenne mobile et volatilité cible)"
HORIZONS = ["moyen", "long"]
GRILLE = [{"n": 150, "cible": 0.15}, {"n": 200, "cible": 0.15}, {"n": 200, "cible": 0.20}]


def expositions(prix, n, cible):
    prix = np.asarray(prix, dtype=float)
    e = np.zeros(len(prix))
    if len(prix) <= n:
        return e
    somme = np.cumsum(np.insert(prix, 0, 0.0))
    mm = np.full(len(prix), np.nan)
    mm[n - 1:] = (somme[n:] - somme[:-n]) / n
    rendements = prix[1:] / prix[:-1] - 1
    for t in range(n, len(prix)):
        if prix[t] <= mm[t]:
            continue
        vol = rendements[t - 20:t].std(ddof=1) * np.sqrt(252)
        voulu = 1.0 if vol <= 0 else min(1.0, cible / vol)
        e[t] = np.floor(voulu * 4) / 4
    return e
