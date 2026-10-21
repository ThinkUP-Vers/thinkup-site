---
name: improve-system
description: >
  Analyse les sessions Claude Code des derniers jours (7 par défaut, transcripts .jsonl de
  ~/.claude/projects) pour repérer les échecs, les corrections répétées et les tâches récurrentes,
  puis propose des skills à créer (ou, quand c'est plus juste, une règle, un hook ou l'amélioration
  d'un skill existant), chacun appuyé sur deux exemples datés tirés de deux sessions. Rapport DOCX dans
  ~/rapports-improve-system/. N'installe rien sans accord explicite. Lancement manuel uniquement :
  « /improve-system [jours] ».
argument-hint: "[jours, 7 par défaut]"
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/analyser.py *)
---

# Améliorer le système

`$S` = `${CLAUDE_SKILL_DIR}` ; `$R` = `~/rapports-improve-system` ; `$W` = `$R/travail/AAAA-MM-JJ` (date du
jour). Argument reçu : « $ARGUMENTS ». Si c'est un nombre entre 1 et 60, c'est `$N` ; sinon `$N` = 7.
Sous Windows, remplacer `python3` par `py` si besoin.

## Règles qui ne se négocient pas

1. **Rien n'est installé sans accord explicite.** Ni skill, ni plugin, ni MCP, ni hook, ni réglage, ni ligne
   de CLAUDE.md ou de préférences. L'accord désigne les propositions (« installe 1 et 3 », « toutes ») ; un
   « ok », un « merci » ou un « intéressant » n'en est pas un. Lancé sans interlocuteur (tâche planifiée), le
   skill s'arrête au rapport.
2. **Rien d'inventé.** Chaque exemple est un identifiant de `signaux.json` ; dates et citations sont reprises
   par le script, jamais tapées à la main. Pas de gain chiffré en heures ou en euros : le gain s'exprime en
   fréquence observée et en ce qui est évité.
3. **Les transcripts sont en lecture seule.** Ne jamais modifier, déplacer ni supprimer un fichier de
   `~/.claude/projects`.
