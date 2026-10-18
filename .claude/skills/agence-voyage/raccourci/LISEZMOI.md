# Raccourci « Agence de voyage » sur le bureau

Le raccourci ouvre Claude Code dans le navigateur avec tout préparé : le dépôt `thinkup-site` est
sélectionné et `/agence-voyage` est déjà tapé dans la zone de saisie. Il reste à compléter la demande
(« prépare mon déplacement à Lyon le 12 novembre ») et à appuyer sur Entrée : rien ne part sans toi.
Ce préremplissage repose sur les paramètres d'adresse documentés de claude.ai/code (`prompt`,
`repositories`) ; si un jour ils changeaient, le raccourci ouvrirait simplement Claude Code vide.

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
