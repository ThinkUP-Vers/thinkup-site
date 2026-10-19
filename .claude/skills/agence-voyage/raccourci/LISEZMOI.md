# Raccourci « Agence de voyage » sur le bureau

Le raccourci ouvre Claude Code dans le navigateur avec tout préparé : le dépôt `thinkup-site` est
sélectionné et `/agence-voyage` est déjà tapé dans la zone de saisie. Il reste à compléter la demande
(« prépare mon déplacement à Lyon le 12 novembre ») et à appuyer sur Entrée : rien ne part sans toi.
Ce préremplissage repose sur les paramètres d'adresse documentés de claude.ai/code (`prompt`,
`repositories`) ; si un jour ils changeaient, le raccourci ouvrirait simplement Claude Code vide.

## Méthode la plus simple : glisser le raccourci sur le bureau

Rien ne s'installe tout seul : le raccourci se pose sur l'ordinateur, à la main ou par un installeur.

- **Windows** (méthode qui a fonctionné le 19/10/2026) : clic droit sur le bureau, « Nouveau »,
  « Raccourci », coller l'adresse
  `https://claude.ai/code?prompt=/agence-voyage%20&repositories=ThinkUP-Vers/thinkup-site`, nommer
  « Agence de voyage », « Terminer ». Le fichier `Agence de voyage.url` fait la même chose, mais un
  téléchargement peut en altérer l'extension : Windows ne propose alors que des éditeurs de code pour
  l'ouvrir. Pour l'icône Think'UP : copier
  `agence-voyage.ico` dans un dossier qui restera (par exemple Documents), puis clic droit sur le
  raccourci, « Propriétés », onglet « Document Web », « Changer d'icône », « Parcourir », choisir le
  fichier `.ico`, « OK ».
- **Mac** : faire glisser `Agence de voyage.webloc` sur le bureau. Pour l'icône Think'UP : ouvrir
  `agence-voyage.png` dans Aperçu, Cmd-A puis Cmd-C ; sélectionner le raccourci sur le bureau, Cmd-I,
  cliquer la petite icône en haut à gauche de la fenêtre d'informations, Cmd-V.

## Installation automatique

- **Windows** : double-cliquer sur `installer-windows.cmd`. Si Windows affiche « Windows a protégé
  votre ordinateur » : « Informations complémentaires », puis « Exécuter quand même ».
- **Mac** : clic droit sur `installer-mac.command`, puis « Ouvrir » (un double-clic simple est bloqué
  pour un fichier téléchargé). À défaut, dans le Terminal :
  `bash ~/Downloads/raccourci-agence-voyage/installer-mac.command`.

## Méthode manuelle

- **Windows** : clic droit sur le bureau, « Nouveau », « Raccourci », adresse
  `https://claude.ai/code?prompt=/agence-voyage%20&repositories=ThinkUP-Vers/thinkup-site`,
  nom « Agence de voyage ». Puis clic droit sur le raccourci, « Propriétés », « Changer d'icône »,
  choisir `agence-voyage.ico` (le copier d'abord dans un dossier qui ne sera pas supprimé).
- **Mac** : dans Safari, ouvrir l'adresse ci-dessus et la faire glisser sur le bureau.
  Ouvrir `agence-voyage.png` dans Aperçu, « Tout sélectionner », « Copier » ; sélectionner le
  raccourci, « Lire les informations » (Cmd-I), cliquer la petite icône en haut à gauche, « Coller ».

## Fichiers

`icone.svg` est la source de l'icône ; `agence-voyage.png`, `.ico` (Windows) et `.icns` (Mac) en sont
tirés.
