"""Offline contract tests: FTPS scope, signed proof, cleanup and isolated PHP."""
import contextlib
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('host', root / 'check-brevo-host.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
key = 'synthetic-private-key'
sha = 'a' * 40
nonce = 'b' * 48
expiry = int(time.time()) + 900
payload = f'{nonce}\n{sha}\n{expiry}'
signature = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
proof = hmac.new(key.encode(), ('response\n' + payload + '\n1').encode(), hashlib.sha256).hexdigest()
valid = dict(active=True, nonce=nonce, sha=sha, proof=proof)
for label, data, expected in [('valid', valid, True), ('string-active', dict(valid, active='true'), False), ('wrong-nonce', dict(valid, nonce='c'*48), False), ('wrong-sha', dict(valid, sha='d'*40), False), ('wrong-proof', dict(valid, proof='0'*64), False), ('extra-field', dict(valid, secret=key), False), ('invalid-json', [], False)]:
    assert host.proof_valid(data, nonce, sha, expiry, key) is expected, label
    print('PASS host proof ' + label)

for value in ('', ' \t\n', 'invalid\x01key', 'non-ascii-\u00e9'):
    with patch.dict(os.environ, {'BREVO_API_KEY':value}):
        try: host.brevo_key.normalized_key(); raise AssertionError('accepted invalid key')
        except ValueError: pass
with patch.dict(os.environ, {'BREVO_API_KEY':' \t'+key+'\r\n\v\f'}):
    assert host.brevo_key.normalized_key() == key
print('PASS shared key normalization and invalid keys')

class FakeFTP:
    def __init__(self, **kwargs):
        assert kwargs['context'].check_hostname
        assert kwargs['context'].verify_mode == host.ssl.CERT_REQUIRED
        self.directory = '/home/account'
        self.files = set()
        self.transfers = []
    def connect(self, hostname, port): assert hostname == 'ftp.example.invalid'
    def login(self, user, password): pass
    def prot_p(self): self.protected = True
    def pwd(self): return self.directory
    def cwd(self, directory):
        if directory == './': self.directory = '/home/account'
        elif directory in ('./public_html/', '/public_html/'): self.directory = '/home/account/public_html'
        else: self.directory = directory
    def storbinary(self, command, data):
        assert self.protected
        assert re.fullmatch(r'STOR /home/account(?:/public_html)?/brevo-preflight-[a-f0-9]{48}\.php', command)
        self.files.add(command[5:]); self.transfers.append(command)
        source = data.read().decode()
        assert key not in source
        assert sha in source
    def delete(self, name):
        assert name in self.files
        if cleanup_failure: raise OSError(key)
        self.files.remove(name)
    def close(self): pass

class FakeOpener:
    def open(self, request, timeout):
        assert request.get_method() == 'GET'
        assert request.full_url == 'https://think-up.fr/brevo-preflight-' + nonce + '.php'
        assert request.get_header('X-preflight-signature') == signature
        if not ftp.files or not any('/public_html/' in name for name in ftp.files):
            raise urllib.error.HTTPError(request.full_url, 404, '', {}, None)
        if invalid_proof: return io.BytesIO(json.dumps(dict(valid, proof='0'*64)).encode())
        return io.BytesIO(json.dumps(valid).encode())

for label, invalid_proof, cleanup_failure, expected in [('success', False, False, True), ('invalid-proof', True, False, False), ('cleanup-failure', False, True, False)]:
    ftp = FakeFTP(context=host.ssl.create_default_context())
    with tempfile.TemporaryDirectory() as directory:
        output_path = Path(directory) / 'output'
        env = {'BREVO_API_KEY':' \t' + key + '\n', 'GITHUB_SHA':sha, 'FTP_SERVER':'ftp://192.0.2.1', 'FTP_TLS_HOST':'ftp.example.invalid', 'FTP_USERNAME':'fake-user', 'FTP_PASSWORD':'fake-password', 'GITHUB_OUTPUT':str(output_path), 'RUNNER_TEMP':directory}
        with patch.dict(os.environ, env), patch.object(host.ftplib, 'FTP_TLS', return_value=ftp), patch.object(host.secrets, 'token_hex', return_value=nonce), patch.object(host.time, 'time', return_value=expiry-900), patch.object(host.urllib.request, 'build_opener', return_value=FakeOpener()), contextlib.redirect_stdout(io.StringIO()) as output:
            try: host.main(); result = True
            except Exception as error:
                result = False
                assert key not in str(error)
            assert result is expected, label
            assert key not in output.getvalue()
            assert output_path.exists() is expected
            if expected: assert output_path.read_text() == 'server_dir=./public_html/\nserver_host=ftp.example.invalid\nserver_port=21\n'
            if not cleanup_failure: assert not ftp.files
            if cleanup_failure:
                cleanup_failure = False
                host.cleanup_saved()
                assert not ftp.files
                assert json.loads(host.state_path().read_text())['cleaned'] is True
                host.cleanup_saved()
    print('PASS host FTP ' + label)

php = os.environ.get('PHP_BINARY') or shutil.which('php')
assert php, 'PHP_BINARY or PHP is required for the helper contract'
fixtures = [('active', {'senders':[{'email':'contact@think-up.fr','active':True}]}, True), ('inactive', {'senders':[{'email':'contact@think-up.fr','active':False}]}, False), ('wrong-sender', {'senders':[{'email':'other@example.invalid','active':True}]}, False), ('string-active', {'senders':[{'email':'contact@think-up.fr','active':'true'}]}, False), ('mixed', {'senders':[{'email':'contact@think-up.fr','active':True}, None]}, False), ('invalid-structure', {}, False), ('object-senders', {'senders':{'0':{'email':'contact@think-up.fr','active':True}}}, False)]
for label, data, expected in fixtures:
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        source = (root / 'brevo-host-preflight.php').read_text().replace('__NONCE__', nonce).replace('__SHA__',sha).replace('__EXPIRY__',str(expiry))
        (folder / 'helper.php').write_text(source)
        (folder / 'config.local.php').write_text("<?php define('BREVO_API_KEY', ' " + key + " ');")
        constants = ['CURLOPT_RETURNTRANSFER','CURLOPT_HTTPHEADER','CURLOPT_CONNECTTIMEOUT','CURLOPT_TIMEOUT','CURLOPT_FOLLOWLOCATION','CURLOPT_SSL_VERIFYPEER','CURLOPT_SSL_VERIFYHOST','CURLOPT_PROTOCOLS','CURLPROTO_HTTPS','CURLINFO_HTTP_CODE']
        preamble = '<?php\n' + '\n'.join(f"define('{name}', {i+1});" for i,name in enumerate(constants))
        preamble += "\n$_SERVER['REQUEST_METHOD']='GET'; $_SERVER['HTTP_X_PREFLIGHT_SIGNATURE']='"+signature+"'; $_GET=[];\n"
        preamble += "function curl_init($url) { file_put_contents(__DIR__.'/api-called', '1'); if ($url !== 'https://api.brevo.com/v3/senders') throw new Exception('bad URL'); return true; }\n"
        preamble += "function curl_setopt_array($ch,$options) { if ($options[CURLOPT_CONNECTTIMEOUT]!==2 || $options[CURLOPT_TIMEOUT]!==5 || $options[CURLOPT_FOLLOWLOCATION]!==false || $options[CURLOPT_SSL_VERIFYPEER]!==true || $options[CURLOPT_SSL_VERIFYHOST]!==2) throw new Exception('bad transport'); }\n"
        encoded = json.dumps(json.dumps(data))
        preamble += "function curl_exec($ch) { return " + encoded + "; } function curl_getinfo($ch,$option) { return 200; } function curl_close($ch) {}\nrequire __DIR__.'/helper.php';"
        (folder / 'runner.php').write_text(preamble)
        completed = subprocess.run([php,'-n',str(folder/'runner.php')], capture_output=True, text=True)
        assert completed.returncode == 0, label
        result = json.loads(completed.stdout)
        assert result['active'] is expected and host.proof_valid(result,nonce,sha,expiry,key), label
        assert key not in completed.stdout + completed.stderr, label
        for rejection, old, new in [('signature',signature,'0'*64), ('method',"='GET'","='POST'"), ('query','$_GET=[]',"$_GET=['url'=>'https://example.invalid']")]:
            (folder/'api-called').unlink(missing_ok=True)
            (folder/'runner.php').write_text(preamble.replace(old,new))
            denied = subprocess.run([php,'-n',str(folder/'runner.php')], capture_output=True,text=True)
            assert denied.stdout == '{}', rejection
            assert not (folder/'api-called').exists(), rejection
        for rejection in ('expired', 'wrong-key', 'missing-config', 'invalid-key'):
            (folder/'api-called').unlink(missing_ok=True)
            (folder/'runner.php').write_text(preamble)
            (folder/'helper.php').write_text(source.replace(str(expiry),str(int(time.time())-1)) if rejection == 'expired' else source)
            (folder/'config.local.php').write_text("<?php define('BREVO_API_KEY', '" + ('other-key' if rejection == 'wrong-key' else ('invalid\x01key' if rejection == 'invalid-key' else key)) + "');")
            if rejection == 'missing-config': (folder/'config.local.php').unlink()
            denied = subprocess.run([php,'-n',str(folder/'runner.php')], capture_output=True,text=True)
            assert denied.stdout == '{}', rejection
            assert not (folder/'api-called').exists(), rejection
    print('PASS helper PHP ' + label + ' plus unauthorized requests')

workflow = (root.parent / '.github/workflows/deploy.yml').read_text()
assert workflow.count('server-dir: ${{ steps.host_preflight.outputs.server_dir }}') == 3
assert workflow.count('protocol: ftps') == 3
assert workflow.count('security: strict') == 3
assert workflow.count('server: ${{ steps.host_preflight.outputs.server_host }}') == 3
assert workflow.count('port: ${{ steps.host_preflight.outputs.server_port }}') == 3
assert workflow.index('run: python3 editorial/check-brevo-host.py') < workflow.index('run: |\n          python3 editorial/brevo-key.py') < workflow.index('id: ftp1')
assert 'continue-on-error' not in workflow[workflow.index('id: host_preflight'):workflow.index('# config.local.php')]
assert 'if: always()' in workflow[workflow.index('id: host_preflight'):workflow.index('# config.local.php')]
assert 'run: python3 editorial/check-brevo-host.py --cleanup' in workflow
print('PASS workflow: helper cleanup gate before config and all 3 FTPS uploads')
