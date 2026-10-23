# Événements exogènes

Personne ne prédit un choc imprévisible. L'outil fait trois choses : il recense ce qui est daté et
connu, il estime ce qui est probable sans être daté, et il prépare la réaction avant l'événement
(parade). Ce qui reste imprévisible est couvert par la structure : plancher, stops, diversification,
liquidités.

## 1. Le calendrier, à revérifier à chaque analyse

Sur l'horizon de chaque stratégie, avec la date et la source officielle :

| Domaine | Événements | Sources de référence |
|---|---|---|
| Banques centrales | réunions et décisions BCE, Fed, Banque d'Angleterre, Banque du Japon ; discours de Jackson Hole | calendriers officiels des banques centrales |
| Statistiques | inflation (estimation rapide Eurostat, CPI américain), emploi américain, PIB, indices PMI | Eurostat, BLS, BEA, INSEE |
| Entreprise | résultats, chiffre d'affaires trimestriel, assemblée, détachement du dividende, journée investisseurs | site investisseurs de l'émetteur, Euronext |
| États | budgets, élections, échéances de plafond de dette, revues de notation souveraine | ministères, agences de notation |
| Matières premières | réunions OPEP+, stocks hebdomadaires de pétrole | OPEP, EIA |
| Marché | échéances trimestrielles des dérivés, rééquilibrage des indices | Euronext, fournisseurs d'indices |

## 2. Les risques non datés

Pour chaque risque plausible sur l'horizon : probabilité (faible, moyenne, élevée), sens et ampleur
estimés, canal par lequel il touche l'instrument.

| Famille | Exemples | Canal de transmission habituel |
|---|---|---|
| Géopolitique | conflit, sanctions, droits de douane | énergie, chaînes d'approvisionnement, aversion au risque |
| Politique | dissolution, gouvernement sans majorité, réforme fiscale | écart de taux souverain, valeurs domestiques, banques |
| Monétaire et crédit | surprise d'inflation, hausse de taux, accident de crédit | valorisations, obligations longues, valeurs endettées |
| Réglementaire | enquête de concurrence, nouvelle taxe sectorielle, interdiction | valeur ou secteur visé |
| Climat et catastrophes | sécheresse, ouragan, crue | assureurs, agriculture, énergie, logistique |
| Sanitaire | épidémie | voyage, consommation, chaînes d'approvisionnement |
| Technologique | rupture, cyberattaque, panne majeure | secteur visé, émetteur touché |

Ampleur : la chercher d'abord dans l'historique (réaction de l'instrument à un événement comparable,
tests de crise du script), ensuite dans les estimations publiées ; à défaut, l'écrire comme hypothèse.

## 3. Les signaux avancés de tension

À relever quand l'analyse porte sur un marché ou un horizon moyen et long : volatilité implicite (VIX,
VSTOXX) contre sa moyenne, écart de crédit à haut rendement, écart OAT-Bund, pente de la courbe 10 ans
moins 2 ans, dollar, pétrole, cuivre. Un signal isolé ne décide rien ; plusieurs signaux qui se
tendent ensemble réduisent l'exposition ou retardent l'entrée. Séries disponibles sur FRED
(`finance.py donnees --source fred`) quand le réseau le permet.

## 4. La parade, décidée avant

Pour chaque événement retenu, une action écrite à l'avance : ne pas entrer la veille, solder la poche
court terme avant la publication, alléger de moitié si le seuil X est franchi, ne rien faire (pour un
cœur long terme, c'est souvent la bonne parade, et elle se dit). Une parade décidée dans la panique
n'en est pas une.

## 5. Après coup

Chaque prévision manquée à cause d'un événement est annotée `evenement_exogene` dans le journal. Si
cette cause pèse un tiers des échecs, le bilan le signale : élargir la veille, revoir les parades.

## Déléguer à l'agent veille-marche

Un agent par instrument, lancés en parallèle dans un seul message. Cahier des charges :

```
Instrument : <nom>, <type>, <symbole ou ISIN>, <place>, secteur <...>, pays <...>
Horizons : du <date du jour> au <date de fin du plus long horizon>
Date et heure du relevé : <...>
À trouver : (1) événements datés sur la période ; (2) risques non datés plausibles ;
(3) faits fondamentaux récents et indicateurs de valorisation ; (4) dernier cours connu.
```

Jamais de montant, de position, de budget ni de nom de personne dans le cahier des charges. Vérifier
au retour qu'une date ou un chiffre clé est bien sur la page citée avant de l'inscrire.
