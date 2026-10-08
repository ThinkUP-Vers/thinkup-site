"""Read-only deployment gate. Never print credentials or API response bodies."""
import json
import os
import sys
import urllib.error
import urllib.request

key = os.environ.get("BREVO_API_KEY", "").strip()
if not key:
    sys.exit("Brevo sender preflight: missing API key; deployment stopped")
request = urllib.request.Request(
    "https://api.brevo.com/v3/senders",
    headers={"api-key": key, "accept": "application/json"},
)
try:
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("senders"), list):
        raise ValueError("invalid sender structure")
    if not all(isinstance(sender, dict) for sender in data["senders"]):
        raise ValueError("invalid sender structure")
    valid = any(
        sender.get("email") == "contact@think-up.fr" and sender.get("active") is True
        for sender in data["senders"]
    )
except urllib.error.HTTPError as error:
    code = error.code if type(error.code) is int and 100 <= error.code <= 599 else "unknown"
    sys.exit(f"Brevo sender preflight: HTTP {code}; deployment stopped")
except urllib.error.URLError:
    sys.exit("Brevo sender preflight: network failure; deployment stopped")
except (ValueError, TypeError):
    sys.exit("Brevo sender preflight: invalid JSON or sender structure; deployment stopped")
except Exception:
    sys.exit("Brevo sender preflight: API unavailable or invalid response; deployment stopped")
if not valid:
    sys.exit("Brevo sender preflight: fixed sender missing or inactive; deployment stopped")
print("Brevo sender preflight: fixed sender active; no email sent")
