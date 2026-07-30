<?php
declare(strict_types=1);

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

// Accusé de réception automatique (auto-diagnostic Indice Iceberg uniquement)
if (trim((string)($_POST['ack'] ?? '')) === '1') {
    $ackSubject = "Votre Indice Iceberg — bien reçu";
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
        "patrick@think-up.fr",
    ]);
    $ackHeaders = [
        "From: Think'UP <patrick@think-up.fr>",
        'Reply-To: patrick@think-up.fr',
        'Content-Type: text/plain; charset=UTF-8',
    ];
    // Non bloquant : le lead a deja ete transmis a Patrick ci-dessus.
    @mail($email, $ackSubject, $ackBody, implode("\r\n", $ackHeaders));
}

echo 'OK';
