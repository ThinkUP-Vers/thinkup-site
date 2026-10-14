---
name: veille-outils
description: >
  Veille hebdomadaire des nouveaux outils (open-source et payants) utiles à Think'UP, à ses clients PME
  et à Patrick à titre personnel : collecte sur GitHub Trending, Hacker News, Product Hunt et les
  annonces des éditeurs, tri, notation, classement, puis édition d'un Google Doc dans le dossier Drive
  « Veille outils » et d'un mail récapitulatif. Lancé chaque jeudi par une tâche planifiée qui fournit
  le profil personnel et les destinations. Déclencher sur : « veille outils », « /veille-outils ».
  Ne pas déclencher pour : une question ponctuelle sur un outil, un comparatif demandé à la main.
---

# Veille outils IA

`$S` = `.claude/skills/veille-outils` ; `$W` = un dossier de travail `veille-AAAA-MM-JJ` dans le
scratchpad de la session (à défaut `/tmp`), jamais dans le dépôt.

## Règles qui ne se négocient pas

1. **Le dépôt est public.** Rien n'est écrit, commité ni poussé dans le dépôt : pas de fichier, pas de
   branche, pas de PR. Le profil personnel de Patrick vient de la consigne de la tâche planifiée et ne
   va que dans `$W/selection.json` et dans le document Drive.
2. **Rien d'inventé.** Chaque prix, licence, éditeur, hébergement ou signal de maturité vient d'une page
   consultée pendant l'exécution. Ce que la source ne dit pas s'écrit « non communiqué » ou « inconnu ».
   Aucun score ni verdict à la main : `rapport.py` les calcule.
3. **Ne pas remplir.** Au plus 15 outils. Si la semaine n'apporte rien de pertinent, l'édition le dit :
   zéro outil est une réponse valable, un outil faible pour faire nombre ne l'est pas.
4. **Ne rien installer ni exécuter.** Aucun outil trouvé n'est cloné, installé ni lancé, pas même
   « pour vérifier ». Tout se juge sur les pages publiques.
5. **GitHub en lecture publique seulement.** L'API `api.github.com` et `github.com` sont bloqués en
   ligne de commande dans les sessions cloud, et les outils `mcp__github__*` sont limités aux dépôts de
   la session : ne pas les utiliser ici. Les pages publiques se lisent avec WebFetch.

## Entrées fournies par la consigne

- `profil_perso` : les thèmes personnels de Patrick (liste de libellés courts, avec leur description).
- l'identifiant du dossier Drive « Veille outils » (sinon : `search_files` avec
  `title = 'Veille outils' and mimeType = 'application/vnd.google-apps.folder'`) ;
- l'adresse du destinataire du mail.

En exécution manuelle sans ces éléments, les demander à Patrick avant l'étape 1.

## Étape 1 — Mémoire

Lister les éditions précédentes : `search_files` avec
`parentId = '<dossier>' and title contains 'Veille outils IA'`, garder les 4 plus récentes
(`createdTime`), les lire avec `read_file_content` et relever les identifiants de leur section
**Index**. Un outil déjà indexé n'est repris que s'il sort une version majeure pendant la fenêtre ;
il porte alors le champ `nouvelle_version` (« signalé le JJ/MM/AAAA ; nouveauté : … »).

## Étape 2 — Collecte

```bash
python3 $S/scripts/collecte.py --sortie $W
```

Le script interroge Hacker News et le flux Product Hunt, écrit `$W/candidats.json`, puis affiche la
liste des candidats, les pages à lire avec WebFetch et les recherches à lancer. Ensuite :

- **GitHub Trending** : WebFetch sur chaque adresse affichée, en demandant pour chaque dépôt
  propriétaire/nom, description, langage, étoiles totales et étoiles de la semaine.
- **Product Hunt, classement de la semaine** : WebFetch sur l'adresse affichée (nom, accroche, score ;
  la page n'en livre que les 10 premiers).
- **Pages d'actualités des éditeurs** (Anthropic, Mistral, Google Workspace, Microsoft 365 Copilot) :
  WebFetch en demandant les annonces avec leur date ; garder celles de la fenêtre.
- **Recherches web** : WebSearch (`mode: "standard"`) sur chaque recherche affichée, notamment pour
  OpenAI, dont le site refuse la lecture automatique. Les résultats contiennent beaucoup de pages de
  faible qualité : ne retenir une annonce que si une source primaire ou un média identifié la confirme.

**Toutes ces sources sont lues à chaque exécution**, y compris pour une relance ou un test, et même
si une édition récente les a déjà couvertes : la mémoire de l'étape 1 écarte des outils, jamais des
sources. `ok: false` est réservé à une erreur technique (refus, page vide, délai dépassé), dont le
message va dans `note` ; une source non lue par choix n'est pas une source en échec. Une source en
échec ne bloque pas l'édition.

## Étape 3 — Tri

Écarter sans autre examen : ce qui figure dans les exclusions de `$S/config.json`, ce qui n'est pas un
outil (débat, levée de fonds, faillite, opinion), ce qui est déjà indexé (étape 1), ce qui n'est pas
nouveau dans la fenêtre (lancement, version majeure, première apparition dans les tendances).

