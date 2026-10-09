# Devis

Le devis est **généré** par `audit.py` à partir du bloc `devis` de `dossier.json` : en-tête, tableau
des lots, totaux, échéancier, conditions. On ne rédige à la main que l'objet, l'introduction, la
description et les livrables de chaque lot, les hypothèses de chiffrage et les exclusions.

## Prix

- **Offres du catalogue** : relire `boutique-config.js` à la racine du dépôt (`prixEUR`) au moment du
  devis : Atelier Déclic IA (`atelier`), Diagnostic Index Iceberg (`diagnostic`). Renseigner
  `catalogue` sur le lot : le script refuse un prix différent du prix public.
- **Lots sur mesure** (mise en œuvre, pilotage, formalisation, conformité) : forfait = jours Think'UP ×
  TJM cible, plus la contingence prévue, arrondi. Les paramètres internes viennent de
  `tarifs.local.json` (modèle : `tarifs.local.example.json`) ou de la variable d'environnement
  `THINKUP_TARIFS`. **Jamais dans le dépôt : il est public.** S'ils manquent, les demander à Patrick
  une fois, avec la question de cadrage.
- Renseigner `chiffrage_interne` sur chaque lot : le script calcule le TJM effectif et l'écart à la
  cible (tableau `rentabilite`, dossier interne uniquement).
- Lots au forfait de préférence ; la régie (`unite: "jour"`) pour un pilotage dont le volume est inconnu.

## Mode de réalisation

- **Direct** (par défaut, cohérent avec l'offre Pilotage : « le challenge des devis ») : les freelances
  contractent avec le client. Le devis Think'UP couvre ce que fait Patrick (cadrage, paramétrage no-code,
  pilotage, formation, mesure). Les travaux des freelances vont dans `budget_tiers` en fourchette, non
  facturés par Think'UP mais comptés dans le business case du client.
- **Sous-traitance** : Think'UP facture tout et paie les freelances. À ne retenir que sur décision de
  Patrick : cela augmente le chiffre d'affaires facturé (voir franchise de TVA) et la responsabilité.

## Entité émettrice et TVA

`assets/emetteur.json` liste les entités qui émettent les devis ; `audit.py` retient celle qui est
active à la date d'émission (`a_compter_du`). Active : l'entreprise individuelle, en franchise en base
(art. 293 B du CGI). Préparée, inactive : PL Holding, SASU, nom commercial Think'UP, assujettie.

- **Franchise** : montants « net » et mention d'exonération. Avant un devis important, demander à
  Patrick le chiffre d'affaires déjà encaissé dans l'année et vérifier sur une source officielle
  (impots.gouv.fr, service-public.fr) **le seuil en vigueur à la date du jour**. Si le devis risque de
  le faire franchir, s'arrêter et le signaler.
- **Assujetti** : le script affiche HT, TVA et TTC, l'échéancier en HT et TTC, retire la mention
  d'exonération ; les balises `{{devis.total}}` portent « HT ».
- Le business case compte le devis HT : un client assujetti récupère la TVA. Client qui ne la récupère
  pas (association, activité exonérée : santé, enseignement, assurance, banque) : `client.recupere_tva:
  false`, le business case passe en TTC.
- **Activer la société** : renseigner depuis le Kbis tous les champs de l'entité préparée, sa date
  d'effet, et `cgv_version` une fois les CGV de la société publiées dans `cgv.html` ; le contrôle final
  bloque tant qu'un champ manque. Contenu réglementaire : premier devis de la société relu selon le
  protocole méta-agent de CLAUDE.md. Le sort des devis signés par l'entreprise individuelle avant la
  date d'effet se règle avec l'expert-comptable, pas dans l'outil.

## Découpage

- Un lot par solution retenue, plus si utile un lot commun (`solutions: []`) : cadrage, pilotage, mesure.
- Une solution en option ⇔ des lots en option (le script le contrôle). Les options ne comptent pas
  dans le total ni dans le business case global.
- Proposer une porte d'entrée raisonnable : un pilote ferme et la généralisation en option si le budget
  ou la confiance sont l'enjeu. Le prospect doit pouvoir dire oui à quelque chose.
- Chaque lot : description de ce qui est fait (pas de jargon), livrables concrets et vérifiables,
  durée indicative.

## Échéancier

Par défaut (CGV, art. 5.2) : 30 % à la commande, solde à la livraison. Pour une mission en plusieurs
phases, un échéancier par jalon (par exemple 30 % commande, 40 % fin de pilote, 30 % livraison finale) :
c'est la « mention contraire au devis » que les CGV prévoient. Somme égale à 100 %.

## Hypothèses de chiffrage et exclusions

Elles protègent les deux parties du malentendu. Toujours :
- les hypothèses de volume et de périmètre sur lesquelles repose le prix (nombre d'utilisateurs,
  de modèles de documents, d'outils connectés, de sessions de formation) ;
- ce qui n'est pas compris : abonnements et licences des éditeurs (payés directement par le client),
  travaux des prestataires tiers en mode direct, reprise de données historiques au-delà du périmètre
  décrit, développements non listés, frais de déplacement hors Île-de-France (CGV, art. 4).

## Conditions

Le script reprend les CGV en vigueur (version dans `assets/emetteur.json`, contrôlée contre `cgv.html`)
sans en créer de nouvelles. `conditions_particulieres` reste vide par défaut. Toute clause ajoutée
(pénalité, garantie de résultat, exclusivité, propriété des livrables différente de l'article 10,
plafond de responsabilité différent) est une clause contractuelle : la soumettre à Patrick, et, selon
CLAUDE.md, au protocole méta-agent avec son accord. Ne jamais promettre un résultat chiffré.

## Numérotation et Qonto

- Sans Qonto : `D-AAAAMMJJ-ABC` (proposé par `init`), modifiable par Patrick.
- Avec le connecteur Qonto, **sur accord explicite de Patrick seulement** :
  1. `get_organization` : l'organisation Qonto connectée doit être l'entité active du devis (la société
     aura son propre compte) ; sinon s'arrêter et le signaler ;
  2. `list_clients` pour retrouver le client ; s'il n'existe pas, `create_client` (après accord) ;
  3. `list_quotes` puis `get_quote` sur un devis existant pour reprendre le réglage de TVA déjà utilisé
     par le compte (en franchise : taux 0 et motif « art. 293 B ») ; ne pas l'inventer ;
  4. `create_quote` : une ligne par lot ferme (`title` = titre du lot, `description` = description et
     livrables, `quantity`, `unit`, `unit_price` {value, currency: "EUR"} en HT, `vat_rate` = "0" en
     franchise, sinon le taux de l'entité),
     `issue_date` = date d'émission, `expiry_date` = date de validité, `terms_and_conditions` = la
     section Conditions du devis généré ;
  5. reporter le numéro Qonto dans `devis.numero`, reconstruire, vérifier que les totaux sont identiques ;
  6. **ne jamais appeler `send_quote`** : l'envoi au prospect reste le geste de Patrick.
