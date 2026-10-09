# dossier.json : la source unique

Tout ce qui est factuel, chiffré ou tarifé vit dans `dossier.json`. Les trois livrables en sont tirés :
le devis entièrement par le script, le compte rendu et le dossier de solution par balises `{{...}}`.
Un chiffre tapé à la main dans un `.md` est une faute : il ne suivra pas la prochaine correction.

Exemple complet et valide : `exemple/dossier.json`.

## Blocs

```jsonc
{
  "meta": {
    "reference": "2026-10-06-menuiserie-durand",   // fixé par init, sert aux noms de fichiers
    "date_entretien": "2026-10-06",
    "type_entretien": "échange découverte | atelier Déclic IA | diagnostic",
    "duree_min": 75,
    "participants_thinkup": ["Patrick Langlais"],
    "source": {"type": "noota | texte | audio | drive", "ref": "id Noota, chemin ou lien"},
    "mode": "complet | express"          // fixé à l'étape 6, devis chiffré
  },
  "client": {
    "raison_sociale": "", "forme_juridique": "", "siren": "", "adresse": "",
    "secteur": "", "effectif": 42, "chiffre_affaires": "6,5 M€ (déclaré)",
    "outils_en_place": ["Microsoft 365 Business Standard", "ERP Sage 100"],
    "recupere_tva": true,               // false : activité exonérée, le business case compte le devis TTC
    "interlocuteurs": [{"nom": "", "fonction": "", "role": "décideur | prescripteur | utilisateur"}]
  },
  "faits": [{
    "id": "F1",
    "type": "contexte | processus | chiffre | irritant | outil | contrainte | objectif | objection | budget | délai | données",
    "texte": "Reformulation neutre et courte",
    "citation": "Mot pour mot depuis 00-source.md",
    "localisation": "00:14:32 | §3 | p. 2",
    "locuteur": "Dirigeant | Responsable ADV | Patrick (complément du 08/10)",
    "statut": "mesuré | déclaré | estimé | déduit"        // déduit : préciser les F# d'origine dans texte
  }],
  "problemes": [{
    "id": "P1", "titre": "Constat en une ligne, formulé comme un effet",
    "processus": "Devis", "zone": "visible | immergée",
    "description": "", "faits": ["F3", "F7"],
    "impact": "Ce que ça coûte : temps, argent, qualité, risque",
    "cause_racine": "", "certitude": "confirmé | probable | incertain",
    "priorisation": {"impact": 4, "effort": 2, "risque": 1},   // entiers 1–5, barème : extraction.md
    "hors_perimetre": null                                     // ou la raison s'il n'est pas traité
  }],
  "hypotheses": [{
    "id": "H1", "texte": "Coût horaire chargé d'un technico-commercial",
    "valeur": 38,                       // ou {"prudent": 0.5, "central": 0.65}
    "unite": "€/h",
    "origine": "F9 (coût chargé déclaré) / 1 600 h | référence ThinkUP | Patrick",
    "a_valider": true
  }],
  "solutions": [{
    "id": "S1", "titre": "", "problemes": ["P1"],
    "statut": "retenue | option | écartée", "raison_ecart": "",   // raison_ecart obligatoire si écartée
    "type": "IA générative | automatisation | IA + automatisation | non-IA | organisation",
    "resume_client": "Deux phrases sans jargon",
    "alternatives_ecartees": [{"option": "", "raison": ""}],
    "realisation": "Patrick | freelance | mixte | client",
    "outils": [{
      "nom": "", "usage": "", "cout_mensuel": 0, "unite": "utilisateur/mois", "quantite": 3,
      "hebergement": "UE | hors UE (clauses types) | à vérifier",
      "verifie_le": "2026-10-08", "source": "https://…",
      "note": "déjà payé par le client | compté en S2"   // cout_mensuel 0 dans ces deux cas
    }],
    "conformite": {"donnees_personnelles": true, "ia_act": "", "points": [""]},
    "business_case": {                 // ou "gains_qualitatifs": ["…"] si rien n'est chiffrable honnêtement
      "volume": {"duree_h": "H2", "frequence_an": "H3", "personnes": "H4"},   // ou "heures_annuelles": "H5"
      "taux_automatisation": "H6",     // part du temps réellement prise en charge (0–1)
      "taux_supervision": 0.2,         // part du temps libéré reprise en contrôle humain (0–1)
      "cout_horaire": "H1",
      "adoption_an1": 0.7,             // montée en charge la première année (0–1)
      "gains_autres_annuels": 0,       // erreurs évitées, etc. : seulement si sourcé, via une H
      "maintenance_annuelle": 0,
      "cout_interne_client": "H8"      // temps des équipes du client mobilisé par le projet, en €
    }
  }],
  "devis": {
    "numero": "D-20261006-MEN",   // proposé par init ; ou le numéro Qonto
    "date_emission": "2026-10-08", "validite_jours": 30,
    "objet": "", "introduction": "",
    "lots": [{
      "id": "L1", "titre": "", "solutions": ["S1"],          // [] = lot commun (cadrage, pilotage)
      "description": "", "livrables": [""], "duree": "3 semaines",
      "quantite": 1, "unite": "forfait | jour", "prix_unitaire": 2400,
      "option": false,                                          // true ⇔ toutes ses solutions sont « option »
      "catalogue": "atelier | diagnostic",                      // si offre du catalogue : prix contrôlé
      "chiffrage_interne": {"jours_thinkup": 4, "jours_freelance": 0, "cout_jour_freelance": 0}
    }],
    "budget_tiers": [{"libelle": "", "solutions": ["S2"], "min": 3000, "max": 4500, "option": false}],
    "echeancier": [{"libelle": "Acompte à la commande", "pourcentage": 30},
                   {"libelle": "Solde à la livraison des livrables", "pourcentage": 70}],
    "hypotheses_chiffrage": [""], "exclusions": [""],
    "conditions_particulieres": []     // vide par défaut : toute clause ici exige la validation de Patrick
  },
  "questions_ouvertes": [{
    "id": "Q1", "question": "", "impact": "Ce que la réponse change",
    "destinataire": "client | Patrick", "bloquante": false, "reponse": null
  }]
}
```

