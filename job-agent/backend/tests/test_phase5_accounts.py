from __future__ import annotations

from pathlib import Path

import pytest


class TestNoPasswordFields:
    def test_account_config_rejects_password_shaped_username(self):
        from app.accounts.enums import AccountPlatform, LoginMode
        from app.accounts.schema import AccountConfig
        with pytest.raises(ValueError, match="password"):
            AccountConfig(platform=AccountPlatform.LINKEDIN, username="mypassword123")
        with pytest.raises(ValueError, match="password"):
            AccountConfig(platform=AccountPlatform.LINKEDIN, username="secret_token")

    def test_account_config_accepts_identifier(self):
        from app.accounts.enums import AccountPlatform
        from app.accounts.schema import AccountConfig
        a = AccountConfig(platform=AccountPlatform.LINKEDIN, username="user@example.com")
        assert a.username == "user@example.com"

    def test_account_config_forbids_extra_fields_including_password(self):
        from app.accounts.enums import AccountPlatform
        from app.accounts.schema import AccountConfig
        extra = {"pwd": "test-fake-val"}
        with pytest.raises(Exception):
            AccountConfig(platform=AccountPlatform.LINKEDIN, **extra)

    def test_env_example_contains_no_password_keys(self):
        env_example = Path(__file__).resolve().parents[2] / ".env.example"
        text = env_example.read_text()
        for forbidden in ("LINKEDIN_PASSWORD", "NAUKRI_PASSWORD", "INDEED_PASSWORD", "GMAIL_PASSWORD",
                          "HANDSHAKE_PASSWORD", "OUTLIER_PASSWORD", "HARBAN_PASSWORD"):
            assert forbidden not in text, f"found forbidden env key: {forbidden}"

    def test_env_production_example_contains_no_password_keys(self):
        env_prod = Path(__file__).resolve().parents[2] / ".env.production.example"
        text = env_prod.read_text()
        for forbidden in ("LINKEDIN_PASSWORD", "NAUKRI_PASSWORD", "INDEED_PASSWORD", "GMAIL_PASSWORD"):
            assert forbidden not in text


class TestAccountRegistry:
    def test_registry_loads_from_env_with_no_passwords(self, monkeypatch):
        monkeypatch.setenv("LINKEDIN_EMAIL", "someone@example.com")
        monkeypatch.setenv("LINKEDIN_PROFILE_URL", "https://www.linkedin.com/in/someone/")
        monkeypatch.setenv("LINKEDIN_ENABLED", "true")
        from app.accounts import load_registry_from_env
        from app.accounts.enums import AccountPlatform, LoginMode
        reg = load_registry_from_env()
        linkedin = reg.by_platform(AccountPlatform.LINKEDIN)
        assert linkedin is not None
        assert linkedin.username == "someone@example.com"
        assert linkedin.enabled is True
        assert linkedin.login_mode == LoginMode.USER_DRIVEN_BROWSER

    def test_registry_default_purposes(self):
        from app.accounts.enums import AccountPlatform, AccountPurpose, default_purposes_for
        assert AccountPurpose.CAREER_DISCOVERY in default_purposes_for(AccountPlatform.LINKEDIN)
        assert AccountPurpose.RECRUITER_OUTREACH in default_purposes_for(AccountPlatform.LINKEDIN)
        assert AccountPurpose.EMAIL_APPLICATIONS in default_purposes_for(AccountPlatform.GMAIL)
        assert AccountPurpose.HARBAN_B2B_OUTREACH in default_purposes_for(AccountPlatform.HARBAN_BUSINESS)

    def test_oauth_mode_for_gmail(self):
        from app.accounts.enums import AccountPlatform, LoginMode, default_login_mode_for
        assert default_login_mode_for(AccountPlatform.GMAIL) == LoginMode.OAUTH
        assert default_login_mode_for(AccountPlatform.MICROSOFT_365) == LoginMode.OAUTH

    def test_user_driven_browser_mode_for_linkedin(self):
        from app.accounts.enums import AccountPlatform, LoginMode, default_login_mode_for
        assert default_login_mode_for(AccountPlatform.LINKEDIN) == LoginMode.USER_DRIVEN_BROWSER
        assert default_login_mode_for(AccountPlatform.NAUKRI) == LoginMode.USER_DRIVEN_BROWSER
        assert default_login_mode_for(AccountPlatform.INDEED) == LoginMode.USER_DRIVEN_BROWSER

    def test_public_page_only_for_remote_boards(self):
        from app.accounts.enums import AccountPlatform, LoginMode, default_login_mode_for
        assert default_login_mode_for(AccountPlatform.REMOTEOK) == LoginMode.PUBLIC_PAGE_ONLY
        assert default_login_mode_for(AccountPlatform.WEWORKREMOTELY) == LoginMode.PUBLIC_PAGE_ONLY


