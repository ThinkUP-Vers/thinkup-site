<?php
declare(strict_types=1);

// Secrets locaux (non versionnés). Sur Hostinger : créez config.local.php à
// côté de ce fichier avec putenv('BREVO_API_KEY=...'). Voir config.local.example.php.
if (is_file(__DIR__ . '/config.local.php')) {
    require __DIR__ . '/config.local.php';
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

$to = 'patrick@think-up.fr';
$subject = "Nouveau contact Think'UP - " . $name;
$body = implode("\n", [
    "Nouveau message depuis think-up.fr",
    "",
    "Nom : " . $name,
    "Email : " . $email,
    "Entreprise : " . ($company ?: '-'),
    "Telephone : " . ($phone ?: '-'),
    "Effectif : " . ($size ?: '-'),
    "Stade IA : " . ($stage ?: '-'),
    "",
    "Contexte :",
    $context ?: '-',
]);

$headers = [
    'From: ThinkUP <patrick@think-up.fr>',
    'Reply-To: ' . $email,
    'Content-Type: text/plain; charset=UTF-8',
];

if (!mail($to, $subject, $body, implode("\r\n", $headers))) {
    http_response_code(500);
    echo 'Envoi impossible.';
    exit;
}

// Accusé de réception automatique (auto-diagnostic Indice Iceberg uniquement).
// Envoi prioritaire via l'API transactionnelle Brevo ; repli sur mail() si
// la clé n'est pas configurée ou si l'appel échoue. Toujours non bloquant :
// le lead a déjà été transmis à Patrick ci-dessus.
if (trim((string)($_POST['ack'] ?? '')) === '1') {
    $brevoSent = false;
    $brevoKey = getenv('BREVO_API_KEY') ?: '';

    if ($brevoKey !== '' && function_exists('curl_init')) {
        $payload = json_encode([
            'templateId' => 1, // « Indice Iceberg — Accusé de réception »
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
            "Merci d'avoir realise votre auto-diagnostic Indice Iceberg. Votre demande est bien arrivee.",
            ($stage !== '' ? ("Pour memoire : " . $stage . ".") : ""),
            "",
            "Patrick Langlais vous envoie votre restitution personnalisee",
            "(score detaille + vos 3 chantiers IA priorises) sous 24 a 48 heures.",
            "",
            "Vous voulez aller plus vite ? Reservez 30 minutes : https://think-up.fr/contact.html",
            "",
            "A tres vite,",
            "Patrick Langlais — Think'UP",
        ]);
        $ackHeaders = [
            "From: Think'UP <contact@thinkupcom.com>",
            'Reply-To: patrick@think-up.fr',
            'Content-Type: text/plain; charset=UTF-8',
        ];
        @mail($email, "Votre Indice Iceberg — bien recu", $ackBody, implode("\r\n", $ackHeaders));
    }
}

echo 'OK';
