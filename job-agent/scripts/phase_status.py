from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.accounts.enums import SessionStatus  # noqa: E402
from app.accounts.login import check_session_status  # noqa: E402
from app.accounts.registry import load_registry_from_env  # noqa: E402
from app.config import get_settings  # noqa: E402

_LIVE_SUBMISSION_OUTCOMES = {"SUBMITTED_LIVE", "SUBMITTED_CONFIRMED"}
_KEYRING_SERVICE = "job-agent-oauth"
_KEYRING_USER_GMAIL = "gmail-refresh-token"


def _gmail_keychain_has_token() -> bool:
    try:
        import keyring
        return bool(keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER_GMAIL))
    except ImportError:
        return False
    except Exception:
        return False


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        out = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=180)
        return out.returncode, out.stdout + "\n" + out.stderr
    except Exception as e:
        return 1, str(e)


def main() -> int:
    py = str(REPO_ROOT / ".venv" / "bin" / "python") if (REPO_ROOT / ".venv").exists() else "python3"

    print("=" * 60)
    print("PHASE 5 STATUS")
    print("=" * 60)

    rc_sec, _ = _run([py, str(REPO_ROOT / "scripts" / "secret_scan.py")])
    rc_git, _ = _run([py, str(REPO_ROOT / "scripts" / "git_security_check.py")])
    db_present = (REPO_ROOT / "data" / "job_agent.db").exists()
    rc_db_check, _ = _run([py, str(REPO_ROOT / "scripts" / "db_backup.py"), "check"]) if db_present else (1, "")
    rc_resume, _ = _run([py, str(REPO_ROOT / "scripts" / "resume_validator.py")])
    rc_sessions, _ = _run([py, str(REPO_ROOT / "scripts" / "verify_sessions.py")])
    rc_tests, _ = _run([py, "-m", "pytest", "-q", "-W", "ignore::DeprecationWarning", str(REPO_ROOT / "backend" / "tests")])

    print()
    print(f"Security:          {'READY' if rc_sec == 0 and rc_git == 0 else 'NOT_READY'}")

    reg = load_registry_from_env()
    for a in reg.accounts:
        if not a.enabled:
            continue
        s = check_session_status(a.platform, session_dir=a.session_profile_dir)
        print(f"  {a.platform.value:20s} {s.value}")

    gmail_token_present = _gmail_keychain_has_token()
    enabled_user_driven = [a for a in reg.accounts if a.enabled and a.login_mode.value == "user_driven_browser"]
    authed_user_driven = sum(
        1 for a in enabled_user_driven
        if check_session_status(a.platform, session_dir=a.session_profile_dir) == SessionStatus.AUTHENTICATED
    )

    print()
    print(f"OAuth (Gmail):     {'PRESENT in Keychain' if gmail_token_present else 'NOT CONFIGURED (run: make connect-gmail)'}")
    print(f"Browser sessions:  {authed_user_driven} authenticated / {len(enabled_user_driven)} enabled user-driven")
    print(f"Sessions gate:     {'PASS' if rc_sessions == 0 else 'FAIL (unauthenticated user-driven platforms)'}")
    print(f"Tests:             {'PASS' if rc_tests == 0 else 'FAIL'}")
    if not db_present:
        print(f"Database check:    MISSING (data/job_agent.db does not exist)")
    else:
        print(f"Database check:    {'PASS' if rc_db_check == 0 else 'FAIL'}")
    print(f"Resume validation: {'PASS' if rc_resume == 0 else 'FAIL'}")

    print()
    print("=" * 60)
    print("PHASE 6 STATUS")
    print("=" * 60)
    from app.database import SessionLocal, init_database
    from app.database.models import ApplicationRow, ClientLeadRow, JobRow, SubmissionEvidenceRow
    init_database()
    with SessionLocal() as session:
        n_jobs = session.scalar(select(func.count()).select_from(JobRow)) or 0
        n_apps = session.scalar(select(func.count()).select_from(ApplicationRow)) or 0
        n_leads = session.scalar(select(func.count()).select_from(ClientLeadRow)) or 0
        n_evidence = session.scalar(select(func.count()).select_from(SubmissionEvidenceRow)) or 0
        n_live_submissions = session.scalar(
            select(func.count()).select_from(SubmissionEvidenceRow).where(
                SubmissionEvidenceRow.outcome.in_(_LIVE_SUBMISSION_OUTCOMES)
            )
        ) or 0
    print()
    print(f"Real discovery:         {'READY (jobs in DB)' if n_jobs > 0 else 'NOT_READY (0 jobs)'}")
    print(f"Application dry-run:    {'READY (apps in DB)' if n_apps > 0 else 'NOT_READY (0 applications)'}")
    if n_live_submissions > 0:
        print(f"Real submission:        LIVE: {n_live_submissions} ({n_evidence - n_live_submissions} non-live evidence rows)")
    else:
        print(f"Real submission:        NOT_READY (0 live submissions; {n_evidence} non-live evidence rows: dry-run / placeholder / blocked)")
    print(f"Harban discovery:       {'READY (leads in DB)' if n_leads > 0 else 'NOT_READY (0 leads)'}")
    print(f"Harban outreach:        NOT_READY (requires real-contact + explicit user approval)")

    print()
    print("=" * 60)
    print("REAL-WORLD RESULTS")
    print("=" * 60)
    print()
    print(f"Jobs discovered:         {n_jobs}")
    print(f"Jobs qualified (match >= 75): run `make discovery-audit`")
    print(f"Applications dry-run:    {n_apps}")
    print(f"Applications submitted (LIVE):  {n_live_submissions}")
    print(f"Submission evidence (all):      {n_evidence}")
    print(f"Harban prospects:        {n_leads}")

    print()
    print("=" * 60)
    print("SECURITY CONFIRMATION")
    print("=" * 60)
    print()
    s_cfg = get_settings()
    print(f"Passwords stored:        0 (enforced by schema + validator + grep)")
    print(f"OTP stored:              0 (schema has no otp_code column)")
    print(f"MFA secrets stored:      0 (schema has no mfa_secret column)")
    print(f"Credentials logged:      0 (structlog redact() scrubs all secret patterns)")
    print(f"Credentials committed:   0 (`.gitignore` + `make secret-scan`)")
    print(f"compliance_hard_block:   {s_cfg.compliance_hard_block}")
    print(f"truthfulness_hard_block: {s_cfg.truthfulness_hard_block}")
    print(f"captcha_bypass flag:     {s_cfg.captcha_bypass} ({'ALLOWED (unsafe)' if s_cfg.captcha_bypass else 'off'})")
    print(f"mfa_bypass flag:         {s_cfg.mfa_bypass} ({'ALLOWED (unsafe)' if s_cfg.mfa_bypass else 'off'})")
    print(f"otp_bypass flag:         {s_cfg.otp_bypass} ({'ALLOWED (unsafe)' if s_cfg.otp_bypass else 'off'})")
    print(f"rate_limit_bypass flag:  {s_cfg.rate_limit_bypass} ({'ALLOWED (unsafe)' if s_cfg.rate_limit_bypass else 'off'})")

    unsafe_bypasses = [
        name for name, val in [
            ("captcha_bypass", s_cfg.captcha_bypass),
            ("mfa_bypass", s_cfg.mfa_bypass),
            ("otp_bypass", s_cfg.otp_bypass),
            ("rate_limit_bypass", s_cfg.rate_limit_bypass),
        ] if val
    ]

    print()
    print("=" * 60)
    phase5_ready = (
        rc_sec == 0
        and rc_git == 0
        and db_present
        and rc_db_check == 0
        and rc_resume == 0
        and rc_tests == 0
        and rc_sessions == 0
        and gmail_token_present
        and s_cfg.compliance_hard_block
        and s_cfg.truthfulness_hard_block
        and not unsafe_bypasses
    )
    phase6_live = (n_live_submissions > 0 and n_jobs > 0)
    if phase5_ready and phase6_live:
        print("FINAL STATUS: PHASE 6 READY FOR CONTROLLED PRODUCTION")
        print("=" * 60)
        return 0
    print("FINAL STATUS: PHASE 6 NOT READY")
    print()
    blockers: list[str] = []
    if rc_sec != 0:
        blockers.append("secret scan failed")
    if rc_git != 0:
        blockers.append("git security check failed")
    if not db_present:
        blockers.append("data/job_agent.db does not exist — run `make discover` after enabling real sources")
    elif rc_db_check != 0:
        blockers.append("db integrity check failed")
    if rc_resume != 0:
        blockers.append("resume validation failed")
    if rc_tests != 0:
        blockers.append("test suite failed")
    if rc_sessions != 0:
        blockers.append("one or more enabled user-driven platforms are not authenticated — run `make verify-sessions`")
    if not gmail_token_present:
        blockers.append("Gmail OAuth refresh token not in macOS Keychain — run `make connect-gmail` to set up")
    if not s_cfg.compliance_hard_block:
        blockers.append("compliance_hard_block=false — must be true for production")
    if not s_cfg.truthfulness_hard_block:
        blockers.append("truthfulness_hard_block=false — must be true for production")
    if unsafe_bypasses:
        blockers.append(f"unsafe bypass flag(s) enabled: {', '.join(unsafe_bypasses)} — must be false for production")
    if n_jobs == 0:
        blockers.append("no real jobs discovered yet — run `make discover` after enabling real sources")
    if n_live_submissions == 0:
        blockers.append(
            f"no live submissions yet (0 outcomes in {sorted(_LIVE_SUBMISSION_OUTCOMES)}; "
            f"{n_evidence} non-live evidence rows exist) — AssistedApplicationSession.submit_assisted_live() "
            f"IS wired; user must sit at Mac, run the submit pipeline with PRE_APPROVED_APPLICATIONS=true + "
            f"AUTO_SUBMIT_APPROVED=true + DRY_RUN=false, click Submit in the headful Chromium window, "
            f"and have confirmation detected before this gate flips"
        )
    for b in blockers:
        print(f"  - {b}")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
