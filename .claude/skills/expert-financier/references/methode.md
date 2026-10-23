# Méthode d'analyse

Ordre de travail : ce que dit le prix (script), ce que vaut l'actif (fondamentaux), ce qui peut le
faire bouger (événements exogènes), ce qu'un modèle a su exploiter dans le passé (backtest), puis la
stratégie. Chaque fait sourcé et daté ; les sources primaires d'abord (document de l'émetteur,
régulateur, banque centrale, agence statistique), la presse ensuite, les forums jamais seuls.

## Par type d'instrument

### Action
- Activité : moteurs de croissance, part de marché, pouvoir de fixation des prix, dépendance à un
  client, un pays, une matière première.
- Comptes (dernier rapport annuel et dernière publication) : croissance du chiffre d'affaires, marge
  opérationnelle et sa tendance, conversion en flux de trésorerie disponible, dette nette sur excédent
  brut d'exploitation, échéancier de la dette, dilution.
- Valorisation, toujours relative (à son histoire, au secteur, au marché) : PER prévisionnel, valeur
  d'entreprise sur EBITDA ou sur EBIT, rendement du flux de trésorerie disponible, rendement du
  dividende et taux de distribution. Raisonnement inverse : quelle croissance le cours actuel
  suppose-t-il, et est-elle crédible ?
- Catalyseurs datés : résultats, journée investisseurs, assemblée, détachement du dividende,
  échéance réglementaire, décision de justice.
- Gouvernance : actionnaire de contrôle, rachats d'actions, rémunération alignée ou non.

### ETF et fonds
- Indice suivi et sa construction (pondération, concentration des dix premières lignes).
- Frais courants, écart de suivi, encours, mode de réplication (physique ou synthétique), politique de
  dividende (capitalisant ou distribuant), devise de cotation et devise des actifs, éligibilité PEA.

### Obligation
- Émetteur et notation (date de la dernière action des agences), rang (senior, subordonnée), clauses
  (remboursement anticipé, perpétuelle).
- Rendement actuariel, écart de rendement avec l'État de même durée, duration et convexité (le script
  les calcule), sensibilité à un point de taux.
- Liquidité : taille de l'émission, coupure minimale (souvent 100 000 € pour une obligation
  d'entreprise : inaccessible avec ces budgets ; passer alors par un ETF obligataire et le dire ; les
  emprunts d'État se négocient par petites coupures).

### Marché ou indice
- Niveau de valorisation agrégé, croissance attendue des bénéfices, concentration sectorielle.
- Cycle : croissance, inflation, taux réels, courbe des taux, crédit, liquidité des banques centrales.
- Positionnement et sentiment : volatilité implicite, flux, écart au plus haut.

### Matières premières, devises, crypto-actifs
- Matières premières : offre et demande, stocks, coûts de production, géopolitique ; le support (ETC)
  et le coût de portage du contrat à terme sous-jacent.
- Devises : écart de taux, balance courante, politique monétaire, risque politique.
- Crypto-actifs : pas de flux de trésorerie ; volatilité extrême, réglementation (MiCA en Europe),
  sécurité de la conservation. Ligne satellite seulement, budget de risque strict.

## Le trader

- Tendance de fond (cours contre moyenne mobile 200 jours), tendance intermédiaire (50 jours),
  momentum 12 mois hors dernier mois, RSI pour les excès de court terme.
- Niveaux : plus haut et plus bas 52 semaines, zones où le cours a réagi plusieurs fois.
- Volatilité : régime actuel contre son historique (percentile) ; un régime haut élargit les stops et
  réduit les tailles.
- Entrées échelonnées quand la thèse attend un catalyseur ; jamais de moyenne à la baisse sur une ligne
  dont l'invalidation est atteinte.
- Ratio gain sur risque d'au moins 1,5 en court terme ; sortie écrite avant l'entrée.

## Trois budgets, trois réalités

- **1 000 €** : deux lignes au plus ; ETF à part peu chère ou plan fractionné ; le court terme y coûte
  souvent plus en frais qu'il ne rapporte. Le script le montre ligne par ligne.
- **5 000 €** : un cœur ETF et un ou deux satellites (action, thématique) deviennent possibles.
- **10 000 €** : diversification réelle, poche court terme à budget de risque strict.

Dans les trois cas, l'enveloppe (PEA de plus de 5 ans contre compte-titres) pèse souvent plus sur le
résultat net que le choix entre deux actions : `references/fiscalite-cadre.md`.

## Les pièges à nommer quand ils se présentent

Biais de confirmation (chercher ce qui contredit la thèse : c'est le pré-mortem), ancrage sur le prix
d'achat, gagnant d'hier extrapolé (la dérive historique des simulations l'illustre), surajustement
d'un modèle, confusion entre une bonne entreprise et un bon placement au prix actuel, excès de
confiance mesuré par le bilan.
