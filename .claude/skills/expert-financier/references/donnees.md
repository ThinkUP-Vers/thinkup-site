# Données

## Sources automatiques (`finance.py donnees`)

| Source | Symboles | Contenu | Clé |
|---|---|---|---|
| `yahoo` | `MC.PA` (Paris), `CW8.PA`, `^FCHI` (CAC 40), `AAPL`, `EURUSD=X`, `BTC-EUR` | cours quotidiens ajustés des dividendes et divisions | aucune ; API non officielle, peut changer |
| `stooq` | `^cac`, `aapl.us`... | cours quotidiens | aucune |
| `fred` | `DGS10`, `T10Y2Y`, `VIXCLS`, `BAMLH0A0HYM2`, `DCOILBRENTEU` | séries macroéconomiques et de marché américaines | aucune |

Format des réponses : vérifié pour aucune des trois depuis le conteneur cloud, dont le réseau les
bloque au 23/10/2026. Contrôler le premier téléchargement réel (nombre de cours, dates, ordre de
grandeur du dernier cours contre une source de référence).

### Autoriser ces sources dans l'environnement cloud

Domaines à ajouter : `query1.finance.yahoo.com`, `stooq.com`, `fred.stlouisfed.org`. Procédure pour
Patrick, dans l'application de bureau Claude :

1. Dans la barre de titre de la session, cliquer sur le nom de l'environnement cloud. Un menu s'ouvre.
2. Cliquer sur « Modifier » (Edit) à côté de l'environnement. La fenêtre de réglages s'ouvre.
3. Dans « Accès réseau », choisir le niveau « Limité » s'il ne l'est pas déjà. La liste « Domaines
   autorisés » apparaît.
4. Ajouter les trois domaines, un par ligne, en laissant cochée la case des gestionnaires de paquets.
5. Enregistrer. Le réglage vaut pour les sessions suivantes : en ouvrir une nouvelle.

Documentation : https://code.claude.com/docs/en/cloud-environments#network-access

## Import d'un fichier (`finance.py importer`)

Accepte les exports courants : Yahoo (`Adj Close` retenu), Boursorama et ABC Bourse (point-virgule,
virgule décimale, dates jj/mm/aaaa), Investing.com (dates américaines, séparateurs de milliers), FRED,
ou tout CSV à deux colonnes. Le script choisit le format de date qui donne une suite ordonnée, retient
la clôture ajustée quand elle existe, écarte les valeurs vides, trie et dédoublonne. `--colonne` force
la colonne de cours.

Export depuis le site d'un courtier ou d'un portail, procédure type pour Patrick :

1. Ouvrir la fiche de la valeur sur le site (Boursorama, Investing.com, Yahoo Finance).
2. Ouvrir l'onglet « Historique » ou « Données historiques ». Un tableau des cours apparaît.
3. Choisir la période la plus longue proposée et la fréquence quotidienne.
4. Cliquer sur « Télécharger » ou « Exporter ». Un fichier `.csv` est enregistré sur le poste.
5. Joindre ce fichier à la conversation. Claude le passe par `importer`.

## Exigences

- Dix ans d'historique ou plus pour une analyse moyen et long terme ; trois ans au minimum (le script
  alerte en dessous) ; idéalement une série qui traverse 2008, 2020 et 2022.
- Cours ajustés des dividendes : sans eux, l'achat-conservation est sous-estimé de la valeur des
  dividendes (2 à 4 % par an pour un indice d'actions européen).
- Même devise que l'investissement, ou conversion assumée et écrite.
- `donnees/sources.json` dit d'où vient chaque série et quand elle a été relevée ; il se remplit seul
  avec `donnees` et `importer`.

## Ce qui ne vient pas des séries

Cours du jour, résultats, consensus, notations, calendrier : recherche web (agent `veille-marche`),
sources primaires d'abord, chaque fait daté. Le connecteur data.gouv.fr et le skill `datagouv-apis`
servent pour les statistiques publiques françaises (INSEE, Banque de France).
