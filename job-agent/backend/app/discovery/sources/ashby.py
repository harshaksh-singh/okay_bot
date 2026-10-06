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
from app.schemas.enums import ApplicationMethod, EmploymentType, JobSource, RemotePolicy
from app.schemas.job import SalaryRange

log = get_logger("source.ashby")


ASHBY_ORGS: dict[str, dict[str, Any]] = {
    "cursor": {"display": "Cursor"},
    "fireworks": {"display": "Fireworks AI"},
    "replit": {"display": "Replit"},
    "anthropic": {"display": "Anthropic (Ashby)"},
    "scale": {"display": "Scale AI (Ashby)"},
    "glean": {"display": "Glean"},
    "elevenlabs": {"display": "ElevenLabs"},
    "runway": {"display": "Runway"},
}


_EMP_TYPE_MAP = {
    "FULL_TIME": EmploymentType.FULL_TIME,
    "PART_TIME": EmploymentType.PART_TIME,
    "CONTRACTOR": EmploymentType.CONTRACT,
    "INTERN": EmploymentType.INTERNSHIP,
    "TEMPORARY": EmploymentType.TEMPORARY,
}

_WORKPLACE_MAP = {
    "ON_SITE": RemotePolicy.ONSITE,
    "HYBRID": RemotePolicy.HYBRID,
    "REMOTE": RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
}


class AshbyOrgSource(BaseSource):
    source_id = JobSource.COMPANY_CAREERS
    requires_browser = False
    requires_credentials = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 20

    def __init__(self, org: str, display_name: str | None = None, client: HttpClient | None = None) -> None:
        self.org = org
        self.display_name = display_name or ASHBY_ORGS.get(org, {}).get("display", org)
        self.client = client or get_http_client()

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().company_careers_enabled

    def _url(self) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{self.org}?includeCompensation=true"

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        try:
            resp = self.client.get(self._url())
            if resp is None:
                r.errors.append(f"ashby[{self.org}]: request failed")
                return r
            if resp.status_code != 200:
                r.errors.append(f"ashby[{self.org}]: HTTP {resp.status_code}")
                return r
            payload = resp.json()
        except Exception as e:
            r.errors.append(f"ashby[{self.org}]: {e!r}")
            return r

        jobs_payload = payload.get("jobs", []) if isinstance(payload, dict) else payload if isinstance(payload, list) else []
        for raw in jobs_payload:
            try:
                job = self._parse_job(raw)
                if job:
                    r.jobs.append(job)
            except Exception as e:
                log.warning("ashby.parse_error", error=str(e), id=raw.get("id"))

        if context.limit:
            r.jobs = r.jobs[: context.limit]
        r.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.info("ashby.discovered", org=self.org, count=len(r.jobs))
        return r

    def _parse_job(self, raw: dict) -> Job | None:
        if not raw or not raw.get("title"):
            return None
        title = raw["title"].strip()
        location = raw.get("locationName") or raw.get("primaryLocation") or ""
        description_html = raw.get("descriptionHtml") or raw.get("descriptionPlain") or ""
        description = _clean_html(description_html)[:5000]

        emp_raw = (raw.get("employmentType") or "").upper()
        emp = _EMP_TYPE_MAP.get(emp_raw) or _detect_employment_type(title, description)

        wp_raw = (raw.get("workplaceType") or "").upper()
        remote = _WORKPLACE_MAP.get(wp_raw) or _detect_remote(title, location, description)

        shift = _detect_shift(title, description)
        salary = _parse_salary(description)
        comp = raw.get("compensation") or {}
        if comp and isinstance(comp, dict):
            summary = comp.get("compensationTierSummary")
            if summary and not salary.raw:
                salary = _parse_salary(summary) or salary
                if not salary.raw:
                    salary = SalaryRange(raw=str(summary))
        posted_at = _parse_posted_at(raw.get("publishedDate") or raw.get("publishedAt"))

        create = JobCreate(
            source=JobSource.COMPANY_CAREERS,
            source_job_id=str(raw.get("id")),
            company=self.display_name,
            title=title,
            location=location,
            remote=remote,
            employment_type=emp,
            shift=shift,
            salary=salary,
            description=description,
            application_url=raw.get("jobUrl") or raw.get("applyUrl"),
            application_method=ApplicationMethod.COMPANY_SITE,
            posted_at=posted_at,
        )
        return Job.from_create(create)


def build_all_ashby_sources(client: HttpClient | None = None) -> list[AshbyOrgSource]:
    return [AshbyOrgSource(org, meta["display"], client=client) for org, meta in ASHBY_ORGS.items()]
