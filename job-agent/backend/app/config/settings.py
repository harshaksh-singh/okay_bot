from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"


class ScoringWeights(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WEIGHT_", extra="ignore")

    technical_skills: float = Field(default=0.30, ge=0, le=1)
    experience: float = Field(default=0.20, ge=0, le=1)
    role_relevance: float = Field(default=0.15, ge=0, le=1)
    location: float = Field(default=0.10, ge=0, le=1)
    employment_type: float = Field(default=0.10, ge=0, le=1)
    schedule: float = Field(default=0.05, ge=0, le=1)
    company_priority: float = Field(default=0.05, ge=0, le=1)
    salary: float = Field(default=0.05, ge=0, le=1)

    def total(self) -> float:
        return (
            self.technical_skills
            + self.experience
            + self.role_relevance
            + self.location
            + self.employment_type
            + self.schedule
            + self.company_priority
            + self.salary
        )

    def normalized(self) -> dict[str, float]:
        t = self.total() or 1.0
        return {
            "technical_skills": self.technical_skills / t,
            "experience": self.experience / t,
            "role_relevance": self.role_relevance / t,
            "location": self.location / t,
            "employment_type": self.employment_type / t,
            "schedule": self.schedule / t,
            "company_priority": self.company_priority / t,
            "salary": self.salary / t,
        }


class ScoringThresholds(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCORE_",
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    apply_immediately: int = Field(default=95, ge=0, le=100)
    high_priority: int = Field(default=85, ge=0, le=100)
    apply: int = Field(default=75, ge=0, le=100)
    consider: int = Field(default=65, ge=0, le=100)
    low_priority: int = Field(default=50, ge=0, le=100)


_ENV_FILE = str(REPO_ROOT / ".env") if os.environ.get("APP_ENV", "").lower() != "test" else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    mock_mode: bool = Field(default=True)
    dry_run: bool = Field(default=True)
    user_approval_required: bool = Field(default=True)
    auto_submit: bool = Field(default=False)
    auto_email: bool = Field(default=False)
    auto_message: bool = Field(default=False)
    captcha_bypass: bool = Field(default=False)
    mfa_bypass: bool = Field(default=False)
    rate_limit_bypass: bool = Field(default=False)

    pre_approved_applications: bool = Field(default=False)
    auto_submit_approved: bool = Field(default=False)
    auto_email_approved: bool = Field(default=False)
    auto_message_approved: bool = Field(default=False)
    compliance_hard_block: bool = Field(default=True)
    truthfulness_hard_block: bool = Field(default=True)
    submission_enabled: bool = Field(default=False)

    auto_apply_match_threshold: int = Field(default=85, ge=0, le=100)
    auto_apply_quality_threshold: int = Field(default=80, ge=0, le=100)
    review_required_match_floor: int = Field(default=75, ge=0, le=100)

    harban_website: str = Field(default="https://harban-ai-labs.vercel.app/")
    harban_enabled: bool = Field(default=True)
    harban_client_score_threshold: int = Field(default=70, ge=0, le=100)

    outreach_max_prospects_per_day: int = Field(default=10, ge=0)
    outreach_max_linkedin_per_day: int = Field(default=5, ge=0)
    outreach_max_emails_per_day: int = Field(default=10, ge=0)
    outreach_max_initial_per_contact: int = Field(default=1, ge=0)
    outreach_max_followups_per_contact: int = Field(default=1, ge=0)
    outreach_followup_day_1: int = Field(default=5, ge=0)
    outreach_followup_day_2: int = Field(default=12, ge=0)

    client_discovery_enabled: bool = Field(default=True)
    client_outreach_enabled: bool = Field(default=False)
    requires_real_contact: bool = Field(default=True)

    discovery_pilot_mode: bool = Field(default=False)
    discovery_pilot_max_per_source: int = Field(default=20, ge=0)

    http_circuit_failure_threshold: int = Field(default=5, ge=1)
    http_circuit_cooldown_seconds: int = Field(default=600, ge=0)

    otp_bypass: bool = Field(default=False)

    database_url: str = Field(default=f"sqlite:///{DATA_DIR / 'job_agent.db'}")
    redis_url: str | None = Field(default=None)

    llm_provider: str = Field(default="mock")
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)

    linkedin_enabled: bool = Field(default=False)
    indeed_enabled: bool = Field(default=False)
    naukri_enabled: bool = Field(default=False)
    glassdoor_enabled: bool = Field(default=False)
    wellfound_enabled: bool = Field(default=False)
    handshake_enabled: bool = Field(default=False)
    instahyre_enabled: bool = Field(default=False)
    hirist_enabled: bool = Field(default=False)
    foundit_enabled: bool = Field(default=False)
    internshala_enabled: bool = Field(default=False)
    remoteok_enabled: bool = Field(default=False)
    weworkremotely_enabled: bool = Field(default=False)
    cutshort_enabled: bool = Field(default=False)
    google_search_enabled: bool = Field(default=False)
    hackernews_enabled: bool = Field(default=False)
    ycombinator_enabled: bool = Field(default=False)
    hn_jobs_enabled: bool = Field(default=False)
    company_careers_enabled: bool = Field(default=False)
    outlier_enabled: bool = Field(default=False)
    surge_ai_enabled: bool = Field(default=False)
    telus_digital_ai_enabled: bool = Field(default=False)

    browser_automation_enabled: bool = Field(default=False)
    playwright_headless: bool = Field(default=False)
    playwright_user_data_dir: str = Field(default="./browser")

    email_enabled: bool = Field(default=False)
    email_provider: str = Field(default="gmail")
    email_oauth_client_id: str | None = Field(default=None)
    email_oauth_client_secret: str | None = Field(default=None)
    email_oauth_redirect_uri: str = Field(default="http://localhost:8000/oauth/callback")
    email_sender_address: str | None = Field(default=None)
    email_draft_only: bool = Field(default=True)

    scheduler_enabled: bool = Field(default=False)
    schedule_morning_ist: str = Field(default="09:00")
    schedule_evening_ist: str = Field(default="18:00")
    schedule_night_ist: str = Field(default="22:00")

    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)
    scoring_thresholds: ScoringThresholds = Field(default_factory=ScoringThresholds)

    # ---- User-facing identifiers / preferences (optional - override profile defaults) ----
    user_linkedin_url: str | None = Field(default=None)
    user_github_url: str | None = Field(default=None)
    user_portfolio_url: str | None = Field(default=None)
    user_notice_period_weeks: int | None = Field(default=None)
    user_earliest_start: str | None = Field(default=None)
    user_salary_min_usd_hourly: int | None = Field(default=None)
    user_salary_min_inr_monthly: int | None = Field(default=None)

    data_dir: Path = Field(default=DATA_DIR)
    cache_dir: Path = Field(default=DATA_DIR / "cache")
    logs_dir: Path = Field(default=DATA_DIR / "logs")
    resumes_dir: Path = Field(default=REPO_ROOT / "resumes")
    generated_resumes_dir: Path = Field(default=DATA_DIR / "resumes_generated")

    @field_validator("auto_submit", "auto_email", "auto_message", "captcha_bypass", "mfa_bypass", "rate_limit_bypass")
    @classmethod
    def _enforce_safety_defaults(cls, v: bool, info) -> bool:
        return bool(v)

    @field_validator("database_url")
    @classmethod
    def _resolve_relative_sqlite(cls, v: str) -> str:
        if v.startswith("sqlite:///") and "./" in v:
            relative = v.replace("sqlite:///", "", 1)
            if not relative.startswith("/"):
                abs_path = (REPO_ROOT / relative.lstrip("./")).resolve()
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite:///{abs_path}"
        return v

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.cache_dir, self.logs_dir, self.resumes_dir, self.generated_resumes_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
