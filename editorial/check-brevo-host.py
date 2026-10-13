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


# Incidents passagers (pare-feu ou surcharge côté Hostinger, API Brevo lente ou
# indisponible, coupure réseau) : jusqu'à 3 essais. Jamais pour une preuve
# invalide ni pour un expéditeur réellement inactif.
ATTEMPTS = 3
PAUSES = (5, 10)
RETRY_HTTP = {403, 408, 425, 429, 500, 502, 503, 504}

# Journal des tentatives, imprimé en cas d'échec. Il ne contient que des
# codes, des noms de classe et des messages fixes : ni clé, ni signature, ni
# identifiant FTP.
journal = []


class PreflightError(ValueError):
    """Échec identifié ; le message est fixe ou ne contient que des codes."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def proof_valid(data, nonce, sha, expiry, key):
    if not isinstance(data, dict) or set(data) != {'active', 'nonce', 'sha', 'api_status', 'api_errno', 'proof'}:
        return False
    if type(data['active']) is not bool or data['nonce'] != nonce or data['sha'] != sha or not isinstance(data['proof'], str):
        return False
    if type(data['api_status']) is not int or type(data['api_errno']) is not int:
        return False
    payload = f"response\n{nonce}\n{sha}\n{expiry}\n{int(data['active'])}\n{data['api_status']}\n{data['api_errno']}"
    return hmac.compare_digest(data['proof'], hmac.new(key.encode('ascii'), payload.encode('ascii'), hashlib.sha256).hexdigest())


def pause(attempt):
    if attempt < ATTEMPTS:
        time.sleep(PAUSES[attempt - 1])


def http_error(error):
    """(code, refus du helper) : le helper refuse par un 403 au corps « {} » ;
    un 403 en HTML vient d'un pare-feu."""
    try:
        body = error.read(64)
    except Exception:
        body = b''
    return error.code, error.code == 403 and body.strip() == b'{}'


def query_helper(opener, request, directory, nonce, sha, expiry, key):
    """'absent' si le helper n'est pas servi depuis ce dossier, 'active' si
    l'expéditeur est actif ; PreflightError sinon."""
    last = 'aucune réponse'
    for attempt in range(1, ATTEMPTS + 1):
        step = f'helper {directory}, essai {attempt}'
        try:
            with opener.open(request, timeout=12) as response:
                raw = response.read(4097)
        except urllib.error.HTTPError as error:
            code, denied = http_error(error)
            journal.append(f'{step} : HTTP {code}' + (' (refus du helper)' if denied else ''))
            if code in (404, 410) or denied:
                return 'absent'
            if code not in RETRY_HTTP:
                raise PreflightError(f'helper : HTTP {code}')
            last = f'HTTP {code}'
            pause(attempt)
            continue
        except OSError as error:
            reason = getattr(error, 'reason', None)
            last = type(error).__name__ + (f' ({type(reason).__name__})' if reason is not None else '')
            journal.append(f'{step} : {last}')
            pause(attempt)
            continue
        try:
            data = json.loads(raw)
        except ValueError:
            last = f'réponse non JSON ({len(raw)} octets)'
            journal.append(f'{step} : {last}')
            pause(attempt)
            continue
        if not proof_valid(data, nonce, sha, expiry, key):
            journal.append(f'{step} : preuve invalide')
            raise PreflightError('invalid host proof')
        if data['active'] is True:
            journal.append(f'{step} : expéditeur actif')
            return 'active'
        last = f"API Brevo : statut {data['api_status']}, erreur curl {data['api_errno']}"
        journal.append(f'{step} : {last}')
        if data['api_status'] == 200 and data['api_errno'] == 0:
            raise PreflightError('inactive sender: contact@think-up.fr absent or inactive in Brevo (API answered 200)')
        pause(attempt)
    raise PreflightError(f'helper unavailable after {ATTEMPTS} attempts, last: {last}')


def verify_removed(opener, request):
    """Vrai si le helper ne répond plus (404 ou 410)."""
    for attempt in range(1, ATTEMPTS + 1):
        step = f'contrôle du retrait, essai {attempt}'
        try:
            with opener.open(request, timeout=12):
                journal.append(f'{step} : helper encore servi')
                return False
        except urllib.error.HTTPError as error:
            code, denied = http_error(error)
            journal.append(f'{step} : HTTP {code}' + (' (refus du helper)' if denied else ''))
            if code in (404, 410):
                return True
            if denied or code not in RETRY_HTTP:
                return False
        except OSError as error:
            journal.append(f'{step} : {type(error).__name__}')
        pause(attempt)
    return False


def describe(error):
    """Cause imprimable, sans secret : message fixe, code HTTP ou FTP, nom de classe."""
    if isinstance(error, PreflightError):
        return str(error)
    if isinstance(error, urllib.error.HTTPError):
        return f'HTTP {error.code}'
    if isinstance(error, ftplib.Error):
        code = str(error)[:3]
        return f'FTP {type(error).__name__}' + (f' {code}' if code.isdigit() else '')
    return type(error).__name__


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
        if not verify_removed(urllib.request.build_opener(NoRedirect()), request):
            raise PreflightError('cleanup not verified: helper still reachable or check unavailable')
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
            if query_helper(opener, request, directory, nonce, sha, expiry, key) == 'absent':
                continue
            selected = directory
            break
        if selected is None:
            raise PreflightError('no authenticated public path')
    finally:
        if uploaded:
            for remote in uploaded:
                try:
                    ftp.delete(remote)
                    state['uploaded'].remove(remote)
                    save_state(state)
                except Exception:
                    cleanup_ok = False
            cleanup_ok = verify_removed(opener, request) and cleanup_ok
        if ftp is not None:
            try:
                ftp.close()
            except Exception:
                pass
        if not cleanup_ok:
            raise PreflightError('cleanup not verified')
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
    except Exception as error:
        for line in journal:
            print('  ' + line, file=sys.stderr)
        print('Cause : ' + describe(error), file=sys.stderr)
        sys.exit('Brevo Hostinger preflight: verification or cleanup failed; deployment stopped (helper expires within 15 minutes)')
