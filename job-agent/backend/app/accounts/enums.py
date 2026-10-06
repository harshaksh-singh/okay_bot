from __future__ import annotations

from enum import Enum


class AccountPlatform(str, Enum):
    LINKEDIN = "linkedin"
    NAUKRI = "naukri"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    WELLFOUND = "wellfound"
    HANDSHAKE = "handshake"
    CUTSHORT = "cutshort"
    INSTAHYRE = "instahyre"
    HIRIST = "hirist"
    FOUNDIT = "foundit"
    INTERNSHALA = "internshala"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"
    OUTLIER = "outlier"
    SURGE_AI = "surge_ai"
    TELUS_DIGITAL_AI = "telus_digital_ai"
    GMAIL = "gmail"
    MICROSOFT_365 = "microsoft_365"
    HARBAN_BUSINESS = "harban_business"
    COMPANY_CAREERS = "company_careers"


class AccountPurpose(str, Enum):
    CAREER_DISCOVERY = "career_discovery"
    CAREER_APPLICATION = "career_application"
    RECRUITER_OUTREACH = "recruiter_outreach"
    EMAIL_APPLICATIONS = "email_applications"
    EMAIL_RECRUITER = "email_recruiter"
    HARBAN_B2B_OUTREACH = "harban_b2b_outreach"
    HARBAN_B2B_EMAIL = "harban_b2b_email"
    REFERENCE_ONLY = "reference_only"


class LoginMode(str, Enum):
    USER_DRIVEN_BROWSER = "user_driven_browser"
    OAUTH = "oauth"
    PUBLIC_PAGE_ONLY = "public_page_only"
    MANUAL_ASSISTED = "manual_assisted"


class SessionStatus(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    AUTHENTICATED = "AUTHENTICATED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    MFA_REQUIRED = "MFA_REQUIRED"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    PLATFORM_BLOCKED = "PLATFORM_BLOCKED"
    OAUTH_CONNECTED = "OAUTH_CONNECTED"
    OAUTH_EXPIRED = "OAUTH_EXPIRED"
    ERROR = "ERROR"


_DEFAULT_PLATFORM_PURPOSES: dict[AccountPlatform, tuple[AccountPurpose, ...]] = {
    AccountPlatform.LINKEDIN: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.RECRUITER_OUTREACH),
    AccountPlatform.NAUKRI: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.CAREER_APPLICATION),
    AccountPlatform.INDEED: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.CAREER_APPLICATION),
    AccountPlatform.GLASSDOOR: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.WELLFOUND: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.CAREER_APPLICATION),
    AccountPlatform.HANDSHAKE: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.CAREER_APPLICATION),
    AccountPlatform.CUTSHORT: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.CAREER_APPLICATION),
    AccountPlatform.INSTAHYRE: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.HIRIST: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.FOUNDIT: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.INTERNSHALA: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.REMOTEOK: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.WEWORKREMOTELY: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.OUTLIER: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.CAREER_APPLICATION),
    AccountPlatform.SURGE_AI: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.TELUS_DIGITAL_AI: (AccountPurpose.CAREER_DISCOVERY,),
    AccountPlatform.GMAIL: (AccountPurpose.EMAIL_APPLICATIONS, AccountPurpose.EMAIL_RECRUITER),
    AccountPlatform.MICROSOFT_365: (AccountPurpose.EMAIL_APPLICATIONS, AccountPurpose.EMAIL_RECRUITER),
    AccountPlatform.HARBAN_BUSINESS: (AccountPurpose.HARBAN_B2B_OUTREACH, AccountPurpose.HARBAN_B2B_EMAIL),
    AccountPlatform.COMPANY_CAREERS: (AccountPurpose.CAREER_DISCOVERY, AccountPurpose.CAREER_APPLICATION),
}


def default_purposes_for(platform: AccountPlatform) -> tuple[AccountPurpose, ...]:
    return _DEFAULT_PLATFORM_PURPOSES.get(platform, (AccountPurpose.REFERENCE_ONLY,))


_DEFAULT_LOGIN_MODE: dict[AccountPlatform, LoginMode] = {
    AccountPlatform.GMAIL: LoginMode.OAUTH,
    AccountPlatform.MICROSOFT_365: LoginMode.OAUTH,
    AccountPlatform.REMOTEOK: LoginMode.PUBLIC_PAGE_ONLY,
    AccountPlatform.WEWORKREMOTELY: LoginMode.PUBLIC_PAGE_ONLY,
    AccountPlatform.COMPANY_CAREERS: LoginMode.PUBLIC_PAGE_ONLY,
}


def default_login_mode_for(platform: AccountPlatform) -> LoginMode:
    return _DEFAULT_LOGIN_MODE.get(platform, LoginMode.USER_DRIVEN_BROWSER)
