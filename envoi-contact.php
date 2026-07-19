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

echo 'OK';
