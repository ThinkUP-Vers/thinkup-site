"""Temporary helper only: exact STOR/DELE, no FTP sync or application upload."""
import ftplib
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import secrets
import sys
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

spec = importlib.util.spec_from_file_location("brevo_key", Path(__file__).with_name("brevo-key.py"))
brevo_key = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brevo_key)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def proof_valid(data, nonce, sha, expiry, key):
    if not isinstance(data, dict) or set(data) != {'active', 'nonce', 'sha', 'proof'}:
        return False
    if type(data['active']) is not bool or data['nonce'] != nonce or data['sha'] != sha or not isinstance(data['proof'], str):
        return False
    payload = f"response\n{nonce}\n{sha}\n{expiry}\n{int(data['active'])}"
    return hmac.compare_digest(data['proof'], hmac.new(key.encode('ascii'), payload.encode('ascii'), hashlib.sha256).hexdigest())


def state_path():
    return Path(os.environ['RUNNER_TEMP']) / 'brevo-host-preflight-state.json'


def save_state(state):
    path = state_path()
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state), encoding='utf-8')
    temporary.replace(path)


def connect_ftp():
    server = urllib.parse.urlsplit('//' + os.environ['FTP_TLS_HOST'] if '://' not in os.environ['FTP_TLS_HOST'] else os.environ['FTP_TLS_HOST'])
    if server.scheme not in ('', 'ftp', 'ftps') or not server.hostname or not re.fullmatch(r'[A-Za-z0-9.-]{1,253}', server.hostname) or server.path not in ('', '/') or server.username or server.password or server.query or server.fragment:
        raise ValueError('invalid FTP host')
    ftp = ftplib.FTP_TLS(timeout=30, context=ssl.create_default_context())
    ftp.connect(server.hostname, server.port or 21)
    ftp.login(os.environ['FTP_USERNAME'], os.environ['FTP_PASSWORD'])
    ftp.prot_p()
    return ftp


def cleanup_saved():
    path = state_path()
    if not path.exists():
        return
    state = json.loads(path.read_text(encoding='utf-8'))
    nonce, sha, expiry = state['nonce'], state['sha'], state['expiry']
    if not re.fullmatch('[a-f0-9]{48}', nonce) or sha != os.environ['GITHUB_SHA'] or type(expiry) is not int:
        raise ValueError('invalid cleanup state')
    filename = 'brevo-preflight-' + nonce + '.php'
    base = state['base']
    if not isinstance(base, str) or not base.startswith('/') or any(c in base for c in '\r\n\0') or '..' in base.split('/'):
        raise ValueError('invalid cleanup base')
    allowed = {base.rstrip('/') + '/' + filename, base.rstrip('/') + '/public_html/' + filename, '/public_html/' + filename}
    if not isinstance(state['uploaded'], list) or any(remote not in allowed for remote in state['uploaded']):
        raise ValueError('invalid cleanup paths')
    if state['cleaned'] is True:
        return
    ftp = None
    try:
        if state['uploaded']:
            ftp = connect_ftp()
            for remote in list(state['uploaded']):
                ftp.delete(remote)
                state['uploaded'].remove(remote)
                save_state(state)
        key = brevo_key.normalized_key()
        signature = hmac.new(key.encode('ascii'), f'{nonce}\n{sha}\n{expiry}'.encode('ascii'), hashlib.sha256).hexdigest()
        request = urllib.request.Request('https://think-up.fr/' + filename, headers={'X-Preflight-Signature':signature, 'Cache-Control':'no-cache'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=12):
                raise ValueError('helper still reachable')
        except urllib.error.HTTPError as error:
            if error.code not in (404, 410):
                raise
        state['cleaned'] = True
        save_state(state)
    finally:
        if ftp is not None:
            ftp.close()


def main():
    uploaded = []
    ftp = None
    cleanup_ok = True
    selected = None
    try:
        key = brevo_key.normalized_key()
        sha = os.environ['GITHUB_SHA']
        if not re.fullmatch('[a-f0-9]{40}', sha):
            raise ValueError('invalid SHA')
        nonce = secrets.token_hex(24)
        expiry = int(time.time()) + 900
        filename = f'brevo-preflight-{nonce}.php'
        payload = f'{nonce}\n{sha}\n{expiry}'
        signature = hmac.new(key.encode('ascii'), payload.encode('ascii'), hashlib.sha256).hexdigest()
        source = Path(__file__).with_name('brevo-host-preflight.php').read_text(encoding='utf-8').replace('__NONCE__', nonce).replace('__SHA__', sha).replace('__EXPIRY__', str(expiry)).encode('utf-8')
        request = urllib.request.Request('https://think-up.fr/' + filename, headers={'X-Preflight-Signature': signature, 'Cache-Control': 'no-cache'})
        opener = urllib.request.build_opener(NoRedirect())
        ftp = connect_ftp()
        base = ftp.pwd()
        state = dict(nonce=nonce, sha=sha, expiry=expiry, base=base, uploaded=[], cleaned=False)
        save_state(state)
        for directory in ('./', './public_html/', '/public_html/'):
            # Resolve known candidates before any upload; no directory listing.
            try:
                ftp.cwd(directory)
                absolute = ftp.pwd().rstrip('/') + '/' + filename
                ftp.cwd(base)
            except ftplib.error_perm as error:
                if str(error).startswith('550'):
                    ftp.cwd(base)
                    continue
                raise
            # Track before STOR: a timed-out transfer may still have created it.
            if absolute not in uploaded:
                uploaded.append(absolute)
            state['uploaded'] = list(uploaded)
            save_state(state)
            ftp.storbinary('STOR ' + absolute, io.BytesIO(source))
            try:
                with opener.open(request, timeout=12) as response:
                    data = json.loads(response.read(4097))
            except urllib.error.HTTPError as error:
                if error.code in (404, 403):
                    continue
                raise
            if not proof_valid(data, nonce, sha, expiry, key):
                raise ValueError('invalid host proof')
            if data['active'] is not True:
                raise ValueError('inactive sender or API unavailable')
            selected = directory
            break
        if selected is None:
            raise ValueError('no authenticated public path')
    finally:
        if uploaded:
            for remote in uploaded:
                try:
                    ftp.delete(remote)
                    state['uploaded'].remove(remote)
                    save_state(state)
                except Exception:
                    cleanup_ok = False
            try:
                with opener.open(request, timeout=12):
                    cleanup_ok = False
            except urllib.error.HTTPError as error:
                cleanup_ok = cleanup_ok and error.code in (404, 410)
            except Exception:
                cleanup_ok = False
        if ftp is not None:
            try:
                ftp.close()
            except Exception:
                pass
        if not cleanup_ok:
            raise RuntimeError('cleanup not verified')
        if uploaded:
            state['cleaned'] = True
            save_state(state)
    # Emit a bounded path only after authenticated sender and successful cleanup.
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write('server_dir=' + selected + '\n')
        server = urllib.parse.urlsplit('//' + os.environ['FTP_TLS_HOST'] if '://' not in os.environ['FTP_TLS_HOST'] else os.environ['FTP_TLS_HOST'])
        output.write('server_host=' + server.hostname + '\nserver_port=' + str(server.port or 21) + '\n')
    print('Brevo Hostinger preflight: fixed sender active, key identity proved, helper removed; no email sent')


if __name__ == '__main__':
    try:
        cleanup_saved() if sys.argv[1:] == ['--cleanup'] else main()
    except Exception:
        sys.exit('Brevo Hostinger preflight: verification or cleanup failed; deployment stopped (helper expires within 15 minutes)')
