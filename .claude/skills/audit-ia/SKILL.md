---
name: audit-ia
description: >
  Transforme le compte rendu d'un audit ou d'un échange de découverte (transcription Noota, fichier
  audio, notes écrites, document Drive) en trois livrables Think'UP : le compte rendu d'audit complet
  à envoyer au prospect, le dossier de mise en œuvre de la solution IA (interne, pour Patrick) et le
  devis. Rédaction en plusieurs passes avec relecture croisée par deux à quatre relecteurs indépendants.
  Déclencher sur : « CR d'audit », « compte rendu d'audit », « transforme cet audit », « proposition
  après l'audit », « devis à partir de l'audit », « /audit-ia ». Ne pas déclencher pour : un post
  LinkedIn, une offre générique sans audit, une question ponctuelle sur l'IA.
---

# Audit IA → compte rendu, solution, devis

`$S` = `.claude/skills/audit-ia` ; `$A` = le dossier de l'audit en cours (`audits/AAAA-MM-JJ-client`).

## Cinq règles qui ne se négocient pas

1. **Rien d'inventé.** Tout constat remonte à un fait F cité mot pour mot depuis la source. Ce qui
   manque devient une hypothèse H signalée « à valider » ou une question Q. Un prix, une fonction
   d'outil, une obligation réglementaire se vérifient sur le web à la date du jour, jamais de mémoire.
2. **Aucun chiffre à la main.** Business case et devis sont calculés par `$S/scripts/audit.py` à
   partir de `$A/dossier.json` ; les textes les appellent par balises `{{...}}`
   (`references/dossier-json.md`).
3. **Le problème commande la solution.** Chaque constat P reçoit une solution S (ou un refus motivé),
   chaque S retenue est chiffrée par un lot L. « Pas d'IA ici » est une réponse valable.
4. **Rien ne part chez le prospect sans Patrick.** L'outil prépare et livre à Patrick ; il n'envoie
   jamais rien au prospect, ne crée rien dans Qonto ou Drive sans accord explicite.
5. **Confidentialité : le dépôt est public.** Tout le travail reste dans `audits/` (ignoré par git).
   Ne jamais committer ce dossier, ni copier un élément du client ailleurs, ni mettre le nom du client,
   de ses salariés ou ses chiffres dans une recherche web.

## Étape 0 — Récupérer la source

Demander, si ce n'est pas clair, le client concerné et la source. Puis :

```bash
python3 $S/scripts/audit.py init audits --client "Raison sociale" --date AAAA-MM-JJ   # affiche $A
```

Écrire la source **verbatim** dans `$A/00-source.md`, sous l'en-tête prévu (provenance, date,
participants, nature) :

| Source | Procédure |
|---|---|
| Noota | `search_records` (titre, contact ou date ; `summary_length: "long"`) ; si plusieurs résultats, faire confirmer le bon par Patrick ; `get_transcript` avec `include_timestamps: true`, `limit: 200`, en suivant le `cursor` jusqu'à la fin. Le résumé Noota peut figurer en fin de fichier, titré « Résumé Noota — non verbatim, ne pas citer ». |
| Fichier audio | `python3 $S/scripts/transcrire.py fichier.m4a >> $A/00-source.md` (transcription locale, rien ne quitte la machine). Signaler dans l'en-tête l'absence de séparation des locuteurs. |
| Texte collé, .md, .txt | copie intégrale. |
| .docx, .pdf | `pandoc fichier.docx -t gfm`, ou lecture du PDF ; copie intégrale. |
| Google Drive | `read_file_content`, copie intégrale. |

Si la source est une transcription d'entretien, rappeler à Patrick en une ligne que l'enregistrement et
son traitement par des outils d'IA doivent avoir été annoncés aux participants.

Renseigner `meta.source`. Le mode de relecture se choisit à l'étape 6, une fois le devis chiffré.

## Étape 1 — Extraction (lire `references/extraction.md`)

Remplir dans `dossier.json` : `meta`, `client`, `faits`, `problemes` (sans solution), `hypotheses`,
`questions_ouvertes`. Contrôle : `python3 $S/scripts/audit.py verifier $A --etape extraction`.

## Étape 2 — Cadrage avec Patrick (un seul échange)

Poser **en un seul message** les questions qui bloquent réellement, et attendre la réponse :
- les questions Q de destinataire `Patrick` (il était dans la pièce : volumes, coûts, contexte non dit) ;
- le mode de réalisation (direct : freelances payés par le client ; ou sous-traitance), s'il n'est pas évident ;
- les tarifs internes si `$S/tarifs.local.json` et `THINKUP_TARIFS` sont absents (TJM cible, contingence) ;
- si l'entité émettrice active est en franchise de TVA et que le devis s'annonce important, le chiffre
  d'affaires déjà facturé dans l'année (`references/devis.md`).

