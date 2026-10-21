# ThinkUP — Site vitrine

Site statique (HTML/CSS, sans framework ni build) de ThinkUP, cabinet de
conseil en adoption de l'IA pour dirigeants de PME. Contenu en français.
Chaque page est un fichier `.html` à la racine.

Feuilles de style réellement chargées : `style-v2.css` sur les 30 pages,
`style-legacy.css` sur 8 d'entre elles, `conformite.css` sur `ai-act.html`
et `rgpd.html`. style.css et styles.css n'existent plus.

Chaque page porte aussi un bloc `<style>` en ligne, chargé APRÈS les
feuilles liées. À spécificité égale, c'est donc lui qui l'emporte : une
règle mutualisée dans `style-v2.css` doit monter d'un cran (par exemple
`.navlinks li.cta a` plutôt que `.navlinks .cta a`) pour passer devant.

## Cache : incrémenter le `?v=` à CHAQUE modification d'une feuille

`.htaccess` sert les fichiers `.css` et `.js` avec
`Cache-Control: public, max-age=31536000, immutable`. `immutable` signifie
que le navigateur ne revalide même pas au rechargement : tant que l'URL ne
change pas, un visiteur au cache tiède garde l'ancienne feuille pendant un
an.

Le HTML, lui, n'est mis en cache qu'une heure. Modifier une feuille sans
changer son `?v=` livre donc le nouveau balisage avec l'ancien CSS — c'est
exactement ce qui a cassé la navigation en production le 04/09/2026 (liens
empilés avec des puces, boutons sans style).

Donc, dès qu'on touche `style-v2.css`, `style-legacy.css` ou
`conformite.css` : incrémenter le `?v=` dans TOUTES les pages qui la
chargent, dans le même commit.

```
sed -i 's/style-v2\.css?v=[0-9]*/style-v2.css?v=4/' *.html
```

Attention : `curl` et un navigateur sans cache récupèrent toujours la
dernière version. Vérifier que le serveur sert le bon fichier ne prouve
donc rien sur ce que reçoivent les visiteurs. Le seul contrôle qui vaut
est de comparer le `?v=` des pages à celui du dernier changement de
feuille.

## Publication automatique du blog : les gabarits vivent en double

`editorial/publish-blog.php`, lancé chaque jour par `publier-blog.yml`,
copie des pages ENTIÈRES depuis `editorial/scheduled-blog/` vers la
racine quand leur date arrive. Ces fichiers portent leur propre en-tête,
leur propre `?v=` et leurs propres `<script>`.

Conséquence : toute modification du gabarit commun — navigation, feuille
de style, script — doit être appliquée AUSSI aux fichiers de
`editorial/scheduled-blog/`, sinon la prochaine publication réintroduit
l'ancienne version en production, en silence.

C'est arrivé le 05/09/2026 : la publication automatique a écrasé
`ai-act-rgpd-checklist-pme.html` avec un gabarit antérieur au menu
mobile — burger disparu, `nav.js` retiré, `?v=` retombé à 1.

Contrôle avant de clore un chantier qui touche l'en-tête :

```
grep -L nav-burger *.html editorial/scheduled-blog/*.html | grep -v '^google[0-9a-f]*\.html$'
grep -o 'style-v2\.css?v=[0-9]*' *.html editorial/scheduled-blog/*.html | grep -v 'v=3'
```

## Méta-agent : usage restreint

