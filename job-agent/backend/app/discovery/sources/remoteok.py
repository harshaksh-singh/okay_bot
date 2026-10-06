from __future__ import annotations

from datetime import datetime, timezone

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.discovery.http_client import HttpClient, get_http_client
from app.discovery.sources.greenhouse import (
    _clean_html,
    _detect_employment_type,
    _detect_shift,
    _parse_posted_at,
    _parse_salary,
)
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, JobSource, RemotePolicy
from app.schemas.job import SalaryRange

log = get_logger("source.remoteok")


class RemoteOkSource(BaseSource):
    source_id = JobSource.REMOTEOK
    requires_browser = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 10

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or get_http_client()

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().remoteok_enabled

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        try:
            resp = self.client.get("https://remoteok.com/api")
            if resp is None:
                r.errors.append("remoteok: request failed")
                return r
            if resp.status_code != 200:
                r.errors.append(f"remoteok: HTTP {resp.status_code}")
                return r
            payload = resp.json()
        except Exception as e:
            r.errors.append(f"remoteok: {e!r}")
            return r

        if not isinstance(payload, list) or not payload:
            return r

        for raw in payload[1:]:
            try:
                job = self._parse_job(raw)
                if job:
                    r.jobs.append(job)
            except Exception as e:
                log.warning("remoteok.parse_error", error=str(e), id=raw.get("id"))

        if context.limit:
            r.jobs = r.jobs[: context.limit]
        r.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.info("remoteok.discovered", count=len(r.jobs))
        return r

    def _parse_job(self, raw: dict) -> Job | None:
        if not raw or not raw.get("position") or not raw.get("company"):
            return None
        title = raw["position"].strip()
        company = raw["company"].strip()
        location = raw.get("location") or "Remote"
        description = _clean_html(raw.get("description", ""))[:5000]
        emp = _detect_employment_type(title, description)
        shift = _detect_shift(title, description)

        salary = _parse_salary(description)
        if not salary.raw and (raw.get("salary_min") or raw.get("salary_max")):
            try:
                salary = SalaryRange(
                    min_value=float(raw.get("salary_min") or 0) or None,
                    max_value=float(raw.get("salary_max") or 0) or None,
                    currency="USD",
                    unit="year",
                    raw=f"${raw.get('salary_min', '?')}-${raw.get('salary_max', '?')}/year",
                )
            except (ValueError, TypeError):
                pass

        posted_at = _parse_posted_at(raw.get("date"))

        create = JobCreate(
            source=JobSource.REMOTEOK,
            source_job_id=str(raw.get("id") or raw.get("slug")),
            company=company,
            title=title,
            location=location,
            remote=RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
            employment_type=emp,
            shift=shift,
            salary=salary,
            description=description,
            application_url=raw.get("apply_url") or raw.get("url"),
            application_method=ApplicationMethod.PLATFORM_APPLY,
            posted_at=posted_at,
        )
        return Job.from_create(create)