Les choix fermés passent par AskUserQuestion. Chaque réponse devient un fait
(`locuteur: "Patrick (complément du JJ/MM)"`) ou une hypothèse. Ce que Patrick ignore reste une
hypothèse à valider avec le client. Sans question bloquante, passer directement à l'étape 3.

## Étape 3 — Conception de la solution (lire `references/solution.md`)

Remplir `solutions` dans `dossier.json` (options, choix, outils vérifiés sur le web, conformité,
business case, réalisation), corriger `priorisation.effort` des constats, puis rédiger
`$A/02-dossier-solution.md` à partir du gabarit.

## Étape 4 — Devis (lire `references/devis.md`)

Remplir le bloc `devis` : lots, budget hors devis, échéancier, hypothèses de chiffrage, exclusions.

## Étape 5 — Compte rendu (lire `references/compte-rendu.md`)

Rédiger `$A/01-compte-rendu.md` à partir du gabarit, puis construire et corriger jusqu'à zéro erreur :

```bash
python3 $S/scripts/audit.py construire $A
```

Le script calcule (`calculs.json`), contrôle la cohérence et produit `$A/livrables/` (`.md` interpolés
et `.html`). Chaque alerte se lit ; chaque erreur se corrige à la source (`dossier.json` ou `.md`),
jamais dans les livrables générés.

## Étape 6 — Relecture croisée (lire `references/relectures.md`)

Choisir le mode et l'inscrire dans `meta.mode` :
- **complet** (R1 à R4, deux tours au plus) si le total ferme du devis atteint
  `seuil_relecture_complete` de `tarifs.local.json` (5 000 € à défaut), si une solution traite des
  données sensibles (santé, RH), prépare une décision sur des personnes ou relève d'un risque élevé au
  sens de l'IA Act, ou si Patrick le demande ;
- **express** (R1 et R4, un seul tour) sinon.

Les relecteurs tournent sur Sonnet (champ `model` de l'agent) ; la rédaction reste sur le modèle de la
session.

1. **Tour 1** : lancer en parallèle, dans un seul message, les quatre relecteurs (agent
   `relecteur-audit`, rôles R1 à R4). En mode express : R1 et R4.
2. **Correction** : traiter toute objection BLOQUANT et IMPORTANT ; les MINEUR au jugement. Une
   objection qu'on rejette se justifie dans le journal. Reconstruire après correction.
3. **Tour 2** (mode complet) : relancer uniquement les relecteurs qui avaient du BLOQUANT ou de
   l'IMPORTANT, avec leurs objections et le traitement annoncé. Pas de tour 3 : ce qui reste après le
   tour 2 va dans les points à arbitrer par Patrick.
4. Consigner chaque tour dans `$A/journal.md` : `## Tour 1`, puis par relecteur le verdict, le nombre
   d'objections par niveau et le traitement de chacune (corrigée, rejetée et pourquoi, à arbitrer).

## Étape 7 — Contrôle final et livraison

```bash
python3 $S/scripts/audit.py construire $A --final --pdf
```

Zéro erreur exigé (le contrôle final bloque notamment un SIREN client absent et une question bloquante
sans réponse). Dérouler la liste du contrôle final de `references/relectures.md` et la cocher dans
`journal.md`.

Livrer à Patrick : envoyer les fichiers de `$A/livrables/` (PDF, et HTML en secours) avec l'outil
d'envoi de fichiers de la session s'il existe, puis un message court :
- ce qui est proposé, en trois lignes ; total du devis ; gain annuel et retour en scénario prudent ;
- les hypothèses à valider avec le client et les points à arbitrer par Patrick ;
- le rappel : le dossier `-INTERNE` ne part jamais chez le client.

Proposer ensuite, sans rien faire avant son accord explicite : création du devis en brouillon dans
Qonto (procédure dans `references/devis.md`), dépôt des livrables sur Google Drive.

**Session cloud** (claude.ai/code, application mobile) : le conteneur s'efface après la session, et
`audits/` avec lui. À la fin de chaque séance de travail, pas seulement à la livraison :
`python3 $S/scripts/audit.py archiver $A`, puis envoyer l'archive à Patrick en pièce jointe, pour
qu'il la range avec le dossier du client.

## Reprendre un audit existant

Si `$A` n'existe pas mais que Patrick fournit son archive :
`python3 $S/scripts/audit.py restaurer archive.zip audits`. Puis lire `journal.md` pour savoir où on en
est, et repartir de l'étape suivante. Pour une
correction demandée par Patrick après livraison : modifier la source, reconstruire, relancer le seul
relecteur concerné, mettre le journal à jour.
