from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.accounts.enums import AccountPlatform, SessionStatus
from app.accounts.registry import load_registry_from_env
from app.accounts.schema import AccountConfig
from app.observability import get_logger

log = get_logger("accounts.login")


_PLATFORM_LOGIN_URLS: dict[AccountPlatform, str] = {
    AccountPlatform.LINKEDIN: "https://www.linkedin.com/login",
    AccountPlatform.NAUKRI: "https://www.naukri.com/nlogin/login",
    AccountPlatform.INDEED: "https://secure.indeed.com/account/login",
    AccountPlatform.GLASSDOOR: "https://www.glassdoor.com/profile/login_input.htm",
    AccountPlatform.WELLFOUND: "https://wellfound.com/login",
    AccountPlatform.HANDSHAKE: "https://joinhandshake.com/login",
    AccountPlatform.CUTSHORT: "https://cutshort.io/login",
    AccountPlatform.INSTAHYRE: "https://www.instahyre.com/login",
    AccountPlatform.HIRIST: "https://www.hirist.tech/login",
    AccountPlatform.FOUNDIT: "https://www.foundit.in/seeker/login",
    AccountPlatform.INTERNSHALA: "https://internshala.com/login",
    AccountPlatform.OUTLIER: "https://app.outlier.ai/en/login",
    AccountPlatform.SURGE_AI: "https://app.surgehq.ai/login",
    AccountPlatform.TELUS_DIGITAL_AI: "https://www.telusinternational.com/login",
}


_SUCCESS_INDICATORS: dict[AccountPlatform, tuple[str, ...]] = {
    AccountPlatform.LINKEDIN: ("/feed", "/mynetwork", "/jobs"),
    AccountPlatform.NAUKRI: ("/mnjuser/", "/dashboard"),
    AccountPlatform.INDEED: ("/account", "/profile"),
    AccountPlatform.WELLFOUND: ("/jobs", "/me"),
    AccountPlatform.HANDSHAKE: ("/stu/dashboard", "/discover"),
}


@dataclass
class LoginSessionResult:
    platform: AccountPlatform
    outcome: str
    session_dir: Path
    url_visited: str | None = None
    indicator_seen: str | None = None
    notes: list[str] = None

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def login_url_for(platform: AccountPlatform) -> str:
    return _PLATFORM_LOGIN_URLS.get(platform, f"https://{platform.value}.com/")


def is_playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def interactive_login(
    platform: AccountPlatform,
    session_dir: Path | None = None,
    *,
    wait_seconds: int = 180,
    on_prompt: Callable[[str], None] = print,
) -> LoginSessionResult:
    reg = load_registry_from_env()
    account = reg.by_platform(platform)
    if account is None:
        return LoginSessionResult(
            platform=platform,
            outcome="UNKNOWN_PLATFORM",
            session_dir=session_dir or Path("./browser/profiles") / platform.value,
            notes=[f"platform {platform.value} not registered in AccountRegistry"],
        )

    if account.login_mode.value == "oauth":
        return LoginSessionResult(
            platform=platform,
            outcome="OAUTH_FLOW_REQUIRED",
            session_dir=session_dir or Path("./browser/profiles") / platform.value,
            notes=[
                f"{platform.value} uses OAuth. Register a Google OAuth client at "
                "https://console.cloud.google.com/apis/credentials and run `make gmail-oauth-setup` "
                "(Phase 5b patch) — do NOT paste your password here."
            ],
        )

    target_dir = session_dir or (account.session_profile_dir or Path("./browser/profiles") / platform.value)
    _ensure_dir(target_dir)
    url = login_url_for(platform)

    if not is_playwright_available():
        return LoginSessionResult(
            platform=platform,
            outcome="PLAYWRIGHT_NOT_INSTALLED",
            session_dir=target_dir,
            url_visited=url,
            notes=[
                "Playwright is not installed. Install with `pip install playwright && playwright install chromium`.",
                f"Alternative: open {url} manually in your regular Chrome, sign in there, and the system will route "
                "through 'Discovery + User-Assisted Application' mode using your real browser.",
                f"The expected session profile directory is: {target_dir}",
                "The bot will NEVER capture, read, or store your password.",
            ],
        )

    try:
        from playwright.sync_api import sync_playwright

        on_prompt(
            f"\n==== {platform.value.upper()} LOGIN ====\n"
            f"A Chromium window will open and navigate to:\n  {url}\n\n"
            f"Please:\n"
            f"  1. Sign in with YOUR credentials (password manager autofill is fine)\n"
            f"  2. Complete MFA / OTP if prompted\n"
            f"  3. Solve any CAPTCHA\n"
            f"  4. Reach your logged-in home / dashboard\n"
            f"  5. Close the window\n\n"
            f"The browser session (cookies, localStorage) will be saved to:\n  {target_dir}\n\n"
            f"The bot does NOT see or store your password at any step.\n"
        )

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(target_dir),
                headless=False,
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(url)
            try:
                page.wait_for_event("close", timeout=wait_seconds * 1000)
            except Exception:
                pass
            final_url = page.url if not page.is_closed() else url
            ctx.close()

        indicator = None
        for marker in _SUCCESS_INDICATORS.get(platform, ()):
            if marker in final_url:
                indicator = marker
                break

        outcome = "AUTHENTICATED" if indicator else "SESSION_SAVED_UNVERIFIED"
        return LoginSessionResult(
            platform=platform,
            outcome=outcome,
            session_dir=target_dir,
            url_visited=final_url,
            indicator_seen=indicator,
            notes=[
                f"session saved to {target_dir}",
                f"logged-in indicator detected: {indicator}" if indicator else "no success URL marker detected — re-run session health check next time you use the platform",
            ],
        )
    except Exception as e:
        log.warning("accounts.login_error", platform=platform.value, error=str(e))
        return LoginSessionResult(
            platform=platform,
            outcome="ERROR",
            session_dir=target_dir,
            url_visited=url,
            notes=[f"login error: {e}"],
        )


def check_session_status(platform: AccountPlatform, session_dir: Path | None = None) -> SessionStatus:
    reg = load_registry_from_env()
    account = reg.by_platform(platform)
    if account is None:
        return SessionStatus.NOT_CONFIGURED
    if account.login_mode.value == "public_page_only":
        return SessionStatus.AUTHENTICATED
    if account.login_mode.value == "oauth":
        from app.accounts.registry import _oauth_status_from_keychain
        return _oauth_status_from_keychain(platform)
    target = session_dir or account.session_profile_dir
    if target is None or not target.exists() or not any(target.iterdir()):
        return SessionStatus.LOGIN_REQUIRED

    cookie_file = target / "Default" / "Cookies"
    if not cookie_file.exists():
        cookie_file = target / "Cookies"
    if cookie_file.exists():
        import time
        age_days = (time.time() - cookie_file.stat().st_mtime) / 86400
        if age_days > 30:
            return SessionStatus.SESSION_EXPIRED
        return SessionStatus.AUTHENTICATED
    return SessionStatus.LOGIN_REQUIRED
