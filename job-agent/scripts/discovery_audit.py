from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import desc, select  # noqa: E402

from app.database import SessionLocal, init_database  # noqa: E402
from app.database.models import JobRow  # noqa: E402


def _url_valid(url: str | None) -> bool:
    if not url:
        return False
    try:
        p = urlparse(url)
        return bool(p.scheme and p.netloc and p.scheme in {"http", "https"})
    except Exception:
        return False


def main() -> int:
    init_database()
    with SessionLocal() as session:
        rows = session.scalars(select(JobRow).order_by(desc(JobRow.discovered_at)).limit(500)).all()

    print("=== Discovery audit ===")
    print(f"inspected: {len(rows)} most recently discovered jobs")
    print()
    buckets = {
        "DISCOVERED": len(rows),
        "QUALIFIED": 0,
        "REJECTED": 0,
        "DUPLICATE": 0,
        "EXPIRED": 0,
        "SCAM_RISK": 0,
        "LOW_MATCH": 0,
        "INVALID_URL": 0,
    }
    for r in rows:
        if r.is_duplicate:
            buckets["DUPLICATE"] += 1
            continue
        if r.rejected:
            buckets["REJECTED"] += 1
            continue
        if r.scam_risk == "high":
            buckets["SCAM_RISK"] += 1
            continue
        if r.deadline is not None:
            try:
                if r.deadline < datetime.now(timezone.utc).replace(tzinfo=None).date():
                    buckets["EXPIRED"] += 1
                    continue
            except Exception:
                pass
        if r.posted_at is not None:
            try:
                age = (datetime.now(timezone.utc).replace(tzinfo=None) - r.posted_at.replace(tzinfo=None)).days
                if age > 60:
                    buckets["EXPIRED"] += 1
                    continue
            except Exception:
                pass
        if not _url_valid(r.application_url):
            buckets["INVALID_URL"] += 1
            continue
        if r.match_score < 65:
            buckets["LOW_MATCH"] += 1
            continue
        buckets["QUALIFIED"] += 1

    for k in ["DISCOVERED", "QUALIFIED", "REJECTED", "DUPLICATE", "EXPIRED", "SCAM_RISK", "LOW_MATCH", "INVALID_URL"]:
        print(f"  {k:14s} {buckets[k]}")
    print()
    qual_pct = (buckets["QUALIFIED"] / buckets["DISCOVERED"] * 100) if buckets["DISCOVERED"] else 0.0
    print(f"QUALIFIED rate: {qual_pct:.1f}%")
    return 0 if buckets["DISCOVERED"] > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
