<?php
declare(strict_types=1);

// Secrets locaux (non versionnés). Sur Hostinger : créez config.local.php à
// côté de ce fichier avec  define('BREVO_API_KEY', 'xkeysib-...');
// Voir config.local.example.php.
if (is_file(__DIR__ . '/config.local.php')) {
    require __DIR__ . '/config.local.php';
}

// Récupère la clé Brevo depuis toutes les sources possibles (robuste même si
// putenv() est désactivé par l'hébergeur) : constante define(), variable
// d'environnement, ou variable globale $BREVO_API_KEY.
function thinkup_brevo_key(): string {
    if (defined('BREVO_API_KEY')) {
        $k = (string) constant('BREVO_API_KEY');
        if ($k !== '') { return $k; }
    }
    $k = getenv('BREVO_API_KEY');
    if (is_string($k) && $k !== '') { return $k; }
    if (isset($GLOBALS['BREVO_API_KEY']) && is_string($GLOBALS['BREVO_API_KEY']) && $GLOBALS['BREVO_API_KEY'] !== '') {
        return $GLOBALS['BREVO_API_KEY'];
    }
    // Dernier recours : lire la clé directement dans config.local.php.
    // Certains hébergeurs (Hostinger/LiteSpeed) désactivent putenv() ; un
    // config.local.php écrit sous la forme putenv('BREVO_API_KEY=…') devient
    // alors invisible, et toute la chaîne Brevo bascule en silence sur mail().
    // Cette lecture rend la clé récupérable quelle que soit sa forme.
    $conf = __DIR__ . '/config.local.php';
    if (is_readable($conf)) {
        $contenu = (string) @file_get_contents($conf);
        if (preg_match('/xkeysib-[A-Za-z0-9_\-]+/', $contenu, $m)) {
            return $m[0];
        }
    }
    return '';
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Method Not Allowed';
    exit;
}

header('Content-Type: text/plain; charset=utf-8');

if (!empty($_POST['bot-field'] ?? '')) {
    http_response_code(204);
    exit;
}

$name = trim((string)($_POST['nom'] ?? ''));
$email = trim((string)($_POST['email'] ?? ''));
$company = trim((string)($_POST['entreprise'] ?? ''));
$phone = trim((string)($_POST['tel'] ?? ''));
$size = trim((string)($_POST['effectif'] ?? ''));
$stage = trim((string)($_POST['stade'] ?? ''));
$context = trim((string)($_POST['contexte'] ?? ''));

if ($name === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo 'Nom et email valides requis.';
    exit;
}

$isDiagnostic = trim((string)($_POST['ack'] ?? '')) === '1';
if ($isDiagnostic && ($_POST['diagnostic_consent'] ?? '') !== '1') {
    http_response_code(400);
    echo 'Votre accord pour recevoir la restitution est requis.';
    exit;
}

$to = 'patrick@thinkupcom.com';
// Le nom du prospect peut porter des accents : sujet encodé en MIME.
$subject = '=?UTF-8?B?' . base64_encode("Nouveau contact Think'UP — " . $name) . '?=';
$body = implode("\n", [
    "Nouveau message depuis think-up.fr",
    "",
    "Nom : " . $name,
    "Email : " . $email,
    "Entreprise : " . ($company ?: '-'),
    "Téléphone : " . ($phone ?: '-'),
    "Effectif : " . ($size ?: '-'),
    "Stade IA : " . ($stage ?: '-'),
    "",
    "Contexte :",
    $context ?: '-',
]);

$headers = [
    "From: Think'UP <contact@think-up.fr>",
    'Reply-To: ' . $email,
    'Content-Type: text/plain; charset=UTF-8',
];

// mail() true signifie acceptation par le serveur, pas livraison en boîte.
$mailAccepted = mail($to, $subject, $body, implode("\r\n", $headers));
$contactIncomplete = false;

