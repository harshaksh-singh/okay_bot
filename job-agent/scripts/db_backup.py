from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "job_agent.db"
BACKUP_DIR = REPO_ROOT / "data" / "backups"

_PERSISTED_TABLES = [
    "jobs", "applications", "interviews",
    "client_leads", "client_companies", "client_opportunities",
    "client_interactions", "client_followups", "client_proposals",
    "submission_evidence", "audit_logs", "search_runs",
    "messages", "emails", "followups", "errors",
]

_FORBIDDEN_COLUMNS = {"password", "passwd", "pwd", "secret", "api_key", "token", "cookie", "otp", "mfa_secret"}


def _validate_no_credentials(db_path: Path) -> list[str]:
    issues: list[str] = []
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        for row in cur.fetchall():
            col_name = row[1].lower()
            if col_name in _FORBIDDEN_COLUMNS or any(k in col_name for k in _FORBIDDEN_COLUMNS):
                issues.append(f"{t}.{col_name}")
    con.close()
    return issues


def backup(db_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = out_dir / f"job_agent_backup_{ts}.db"
    shutil.copy2(db_path, dest)
    manifest = out_dir / f"job_agent_backup_{ts}.manifest.json"
    con = sqlite3.connect(dest)
    cur = con.cursor()
    counts: dict[str, int] = {}
    for t in _PERSISTED_TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
        except sqlite3.OperationalError:
            counts[t] = 0
    con.close()
    manifest.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_db": str(db_path),
        "backup_db": str(dest),
        "row_counts": counts,
        "credential_columns_detected": _validate_no_credentials(dest),
    }, indent=2))
    return dest


def restore(backup_path: Path, target_db: Path) -> None:
    if target_db.exists():
        target_db.rename(target_db.with_suffix(f".pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"))
    shutil.copy2(backup_path, target_db)


def check(db_path: Path) -> dict:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA integrity_check")
    integrity = cur.fetchone()[0]
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in _PERSISTED_TABLES:
        if t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
    credential_cols = _validate_no_credentials(db_path)
    con.close()
    return {
        "integrity": integrity,
        "credential_columns_detected": credential_cols,
        "row_counts": counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["backup", "restore", "check"])
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--source", help="path to backup .db for restore")
    args = parser.parse_args()
    db_path = Path(args.db)

    if args.action == "backup":
        if not db_path.exists():
            print(f"ERROR: {db_path} does not exist")
            return 1
        dest = backup(db_path, BACKUP_DIR)
        print(f"OK  backup written: {dest}")
        print(f"OK  manifest:       {dest.with_suffix('.manifest.json').name}")
        return 0
    if args.action == "restore":
        if not args.source:
            print("ERROR: --source required")
            return 1
        restore(Path(args.source), db_path)
        print(f"OK  restored {args.source} -> {db_path}")
        return 0
    if args.action == "check":
        result = check(db_path)
        print(f"integrity: {result['integrity']}")
        print(f"credential_columns_detected: {result['credential_columns_detected']}")
        print(f"row_counts:")
        for t, n in result["row_counts"].items():
            print(f"  {t:28s} {n}")
        print()
        if result["integrity"] != "ok" or result["credential_columns_detected"]:
            print("Status: FAIL")
            return 1
        print("Status: PASS")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
