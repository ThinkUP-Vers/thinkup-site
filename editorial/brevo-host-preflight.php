<?php
// Rendered temporarily by CI; no credential is embedded in this template.
ini_set('display_errors', '0');
header('Cache-Control: no-store');
header('Content-Type: application/json');
$nonce = '__NONCE__';
$sha = '__SHA__';
$expiry = __EXPIRY__;
function denyPreflight() { http_response_code(403); echo '{}'; exit; }
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET' || !empty($_GET) || time() > $expiry) denyPreflight();
try {
    if (!is_file(__DIR__ . '/config.local.php')) denyPreflight();
    require __DIR__ . '/config.local.php';
    if (!defined('BREVO_API_KEY') || !is_string(BREVO_API_KEY)) denyPreflight();
    $key = str_replace([" ", "\t", "\n", "\r", "\v", "\f"], '', BREVO_API_KEY);
    if ($key === '' || preg_match('/[^\x21-\x7e]/', $key)) denyPreflight();
    $payload = $nonce . "\n" . $sha . "\n" . $expiry;
    $signature = $_SERVER['HTTP_X_PREFLIGHT_SIGNATURE'] ?? '';
    if (!is_string($signature) || !preg_match('/^[a-f0-9]{64}$/D', $signature) || !hash_equals(hash_hmac('sha256', $payload, $key), $signature)) denyPreflight();
    $active = false;
    if (function_exists('curl_init')) {
        $ch = curl_init('https://api.brevo.com/v3/senders');
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_HTTPHEADER => ['api-key: ' . $key, 'accept: application/json'], CURLOPT_CONNECTTIMEOUT => 2, CURLOPT_TIMEOUT => 5, CURLOPT_FOLLOWLOCATION => false, CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2, CURLOPT_PROTOCOLS => CURLPROTO_HTTPS]);
        $body = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        $data = is_string($body) ? json_decode($body) : null;
        if ($status === 200 && is_object($data) && isset($data->senders) && is_array($data->senders) && array_is_list($data->senders)) {
            $valid = true;
            foreach ($data->senders as $sender) {
                if (!is_object($sender)) { $valid = false; break; }
                if (($sender->email ?? null) === 'contact@think-up.fr' && ($sender->active ?? null) === true) $active = true;
            }
            $active = $valid && $active;
        }
    }
    echo json_encode(['active' => $active, 'nonce' => $nonce, 'sha' => $sha, 'proof' => hash_hmac('sha256', "response\n" . $payload . "\n" . ($active ? '1' : '0'), $key)]);
} catch (Throwable $error) { denyPreflight(); }
