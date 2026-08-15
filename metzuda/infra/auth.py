"""Credential management infrastructure for Metzuda CLI."""

import base64
import json
from pathlib import Path

CREDENTIALS_FILE = Path.home() / ".metzuda" / "credentials"


def get_credentials() -> dict | None:
    """Returns credentials dict or None if not logged in."""
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_auth_header() -> str | None:
    """Returns the Authorization header value or None."""
    creds = get_credentials()
    if not creds:
        return None
    if creds.get("type") == "api_key" and "key" in creds:
        return f"Bearer {creds['key']}"
    if creds.get("type") == "jwt" and "token" in creds:
        return f"Bearer {creds['token']}"
    return None


def is_logged_in() -> bool:
    return get_credentials() is not None


def get_login_method() -> str:
    """Returns the login method used ('github', 'google', 'api_key', or 'none')."""
    creds = get_credentials()
    if not creds:
        return "none"
    if creds.get("type") == "api_key":
        return creds.get("provider", "api_key")
    if creds.get("type") == "jwt":
        return creds.get("provider", "oauth")
    return "none"


def get_user_email() -> str | None:
    """Returns the email of the logged-in user or None."""
    creds = get_credentials()
    if not creds:
        return None
    if "email" in creds:
        return creds["email"]
    if creds.get("type") == "jwt" and "token" in creds:
        try:
            parts = creds["token"].split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1]
                payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                payload_bytes = base64.urlsafe_b64decode(payload_b64)
                payload = json.loads(payload_bytes)
                return payload.get("email")
        except Exception:
            pass
    return None


def logout() -> None:
    if CREDENTIALS_FILE.exists():
        try:
            CREDENTIALS_FILE.unlink()
        except OSError:
            pass
    from metzuda.infra.config import sync_auth_state_to_config
    sync_auth_state_to_config()