Le skill `meta-agent` (orchestration de plusieurs agents et challenge croisé
par l'agent `challenger`) ne se déclenche PAS automatiquement. Il coûte cher
en tokens et n'apporte rien sur les demandes courantes de ce dépôt : aucune
ligne d'en-tête, aucun score affiché, aucune évaluation à chaque demande.

Il s'active uniquement dans deux cas :

1. L'utilisateur l'invoque avec `/meta-agent`.
2. La demande crée ou modifie un contenu juridique ou réglementaire :
   `cgv.html`, `mentions-legales.html`, `politique-confidentialite.html`,
   `rgpd.html`, `ai-act.html`, ou toute clause contractuelle. Une erreur y a un
   coût réel (conformité, litige) : un passage du challenger est justifié.

Dans le cas 2, présente d'abord l'équipe d'agents envisagée en quelques
lignes et demande confirmation avant de lancer l'orchestration. Pour tout
le reste, réponds directement.

## Aiguillage des modèles : chaque demande au modèle le moins cher qui la réussit

Le tri se fait dans la session principale, sans lancer d'agent pour décider : classer une demande
coûte quelques dizaines de tokens, un agent de tri en coûterait des milliers à son démarrage. Seule
l'exécution se délègue, aux agents `executant-haiku` et `executant-sonnet`.

| Niveau | Signes | Modèle |
|---|---|---|
| 1 Mécanique | résultat vérifiable sans jugement : rechercher, compter, extraire, remplacer en série, reformater, contrôles grep, `?v=` | Haiku |
| 2 Standard | rédaction ou code sur consigne claire : article de blog, section ou modification de pages, synthèse, recherche web | Sonnet |
| 3 Complexe | jugement, arbitrage, conformité : contenus juridiques, audit-ia, devis, stratégie, offre, bug sans cause évidente | Opus |

Fable est réservé à une demande explicite ou à une tâche très difficile qui a échoué sur Opus.

1. Classer la demande. En cas de doute entre deux niveaux, prendre le plus haut : un échec suivi
   d'une reprise coûte plus qu'un niveau au-dessus.
2. Session plus puissante que le niveau : tâche courte (repère : cinq appels d'outils au plus), la
   traiter directement, déléguer coûterait plus que l'économie ; tâche plus longue et autonome, la
   déléguer à l'exécutant du niveau. Si la session ne sert visiblement qu'à des demandes de niveau 1
   ou 2, le dire une fois par session, en une ligne : « Sonnet suffit ici : `/model sonnet` ».
3. Session au bon niveau : traiter directement.
4. Session moins puissante que le niveau : niveau 2, déléguer à `executant-sonnet` ; niveau 3,
   l'annoncer en une ligne et attendre que Patrick bascule (`/model opus`) ou confirme.
5. La consigne de délégation est autonome : fichiers concernés, résultat attendu, contrôle à faire.
   Au retour, vérifier le résultat (diff, grep) avant de l'annoncer ; sur `HORS PÉRIMÈTRE`, reprendre
   au niveau supérieur.

Aucune ligne d'en-tête ni annonce du niveau à chaque réponse. Les skills qui fixent leurs propres
agents (audit-ia, agence-voyage, meta-agent) gardent leurs modèles.

## Veille outils : tâche planifiée du jeudi

Le skill `veille-outils` (`.claude/skills/veille-outils/`, invocable par `/veille-outils`) repère
chaque semaine les nouveaux outils utiles à Think'UP, aux clients PME et à Patrick, ainsi que 5 skills
ou plugins Claude au plus (il remplace l'ancienne veille skills du samedi). Il les note, puis publie
un Google Doc dans le dossier Drive « Veille outils » et envoie un mail récapitulatif. Une tâche
planifiée (Routine claude.ai « Veille outils hebdo ») le lance le jeudi à 6 h 57, heure de Paris.
L'actualité des grands assistants (modèles, nouvelles fonctions de ChatGPT, Claude, Copilot, Gemini)
n'y figure pas : elle relève de la tâche « Veille IA hebdo » du lundi.

Le profil personnel de Patrick et les destinations (dossier Drive, adresse du mail) vivent dans la
consigne privée de cette tâche, jamais dans le dépôt : le dépôt est public. La veille ne modifie pas
le dépôt. Contrôle de non-régression :

```
python3 .claude/skills/veille-outils/scripts/rapport.py construire .claude/skills/veille-outils/exemple/selection.json --sortie /tmp/veille-test
```

## Outil audit-ia : CR d'audit → compte rendu, solution, devis

Le skill `audit-ia` (`.claude/skills/audit-ia/`, invocable par `/audit-ia`)
transforme le compte rendu d'un audit (Noota, audio, texte, Drive) en trois
livrables : compte rendu pour le prospect, dossier de mise en œuvre interne,
devis. Ses passes de relecture (agent `relecteur-audit`) font partie de
l'outil, demandées par l'utilisateur : la règle méta-agent ci-dessus ne s'y
applique pas.

Le dépôt est PUBLIC. Donc :

- les dossiers clients vivent dans `audits/`, ignoré par git — ne jamais le
  committer, ni le forcer avec `git add -f` ; `audits/` est lui-même un clone du dépôt
  privé `thinkup-conseil/thinkup-audits` : on y committe avec `git -C audits`, jamais depuis
  la racine ; `audit.py init` refuse de créer
  un dossier qui ne serait pas ignoré ;
- les tarifs internes (TJM, coût des freelances) vivent dans
  `.claude/skills/audit-ia/tarifs.local.json` (ignoré) ou dans la variable
  d'environnement `THINKUP_TARIFS`, jamais dans un fichier versionné.

`.claude/` est exclu du déploiement FTP : rien de l'outil ne part sur
think-up.fr.

Si `cgv.html` change de version ou si un prix change dans
`boutique-config.js`, `audit.py verifier` le signale : mettre à jour
`.claude/skills/audit-ia/assets/emetteur.json` et relire la section
Conditions du devis généré. Au passage en société (PL Holding, SASU), compléter et dater
l'entité préparée dans ce même fichier : procédure dans `references/devis.md`. Contrôle de non-régression du script :

```
python3 .claude/skills/audit-ia/scripts/audit.py construire .claude/skills/audit-ia/exemple --final
```

## Vérification officielle des entreprises : script, agent et contrôle d'audit

`.claude/skills/audit-ia/scripts/entreprise.py` interroge uniquement les registres publics (API Recherche
d'entreprises : Sirene et RNE, et BODACC) à partir d'un SIREN : identité, forme juridique, siège, effectif
(tranche), derniers comptes publiés, dirigeants, procédure collective. Il sert à deux endroits :

- dans `audit-ia` : `audit.py entreprise <dossier> --siren N --appliquer` écrit `verification-entreprise.json`
  dans le dossier du client, renseigne les champs client vides et signale les écarts avec ce que le client a
  déclaré ; le contrôle final (`--final`) bloque l'envoi du devis si une procédure collective est probable et
  non arbitrée par Patrick (`client.verification_arbitree`), et alerte si la vérification manque ou a plus de
  30 jours ;
- hors audit : l'agent `verification-entreprise` (`.claude/agents/`) lance le même script avant un devis, un
  rendez-vous ou une signature. Il ne prospecte pas, ne note pas, ne contacte personne et n'écrit rien dans le dépôt.

Option `--pappers` (script et `audit.py entreprise`) : ajoute l'API Pappers, service commercial tiers, avec la clé
dans la variable d'environnement `PAPPERS_API_KEY` (jamais dans le dépôt) et 1 crédit par appel, avec l'accord de
Patrick pour chaque client ; le site pappers.fr bloque les accès automatisés. Format de réponse non vérifié sans clé
(le 21/10/2026, seule l'existence de l'endpoint l'est) : contrôler le premier appel réel.

Un SIREN est exigé : la recherche par nom (`--chercher`) envoie le nom à l'API officielle et n'est lancée qu'avec
l'accord de Patrick, les dossiers d'audit étant confidentiels. L'ancien outil de prospection (ciblage, notation,
fiches, séquences LinkedIn) a été retiré le 21/10/2026 : il est dans l'historique git. Le skill `datagouv-apis`
(référence officielle Etalab, copie de https://github.com/etalab-ia/skills) reste disponible pour explorer le
catalogue data.gouv.fr. Contrôle de non-régression (une alerte « verification-entreprise.json absent » est normale
sur l'exemple) :

```
python3 .claude/skills/audit-ia/scripts/audit.py construire .claude/skills/audit-ia/exemple --final
python3 .claude/skills/audit-ia/scripts/entreprise.py 438025306
```

## Outil agence-voyage : brief → proposition → carnet de voyage

Le skill `agence-voyage` (`.claude/skills/agence-voyage/`, invocable par `/agence-voyage`) est
l'agence de voyage personnelle de Patrick, à son seul service (déplacements professionnels et voyages
personnels, seul ou accompagné) : entretien de découverte, conseil (sécurité, formalités, santé),
recherche et comparaison en deux ou trois formules, suivi des réservations, carnet de voyage avec
calendrier `.ics`, incidents et réclamations. Il peut lancer en parallèle l'agent `recherche-voyage`
(un par poste) : cela fait partie de l'outil, la règle méta-agent ne s'y applique pas. Il ne réserve
ni ne paie rien. Prix réels des vols et des hôtels par les connecteurs Kiwi.com et Trivago quand ils
sont actifs ; les autres sources (change BCE, jours fériés, vacances scolaires, régularité TGV,
Légifrance) et les connecteurs recommandés sont dans `references/sources.md`.

Le dépôt est PUBLIC : les dossiers de voyage et les profils des voyageurs vivent dans `voyages/`,
ignoré par git — ne jamais le committer, ni le forcer avec `git add -f` ; `voyage.py init` refuse de
créer un dossier qui ne serait pas ignoré. Aucun numéro de document ou de carte dans les dossiers :
le script les refuse. La conservation d'une session à l'autre passe par le dossier Drive « Voyages »
ou par l'archive (`voyage.py archiver`). Contrôle de non-régression du script :

```
python3 .claude/skills/agence-voyage/scripts/voyage.py construire .claude/skills/agence-voyage/exemple --etape proposition --aujourdhui 2026-10-17
python3 .claude/skills/agence-voyage/scripts/voyage.py construire .claude/skills/agence-voyage/exemple --aujourdhui 2026-10-17
```

Version pour l'application Claude (claude.ai et application de bureau) : même script et mêmes
références, seul `app/SKILL.md` diffère (pas d'agent, pas de dépôt, mémoire par Drive « Voyages » ou
fichiers joints). Après toute modification de `references/`, `scripts/voyage.py`, `exemple/` ou
`app/SKILL.md`, reconstruire le zip et le téléverser à nouveau dans Personnaliser > Skills, sinon
l'application garde l'ancienne version :

```
python3 .claude/skills/agence-voyage/scripts/paquet_app.py --sortie /tmp/agence-voyage-app
```

## Outil improve-system : sessions de la semaine → propositions de skills

Le skill `improve-system` (`.claude/skills/improve-system/`, `/improve-system [jours]`, lancement manuel
uniquement) lit les transcripts `~/.claude/projects/**/*.jsonl` des 7 derniers jours, repère échecs,
corrections répétées et tâches récurrentes, et propose des skills (ou une règle, un hook) appuyés chacun sur
deux exemples datés de deux sessions. Rapport dans `~/rapports-improve-system/`, jamais dans un dépôt : le
script refuse d'y écrire, les extraits pouvant contenir des données clients. Rien n'est installé sans l'accord
de Patrick.

Il ne sert que sur le poste local : en session cloud, le conteneur ne contient que la session en cours et le
skill s'arrête. Pour l'avoir dans tous les projets du poste : `cp -r .claude/skills/improve-system ~/.claude/skills/`.
Contrôle de non-régression :

```
python3 .claude/skills/improve-system/scripts/analyser.py extraire --racine .claude/skills/improve-system/exemple/projects --aujourdhui 2026-10-21 --sortie /tmp/improve-test
python3 .claude/skills/improve-system/scripts/analyser.py rapport .claude/skills/improve-system/exemple/propositions.json --signaux /tmp/improve-test/signaux.json --sortie /tmp/improve-test/rapports
```
