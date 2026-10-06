from __future__ import annotations

import sys

from app.accounts.enums import AccountPlatform
from app.accounts.login import interactive_login


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m app.accounts.cli <platform>")
        print(f"platforms: {', '.join(p.value for p in AccountPlatform)}")
        return 2
    name = sys.argv[1].lower().replace("-", "_")
    try:
        platform = AccountPlatform(name)
    except ValueError:
        print(f"unknown platform: {name}")
        print(f"platforms: {', '.join(p.value for p in AccountPlatform)}")
        return 2
    result = interactive_login(platform)
    print(f"\nResult: {result.outcome}")
    if result.url_visited:
        print(f"URL visited: {result.url_visited}")
    if result.indicator_seen:
        print(f"Logged-in indicator: {result.indicator_seen}")
    for n in result.notes:
        print(f"  - {n}")
    return 0 if result.outcome in {"AUTHENTICATED", "SESSION_SAVED_UNVERIFIED"} else 1


if __name__ == "__main__":
    sys.exit(main())
