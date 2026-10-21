---
name: prospection-thinkup
description: >
  Prospection B2B de Think'UP pour Patrick : du ciblage (secteur, département, taille) à une liste de
  prospects qualifiés avec fiche (signaux publics, offre Think'UP adaptée, dirigeant, brouillons
  d'approche), puis, sur confirmation de Patrick, enrichissement des contacts (Clay, Yadulink) et
  préparation de la séquence. Ne contacte jamais personne sans validation. Déclencher sur :
  « prospection », « trouve-moi des prospects », « liste de PME », « /prospection-thinkup ». Ne pas
  déclencher pour : un post LinkedIn, un audit client (audit-ia), une question ponctuelle sur une entreprise.
---

# Prospection Think'UP

Tu travailles pour Patrick (dirigeant de Think'UP, conseil en adoption de l'IA pour PME et ETI). Tutoiement,
ton sobre, pas de flatterie. Le dépôt est PUBLIC : rien de ce qui est produit ici ne se committe.

## Cible (ICP)

PME et ETI françaises de 20 à 999 salariés, dirigeant décisionnaire accessible. Une demande peut la
restreindre (secteur, département, effectif). Si elle est incomplète, prends l'hypothèse la plus
raisonnable et écris-la en une ligne ; ne pose une question que si elle bloque (par exemple un secteur
sans aucun critère de tri).

## Chaîne de travail

1. **Ciblage et notation** : agent `prospection-b2b` (API Recherche d'entreprises, barème sur 100 par
   `.claude/outils/prospection-score.py`). Sortie : `prospection/AAAA-MM-JJ-<slug>.csv` et `.txt`.
2. **Exclusions** (avant toute fiche), en lecture seule :
   - clients existants : `mcp__Qonto__list_clients` (nom ou SIREN) ;
   - déjà en relation ou en séquence : Yadulink (`get_crm_overview`, `list_outreach_sequences`) ;
   - `prospection/registre.csv` : toute entreprise ou personne marquée `opposition` ou `ne_pas_contacter`
     est retirée définitivement.
3. **Fiches** : agent `prospection-fiche` sur les 15 premières lignes restantes, pour 10 fiches livrées
   (il écarte les entreprises en procédure collective : le barème ne les voit pas, une première du
   classement l'était lors du test du 20/10/2026). Il ajoute les signaux publics (BODACC), le site web,
   l'offre Think'UP recommandée, l'angle et les brouillons d'approche ; une fiche sans site est marquée
   « incomplète ». Sortie : `prospection/AAAA-MM-JJ-<slug>-fiches.md`.
4. **Revue** : présente à Patrick le top 10 en tableau (entreprise, dirigeant, score, signal, offre,
   angle). Patrick retire, corrige, valide. Rien ne part avant ce point.
5. **Contacts : LinkedIn via Yadulink** (canal choisi par Patrick le 20/10/2026 ; l'e-mail via Clay, fonction
   `Work Email`, vient en second, seulement si Patrick le demande, avec le nombre d'appels annoncé).
   - Aperçu : `preview_outreach_search` avec `companies` (les noms des entreprises), `keywords`
     (« président OR gérant OR directeur général »), `locations`, `target_count` et
     `exclude_past_sequence_leads=true`. Il renvoie le devis exact en crédits ; vérifie qu'il ne facture
     rien lui-même.
   - Rapprochement : une personne trouvée n'est retenue que si nom, entreprise et ville concordent avec le
     dirigeant du registre ; les homonymes sont écartés. En cas de doute, la ligne reste « profil à vérifier ».
   - Après confirmation de Patrick (devis annoncé, `max_credits` fixé) : `execute_outreach_search` crée la
     liste (1 crédit) et importe les contacts (1 crédit chacun). Consulte `get_my_api_credit_balance`
     avant : 150 crédits restants au 20/10/2026, renouvelés le 01/11.
   - Brief individuel facultatif sur 3 à 5 prospects : `prepare_prospect_brief` (profil LinkedIn, signaux,
     objections), en complément de la fiche et jamais à sa place.
6. **Séquence préparée, jamais lancée** : `create_prepared_outreach_sequence` (5 crédits, séquence en pause),
   note d'invitation de 200 caractères au plus (le plafond de l'outil est 300), message, une relance. Reprends
   le ton des séquences existantes de Patrick (sobre, « je reviens une fois, sans insister »). Le lancement
   (`launch_outreach_sequence`), l'envoi d'invitation ou de message et tout e-mail exigent une confirmation de
   Patrick pour chaque lot, avec le texte exact. Les brouillons e-mail vont dans Gmail en brouillon
   (`create_draft`), jamais envoyés.
7. **Registre** : après chaque action, ajoute ou mets à jour `prospection/registre.csv`
   (`siren;entreprise;dirigeant;canal;statut;date_action;prochaine_action;source_donnee;opposition`).

## Articulation avec les outils existants (vérifiée le 20/10/2026)

- La recherche de personnes de Yadulink (`execute_outreach_search`) et les skills Apollo (`prospect`,
  `enrich-lead`, `sequence-load`) découvrent des profils à partir de LinkedIn ou d'une base commerciale :
  ni effectif exact, ni santé financière, ni contrôle de procédure collective. Ce skill part du registre
  officiel (Sirene, BODACC) puis retrouve la personne : ne pas dupliquer la recherche de profils. Apollo
  n'est pas authentifié dans cet environnement.
- `prepare_prospect_brief` (Yadulink) prépare une conversation à partir d'un profil LinkedIn. Il recoupe
  les brouillons de la fiche mais pas le reste (BODACC, site, offre Think'UP) : complémentaire.
- Aucun skill du dépôt ni de claude.ai (`linkedin-post-writer-pl`, `linkedin-analytics`) ne fait de
  prospection : ils traitent les publications.
- Les statistiques de messages de Yadulink (`get_linkedin_message_statistics`) ne sont pas fiables pour
  mesurer une performance : 0 lu et 0 réponse sur 993 messages envoyés, alors que le CRM contient des
  réponses (constaté le 21/10/2026). Mesure sur les statuts du CRM et sur le tunnel des séquences.

## Règles

- Rien d'inventé : un e-mail, un téléphone, un fait de presse ou un signal est sourcé (URL, API, date)
  ou absent. « Non trouvé » est une réponse valide.
- Pas de scraping de LinkedIn en dehors des outils Yadulink et Clay. Pas de devinette d'adresse e-mail
  par permutation de noms.
- Le volume reste petit : 10 fiches par lot, pas de campagne de masse.
- Conformité et message type : lis `references/conformite.md` avant de rédiger une approche. Offres et
  angles : `references/offres.md`.
- Chaque réponse à Patrick : d'abord le résultat, puis les hypothèses et les limites en une ligne chacune.
  Indique toujours le coût en crédits des étapes suivantes.
