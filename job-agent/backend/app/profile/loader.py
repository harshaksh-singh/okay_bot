from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.profile.data import build_default_profile
from app.profile.schema import Profile


def load_profile(resume_root: Path | None = None) -> Profile:
    s = get_settings()
    root = resume_root or s.resumes_dir
    p = build_default_profile(resume_root=root)

    if s.user_linkedin_url:
        p.linkedin_url = s.user_linkedin_url
    if s.user_github_url:
        p.github_url = s.user_github_url
    if s.user_portfolio_url:
        p.portfolio_url = s.user_portfolio_url
    if s.user_notice_period_weeks is not None:
        p.availability.notice_period_weeks = s.user_notice_period_weeks
    if s.user_earliest_start:
        from datetime import date as _date
        try:
            p.availability.earliest_start = _date.fromisoformat(s.user_earliest_start)
        except Exception:
            pass
    if s.user_salary_min_usd_hourly is not None:
        p.salary_expectation_min_usd_hourly = s.user_salary_min_usd_hourly
    if s.user_salary_min_inr_monthly is not None:
        p.salary_expectation_min_inr_monthly = s.user_salary_min_inr_monthly
    return p


@lru_cache(maxsize=1)
def get_profile() -> Profile:
    return load_profile()
