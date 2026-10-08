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
grep -L nav-burger *.html editorial/scheduled-blog/*.html
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

## Outil audit-ia : CR d'audit → compte rendu, solution, devis

Le skill `audit-ia` (`.claude/skills/audit-ia/`, invocable par `/audit-ia`)
transforme le compte rendu d'un audit (Noota, audio, texte, Drive) en trois
livrables : compte rendu pour le prospect, dossier de mise en œuvre interne,
devis. Ses passes de relecture (agent `relecteur-audit`) font partie de
l'outil, demandées par l'utilisateur : la règle méta-agent ci-dessus ne s'y
applique pas.

Le dépôt est PUBLIC. Donc :

- les dossiers clients vivent dans `audits/`, ignoré par git — ne jamais le
  committer, ni le forcer avec `git add -f` ; `audit.py init` refuse de créer
  un dossier qui ne serait pas ignoré ;
- les tarifs internes (TJM, coût des freelances) vivent dans
  `.claude/skills/audit-ia/tarifs.local.json` (ignoré) ou dans la variable
  d'environnement `THINKUP_TARIFS`, jamais dans un fichier versionné.

`.claude/` est exclu du déploiement FTP : rien de l'outil ne part sur
think-up.fr.

Si `cgv.html` change de version ou si un prix change dans
`boutique-config.js`, `audit.py verifier` le signale : mettre à jour
`.claude/skills/audit-ia/assets/emetteur.json` et relire la section
Conditions du devis généré. Contrôle de non-régression du script :

```
python3 .claude/skills/audit-ia/scripts/audit.py construire .claude/skills/audit-ia/exemple --final
```