// ---------------------------------------------------------------------------
// Enregistrement du prospect comme contact Brevo.
//
// Jusqu'ici la seule trace d'un prospect etait un e-mail dans la boite de
// Patrick : si mail() echouait en silence ou si le message partait en
// indesirables, le contact etait perdu sans laisser d'empreinte.
//
// Trace CRM complémentaire. La réception intégrale est assurée par mail()
// ou par le canal transactionnel ci-dessous, indépendamment des attributs.
//
// La liste cible se configure dans config.local.php :
//     define('BREVO_LIST_ID', 3);
// Sans elle, le contact est cree hors liste (visible dans « Tous les contacts »).
// ---------------------------------------------------------------------------
$brevoKeyContact = thinkup_brevo_key();
if ($brevoKeyContact !== '' && function_exists('curl_init') && $email !== '') {
    $prenom = '';
    $nomFamille = '';
    if ($name !== '') {
        $morceaux = preg_split('/\s+/', trim($name), 2);
        $prenom = $morceaux[0] ?? '';
        $nomFamille = $morceaux[1] ?? '';
    }

    $attributs = array_filter([
        'PRENOM'     => $prenom,
        'NOM'        => $nomFamille,
        'ENTREPRISE' => $company,
        'TELEPHONE'  => $phone,
        'EFFECTIF'   => $size,
        'STADE_IA'   => $stage,
        'CONTEXTE'   => mb_substr($context, 0, 500),
        'SOURCE'     => (trim((string)($_POST['ack'] ?? '')) === '1')
                        ? 'Auto-diagnostic Indice Iceberg' : 'Formulaire de contact',
        'DATE_DEMANDE' => date('Y-m-d'),
    ], static fn($v) => $v !== '' && $v !== null);

    $corpsContact = [
        'email'          => $email,
        'attributes'     => $attributs,
        // Une nouvelle demande met a jour la fiche plutot que d'echouer en doublon.
        'updateEnabled'  => true,
    ];
    // Liste « Prospects site — formulaires ». Un identifiant de liste n'est pas
    // un secret : il vit ici plutot que dans config.local.php, qui n'est pas
    // deploye. Surchargeable si besoin par une constante du meme nom.
    $listeId = defined('BREVO_LIST_ID') ? (int) constant('BREVO_LIST_ID') : 3;
    if ($listeId > 0) {
        $corpsContact['listIds'] = [$listeId];
    }

    $envoyerContact = static function (array $donnees) use ($brevoKeyContact): int {
        $chc = curl_init('https://api.brevo.com/v3/contacts');
        curl_setopt_array($chc, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode($donnees, JSON_UNESCAPED_UNICODE),
            CURLOPT_TIMEOUT        => 8,
            CURLOPT_HTTPHEADER     => [
                'accept: application/json',
                'content-type: application/json',
                'api-key: ' . $brevoKeyContact,
            ],
        ]);
        @curl_exec($chc);
        $code = (int) curl_getinfo($chc, CURLINFO_HTTP_CODE);
        @curl_close($chc);
        return $code;
    };

    $code = $envoyerContact($corpsContact);
    $contactIncomplete = ($code >= 200 && $code < 300 && ($attributs['CONTEXTE'] ?? '') !== $context);

    // Brevo rejette en bloc un envoi contenant un attribut qu'il ne connait pas.
    // Sans ce repli, un seul attribut manquant dans le compte ferait perdre TOUS
    // les prospects, et en silence. On retente avec les seuls attributs standard.
    if ($code < 200 || $code >= 300) {
        $minimal = array_intersect_key($attributs, array_flip(['PRENOM', 'NOM']));
        $corpsMinimal = ['email' => $email, 'attributes' => $minimal, 'updateEnabled' => true];
        if (isset($corpsContact['listIds'])) {
            $corpsMinimal['listIds'] = $corpsContact['listIds'];
        }
        $code = $envoyerContact($corpsMinimal);
        $contactIncomplete = ($code >= 200 && $code < 300);
    }
}

