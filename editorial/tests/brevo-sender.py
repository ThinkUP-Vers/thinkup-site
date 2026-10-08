import contextlib
import io
import os
from pathlib import Path
import runpy
import urllib.error
import urllib.request
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / 'check-brevo-sender.py'
fixtures = [
 ('active', {'senders':[{'email':'contact@think-up.fr','active':True}]}, True),
 ('inactive', {'senders':[{'email':'contact@think-up.fr','active':False}]}, False),
 ('wrong-sender', {'senders':[{'email':'other@example.invalid','active':True}]}, False),
 ('missing-sender', {'senders':[]}, False),
 ('string-active', {'senders':[{'email':'contact@think-up.fr','active':'true'}]}, False),
 ('malformed', [], False),
 ('missing-field', {}, False),
 ('invalid-list', {'senders':'synthetic-private-key'}, False),
 ('invalid-entry', {'senders':['synthetic-private-key']}, False),
 ('mixed-entries', {'senders':[{'email':'contact@think-up.fr','active':True}, None]}, False),
]
import json
for label, data, expected in fixtures:
 with patch.dict(os.environ, {'BREVO_API_KEY':'synthetic-private-key'}), patch.object(urllib.request, 'urlopen', return_value=io.StringIO(json.dumps(data))) as call, contextlib.redirect_stdout(io.StringIO()) as output:
  try:
   runpy.run_path(str(script)); result=True
  except SystemExit as err:
   result=False
   assert 'synthetic-private-key' not in str(err)
  assert result is expected, label
  assert call.call_count == 1
  assert call.call_args.args[0].full_url == 'https://api.brevo.com/v3/senders'
  assert call.call_args.args[0].get_method() == 'GET'
  assert 'synthetic-private-key' not in output.getvalue()
 print('PASS sender gate ' + label)
secret = 'synthetic-private-key'
malicious_url = 'https://example.invalid/?token=' + secret
failures = [
 ('http-401', urllib.error.HTTPError(malicious_url, 401, secret, {'secret':secret}, io.BytesIO(secret.encode())), 'HTTP 401'),
 ('http-403', urllib.error.HTTPError(malicious_url, 403, secret, None, None), 'HTTP 403'),
 ('http-invalid-code', urllib.error.HTTPError(malicious_url, secret, secret, None, None), 'HTTP unknown'),
 ('network', urllib.error.URLError(secret), 'network failure'),
 ('invalid-json', json.JSONDecodeError(secret, secret, 0), 'invalid JSON or sender structure'),
 ('unexpected', RuntimeError(secret), 'API unavailable or invalid response'),
]
for label, failure, diagnostic in failures:
 with patch.dict(os.environ, {'BREVO_API_KEY':secret}), patch.object(urllib.request,'urlopen',side_effect=failure) as call, contextlib.redirect_stdout(io.StringIO()) as output:
  try:
   runpy.run_path(str(script)); raise AssertionError('accepted')
  except SystemExit as err:
   assert str(err) == 'Brevo sender preflight: ' + diagnostic + '; deployment stopped', label
   assert secret not in str(err), label
   assert malicious_url not in str(err), label
  assert call.call_count == 1, label
  assert output.getvalue() == '', label
 print('PASS sender gate ' + label)
for label, key in [('missing-key',''),('api-failure','synthetic-private-key')]:
 with patch.dict(os.environ, {'BREVO_API_KEY':key}), patch.object(urllib.request,'urlopen',side_effect=OSError('synthetic-private-key')) as call:
  try:
   runpy.run_path(str(script)); raise AssertionError('accepted')
  except SystemExit as err:
   assert 'synthetic-private-key' not in str(err)
  assert call.call_count == (1 if key else 0)
 print('PASS sender gate ' + label)
