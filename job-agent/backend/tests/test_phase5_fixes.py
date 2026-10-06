from __future__ import annotations

import time
from pathlib import Path

import pytest


class TestSessionStatusDetection:
    def test_authenticated_when_cookie_file_recent(self, tmp_path):
        from app.accounts.enums import AccountPlatform, SessionStatus
        from app.accounts.login import check_session_status

        profile = tmp_path / "linkedin"
        default = profile / "Default"
        default.mkdir(parents=True)
        cookies = default / "Cookies"
        cookies.write_bytes(b"stub")

        status = check_session_status(AccountPlatform.LINKEDIN, session_dir=profile)
        assert status == SessionStatus.AUTHENTICATED

    def test_session_expired_when_cookie_file_old(self, tmp_path):
        from app.accounts.enums import AccountPlatform, SessionStatus
        from app.accounts.login import check_session_status

        profile = tmp_path / "linkedin"
        default = profile / "Default"
        default.mkdir(parents=True)
        cookies = default / "Cookies"
        cookies.write_bytes(b"stub")
        old = time.time() - (40 * 86400)
        import os
        os.utime(cookies, (old, old))

        status = check_session_status(AccountPlatform.LINKEDIN, session_dir=profile)
        assert status == SessionStatus.SESSION_EXPIRED

    def test_login_required_when_no_cookie_file(self, tmp_path):
        from app.accounts.enums import AccountPlatform, SessionStatus
        from app.accounts.login import check_session_status
        profile = tmp_path / "linkedin"
        profile.mkdir()
        (profile / "placeholder").touch()
        status = check_session_status(AccountPlatform.LINKEDIN, session_dir=profile)
        assert status == SessionStatus.LOGIN_REQUIRED

    def test_oauth_platform_returns_keychain_backed_status(self, tmp_path):
        from app.accounts.enums import AccountPlatform, SessionStatus
        from app.accounts.login import check_session_status
        status = check_session_status(AccountPlatform.GMAIL, session_dir=tmp_path / "gmail")
        assert status in (SessionStatus.NOT_CONFIGURED, SessionStatus.OAUTH_CONNECTED), (
            f"OAuth status must be NOT_CONFIGURED (no token in Keychain) or "
            f"OAUTH_CONNECTED (token present); got {status}"
        )

    def test_public_page_platform_returns_authenticated(self, tmp_path):
        from app.accounts.enums import AccountPlatform, SessionStatus
        from app.accounts.login import check_session_status
        status = check_session_status(AccountPlatform.REMOTEOK, session_dir=tmp_path / "r")
        assert status == SessionStatus.AUTHENTICATED


class TestGitignoreBriefCompliance:
    def test_gitignore_covers_brief_section_19(self):
        gi = (Path(__file__).resolve().parents[2] / ".gitignore").read_text()
        for required in [".env", ".env.*", "browser/", "browser/profiles/", "browser/sessions/", "cookies/", "secrets/", "*.sqlite", "*.db", "*.pem", "*.key", "*.p12"]:
            assert required in gi, f"missing from .gitignore: {required}"


class TestSecurityMdExists:
    def test_security_md_exists_with_incident_guidance(self):
        p = Path(__file__).resolve().parents[2] / "SECURITY.md"
        assert p.exists()
        text = p.read_text()
        for required_phrase in ["change the password", "2-Step Verification", "incident response", "password manager", "No passwords"]:
            assert required_phrase.lower() in text.lower(), f"SECURITY.md missing phrase: {required_phrase}"
