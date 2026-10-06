from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.accounts.enums import AccountPlatform  # noqa: E402


_CAPABILITIES: dict[AccountPlatform, dict[str, str]] = {
    AccountPlatform.LINKEDIN: {
        "discovery":   "STUB_USER_ASSISTED",
        "login":       "USER_DRIVEN_BROWSER",
        "application": "ASSISTED_ONLY",
        "outreach":    "USER_ASSISTED",
    },
    AccountPlatform.NAUKRI: {
        "discovery":   "STUB_USER_ASSISTED",
        "login":       "USER_DRIVEN_BROWSER",
        "application": "ASSISTED_ONLY",
        "outreach":    "USER_ASSISTED",
    },
    AccountPlatform.INDEED: {
        "discovery":   "STUB_USER_ASSISTED",
        "login":       "USER_DRIVEN_BROWSER",
        "application": "ASSISTED_ONLY",
        "outreach":    "USER_ASSISTED",
    },
    AccountPlatform.GLASSDOOR: {
        "discovery":   "STUB_USER_ASSISTED",
        "login":       "USER_DRIVEN_BROWSER",
        "application": "ASSISTED_ONLY",
        "outreach":    "NONE",
    },
    AccountPlatform.WELLFOUND: {
        "discovery":   "STUB_USER_ASSISTED",
        "login":       "USER_DRIVEN_BROWSER",
        "application": "ASSISTED_ONLY",
        "outreach":    "NONE",
    },
    AccountPlatform.HANDSHAKE: {
        "discovery":   "STUB_USER_ASSISTED",
        "login":       "USER_DRIVEN_BROWSER",
        "application": "ASSISTED_ONLY",
        "outreach":    "NONE",
    },
    AccountPlatform.CUTSHORT: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.INSTAHYRE: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.HIRIST: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.FOUNDIT: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.INTERNSHALA: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.REMOTEOK: {"discovery": "REAL_PUBLIC_API", "login": "PUBLIC_PAGE_ONLY", "application": "LINK_OUT", "outreach": "NONE"},
    AccountPlatform.WEWORKREMOTELY: {"discovery": "REAL_RSS", "login": "PUBLIC_PAGE_ONLY", "application": "LINK_OUT", "outreach": "NONE"},
    AccountPlatform.OUTLIER: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.SURGE_AI: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.TELUS_DIGITAL_AI: {"discovery": "STUB_USER_ASSISTED", "login": "USER_DRIVEN_BROWSER", "application": "ASSISTED_ONLY", "outreach": "NONE"},
    AccountPlatform.GMAIL: {"discovery": "N/A", "login": "OAUTH", "application": "N/A", "outreach": "DRAFT_ONLY_PENDING_OAUTH"},
    AccountPlatform.MICROSOFT_365: {"discovery": "N/A", "login": "OAUTH", "application": "N/A", "outreach": "DRAFT_ONLY_PENDING_OAUTH"},
    AccountPlatform.HARBAN_BUSINESS: {"discovery": "N/A", "login": "USER_DRIVEN_BROWSER", "application": "N/A", "outreach": "DRAFT_ONLY_REQUIRES_REAL_CONTACT"},
    AccountPlatform.COMPANY_CAREERS: {
        "discovery":   "REAL_GREENHOUSE_LEVER_ASHBY",
        "login":       "PUBLIC_PAGE_ONLY",
        "application": "LINK_OUT",
        "outreach":    "NONE",
    },
}

_LEGEND = {
    "REAL_GREENHOUSE_LEVER_ASHBY": "Live JSON API against Greenhouse / Lever / Ashby boards. Works today.",
    "REAL_PUBLIC_API":            "Live public JSON API. Works today (subject to robots.txt).",
    "REAL_RSS":                   "Live public RSS feed. Works today.",
    "STUB_USER_ASSISTED":         "Code path is a STUB that emits an informative error on `discover()`. Discovery for this platform requires user-driven browser work.",
    "USER_DRIVEN_BROWSER":        "User signs in themselves via `make login-<platform>` in a Playwright-opened Chromium window. No password stored.",
    "PUBLIC_PAGE_ONLY":           "No sign-in needed; public pages or feeds only.",
    "OAUTH":                      "Google / Microsoft OAuth; refresh token in macOS Keychain. Phase 5b requires user to register OAuth client.",
    "ASSISTED_ONLY":              "Application happens in the user's authenticated browser; bot opens the job page and prepares answers.",
    "LINK_OUT":                   "Discovery emits a URL; application is a redirect to the company's own ATS.",
    "DRAFT_ONLY_PENDING_OAUTH":   "Draft `.eml` is generated to data/email_drafts/. Actual send transport requires Phase 5b OAuth setup via `make connect-gmail`.",
    "DRAFT_ONLY_REQUIRES_REAL_CONTACT": "Outreach draft is generated with `{{recipient_first_name}}` placeholder and status BLOCKED_REQUIRES_REAL_CONTACT until the user supplies a verified public contact.",
    "USER_ASSISTED":              "Draft message prepared; user sends through their authenticated LinkedIn.",
    "NONE":                       "Not implemented for this platform.",
    "N/A":                        "Not applicable to this platform.",
}


def main() -> int:
    print("=== Platform capability matrix ===")
    print()
    header = f"{'Platform':20s} {'Discovery':30s} {'Login':24s} {'Application':30s} {'Outreach':30s}"
    print(header)
    print("-" * len(header))
    for platform, caps in _CAPABILITIES.items():
        print(f"{platform.value:20s} {caps['discovery']:30s} {caps['login']:24s} {caps['application']:30s} {caps['outreach']:30s}")
    print()
    print("Legend:")
    for key, text in _LEGEND.items():
        print(f"  {key:40s} {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
