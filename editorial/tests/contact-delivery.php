<?php
declare(strict_types=1);

// Execute the actual endpoint in an isolated namespace: every mail/HTTP call is
// a mock, config files are inaccessible, and no real request is transmitted.
namespace ContactTest;

$cases = [
    'mail-only' => [true, [], false, [], 200, 'OK', 0, 0],
    'brevo-rescue' => [false, [201], true, [], 200, 'OK', 1, 0],
    'brevo-truncated-context' => [false, [201], true, ['contexte' => str_repeat('x', 501)], 503, 'coordonnées', 1, 0],
    'retry-identity-only' => [false, [400, 204], true, [], 503, 'coordonnées', 2, 0],
    'diagnostic-identity-only' => [false, [400, 201], true, ['ack' => '1', 'diagnostic_consent' => '1'], 503, 'coordonnées', 2, 0],
    'mail-rescue' => [true, [500, 500], true, [], 200, 'OK', 2, 0],
    'both-fail' => [false, [500, 503], true, [], 503, 'Envoi impossible', 2, 0],
    'no-key' => [false, [], false, [], 503, 'Envoi impossible', 0, 0],
    'diagnostic-missing-consent' => [true, [], true, ['ack' => '1'], 400, 'requis', 0, 0],
    'diagnostic-both-fail' => [false, [500, 500], true, ['ack' => '1', 'diagnostic_consent' => '1'], 503, 'Envoi impossible', 2, 0],
    'diagnostic-success' => [true, [201, 201], true, ['ack' => '1', 'diagnostic_consent' => '1'], 200, 'OK', 1, 1],
    'ack-failure-nonblocking' => [true, [201, 500], true, ['ack' => '1', 'diagnostic_consent' => '1'], 200, 'OK', 1, 1],
];
$case = $argv[1] ?? '';
if (!isset($cases[$case])) { throw new \RuntimeException('Unknown test case'); }
[$mailAccepted, $responses, $key, $extra, $expectedStatus, $expectedBody, $expectedContacts, $expectedAck] = $cases[$case];
$contactCalls = 0;
$ackCalls = 0;
$_SERVER['REQUEST_METHOD'] = 'POST';
$_POST = ['nom' => 'Test Fixture', 'email' => 'fixture@example.invalid'] + $extra;
foreach (['CURLOPT_RETURNTRANSFER', 'CURLOPT_POST', 'CURLOPT_POSTFIELDS', 'CURLOPT_TIMEOUT', 'CURLOPT_HTTPHEADER', 'CURLINFO_HTTP_CODE'] as $index => $constant) {
    if (!\defined($constant)) { \define($constant, $index + 1); }
}
function is_file(string $path): bool { return false; }
function is_readable(string $path): bool { return false; }
function getenv(string $name): string|false { global $key; return $name === 'BREVO_API_KEY' && $key ? 'mock-key' : false; }
function function_exists(string $name): bool { return $name === 'curl_init' || \function_exists($name); }
function mb_substr(string $text, int $start, int $length): string { return \substr($text, $start, $length); }
function mail(string $to, string $subject, string $body, string $headers): bool { global $mailAccepted; return $mailAccepted; }
function curl_init(string $url): object {
    global $contactCalls, $ackCalls;
    if (str_ends_with($url, '/contacts')) { $contactCalls++; } else { $ackCalls++; }
    return (object)['url' => $url];
}
function curl_setopt_array(object $handle, array $options): bool { return true; }
function curl_exec(object $handle): string { return '{}'; }
function curl_getinfo(object $handle, int $option): int { global $responses; return array_shift($responses) ?? 500; }
function curl_close(object $handle): void {}

http_response_code(200);
ob_start();
register_shutdown_function(static function () use ($case, $expectedStatus, $expectedBody, $expectedContacts, $expectedAck): void {
    global $contactCalls, $ackCalls;
    $body = ob_get_clean();
    if (http_response_code() !== $expectedStatus || !str_contains($body, $expectedBody) || $contactCalls !== $expectedContacts || $ackCalls !== $expectedAck) {
        fwrite(STDERR, "FAIL $case: status=" . http_response_code() . ", contacts=$contactCalls, ack=$ackCalls, body=$body\n");
        exit(1);
    }
    echo "PASS $case\n";
});
$source = file_get_contents(__DIR__ . '/../../envoi-contact.php');
$source = preg_replace('/^<\?php\s*declare\(strict_types=1\);/', 'namespace ContactTest;', $source);
eval($source);
