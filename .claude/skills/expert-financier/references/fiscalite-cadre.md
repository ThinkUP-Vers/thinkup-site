# Enveloppes, fiscalité, frais et cadre

Barèmes vérifiés le 23/10/2026 sur des sources secondaires concordantes ; texte officiel à relire
avant toute décision fiscale. Les taux appliqués par le script sont dans `config.json`, section
`fiscalite`, avec leur date : les revérifier à chaque loi de finances et loi de financement de la
sécurité sociale (décembre), et après toute annonce.

## Enveloppes

| Enveloppe | Imposition des gains (au 23/10/2026) | À savoir |
|---|---|---|
| Compte-titres ordinaire | 31,4 % (12,8 % d'impôt + 18,6 % de prélèvements sociaux) | tout instrument ; moins-values imputables sur les plus-values pendant 10 ans |
| PEA | 31,4 % avant 5 ans ; 18,6 % de prélèvements sociaux seuls après 5 ans | actions européennes et ETF éligibles ; plafond de versements 150 000 € ; le délai court depuis l'ouverture du plan ; un retrait avant 5 ans clôture le plan |
| Assurance-vie | 30 % avant 8 ans ; après 8 ans, 17,2 % de prélèvements sociaux sous l'abattement annuel (4 600 € par personne), 7,5 % d'impôt en plus au-delà | supports limités au contrat ; frais de gestion annuels à compter |

Hausse de la CSG (LFSS 2026, loi n° 2025-1403 du 30/12/2025) : prélèvements sociaux de 17,2 % à
18,6 % sur les revenus du capital, assurance-vie exclue d'après les sources lues. Statut : probable,
texte officiel non lu.

Conséquence pratique : avec un PEA ouvert depuis plus de 5 ans, un même gain rapporte 12,8 points de
plus qu'en compte-titres. Le script en tient compte quand `pea_ouvert_le` est renseigné dans
`finance/config.local.json`.

## Frais

- Courtage : à recopier depuis la grille tarifaire du courtier de Patrick dans
  `finance/config.local.json` (`frais_fixes`, `frais_pct`, `frais_min`). La grille de `config.json`
  est volontairement prudente.
- Écart de cotation (`spread`) : 0,1 % par défaut ; plus large sur les petites valeurs, les ETF peu
  échangés et hors des heures de cotation.
- Taxe sur les transactions financières : 0,4 % à l'achat d'actions de sociétés françaises de plus
  d'un milliard d'euros de capitalisation (taux en vigueur depuis le 01/04/2025 ; liste 2026 publiée
  au BOFiP le 17/12/2025). Marquer ces lignes `"ttf": true`. Pas de taxe sur les ETF.
- Frais courants des ETF et fonds : déjà déduits de leur cours, donc des séries historiques.
- Change : frais de conversion pour un titre coté hors euro.

## Cadre réglementaire

- Usage personnel : Patrick décide pour son propre compte ; aucun agrément requis.
- Conseil à un tiers : recommander un placement adapté à la situation d'un client est du conseil en
  investissement, réservé aux personnes habilitées (en France, conseiller en investissements
  financiers immatriculé à l'ORIAS et membre d'une association agréée par l'AMF, ou prestataire
  agréé). Les notes de l'outil ne doivent pas être remises à un client de Think'UP comme conseil.
- Publication : diffuser des recommandations d'investissement (LinkedIn, newsletter) relève des règles
  sur les recommandations d'investissement (règlement européen sur les abus de marché) et, pour la
  promotion de produits financiers, de la loi du 9 juin 2023 sur l'influence commerciale. À vérifier
  avec un juriste avant toute diffusion.
- Signaler ces limites dès qu'une demande glisse vers un usage pour autrui.
