from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.discovery.http_client import HttpClient, get_http_client
from app.discovery.sources.greenhouse import (
    _clean_html,
    _detect_employment_type,
    _detect_remote,
    _detect_shift,
    _parse_posted_at,
    _parse_salary,
)
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, JobSource

log = get_logger("source.lever")


LEVER_COMPANIES: dict[str, dict[str, Any]] = {
    "mistral": {"display": "Mistral AI"},
    "nvidia": {"display": "NVIDIA"},
    "palantir": {"display": "Palantir"},
    "ramp": {"display": "Ramp"},
    "stability": {"display": "Stability AI"},
    "zoox": {"display": "Zoox"},
}


class LeverCompanySource(BaseSource):
    source_id = JobSource.COMPANY_CAREERS
    requires_browser = False
    requires_credentials = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 20

    def __init__(self, company_slug: str, display_name: str | None = None, client: HttpClient | None = None) -> None:
        self.company_slug = company_slug
        self.display_name = display_name or LEVER_COMPANIES.get(company_slug, {}).get("display", company_slug)
        self.client = client or get_http_client()

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().company_careers_enabled

    def _url(self) -> str:
        return f"https://api.lever.co/v0/postings/{self.company_slug}?mode=json"

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        try:
            resp = self.client.get(self._url())
            if resp is None:
                r.errors.append(f"lever[{self.company_slug}]: request failed")
                return r
            if resp.status_code != 200:
                r.errors.append(f"lever[{self.company_slug}]: HTTP {resp.status_code}")
                return r
            payload = resp.json()
        except Exception as e:
            r.errors.append(f"lever[{self.company_slug}]: {e!r}")
            return r

        if not isinstance(payload, list):
            r.errors.append(f"lever[{self.company_slug}]: unexpected payload shape")
            return r

        for raw in payload:
            try:
                job = self._parse_job(raw)
                if job:
                    r.jobs.append(job)
            except Exception as e:
                log.warning("lever.parse_error", error=str(e), id=raw.get("id"))

        if context.limit:
            r.jobs = r.jobs[: context.limit]
        r.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.info("lever.discovered", company=self.company_slug, count=len(r.jobs))
        return r

    def _parse_job(self, raw: dict) -> Job | None:
        if not raw or not raw.get("text"):
            return None
        title = raw["text"].strip()
        categories = raw.get("categories", {}) or {}
        location = categories.get("location", "") or ""
        description_html = (raw.get("descriptionPlain") or raw.get("description") or "")[:8000]
        description = _clean_html(description_html)[:5000]

        emp_type = _detect_employment_type(title, description)
        remote = _detect_remote(title, location, description)
        shift = _detect_shift(title, description)
        salary = _parse_salary(description)
        posted_at = _parse_posted_at(raw.get("createdAt"))

        create = JobCreate(
            source=JobSource.COMPANY_CAREERS,
            source_job_id=str(raw.get("id")),
            company=self.display_name,
            title=title,
            location=location,
            remote=remote,
            employment_type=emp_type,
            shift=shift,
            salary=salary,
            description=description,
            application_url=raw.get("hostedUrl"),
            application_method=ApplicationMethod.COMPANY_SITE,
            posted_at=posted_at,
        )
        return Job.from_create(create)


def build_all_lever_sources(client: HttpClient | None = None) -> list[LeverCompanySource]:
    return [LeverCompanySource(slug, meta["display"], client=client) for slug, meta in LEVER_COMPANIES.items()]