4. **Confidentialité.** Les extraits peuvent contenir des noms de clients, des données d'audit, des secrets.
   Tout reste dans `$R`, hors de tout dépôt git (le script refuse d'y écrire) ; rien n'est envoyé (mail,
   Drive, artifact, PR) sans demande. Aucun nom de client ni secret dans le nom, la description ou le contenu
   d'un skill proposé.
5. **Économie.** Lire `$W/resume.txt` en entier, pas les `.jsonl`. N'ouvrir un transcript que pour vérifier
   un cas précis, par `grep` sur l'identifiant (les 8 caractères après le tiret) ou sur un passage.

## 1. Extraire

```
python3 $S/scripts/analyser.py extraire --jours $N --sortie $W
```

Puis lire `$W/resume.txt` en entier.

S'arrêter sans rapport, en disant pourquoi, dans deux cas :

- avertissement « Session cloud » : ce conteneur ne contient que la session en cours. Dire à Patrick de
  lancer `/improve-system` depuis Claude Code sur son poste, où vivent les transcripts de ses sessions
  locales ; les sessions cloud de claude.ai ne laissent pas de `.jsonl` sur le poste ;
- moins de deux sessions sur la période : aucune récurrence n'est démontrable. Proposer d'élargir
  (`/improve-system 14`).

## 2. Analyser

Trois lectures, chacune sur `resume.txt`.

**Échecs.** Groupes d'erreurs d'outil présents dans au moins deux sessions ; refus (Claude a tenté une action
que Patrick ne voulait pas, le commentaire dit souvent pourquoi) ; interruptions (Claude partait dans une
mauvaise direction : relire la demande indiquée par « après ») ; erreurs d'API. Écarter le bruit : une erreur
réglée à la tentative suivante (`Edit` qui ne trouve pas sa chaîne, fichier à lire avant d'écrire) n'est un
échec que si elle revient souvent. Garder ce qui est structurel : outil absent, permission, commande fausse
répétée, mauvais fichier, mauvaise branche.

**Corrections répétées.** Partir des demandes marquées CORR, et lire aussi les demandes de rang 2 et plus sans
marque : une correction peut être polie (« peux-tu plutôt… »). CORR n'est qu'une présomption : « non » répond
souvent à une question de Claude (marque `?`). Regrouper par attente sous-jacente : format, style,
vérification oubliée, périmètre dépassé, fichier ou outil à ne pas toucher. Une correction est répétée quand
la même attente est corrigée dans au moins deux sessions.

**Tâches récurrentes.** Regrouper les demandes de même nature dans au moins deux sessions, même formulées
autrement ; les THÈMES aident mais ne suffisent pas. Signes forts : longue consigne réécrite d'une fois sur
l'autre, même enchaînement d'étapes, skill existant appelé avec les mêmes compléments à chaque fois.

Pour chaque schéma retenu, choisir la forme la plus légère qui règle le problème :

| Forme | Quand |
|---|---|
| `nouveau-skill` | procédure de plusieurs étapes, stable, qui revient, et qu'aucun skill de l'inventaire ne couvre |
| `skill-existant` | un skill de SKILLS EXISTANTS couvre le sujet mais rate le point ; `nom` = son nom exact |
| `regle` | une attente qui tient en une ou deux phrases (style, format, interdit) : CLAUDE.md ou préférences |
| `hook` | ce qui doit se produire à chaque fois sans que personne y pense (contrôle avant commit, mise en forme) |

La demande porte sur des skills : en proposer quand c'est la bonne forme ; sinon, dire dans `limite` pourquoi
une règle ou un hook vaut mieux. Seuil : au moins deux occurrences dans deux sessions distinctes. Un cas isolé,
ou limité à une seule session, va dans `a_surveiller`. Sept propositions au plus, triées par gain. Une liste
vide est un résultat valable.

## 3. Écrire les propositions

`$W/propositions.json` (modèle complet : `$S/exemple/propositions.json`) :

```json
{
 "synthese": "deux à cinq phrases : ce que montre la période",
 "propositions": [{
   "nom": "kebab-case, nom du futur skill",
   "forme": "nouveau-skill | skill-existant | regle | hook",
   "natures": ["echec", "correction", "recurrence"],
   "constat": "ce qui se répète, factuel",
   "solution": "ce que ferait le skill, la règle ou le hook",
   "declencheurs": ["phrases qui le lanceraient, obligatoire pour un skill"],
   "etapes": ["trois à six étapes envisagées"],
   "gain": "fréquence observée et ce qui est évité",
   "limite": "risque, doublon possible, ou pourquoi une forme plus légère",
   "priorite": "haute | moyenne | basse",
   "certitude": "confirmé | probable | incertain | spéculatif",
   "exemples": ["deux identifiants de deux sessions différentes, les plus parlants"],
   "occurrences": ["tous les identifiants du schéma, exemples compris"]
 }],
 "a_surveiller": [{"sujet": "…", "ids": ["…"]}]
}
```

## 4. Construire le rapport

```
python3 $S/scripts/analyser.py rapport $W/propositions.json --signaux $W/signaux.json --sortie $R
```

Corriger `propositions.json` jusqu'à ce que le contrôle passe ; ne jamais retoucher à la main `signaux.json` ni
le rapport généré. Le script écrit, sous le même nom `$R/improve-system-AAAA-MM-JJ` :

- `.docx` : le rapport à lire, mis en forme, sans dépendance à installer ;
- `.md` : le même contenu en texte ;
- `.json` : les propositions, avec le nom du rapport, pour une installation ultérieure.

## 5. Présenter

Dans la conversation : le chemin du `.docx`, une ligne par proposition (numéro, nom, forme, occurrences,
priorité), puis la question : lesquelles installer ? Rien d'autre ne se fait avant la réponse.

## 6. Installer, après accord seulement

Pour chaque proposition désignée :

- `nouveau-skill` : écrire `~/.claude/skills/<nom>/SKILL.md` (frontmatter `name` et `description` avec les
  déclencheurs, puis les étapes ; le skill `skill-creator` peut servir s'il est disponible). Dans le
  `.claude/skills/` d'un dépôt seulement si Patrick le demande, en rappelant que thinkup-site est public. Si
  le dossier existe déjà : s'arrêter et demander.
- `skill-existant` : montrer la modification (avant, après) et attendre un second accord avant d'écrire : le
  skill peut être partagé ou synchronisé ailleurs.
- `regle` : montrer le texte exact et le fichier visé (CLAUDE.md du projet ou `~/.claude/CLAUDE.md`). Les
  préférences de claude.ai, Patrick les modifie lui-même.
- `hook` : passer par le skill `update-config` et montrer la configuration avant de l'écrire.

Ensuite : lister les fichiers créés ou modifiés avec la commande d'annulation (`rm -r ~/.claude/skills/<nom>`),
puis consigner l'installation dans le rapport. Ajouter à `$R/improve-system-AAAA-MM-JJ.json` une entrée
`"installations": [{"date": "JJ/MM/AAAA", "noms": ["<nom>"]}]` (à la suite des entrées existantes), puis
relancer :

```
python3 $S/scripts/analyser.py rapport $R/improve-system-AAAA-MM-JJ.json --signaux $R/travail/AAAA-MM-JJ/signaux.json --sortie $R
```

Le `.docx` et le `.md` sont réécrits sous le même nom. Un nouveau skill est disponible au plus tard à la
session suivante.

Si Patrick y revient plus tard (« installe la 2 du rapport du 21/10 »), relire
`$R/improve-system-AAAA-MM-JJ.json` plutôt que de relancer l'analyse.

## Contrôle de non-régression

```
python3 $S/scripts/analyser.py extraire --racine $S/exemple/projects --aujourdhui 2026-10-21 --sortie /tmp/improve-test
python3 $S/scripts/analyser.py rapport $S/exemple/propositions.json --signaux /tmp/improve-test/signaux.json --sortie /tmp/improve-test/rapports
```
