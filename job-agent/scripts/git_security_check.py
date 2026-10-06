from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_REQUIRED_IGNORES = [
    ".env",
    ".env.*",
    "browser/",
    "browser/profiles/",
    "browser/sessions/",
    "cookies/",
    "secrets/",
    "data/*.db",
    "data/*.db-journal",
    "data/cache/",
    "data/logs/",
    "data/resumes_generated/",
    "data/email_drafts/",
    "data/submission_evidence/",
    "data/backups/",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    "*.pem",
    "*.key",
    "*.p12",
]

_FORBIDDEN_TRACKED_PATHS = [
    ".env",
    "browser/",
    "data/job_agent.db",
    "data/email_drafts/",
    "data/submission_evidence/",
]


def _read_gitignore() -> str:
    try:
        return (REPO_ROOT / ".gitignore").read_text()
    except FileNotFoundError:
        return ""


def _in_git_repo() -> bool:
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"], cwd=REPO_ROOT, capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _tracked_files() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        return out.stdout.splitlines()
    except subprocess.CalledProcessError:
        return []


def main() -> int:
    print(f"=== Git security check ({REPO_ROOT.name}) ===")
    gi = _read_gitignore()
    missing = [p for p in _REQUIRED_IGNORES if p not in gi]
    if missing:
        print(f"MISSING in .gitignore: {missing}")
    else:
        print("OK     .gitignore covers all required patterns")

    in_repo = _in_git_repo()
    if not in_repo:
        print("INFO   not a git repository yet — git-based tracked-file check skipped")
        print()
        print("Status: " + ("NOT_READY" if missing else "READY"))
        return 1 if missing else 0

    tracked = _tracked_files()
    bad_tracked: list[str] = []
    for forbidden in _FORBIDDEN_TRACKED_PATHS:
        for t in tracked:
            if t == forbidden or t.startswith(forbidden):
                bad_tracked.append(t)

    if bad_tracked:
        print(f"FOUND  tracked forbidden paths: {bad_tracked}")
    else:
        print("OK     no forbidden paths tracked")

    print(f"INFO   total tracked files: {len(tracked)}")
    print()
    ok = not missing and not bad_tracked
    print("Status: " + ("READY" if ok else "NOT_READY"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
