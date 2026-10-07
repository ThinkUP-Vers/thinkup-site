<?php
declare(strict_types=1);
namespace ContactTest;
// Actual endpoint, mocked transports; payloads captured; no config or network.
$cases = [
 'mail-only'=>[true,[],null,false,[],200,0,0,0],
 'brevo-rescue'=>[false,[201],201,true,[],200,1,1,0],
 'long-context-rescue'=>[false,[201],201,true,['contexte'=>str_repeat('é',501).'<fin>'],200,1,1,0],
 'retry-rescue'=>[false,[400,204],201,true,[],200,2,1,0],
 'retry-failure-rescue'=>[false,[400,503],201,true,[],200,2,1,0],
 'crm-success-transaction-fail'=>[false,[201],500,true,[],503,1,1,0],
 'crm-partial-transaction-fail'=>[false,[400,204],500,true,[],503,2,1,0],
 'missing-receipt'=>[false,[201],201,true,['mock_no_receipt'=>'1'],503,1,1,0],
 'malformed-receipt'=>[false,[201],201,true,['mock_receipt'=>'{invalid'],503,1,1,0],
 'invalid-receipt-type'=>[false,[201],201,true,['mock_receipt'=>'{"messageId":["invalid"]}'],503,1,1,0],
 'network-fail'=>[false,[0,0],0,true,[],503,2,1,0],
 'mail-rescue'=>[true,[500,503],null,true,[],200,2,0,0],
 'no-key'=>[false,[],null,false,[],503,0,0,0],
 'diagnostic-missing-consent'=>[true,[],null,true,['ack'=>'1'],400,0,0,0],
 'diagnostic-fail'=>[false,[500,500],500,true,['ack'=>'1','diagnostic_consent'=>'1'],503,2,1,0],
 'diagnostic-rescue'=>[false,[400,201],201,true,['ack'=>'1','diagnostic_consent'=>'1'],200,2,1,1],
 'diagnostic-success'=>[true,[201],null,true,['ack'=>'1','diagnostic_consent'=>'1'],200,1,0,1],
 'ack-failure-nonblocking'=>[true,[201],null,true,['ack'=>'1','diagnostic_consent'=>'1','mock_ack_fail'=>'1'],200,1,0,1],
];
$case=$argv[1]??'';
if (!isset($cases[$case])) { throw new \RuntimeException('Unknown case'); }
[$mailAccepted,$contactResponses,$transactionResponse,$key,$extra,$expectedStatus,$expectedContacts,$expectedTransactions,$expectedAck]=$cases[$case];
$calls=$mails=[];
$_SERVER['REQUEST_METHOD']='POST';
$_POST=$extra+['nom'=>'Test Fixture','email'=>'fixture@example.invalid','entreprise'=>'Entreprise <test>','tel'=>'+33123456789','effectif'=>'12','stade'=>'Exploration','contexte'=>"Contexte complet\nDeuxième ligne <test>"];
foreach (['CURLOPT_RETURNTRANSFER','CURLOPT_POST','CURLOPT_POSTFIELDS','CURLOPT_TIMEOUT','CURLOPT_HTTPHEADER','CURLINFO_HTTP_CODE'] as $index=>$constant) { if (!\defined($constant)) { \define($constant,$index+1); } }
function is_file(string $path): bool { return false; }
function is_readable(string $path): bool { return false; }
function getenv(string $name): string|false { global $key; return $name==='BREVO_API_KEY'&&$key?'mock-key':false; }
function function_exists(string $name): bool { return $name==='curl_init'||\function_exists($name); }
function mb_substr(string $text,int $start,int $length): string { return implode('',array_slice(preg_split('//u',$text,-1,PREG_SPLIT_NO_EMPTY),$start,$length)); }
function mail(string $to,string $subject,string $body,string $headers): bool { global $mails,$mailAccepted; $mails[]=compact('to','subject','body','headers'); return $mailAccepted; }
function curl_init(string $url): object { return (object)['url'=>$url]; }
function curl_setopt_array(object $handle,array $options): bool {
 global $calls;
 $payload=json_decode($options[CURLOPT_POSTFIELDS],true,512,JSON_THROW_ON_ERROR);
 $handle->kind=str_ends_with($handle->url,'/contacts')?'contact':(isset($payload['templateId'])?'ack':'transaction');
 $calls[]=['kind'=>$handle->kind,'payload'=>$payload,'options'=>$options]; return true;
}
function curl_exec(object $handle): string|false { global $transactionResponse; if ($handle->kind==='transaction'&&$transactionResponse===0) { return false; } return $_POST['mock_receipt']??(isset($_POST['mock_no_receipt'])?'{}':'{"messageId":"fixture-message-id"}'); }
function curl_getinfo(object $handle,int $option): int { global $contactResponses,$transactionResponse; return match($handle->kind) {'contact'=>array_shift($contactResponses)??500,'transaction'=>$transactionResponse??500,'ack'=>isset($_POST['mock_ack_fail'])?500:201}; }
function curl_close(object $handle): void {}
function check(bool $condition,string $message): void { if (!$condition) { throw new \RuntimeException($message); } }
http_response_code(200);
ob_start();
register_shutdown_function(static function() use($case,$expectedStatus,$expectedContacts,$expectedTransactions,$expectedAck): void {
 global $calls,$mails;
 $output=ob_get_clean();
 try {
  check(http_response_code()===$expectedStatus,'HTTP status');
  check($expectedStatus!==200||$output==='OK','success response');
  foreach (['contact'=>$expectedContacts,'transaction'=>$expectedTransactions,'ack'=>$expectedAck] as $kind=>$expected) { check(count(array_filter($calls,fn($c)=>$c['kind']===$kind))===$expected,$kind.' count'); }
  $expectedBody=implode("\n",['Nouveau message depuis think-up.fr','','Nom : Test Fixture','Email : fixture@example.invalid','Entreprise : Entreprise <test>','Téléphone : +33123456789','Effectif : 12','Stade IA : Exploration','','Contexte :',$_POST['contexte']]);
  if ($expectedStatus!==400) {
   check($mails[0]['to']==='patrick@thinkupcom.com','mail recipient');
   check($mails[0]['body']===$expectedBody,'mail full body');
   check(str_contains($mails[0]['headers'],"From: Think'UP <contact@think-up.fr>"),'mail sender');
   check(str_contains($mails[0]['headers'],'Reply-To: fixture@example.invalid'),'mail reply-to');
   check($mails[0]['subject']==='=?UTF-8?B?'.base64_encode("Nouveau contact Think'UP — Test Fixture").'?=','mail subject');
  }
  $contactIndex=0;
  foreach ($calls as $call) {
   $p=$call['payload'];
   check($call['options'][CURLOPT_TIMEOUT]===8,'bounded timeout');
   check(in_array('api-key: mock-key',$call['options'][CURLOPT_HTTPHEADER],true),'auth header');
   if ($call['kind']==='contact') {
    $attrs=['PRENOM'=>'Test','NOM'=>'Fixture'];
    if ($contactIndex++===0) { $attrs+=['ENTREPRISE'=>$_POST['entreprise'],'TELEPHONE'=>$_POST['tel'],'EFFECTIF'=>$_POST['effectif'],'STADE_IA'=>$_POST['stade'],'CONTEXTE'=>mb_substr($_POST['contexte'],0,500),'SOURCE'=>isset($_POST['ack'])?'Auto-diagnostic Indice Iceberg':'Formulaire de contact','DATE_DEMANDE'=>date('Y-m-d')]; }
    check($p===['email'=>'fixture@example.invalid','attributes'=>$attrs,'updateEnabled'=>true,'listIds'=>[3]],'contact exact payload');
   } elseif ($call['kind']==='transaction') {
    check($p===['sender'=>['email'=>'contact@think-up.fr','name'=>"Think'UP"],'to'=>[['email'=>'patrick@thinkupcom.com','name'=>'Patrick Langlais']],'replyTo'=>['email'=>'fixture@example.invalid'],'subject'=>"Nouveau contact Think'UP — Test Fixture",'textContent'=>$expectedBody,'htmlContent'=>'<pre>'.htmlspecialchars($expectedBody,ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8').'</pre>'],'transaction full payload');
   } else {
    check($p===['templateId'=>2,'to'=>[['email'=>'fixture@example.invalid','name'=>'Test Fixture']],'params'=>['NOM'=>'Test Fixture','PALIER'=>'Exploration']],'ack exact payload');
   }
  }
  if (isset($_POST['mock_ack_fail'])) { check(count($mails)===2&&$mails[1]['to']==='fixture@example.invalid','ack mail fallback'); }
  echo "PASS $case\n";
 } catch (\Throwable $error) { fwrite(STDERR,"FAIL $case: ".$error->getMessage()."\n"); exit(1); }
});
$source=file_get_contents(__DIR__.'/../../envoi-contact.php');
$source=preg_replace('/^<\?php\s*declare\(strict_types=1\);/','namespace ContactTest;',$source);
eval($source);
