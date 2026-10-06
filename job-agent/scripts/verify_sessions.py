from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.accounts.enums import AccountPlatform, LoginMode  # noqa: E402
from app.accounts.login import check_session_status  # noqa: E402
from app.accounts.registry import load_registry_from_env  # noqa: E402


def main() -> int:
    reg = load_registry_from_env()
    print("=== Session verification ===")
    print()
    header = f"{'Platform':20s} {'Mode':24s} {'Status':24s} {'Enabled':8s} {'Account':30s}"
    print(header)
    print("-" * len(header))

    pass_count = 0
    login_required = 0
    expired = 0
    not_configured = 0
    for a in reg.accounts:
        status = check_session_status(a.platform, session_dir=a.session_profile_dir)
        account_display = a.username or "—"
        print(f"{a.platform.value:20s} {a.login_mode.value:24s} {status.value:24s} {'YES' if a.enabled else 'no':8s} {account_display:30s}")
        if status.value == "AUTHENTICATED":
            pass_count += 1
        elif status.value == "LOGIN_REQUIRED":
            login_required += 1
        elif status.value == "SESSION_EXPIRED":
            expired += 1
        elif status.value == "NOT_CONFIGURED":
            not_configured += 1

    print()
    print(f"AUTHENTICATED:   {pass_count}")
    print(f"LOGIN_REQUIRED:  {login_required}")
    print(f"SESSION_EXPIRED: {expired}")
    print(f"NOT_CONFIGURED:  {not_configured}")
    print()
    enabled_user_driven = [a for a in reg.accounts if a.enabled and a.login_mode == LoginMode.USER_DRIVEN_BROWSER]
    if enabled_user_driven:
        unauth = [a for a in enabled_user_driven if check_session_status(a.platform, session_dir=a.session_profile_dir).value != "AUTHENTICATED"]
        if unauth:
            print(f"ACTION REQUIRED: {len(unauth)} enabled platform(s) need user-driven login:")
            for a in unauth:
                print(f"  make login-{a.platform.value.replace('_', '-')}")
            print()
            print("Status: NOT_READY")
            return 1
    print("Status: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