Les valeurs du business case acceptent un nombre, un couple `{"prudent": a, "central": b}` ou une
référence `"H3"`. Préférer la référence : elle rend la valeur visible au client dans le tableau des
hypothèses. Le script alerte sur toute valeur en dur hors `taux_supervision` et `adoption_an1`.

## Ce que calcule le script

Par solution et par scénario (prudent, central) :

| Grandeur | Calcul |
|---|---|
| heures_annuelles | `heures_annuelles`, ou durée × fréquence × personnes |
| heures_liberees | heures × taux_automatisation × (1 − taux_supervision) |
| gain_annuel | heures_liberees × cout_horaire + gains_autres_annuels |
| gain_an1 | gain_annuel × adoption_an1 |
| mise_en_place | lots du devis liés (partagés à parts égales) + budget tiers (prudent : max, central : milieu) |
| recurrent_annuel | Σ outils (coût mensuel × quantité × 12) + maintenance_annuelle |
| roi_12 | (gain_an1 − récurrent − investissement) / (investissement + récurrent) |
| roi_36 | (gain_an1 + 2 × gain_annuel − 3 × récurrent − investissement) / (investissement + 3 × récurrent) |
| retour_mois | mois pour que le cumul (gain − récurrent) couvre l'investissement ; « non atteint » sinon |

Investissement = mise_en_place + cout_interne_client. Le global additionne les solutions **retenues** et
prend comme mise en place le total ferme du devis + le budget tiers hors options. Même formule que
l'article « Calculer le ROI de l'IA » du site, avec en plus la supervision, la montée en charge et le
temps interne du client.

## Balises utilisables dans les `.md`

| Balise | Rendu |
|---|---|
| `{{client.raison_sociale}}`, `{{client.effectif}}`… | champs simples du bloc client |
| `{{meta.date_entretien}}`, `{{meta.duree_min}}`… | champs simples du bloc meta (dates en toutes lettres) |
| `{{bc.S1.gain_annuel.central}}` | grandeur calculée d'une solution, par scénario |
| `{{bc.global.retour_mois.prudent}}` | idem pour l'ensemble des solutions retenues |
| `{{devis.numero}}`, `{{devis.total}}`, `{{devis.total_options}}`, `{{devis.acompte}}` | devis ; montants suivis de « net » (franchise de TVA) ou « HT » : ne pas l'écrire après la balise |
| `{{devis.tva}}`, `{{devis.total_ttc}}` | TVA et total TTC (égal au net en franchise) |
| `{{devis.date_emission}}`, `{{devis.date_validite}}`, `{{devis.validite_jours}}`, `{{devis.objet}}` | devis |
| `{{devis.budget_tiers_min}}`, `{{devis.budget_tiers_max}}` | budget hors devis, hors options |
| `{{sol.S1.titre}}`, `{{pb.P2.titre}}`, `{{hyp.H3.valeur}}` | libellés |
| `{{nb.problemes}}`, `{{nb.solutions_retenues}}` | compteurs |

Tableaux, seuls sur leur ligne : `{{TABLEAU:problemes}}`, `matrice`, `solutions`, `tracabilite`,
`business_case`, `hypotheses`, `questions` (client, sans réponse), `questions_internes`, `outils`,
`rentabilite` (interne uniquement).

Une balise inconnue, un identifiant P/S/L/H/Q cité mais absent du dossier, une section vide : erreur
à la construction.
