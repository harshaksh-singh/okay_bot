from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai_api_key", re.compile(r"\b(sk-[A-Za-z0-9]{20,})\b")),
    ("anthropic_api_key", re.compile(r"\b(sk-ant-[A-Za-z0-9\-]{20,})\b")),
    ("google_api_key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{20,})\b")),
    ("github_token", re.compile(r"\b(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b")),
    ("slack_token", re.compile(r"\b(xox[baprs]-[A-Za-z0-9\-]{10,})\b")),
    ("aws_access_key", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("aws_secret_key", re.compile(r"\b([A-Za-z0-9/+=]{40})\b.*aws", re.I)),
    ("private_rsa_key", re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----")),
    ("jwt_bearer", re.compile(r"\b(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})\b")),
    ("password_assignment", re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*['\"]([^'\"\s]{4,})['\"]", re.I)),
    ("otp_literal", re.compile(r"\botp\s*[:=]\s*['\"]?(\d{4,8})['\"]?", re.I)),
    ("session_cookie", re.compile(r"\b(session(?:id|_id|_token)?\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,})['\"]", re.I)),
]

_SCAN_EXTENSIONS = {".py", ".env", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".json", ".md", ".txt", ".eml", ".sh", ".make", "Makefile"}
_SKIP_DIR_NAMES = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "browser", ".coverage"}
_SKIP_FILE_SUFFIXES = {".db", ".db-journal", ".pyc", ".so", ".jpg", ".png", ".pdf", ".ico"}

_POLICY_TEXT_HINTS = (
    "NEVER store", "never store", "do NOT store", "do not store", "forbid", "forbidden",
    "no password", "no passwords", "REDACT", "redact", "policy", "spec", "brief",
    "placeholder", "stub", "example", "docstring", "pattern", "test",
    "assert", "fixture", "mock", "write_text", "scan", "fake", "dummy", "sample",
    "sk-abc", "sk-ant-apic", "AIzaSyDummy",
)


def _is_policy_text_hit(line: str) -> bool:
    low = line.lower()
    return any(hint.lower() in low for hint in _POLICY_TEXT_HINTS)


def _should_scan(path: Path) -> bool:
    if any(part in _SKIP_DIR_NAMES for part in path.parts):
        return False
    if path.suffix in _SKIP_FILE_SUFFIXES:
        return False
    if path.name == ".env.example" or path.name == ".env.production.example":
        return True
    if path.name.startswith(".env"):
        return True
    if path.suffix in _SCAN_EXTENSIONS or path.name == "Makefile":
        return True
    return False


def scan(root: Path) -> dict[str, list[dict]]:
    hits_by_kind: dict[str, list[dict]] = {}
    files_scanned = 0
    for path in root.rglob("*"):
        if not path.is_file() or not _should_scan(path):
            continue
        files_scanned += 1
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if _is_policy_text_hit(line):
                continue
            for kind, pattern in _SECRET_PATTERNS:
                if pattern.search(line):
                    hits_by_kind.setdefault(kind, []).append({
                        "file": str(path.relative_to(root)),
                        "line": i,
                    })
    hits_by_kind["_meta"] = [{"files_scanned": files_scanned}]
    return hits_by_kind


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(REPO_ROOT), help="root directory to scan (default: repo root)")
    args = parser.parse_args()
    root = Path(args.path).resolve()
    hits = scan(root)
    meta = hits.pop("_meta", [{}])[0]
    print(f"=== Secret scan ({root.name}) ===")
    print(f"files_scanned: {meta.get('files_scanned', 0)}")
    print()
    any_hit = False
    for kind, _ in _SECRET_PATTERNS:
        matches = hits.get(kind, [])
        if matches:
            any_hit = True
            print(f"FOUND  {kind} ({len(matches)}):")
            for m in matches[:10]:
                print(f"  - {m['file']}:{m['line']}")
            if len(matches) > 10:
                print(f"  ... and {len(matches) - 10} more")
        else:
            print(f"OK     {kind}")
    print()
    if any_hit:
        print("Status: FOUND — review the files above and remediate.")
        return 1
    print("Status: NOT FOUND — no secret patterns detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
