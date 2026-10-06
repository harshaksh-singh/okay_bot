from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


_KEYRING_SERVICE = "job-agent-oauth"
_KEYRING_USER_GMAIL = "gmail-refresh-token"
_KEYRING_USER_M365 = "microsoft-365-refresh-token"


def _keyring_available() -> bool:
    try:
        import keyring  # noqa: F401
        return True
    except ImportError:
        return False


def _env_or_dotenv(key: str) -> str | None:
    import os
    val = os.environ.get(key)
    if val:
        return val
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip() or None
    return None


def main() -> int:
    print("=== Gmail OAuth setup ===")
    print()
    print("This system NEVER accepts your Gmail password.")
    print("Gmail integration uses Google OAuth 2.0 with a refresh token stored in your macOS Keychain.")
    print()
    print("Step 1 — Register an OAuth client in Google Cloud Console:")
    print("  1. Open https://console.cloud.google.com/apis/credentials")
    print("  2. Create (or select) a project.")
    print("  3. Enable the Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com")
    print("  4. 'Create credentials' → 'OAuth client ID' → 'Desktop app'.")
    print("  5. Copy the Client ID and Client Secret.")
    print()
    print("Step 2 — Set env vars in your .env:")
    print("  EMAIL_OAUTH_CLIENT_ID=<from step 1>")
    print("  EMAIL_OAUTH_CLIENT_SECRET=<from step 1>")
    print("  EMAIL_SENDER_ADDRESS=<the Gmail you'll send from>")
    print("  GMAIL_ACCOUNT=<same address>")
    print()
    print("Step 3 — Authorize this app in your Google account:")
    print("  Install google-auth-oauthlib (optional): pip install google-auth-oauthlib google-auth-httplib2")
    print("  Run: python scripts/connect_gmail.py --authorize")
    print("  A browser window will open. You'll sign in to Google and grant Gmail-send permission.")
    print("  The refresh token will be stored in macOS Keychain under:")
    print(f"    service = {_KEYRING_SERVICE!r}")
    print(f"    user    = {_KEYRING_USER_GMAIL!r}")
    print()
    if "--authorize" in sys.argv:
        if not _keyring_available():
            print("ERROR: `keyring` is not installed. Install with: pip install keyring")
            return 1
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            print("ERROR: google-auth-oauthlib not installed.")
            print("Install with: pip install google-auth-oauthlib google-auth-httplib2")
            return 1
        secrets_file = _env_or_dotenv("EMAIL_OAUTH_CLIENT_SECRETS_FILE")
        if secrets_file:
            secrets_path = Path(secrets_file) if Path(secrets_file).is_absolute() else (REPO_ROOT / secrets_file)
            if not secrets_path.exists():
                print(f"ERROR: EMAIL_OAUTH_CLIENT_SECRETS_FILE points to {secrets_path} but that file does not exist")
                print("  Fix: run `make install-gmail-client FILE=~/Downloads/client_secret_*.json`")
                return 1
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secrets_path),
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            )
        else:
            client_id = _env_or_dotenv("EMAIL_OAUTH_CLIENT_ID")
            client_secret = _env_or_dotenv("EMAIL_OAUTH_CLIENT_SECRET")
            if not client_id or not client_secret:
                print("ERROR: no OAuth client configured. Either:")
                print("  a) run `make install-gmail-client FILE=~/Downloads/client_secret_*.json`")
                print("  b) OR set EMAIL_OAUTH_CLIENT_ID + EMAIL_OAUTH_CLIENT_SECRET in .env")
                return 1
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(
                client_config,
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            )
        creds = flow.run_local_server(port=0)
        if not creds.refresh_token:
            print("ERROR: no refresh_token returned. Re-run and ensure 'offline access' was granted.")
            return 1
        import keyring
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER_GMAIL, creds.refresh_token)
        print("OK — refresh token stored in macOS Keychain. Gmail send is now authorized.")
        print("Verify at any time with: python scripts/connect_gmail.py --verify")
        return 0
    if "--verify" in sys.argv:
        if not _keyring_available():
            print("ERROR: `keyring` is not installed. Install with: pip install keyring")
            return 1
        import keyring
        token = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER_GMAIL)
        if token:
            print(f"OK — refresh token present in Keychain under {_KEYRING_SERVICE!r}/{_KEYRING_USER_GMAIL!r}")
            print(f"token length: {len(token)} (value NOT shown)")
            return 0
        print("NOT CONFIGURED — no refresh token in Keychain yet. Run with --authorize to set up.")
        return 1
    print("Current status:")
    if _keyring_available():
        import keyring
        token = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER_GMAIL)
        print(f"  Keychain refresh token present: {'YES' if token else 'no'}")
    else:
        print("  keyring library not installed; token storage not available")
    return 0


if __name__ == "__main__":
    sys.exit(main())
