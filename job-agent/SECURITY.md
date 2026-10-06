# SECURITY

## No passwords. Ever.

The job-agent system is **password-less by design**. No part of the code, database, env file, log, test fixture, or chat transcript ever accepts or stores a platform password (LinkedIn, Naukri, Indeed, Gmail, Glassdoor, Wellfound, Handshake, Outlier, or any other).

### Why the architecture is password-less

Password-based automation of consumer job platforms violates each platform's Terms of Service AND their anti-abuse detection. A single automated sign-in from an unfamiliar IP typically triggers one of:

- immediate account lockout
- forced password reset
- CAPTCHA challenge on every subsequent session
- indefinite shadow-ban of the account
- deletion of saved jobs, applications, and connections

Any of those directly damages the user's real job search — the opposite of what this system exists to do.

### The correct architecture (what this system actually uses)

| What | Where it lives | Who controls it |
|---|---|---|
| `LINKEDIN_EMAIL=you@example.com` | `.env` (identifier, not a secret) | you edit the file |
| `LINKEDIN_PROFILE_URL=https://.../in/you/` | `.env` | you edit the file |
| **LinkedIn session cookies** | `./browser/profiles/linkedin/` (Chromium persistent profile) | your real Chrome stores them, bot reuses them |
| **Your LinkedIn password** | **nowhere** — you type it into the real LinkedIn login page ONCE in a Playwright-opened window | nothing in this codebase ever sees it |
| Gmail OAuth refresh token | macOS Keychain via `keyring` library | Google can revoke anytime from your account page |

Flow for enabling a platform (e.g. LinkedIn):

```
1. Set LINKEDIN_ENABLED=true and LINKEDIN_EMAIL=you@example.com in .env.
2. Run `make login-linkedin`.
3. A real Chromium window opens at the real LinkedIn login page.
4. You sign in yourself (password manager autofill is fine).
5. You complete MFA / OTP / CAPTCHA yourself.
6. You close the window.
7. Playwright persists the session cookies to ./browser/profiles/linkedin/.
8. The bot reuses that logged-in session for discovery and assisted application.
```

No password ever flows through our code.

---

## If you accidentally shared a password in chat (incident response)

> **This system refuses to use a password even if you paste it in. But chat logs persist beyond our control.** If you ever typed a password (into this chat, a Slack DM, a GitHub issue, a bug report, an AI chat, or anywhere else that stores conversation history), the password is **functionally compromised** and must be rotated. The exposure doesn't come from this codebase; it comes from the chat/log infrastructure retaining the words you typed.

Do all three of these, in order, within the next 10 minutes:

### 1. Change the password on EVERY account that shares it

If you reuse passwords across accounts (very common, highly dangerous), rotate all of them. A password manager — **1Password, Bitwarden, Apple Passwords (built into iOS/macOS), or Google Password Manager** — makes this painless and generates a different strong password for each account:

- Gmail: https://myaccount.google.com/security
- LinkedIn: https://www.linkedin.com/mypreferences/d/change-password
- Naukri: https://www.naukri.com/manage-account (change-password)
- Indeed: https://secure.indeed.com/account/edit
- Glassdoor: https://www.glassdoor.com/profile/account_input.htm
- Wellfound: https://wellfound.com/settings
- Microsoft: https://account.microsoft.com/security

### 2. Enable 2-Step Verification (2FA) on every email and recruiting account

Especially the Gmail accounts you use for job applications and Harban business. 2FA means a stolen password alone cannot log in — the attacker also needs your phone / authenticator app. Use an authenticator app (Google Authenticator, Authy, 1Password, Apple Passwords) rather than SMS where offered.

- Gmail 2SV: https://myaccount.google.com/signinoptions/two-step-verification
- LinkedIn 2SV: https://www.linkedin.com/psettings/two-step-verification
- Naukri (search for "2FA" / "two-factor" in Security settings)
- Microsoft 2SV: https://account.microsoft.com/security

### 3. Review recent sign-in activity

Within 24 hours of any password exposure, review the "recent sign-in activity" or "where you're logged in" page of each account. Sign out all sessions you don't recognize.

- Gmail: https://myaccount.google.com/device-activity → "Sign out" everything you don't recognize
- LinkedIn: https://www.linkedin.com/psettings/sessions
- Naukri: Settings → Account Security → Active Sessions

### Longer term

- **Use a password manager.** The single highest-ROI change you can make. One strong master password + unique generated passwords for every site.
- **Never paste a password into any chat, AI chat, GitHub issue, Slack DM, email, or support ticket.** If a service representative asks for your password, they are either phishing you or violating their own security policy — treat it as a scam.
- **If a tool legitimately needs account access**, it should use OAuth (Google, Microsoft, GitHub) or an API token with scoped permissions — never your password.

---

## What this codebase does NOT do (brief §21)

- No password login automation
- No credential guessing
- No credential rotation on your behalf
- No OTP interception
- No MFA bypass
- No CAPTCHA bypass
- No anti-bot bypass
- No session theft
- No cookie extraction from unrelated browsers
- No scraping of logged-in LinkedIn / Naukri / Indeed (ToS violation)

Any pull request that adds any of the above will be rejected.

---

## Reporting a security issue

If you discover a security flaw in this codebase — e.g. a code path that could cause a secret to be logged, a column that could leak session data, a test fixture that accidentally commits a real credential — please:

1. **Do not open a public GitHub issue** that includes the exploit details.
2. Email the maintainer directly with a minimal reproduction.
3. Rotate any credential that could have been exposed by the flaw as a precaution.

Thank you for taking security seriously. The whole point of this project is to help you find a job without jeopardising the accounts you need to do it.
