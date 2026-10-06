from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _validate_json(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"file does not exist: {path}"
    if not path.is_file():
        return False, f"not a regular file: {path}"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return False, f"not valid JSON: {e}"
    kind = "installed" if "installed" in data else ("web" if "web" in data else None)
    if not kind:
        return False, "missing top-level 'installed' or 'web' key - not a Google OAuth client JSON"
    inner = data[kind]
    for required in ("client_id", "client_secret"):
        if not inner.get(required):
            return False, f"missing {kind}.{required}"
    if kind != "installed":
        return False, f"this is a '{kind}' app, not an 'installed' (Desktop) app - re-create in Google Cloud as Desktop app"
    return True, ""


def _write_env_lines(env_path: Path, new_lines: dict[str, str]) -> list[str]:
    actions: list[str] = []
    content = env_path.read_text() if env_path.exists() else ""
    lines = content.splitlines()
    existing_keys: dict[str, int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k = stripped.split("=", 1)[0].strip()
        existing_keys[k] = i
    for key, val in new_lines.items():
        if key in existing_keys:
            idx = existing_keys[key]
            if lines[idx] != f"{key}={val}":
                lines[idx] = f"{key}={val}"
                actions.append(f"updated {key}")
        else:
            lines.append(f"{key}={val}")
            actions.append(f"added {key}")
    body = "\n".join(lines)
    if not body.endswith("\n"):
        body += "\n"
    env_path.write_text(body)
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a Google OAuth client secret JSON for Gmail OAuth.")
    parser.add_argument("file", help="Path to the client_secret_*.apps.googleusercontent.com.json file")
    parser.add_argument("--email", default="", help="Your Gmail address (optional)")
    args = parser.parse_args()

    source = Path(args.file).expanduser()
    print("=== Install Gmail OAuth client ===")

    ok, err = _validate_json(source)
    if not ok:
        print(f"ERROR: {err}")
        return 1

    secrets_dir = REPO_ROOT / ".secrets"
    secrets_dir.mkdir(exist_ok=True, mode=0o700)
    dest = secrets_dir / "gmail_client.json"
    shutil.copy2(source, dest)
    os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)

    gi_path = REPO_ROOT / ".gitignore"
    gi_text = gi_path.read_text() if gi_path.exists() else ""
    if ".secrets/" not in gi_text and "\nsecrets/\n" not in ("\n" + gi_text + "\n"):
        with gi_path.open("a") as f:
            f.write("\n.secrets/\n")
        print("  added .secrets/ to .gitignore")

    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        env_path.touch()
        os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
    updates = {"EMAIL_OAUTH_CLIENT_SECRETS_FILE": ".secrets/gmail_client.json"}
    if args.email:
        updates["EMAIL_SENDER_ADDRESS"] = args.email
        updates["GMAIL_ACCOUNT"] = args.email
    actions = _write_env_lines(env_path, updates)

    print(f"  copied {source.name} -> {dest} (mode 0600, owner-only)")
    for a in actions:
        print(f"  .env: {a}")
    print()
    print("Next step: run `make check-oauth-config` to verify, then `make authorize-gmail`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
