from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.accounts.enums import AccountPlatform, AccountPurpose, LoginMode, SessionStatus


_FORBIDDEN_PASSWORD_FIELDS = {"password", "passwd", "pwd", "secret", "credential"}


class AccountConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    platform: AccountPlatform
    username: str | None = None
    profile_url: str | None = None
    purposes: list[AccountPurpose] = Field(default_factory=list)
    login_mode: LoginMode = LoginMode.USER_DRIVEN_BROWSER
    session_status: SessionStatus = SessionStatus.NOT_CONFIGURED
    enabled: bool = False
    session_profile_dir: Path | None = None
    last_verified_at: datetime | None = None
    last_error: str | None = None
    notes: str | None = None

    @field_validator("username")
    @classmethod
    def _username_is_not_a_password(cls, v: str | None) -> str | None:
        if v is None:
            return None
        lv = v.lower()
        for forbidden in _FORBIDDEN_PASSWORD_FIELDS:
            if forbidden in lv and len(v) < 60:
                raise ValueError(
                    f"username field looks like it might be a password or secret ('{forbidden}' substring). "
                    "Usernames go here; passwords NEVER do."
                )
        return v

    def is_identifier_safe(self) -> bool:
        if not self.username:
            return True
        if "@" in self.username or self.username.startswith("http"):
            return True
        return len(self.username) <= 80


class PlatformAccountsRegistry(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    accounts: list[AccountConfig] = Field(default_factory=list)

    def by_platform(self, platform: AccountPlatform) -> AccountConfig | None:
        for a in self.accounts:
            if a.platform == platform:
                return a
        return None

    def enabled_accounts(self) -> list[AccountConfig]:
        return [a for a in self.accounts if a.enabled]

    def accounts_for_purpose(self, purpose: AccountPurpose) -> list[AccountConfig]:
        return [a for a in self.accounts if purpose in a.purposes]

    def summary_rows(self) -> list[dict]:
        return [
            {
                "platform": a.platform.value,
                "username": a.username or "—",
                "purposes": ", ".join(p.value for p in a.purposes) or "—",
                "login_mode": a.login_mode.value,
                "session_status": a.session_status.value,
                "enabled": a.enabled,
                "last_verified_at": a.last_verified_at.isoformat() if a.last_verified_at else "—",
            }
            for a in self.accounts
        ]
