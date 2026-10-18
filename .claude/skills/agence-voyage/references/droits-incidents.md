# Incidents, droits des voyageurs, réclamations

Ordre de traitement : la solution d'abord (comment arriver, où dormir), les droits ensuite (ce qui
est dû, comment le réclamer). Avant de citer un seuil ou un montant, vérifier le texte en vigueur :
la réglementation des droits des passagers aériens est en cours de réforme.

## Sur place, tout de suite

1. **Faits** : transporteur, numéro, retard annoncé ou annulation, motif donné, ce que propose le
   comptoir.
2. **Solutions** : vol ou train suivant, autre compagnie, autre aéroport ou gare, nuit sur place ;
   chercher en direct et indiquer ce qu'il faut demander au comptoir (réacheminement, prise en
   charge).
3. **Assistance due par le transporteur** pendant l'attente, selon le régime applicable : repas,
   rafraîchissements, hôtel et transfert si une nuit est nécessaire. Garder les reçus de ce que l'on
   paie soi-même faute d'assistance.
4. **Preuves** : carte d'embarquement, billet, attestation écrite du retard ou de l'annulation et de
   son motif, photos, reçus, échanges écrits.
5. **Consigner** l'incident dans `incidents` (date, prestation, nature, faits, démarche, échéance).

## Avion

- **Règlement (CE) n° 261/2004** : s'applique aux vols au départ d'un aéroport de l'Union, et aux vols
  à destination de l'Union opérés par une compagnie européenne. Il prévoit l'assistance, le
  réacheminement ou le remboursement, et une indemnisation forfaitaire de 250, 400 ou 600 € selon la
  distance en cas d'annulation tardive, de refus d'embarquement ou de retard d'au moins trois heures à
  l'arrivée, sauf circonstances extraordinaires.
- **Réforme** (état au 17/10/2026, probable) : accord entre le Parlement européen et le Conseil conclu
  en juin 2026, vote du Parlement en juillet 2026 d'après la presse spécialisée ; les sources ne
  concordent pas sur les seuils retenus et l'entrée en application annoncée est postérieure.
  Tant que le nouveau texte n'est pas applicable, le règlement de 2004 s'applique. Vérifier sur
  EUR-Lex ou sur le portail L'Europe est à vous (europa.eu) avant de citer des chiffres.
- **Bagages** (convention de Montréal) : déclaration au comptoir bagages avant de quitter l'aéroport ;
  réclamation écrite à la compagnie dans les 7 jours pour un bagage endommagé, dans les 21 jours à
  compter de sa remise pour un bagage retardé. L'indemnisation est plafonnée par la convention.
- **Recours en France** : réclamation écrite à la compagnie, puis, sans réponse satisfaisante, la
  médiation (Médiation Tourisme et Voyage pour les compagnies adhérentes) et le signalement à la
  Direction générale de l'aviation civile ; en dernier lieu, le tribunal. Les sociétés de
  réclamation prennent une commission sur l'indemnité : le dire avant que Patrick y recoure.

## Train

- **Règlement (UE) 2021/782** : réacheminement ou remboursement, assistance, et indemnisation de 25 %
  du prix du billet pour un retard de 60 à 119 minutes, 50 % à partir de 120 minutes, sauf exceptions
  prévues par le texte. Les transporteurs ont souvent des garanties commerciales plus favorables :
  les lire.

## Forfait et hébergement

- **Forfait** (Code du tourisme, art. L211-1 et suivants) : l'organisateur ou le détaillant répond de
  la bonne exécution de toutes les prestations du forfait ; s'adresser à lui en premier.
- **Hébergement** réservé seul : réclamation à l'établissement, puis à la plateforme de réservation ;
  médiation de la consommation ensuite.

## Urgences

- Union européenne : 112. Hors Union : numéros d'urgence de la fiche pays du ministère, et consulat.
- Papiers perdus ou volés : déclaration à la police locale, puis consulat pour un document de voyage.
- Carte bancaire : opposition immédiate auprès de la banque.

## Réclamation écrite

Préparer le texte (brouillon de mail, avec l'accord de Patrick) : identité du passager, numéro de vol
ou de billet, date, faits datés et chiffrés, texte invoqué, demande précise (montant, remboursement de
frais avec reçus), délai de réponse attendu, pièces jointes. Enregistrer dans `incidents` la date
d'envoi et l'échéance de relance ; `voyage.py echeances` la fera remonter.
