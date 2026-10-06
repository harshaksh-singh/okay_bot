from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from app.accounts.enums import (
    AccountPlatform,
    AccountPurpose,
    LoginMode,
    SessionStatus,
    default_login_mode_for,
    default_purposes_for,
)
from app.accounts.schema import AccountConfig, PlatformAccountsRegistry
from app.config import get_settings


_PLATFORM_ENV_KEYS: dict[AccountPlatform, tuple[str, str, str]] = {
    AccountPlatform.LINKEDIN: ("LINKEDIN_ENABLED", "LINKEDIN_EMAIL", "LINKEDIN_PROFILE_URL"),
    AccountPlatform.NAUKRI: ("NAUKRI_ENABLED", "NAUKRI_EMAIL", "NAUKRI_PROFILE_URL"),
    AccountPlatform.INDEED: ("INDEED_ENABLED", "INDEED_EMAIL", "INDEED_PROFILE_URL"),
    AccountPlatform.GLASSDOOR: ("GLASSDOOR_ENABLED", "GLASSDOOR_EMAIL", "GLASSDOOR_PROFILE_URL"),
    AccountPlatform.WELLFOUND: ("WELLFOUND_ENABLED", "WELLFOUND_EMAIL", "WELLFOUND_PROFILE_URL"),
    AccountPlatform.HANDSHAKE: ("HANDSHAKE_ENABLED", "HANDSHAKE_EMAIL", "HANDSHAKE_PROFILE_URL"),
    AccountPlatform.CUTSHORT: ("CUTSHORT_ENABLED", "CUTSHORT_EMAIL", "CUTSHORT_PROFILE_URL"),
    AccountPlatform.INSTAHYRE: ("INSTAHYRE_ENABLED", "INSTAHYRE_EMAIL", "INSTAHYRE_PROFILE_URL"),
    AccountPlatform.HIRIST: ("HIRIST_ENABLED", "HIRIST_EMAIL", "HIRIST_PROFILE_URL"),
    AccountPlatform.FOUNDIT: ("FOUNDIT_ENABLED", "FOUNDIT_EMAIL", "FOUNDIT_PROFILE_URL"),
    AccountPlatform.INTERNSHALA: ("INTERNSHALA_ENABLED", "INTERNSHALA_EMAIL", "INTERNSHALA_PROFILE_URL"),
    AccountPlatform.REMOTEOK: ("REMOTEOK_ENABLED", "REMOTEOK_EMAIL", "REMOTEOK_PROFILE_URL"),
    AccountPlatform.WEWORKREMOTELY: ("WEWORKREMOTELY_ENABLED", "WEWORKREMOTELY_EMAIL", "WEWORKREMOTELY_PROFILE_URL"),
    AccountPlatform.OUTLIER: ("OUTLIER_ENABLED", "OUTLIER_EMAIL", "OUTLIER_PROFILE_URL"),
    AccountPlatform.SURGE_AI: ("SURGE_AI_ENABLED", "SURGE_AI_EMAIL", "SURGE_AI_PROFILE_URL"),
    AccountPlatform.TELUS_DIGITAL_AI: ("TELUS_DIGITAL_AI_ENABLED", "TELUS_DIGITAL_AI_EMAIL", "TELUS_DIGITAL_AI_PROFILE_URL"),
    AccountPlatform.GMAIL: ("GMAIL_ENABLED", "GMAIL_ACCOUNT", "GMAIL_PROFILE_URL"),
    AccountPlatform.MICROSOFT_365: ("M365_ENABLED", "M365_ACCOUNT", "M365_PROFILE_URL"),
    AccountPlatform.HARBAN_BUSINESS: ("HARBAN_ENABLED", "HARBAN_BUSINESS_EMAIL", "HARBAN_WEBSITE"),
    AccountPlatform.COMPANY_CAREERS: ("COMPANY_CAREERS_ENABLED", "", ""),
}


_REPO_ROOT = Path(__file__).resolve().parents[3]
_DOTENV_LOADED = False


def _ensure_dotenv_loaded() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    env_path = _REPO_ROOT / ".env"
    _DOTENV_LOADED = True
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        if k and k not in os.environ:
            os.environ[k] = v


def _env_true(key: str) -> bool:
    return (os.environ.get(key) or "").lower() in {"1", "true", "yes", "on"}


def _env_str(key: str) -> str | None:
    if not key:
        return None
    v = os.environ.get(key)
    return v or None


_OAUTH_KEYRING_SERVICE = "job-agent-oauth"
_OAUTH_KEYRING_USERS: dict[AccountPlatform, str] = {
    AccountPlatform.GMAIL: "gmail-refresh-token",
    AccountPlatform.MICROSOFT_365: "microsoft-365-refresh-token",
}


def _oauth_status_from_keychain(platform: AccountPlatform) -> SessionStatus:
    user = _OAUTH_KEYRING_USERS.get(platform)
    if not user:
        return SessionStatus.NOT_CONFIGURED
    try:
        import keyring
        tok = keyring.get_password(_OAUTH_KEYRING_SERVICE, user)
        return SessionStatus.OAUTH_CONNECTED if tok else SessionStatus.NOT_CONFIGURED
    except Exception:
        return SessionStatus.NOT_CONFIGURED


def load_registry_from_env(browser_root: Path | None = None) -> PlatformAccountsRegistry:
    _ensure_dotenv_loaded()
    s = get_settings()
    root = browser_root or (s.data_dir.parent / "browser" / "profiles")

    accounts: list[AccountConfig] = []
    for platform, (enabled_key, user_key, url_key) in _PLATFORM_ENV_KEYS.items():
        username = _env_str(user_key)
        profile_url = _env_str(url_key)
        login_mode = default_login_mode_for(platform)
        purposes = list(default_purposes_for(platform))
        session_profile_dir = root / platform.value if login_mode == LoginMode.USER_DRIVEN_BROWSER else None

        if session_profile_dir and session_profile_dir.exists() and any(session_profile_dir.iterdir()):
            session_status = SessionStatus.LOGIN_REQUIRED
        elif login_mode == LoginMode.OAUTH:
            session_status = _oauth_status_from_keychain(platform)
        elif login_mode == LoginMode.PUBLIC_PAGE_ONLY:
            session_status = SessionStatus.AUTHENTICATED
        else:
            session_status = SessionStatus.NOT_CONFIGURED

        explicitly_enabled = _env_true(enabled_key)
        implicitly_enabled = bool(username) or bool(profile_url) or session_status in (
            SessionStatus.AUTHENTICATED, SessionStatus.OAUTH_CONNECTED
        )
        enabled = explicitly_enabled or implicitly_enabled

        accounts.append(AccountConfig(
            platform=platform,
            username=username,
            profile_url=profile_url,
            purposes=purposes,
            login_mode=login_mode,
            session_status=session_status,
            enabled=enabled,
            session_profile_dir=session_profile_dir,
        ))

    return PlatformAccountsRegistry(accounts=accounts)


@lru_cache(maxsize=1)
def get_accounts_registry() -> PlatformAccountsRegistry:
    return load_registry_from_env()


def reset_accounts_registry_cache() -> None:
    get_accounts_registry.cache_clear()
