<?php
/**
 * Modèle de configuration locale — SECRETS.
 *
 * 1. Copiez ce fichier en « config.local.php » (même dossier que envoi-contact.php).
 * 2. Remplacez la valeur par VOTRE clé API Brevo (v3, commence par xkeysib-).
 * 3. NE VERSIONNEZ JAMAIS config.local.php — il est ignoré par git (.gitignore).
 *
 * On utilise define() plutôt que putenv() : c'est fiable même quand
 * l'hébergeur (Hostinger/LiteSpeed) restreint putenv().
 */

define('BREVO_API_KEY', 'xkeysib-VOTRE_CLE_ICI');
