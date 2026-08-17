<?php
declare(strict_types=1);
/**
 * SONDE TEMPORAIRE — à supprimer une fois le diagnostic terminé.
 *
 * Vérifie pourquoi la chaîne Brevo ne part pas depuis le serveur, sans jamais
 * exposer la clé : on n'affiche que sa longueur et ses quatre derniers
 * caractères, jamais sa valeur.
 *
 * Accès protégé par un jeton en paramètre.
 */
header('Content-Type: text/plain; charset=utf-8');

$jeton = 'sonde-17aout-2026-9f3c';
if (($_GET['t'] ?? '') !== $jeton) {
    http_response_code(404);
    exit("Not found\n");
}

$conf = __DIR__ . '/config.local.php';
if (is_file($conf)) {
    require $conf;
}

$rapport = [];
$rapport[] = "config.local.php existe      : " . (is_file($conf) ? 'oui' : 'NON');
$rapport[] = "config.local.php lisible     : " . (is_readable($conf) ? 'oui' : 'NON');
$rapport[] = "taille                       : " . (is_file($conf) ? filesize($conf) . ' octets' : '-');
$rapport[] = "constante BREVO_API_KEY      : " . (defined('BREVO_API_KEY') ? 'definie' : 'NON DEFINIE');

$cle = defined('BREVO_API_KEY') ? (string) constant('BREVO_API_KEY') : '';
if ($cle === '' && is_readable($conf)) {
    // Le même repli que celui d'envoi-contact.php.
    if (preg_match('/xkeysib-[A-Za-z0-9_\-]+/', (string) @file_get_contents($conf), $m)) {
        $cle = $m[0];
        $rapport[] = "cle recuperee par le repli   : oui";
    }
}
$rapport[] = "longueur de la cle           : " . strlen($cle);
$rapport[] = "fin de la cle                : " . ($cle !== '' ? '…' . substr($cle, -4) : '-');
$rapport[] = "prefixe attendu xkeysib-     : " . (str_starts_with($cle, 'xkeysib-') ? 'oui' : 'NON');
$rapport[] = "curl_init disponible         : " . (function_exists('curl_init') ? 'oui' : 'NON');
$rapport[] = "allow_url_fopen              : " . (ini_get('allow_url_fopen') ? 'oui' : 'non');

// Appel réel à Brevo, en lecture seule : /v3/account ne modifie rien.
if ($cle !== '' && function_exists('curl_init')) {
    $ch = curl_init('https://api.brevo.com/v3/account');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
        CURLOPT_HTTPHEADER     => ['accept: application/json', 'api-key: ' . $cle],
    ]);
    $rep  = curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err  = curl_error($ch);
    curl_close($ch);
    $rapport[] = "appel test /v3/account       : HTTP " . $code;
    if ($err !== '') {
        $rapport[] = "erreur curl                  : " . $err;
    }
    if ($code !== 200 && is_string($rep)) {
        $rapport[] = "reponse (extrait)            : " . substr($rep, 0, 160);
    }
} else {
    $rapport[] = "appel test /v3/account       : non tente";
}

echo implode("\n", $rapport), "\n";