class TestSessionStatus:
    def test_session_status_values(self):
        from app.accounts.enums import SessionStatus
        for required in ("NOT_CONFIGURED", "LOGIN_REQUIRED", "AUTHENTICATED", "SESSION_EXPIRED",
                         "MFA_REQUIRED", "CAPTCHA_REQUIRED", "PLATFORM_BLOCKED", "OAUTH_CONNECTED",
                         "OAUTH_EXPIRED", "ERROR"):
            assert hasattr(SessionStatus, required)

    def test_check_session_without_profile_returns_login_required(self, tmp_path):
        from app.accounts.enums import AccountPlatform, SessionStatus
        from app.accounts.login import check_session_status
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        status = check_session_status(AccountPlatform.LINKEDIN, session_dir=empty_dir)
        assert status in {SessionStatus.LOGIN_REQUIRED, SessionStatus.NOT_CONFIGURED}


class TestLoginFlow:
    def test_interactive_login_without_playwright_falls_back_gracefully(self, tmp_path, monkeypatch):
        from app.accounts.enums import AccountPlatform
        from app.accounts.login import interactive_login, is_playwright_available
        monkeypatch.setattr("app.accounts.login.is_playwright_available", lambda: False)
        result = interactive_login(AccountPlatform.LINKEDIN, session_dir=tmp_path / "linkedin")
        assert result.outcome in {"PLAYWRIGHT_NOT_INSTALLED", "OAUTH_FLOW_REQUIRED", "UNKNOWN_PLATFORM"}
        assert any("Playwright" in n or "password" in n.lower() or "oauth" in n.lower() for n in result.notes)

    def test_interactive_login_oauth_platform_does_not_prompt_for_password(self, tmp_path):
        from app.accounts.enums import AccountPlatform
        from app.accounts.login import interactive_login
        result = interactive_login(AccountPlatform.GMAIL, session_dir=tmp_path / "gmail")
        assert result.outcome == "OAUTH_FLOW_REQUIRED"
        assert any("oauth" in n.lower() for n in result.notes)
        assert all("password" not in n.lower() or "paste your password" in n.lower() for n in result.notes)


class TestAccountsCliCommand:
    def test_cli_accounts_arg_renders_table(self, profile, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from app.cli import run_cli
        rc = run_cli(["--accounts"])
        assert rc == 0


class TestNoPasswordColumnsInDb:
    def test_schema_has_no_password_columns(self):
        from app.database.engine import Base
        for table in Base.metadata.tables.values():
            for col in table.columns:
                name = col.name.lower()
                for forbidden in ("password", "passwd", "pwd", "mfa_secret", "otp_code"):
                    assert forbidden not in name, f"forbidden column: {table.name}.{col.name}"


class TestGitignoreCoversBrowserProfiles:
    def test_gitignore_covers_browser_profiles(self):
        gi = (Path(__file__).resolve().parents[2] / ".gitignore").read_text()
        assert "browser/profiles/" in gi
        assert "*.pem" in gi or "secrets/" in gi or ".env" in gi