// La fiche CRM reste un complément : elle peut être partielle ou remplacée
// par une demande ultérieure. Le repli transmet donc le message intégral
// à Patrick, avec le même expéditeur fixe que mail(), sans créer de queue.
$transactionAccepted = false;
if (!$mailAccepted && $brevoKeyContact !== '' && function_exists('curl_init')) {
    $payload = json_encode([
        'sender' => ['email' => 'contact@think-up.fr', 'name' => "Think'UP"],
        'to' => [['email' => $to, 'name' => 'Patrick Langlais']],
        'replyTo' => ['email' => $email],
        'subject' => "Nouveau contact Think'UP — " . $name,
        'textContent' => $body,
        'htmlContent' => '<pre>' . htmlspecialchars($body, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . '</pre>',
    ], JSON_UNESCAPED_UNICODE);
    $ch = curl_init('https://api.brevo.com/v3/smtp/email');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_TIMEOUT => 8,
        CURLOPT_HTTPHEADER => ['accept: application/json', 'content-type: application/json', 'api-key: ' . $brevoKeyContact],
    ]);
    $response = @curl_exec($ch);
    $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    @curl_close($ch);
    $receipt = is_string($response) ? json_decode($response, true) : null;
    $transactionAccepted = $httpCode === 201 && is_array($receipt) && !empty($receipt['messageId']);
}

if (!$mailAccepted && !$transactionAccepted) {
    http_response_code(503);
    echo $contactIncomplete
        ? 'Vos coordonnées ont été enregistrées, mais le contenu complet de votre demande n’a pas été transmis. Merci de réessayer ou de nous contacter directement.'
        : 'Envoi impossible. Votre demande n’a pas été acceptée ; merci de réessayer ou de nous contacter directement.';
    exit;
}

// Accusé de réception automatique (auto-diagnostic Indice Iceberg uniquement).
// Envoi prioritaire via l'API transactionnelle Brevo ; repli sur mail() si
// la clé n'est pas configurée ou si l'appel échoue. Toujours non bloquant :
// au moins un canal de réception a accepté la demande ci-dessus.
if ($isDiagnostic) {
    $brevoSent = false;
    $brevoKey = thinkup_brevo_key();

    if ($brevoKey !== '' && function_exists('curl_init')) {
        $payload = json_encode([
            'templateId' => 2, // « Indice Iceberg — Accusé de réception (think-up.fr) »
            'to'         => [['email' => $email, 'name' => ($name ?: $email)]],
            'params'     => ['NOM' => $name, 'PALIER' => ($stage !== '' ? $stage : 'Votre diagnostic')],
        ], JSON_UNESCAPED_UNICODE);

        $ch = curl_init('https://api.brevo.com/v3/smtp/email');
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => $payload,
            CURLOPT_TIMEOUT        => 8,
            CURLOPT_HTTPHEADER     => [
                'accept: application/json',
                'content-type: application/json',
                'api-key: ' . $brevoKey,
            ],
        ]);
        curl_exec($ch);
        $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        $brevoSent = ($httpCode >= 200 && $httpCode < 300);
    }

    if (!$brevoSent) {
        // Repli : accusé texte via le serveur d'envoi de l'hébergeur.
        $ackBody = implode("\n", [
            "Bonjour " . $name . ",",
            "",
            "Merci d'avoir réalisé votre auto-diagnostic Indice Iceberg. Votre demande est bien arrivée.",
            ($stage !== '' ? ("Pour mémoire : " . $stage . ".") : ""),
            "",
            "Patrick Langlais vous envoie votre restitution personnalisée",
            "(score détaillé + vos 3 chantiers IA priorisés) sous 24 à 48 heures.",
            "",
            "Vous voulez aller plus vite ? Réservez 30 minutes : https://think-up.fr/contact.html",
            "",
            "À très vite,",
            "Patrick Langlais — Think'UP",
        ]);
        $ackHeaders = [
            "From: Think'UP <contact@think-up.fr>",
            'Reply-To: patrick@thinkupcom.com',
            'Content-Type: text/plain; charset=UTF-8',
        ];
        // Un sujet non-ASCII doit être encodé MIME : sans ça, le tiret cadratin
        // et les accents ressortent en mojibake dans certains clients mail.
        $ackSubject = '=?UTF-8?B?' . base64_encode("Votre Indice Iceberg — bien reçu") . '?=';
        @mail($email, $ackSubject, $ackBody, implode("\r\n", $ackHeaders));
    }
}

echo 'OK';
