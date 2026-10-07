"""Read-only deployment gate. Never print credentials or API response bodies."""
import json
import os
import sys
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
    valid = any(
        sender.get("email") == "contact@think-up.fr" and sender.get("active") is True
        for sender in data.get("senders", [])
    )
except Exception:
    sys.exit("Brevo sender preflight: API unavailable or invalid response; deployment stopped")
if not valid:
    sys.exit("Brevo sender preflight: fixed sender missing or inactive; deployment stopped")
print("Brevo sender preflight: fixed sender active; no email sent")
