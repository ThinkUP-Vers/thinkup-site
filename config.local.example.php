<?php
/**
 * Modèle de configuration locale — SECRETS.
 *
 * 1. Copiez ce fichier en « config.local.php » (même dossier) sur le serveur.
 * 2. Remplacez la valeur par VOTRE nouvelle clé API Brevo (v3, commence par xkeysib-).
 * 3. NE VERSIONNEZ JAMAIS config.local.php — il est ignoré par git (.gitignore).
 *
 * config.local.php n'affiche rien et ne fait que déclarer le secret pour
 * envoi-contact.php, qui le lit via getenv('BREVO_API_KEY').
 */

putenv('BREVO_API_KEY=xkeysib-VOTRE_NOUVELLE_CLE_ICI');
