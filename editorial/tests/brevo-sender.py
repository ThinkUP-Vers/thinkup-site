import contextlib
import io
import os
from pathlib import Path
import runpy
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
for label, key in [('missing-key',''),('api-failure','synthetic-private-key')]:
 with patch.dict(os.environ, {'BREVO_API_KEY':key}), patch.object(urllib.request,'urlopen',side_effect=OSError('synthetic-private-key')) as call:
  try:
   runpy.run_path(str(script)); raise AssertionError('accepted')
  except SystemExit as err:
   assert 'synthetic-private-key' not in str(err)
  assert call.call_count == (1 if key else 0)
 print('PASS sender gate ' + label)
