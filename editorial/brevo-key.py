"""One ASCII whitespace normalization for preflight and generated PHP config."""
import os
import sys
from pathlib import Path


def normalized_key():
    key = os.environ.get("BREVO_API_KEY", "").translate(str.maketrans("", "", " \t\n\r\v\f"))
    if not key or not key.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError("invalid API key")
    return key


if __name__ == "__main__":
    try:
        key = normalized_key().replace("\\", "\\\\").replace("'", "\\'")
        Path("config.local.php").write_text("<?php\ndefine('BREVO_API_KEY', '" + key + "');\n", encoding="ascii")
    except Exception:
        sys.exit("Brevo configuration: invalid key; deployment stopped")
