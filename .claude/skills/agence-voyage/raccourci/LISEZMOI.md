# Raccourci « Agence de voyage » sur le bureau

Le raccourci ouvre Claude Code dans le navigateur (claude.ai/code). Dans la session qui s'ouvre,
choisir le dépôt `thinkup-site`, puis taper `/agence-voyage` suivi de la demande (« prépare mon
déplacement à Lyon le 12 novembre »). Aucun lien officiel ne permet aujourd'hui d'ouvrir Claude Code
directement sur un skill ou un dépôt donné : ces deux gestes restent à faire à chaque fois.

## Installation automatique

- **Windows** : double-cliquer sur `installer-windows.cmd`. Si Windows affiche « Windows a protégé
  votre ordinateur » : « Informations complémentaires », puis « Exécuter quand même ».
- **Mac** : clic droit sur `installer-mac.command`, puis « Ouvrir » (un double-clic simple est bloqué
  pour un fichier téléchargé). À défaut, dans le Terminal :
  `bash ~/Downloads/raccourci-agence-voyage/installer-mac.command`.

## Méthode manuelle

- **Windows** : clic droit sur le bureau, « Nouveau », « Raccourci », adresse `https://claude.ai/code`,
  nom « Agence de voyage ». Puis clic droit sur le raccourci, « Propriétés », « Changer d'icône »,
  choisir `agence-voyage.ico` (le copier d'abord dans un dossier qui ne sera pas supprimé).
- **Mac** : dans Safari, ouvrir `https://claude.ai/code` et faire glisser l'adresse sur le bureau.
  Ouvrir `agence-voyage.png` dans Aperçu, « Tout sélectionner », « Copier » ; sélectionner le
  raccourci, « Lire les informations » (Cmd-I), cliquer la petite icône en haut à gauche, « Coller ».

## Fichiers

`icone.svg` est la source de l'icône ; `agence-voyage.png`, `.ico` (Windows) et `.icns` (Mac) en sont
tirés.