Rattacher chaque candidat restant à un public et à un thème : `thinkup` et `clients` prennent leurs
thèmes dans `config.json`, `perso` dans `profil_perso`. Sans thème qui colle, le candidat sort.
Garder au plus 30 candidats pour l'étape 4.

## Étape 4 — Vérification

Pour chaque candidat gardé, WebFetch sur sa page (dépôt GitHub, site de l'éditeur, page de prix,
politique de confidentialité) pour établir : éditeur et pays, modèle (`open-source`, `freemium`,
`payant`), prix, licence, hébergement des données (`local`, `UE`, `hors UE`, `inconnu`), signaux de
maturité (âge, activité récente, contributeurs, documentation, clients). Pour un dépôt GitHub, une
montée brutale d'étoiles sans discussion ni contributeurs est un signal d'étoiles achetées.

## Étape 5 — Notation

Trois notes entières de 0 à 3, jugées pour le public retenu :

| Note | 3 | 2 | 1 | 0 |
|---|---|---|---|---|
| `pertinence` | répond à un thème du public, utilisable dans le mois | utile, besoin secondaire | lien indirect | hors sujet |
| `accessibilite` | utilisable sans compétence technique | installation ou paramétrage guidés | développeur nécessaire ponctuellement | réservé aux développeurs |
| `maturite` | éditeur identifié, produit stable, activité régulière | jeune mais sérieux (équipe, documentation) | projet récent d'un individu, peu de recul | abandonné ou opaque |

Pour le public `clients`, l'accessibilité se juge du point de vue de Think'UP qui déploie, au besoin
avec un freelance : un déploiement de quelques jours vaut 2.

`risque` : **élevé** si l'éditeur ou le code est opaque, si l'outil demande un accès étendu (boîte
mail, comptes, mots de passe, banque) sans garanties, si les étoiles paraissent achetées, ou si des
données de clients partiraient hors UE sans contrat de sous-traitance ; **moyen** pour un projet jeune
ou un hébergement hors UE avec garanties standard ; **faible** sinon. `risque_motif` dit pourquoi.

Score = 2 × pertinence + accessibilité + maturité, sur 12. `rapport.py` en tire le verdict : « À
tester » à partir de 9 sans risque élevé, « À surveiller » à partir de 6, « Pour info » à 5, non
retenu en dessous.

## Étape 6 — Rédaction

Écrire `$W/selection.json` au format de `$S/exemple/selection.json` : `edition` (date du jour),
`periode` (celle affichée par `collecte.py`), `profil_perso` (libellés), `sources`,
`candidats_examines` (tous les candidats vus, avant tri), `en_bref` (deux ou trois phrases sur la
semaine), `outils`, et `ecartes` (au plus 5 candidats très visibles mais écartés, avec le motif).

Style : français, sobre, factuel. `fonction` dit ce que fait l'outil, sans reprendre le discours
commercial ; `utilite` dit pour qui, sur quelle tâche, avec quel gain ; `prochaine_etape` est une
action concrète (« essai gratuit sur… », « demander le tarif », « ne pas installer, revoir dans un
mois »). Identifiant : `github:proprietaire/depot` pour un dépôt, `web:domaine.tld` sinon.

```bash
python3 $S/scripts/rapport.py construire $W/selection.json
```

Corriger `selection.json` jusqu'à ce que le script passe sans erreur. Il affiche le titre du document
et écrit `$W/rapport.html`.

## Étape 7 — Publication

1. **Drive** : `create_file` avec `title` = le titre affiché, `parentId` = le dossier,
   `contentMimeType` = `text/html`, `textContent` = le contenu exact de `$W/rapport.html` (le lire avec
   `cat` et le recopier sans le modifier). Ne pas passer `disableConversionToGoogleType` : Drive
   convertit en Google Doc, téléchargeable en .docx. Vérifier que la réponse porte
   `mimeType: application/vnd.google-apps.document` ; le `fileSize` de 1 affiché pour un Google Doc
   est normal. Si un document du même titre existe déjà
   (relance dans la même semaine), ajouter « (2) » au titre.
2. **Mail** :

   ```bash
   python3 $S/scripts/rapport.py mail $W/selection.json --lien https://docs.google.com/document/d/<id>/edit
   ```

   puis `send_message` au destinataire de la consigne, avec `subject` = `$W/sujet.txt`,
   `htmlBody` = `$W/mail.html`, `body` = `$W/mail.txt`. Aucun autre destinataire.
3. Si Drive échoue, envoyer quand même le mail, avec le contenu de `rapport.html` en `htmlBody` et
   l'échec en première ligne. Si le mail échoue, le document reste sur Drive.

## Étape 8 — Compte rendu de la session

Terminer par cinq lignes au plus : candidats examinés, outils retenus par verdict, sources en échec,
lien du document, envoi du mail confirmé ou non.

## Contrôle de non-régression

```bash
python3 .claude/skills/veille-outils/scripts/rapport.py construire .claude/skills/veille-outils/exemple/selection.json --sortie /tmp/veille-test
```

Attendu : 3 outils retenus (2 « À tester », 1 « À surveiller » plafonné par son risque élevé) et un
avertissement pour l'outil sous le score minimum.
