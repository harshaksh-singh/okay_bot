from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], label: str) -> tuple[bool, str]:
    try:
        out = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        passed = out.returncode == 0
        return passed, (out.stdout or "")[-400:] + ("\n" + (out.stderr or "")[-200:] if out.stderr else "")
    except Exception as e:
        return False, f"{label}: exception {e}"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    py = str(REPO_ROOT / ".venv" / "bin" / "python") if (REPO_ROOT / ".venv").exists() else "python3"

    ok, tail = _run([py, str(REPO_ROOT / "scripts" / "secret_scan.py")], "secret_scan")
    checks.append(("secrets", ok, tail))

    ok, tail = _run([py, str(REPO_ROOT / "scripts" / "git_security_check.py")], "git_security")
    checks.append(("git_security", ok, tail))

    if (REPO_ROOT / "data" / "job_agent.db").exists():
        ok, tail = _run([py, str(REPO_ROOT / "scripts" / "db_backup.py"), "check"], "db_check")
        checks.append(("db_integrity", ok, tail))
    else:
        checks.append(("db_integrity", True, "no DB file yet (will be created on first run)"))

    ok, tail = _run([py, str(REPO_ROOT / "scripts" / "resume_validator.py")], "resume_validator")
    checks.append(("resumes", ok, tail))

    ok, tail = _run(
        [py, "-m", "pytest", "-q", "-W", "ignore::DeprecationWarning", str(REPO_ROOT / "backend" / "tests")],
        "pytest",
    )
    checks.append(("tests", ok, tail))

    env_example = REPO_ROOT / ".env.production.example"
    env_live = REPO_ROOT / ".env"
    unsafe_defaults = []
    if env_live.exists():
        env_text = env_live.read_text()
        unsafe_lines = [
            "AUTO_SUBMIT=true",
            "AUTO_EMAIL=true",
            "AUTO_MESSAGE=true",
            "CAPTCHA_BYPASS=true",
            "MFA_BYPASS=true",
            "OTP_BYPASS=true",
            "RATE_LIMIT_BYPASS=true",
            "COMPLIANCE_HARD_BLOCK=false",
            "TRUTHFULNESS_HARD_BLOCK=false",
        ]
        for pat in unsafe_lines:
            if pat in env_text:
                unsafe_defaults.append(pat)
    env_ok = not unsafe_defaults and env_example.exists()
    checks.append(("env_safe_defaults", env_ok, f"unsafe in .env: {unsafe_defaults}" if unsafe_defaults else "safe"))

    print("=== Production readiness check ===")
    for name, ok, tail in checks:
        print(f"{'PASS' if ok else 'FAIL':6s}  {name}")
    print()
    overall_ok = all(ok for _, ok, _ in checks)
    print("Status: " + ("READY" if overall_ok else "NOT_READY"))
    if not overall_ok:
        print("\nFailing checks tail:")
        for name, ok, tail in checks:
            if not ok:
                print(f"\n-- {name} --")
                print(tail[-400:])
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
