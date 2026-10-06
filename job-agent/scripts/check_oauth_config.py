from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _dep(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _load_env() -> dict[str, str]:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return {}
    env: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def _mask(v: str) -> str:
    if not v:
        return "(empty)"
    return v[:4] + "..." + v[-4:] if len(v) >= 8 else "***"


def main() -> int:
    print("=== Gmail OAuth pre-flight check ===")
    print()
    env = _load_env()
    cid = env.get("EMAIL_OAUTH_CLIENT_ID", "")
    cs = env.get("EMAIL_OAUTH_CLIENT_SECRET", "")
    sender = env.get("EMAIL_SENDER_ADDRESS", "")

    secrets_file = env.get("EMAIL_OAUTH_CLIENT_SECRETS_FILE", "")
    secrets_file_ok = False
    if secrets_file:
        from pathlib import Path as _P
        sp = _P(secrets_file) if _P(secrets_file).is_absolute() else (REPO_ROOT / secrets_file)
        secrets_file_ok = sp.exists() and sp.is_file()

    print("[1] .env OAuth config")
    if secrets_file:
        print(f"    EMAIL_OAUTH_CLIENT_SECRETS_FILE: {secrets_file} ({'OK' if secrets_file_ok else 'MISSING ON DISK'})")
    else:
        print(f"    EMAIL_OAUTH_CLIENT_SECRETS_FILE: (not set)")
    print(f"    EMAIL_OAUTH_CLIENT_ID:     {_mask(cid)}")
    print(f"    EMAIL_OAUTH_CLIENT_SECRET: {_mask(cs)}")
    print(f"    EMAIL_SENDER_ADDRESS:      {sender or '(empty)'}")
    env_ok = (secrets_file_ok or (bool(cid) and bool(cs))) and bool(sender)

    oauthlib_ok = _dep("google_auth_oauthlib")
    keyring_ok = _dep("keyring")
    print()
    print("[2] Python dependencies")
    print(f"    google-auth-oauthlib: {'INSTALLED' if oauthlib_ok else 'MISSING'}")
    print(f"    keyring:              {'INSTALLED' if keyring_ok else 'MISSING'}")
    deps_ok = oauthlib_ok and keyring_ok

    token_present = False
    print()
    print("[3] macOS Keychain token")
    if keyring_ok:
        try:
            import keyring as _kr
            tok = _kr.get_password("job-agent-oauth", "gmail-refresh-token")
            token_present = bool(tok)
            print(f"    refresh token: {'PRESENT' if token_present else 'MISSING'}")
            if token_present and tok is not None:
                print(f"    token length: {len(tok)} (value NOT shown)")
        except Exception as e:
            print(f"    error reading Keychain: {e}")
    else:
        print("    (skipped - keyring not installed)")

    print()
    print("=" * 60)
    if not env_ok:
        print("NEXT STEP: Edit .env - add EMAIL_OAUTH_CLIENT_ID + EMAIL_OAUTH_CLIENT_SECRET + EMAIL_SENDER_ADDRESS")
        print("  Get Client ID/Secret from: https://console.cloud.google.com/apis/credentials")
        return 1
    if not deps_ok:
        print("NEXT STEP: Install Python dependencies:")
        print("  .venv/bin/pip install google-auth-oauthlib google-auth-httplib2 keyring")
        return 1
    if not token_present:
        print("NEXT STEP: Run the OAuth flow (opens browser):")
        print("  make authorize-gmail")
        return 1
    print("ALL CHECKS PASS. Gmail OAuth is fully configured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
