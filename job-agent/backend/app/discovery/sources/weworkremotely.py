from __future__ import annotations

from datetime import datetime, timezone

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
from app.schemas.enums import ApplicationMethod, JobSource, RemotePolicy

log = get_logger("source.wwr")


_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
]


class WeWorkRemotelySource(BaseSource):
    source_id = JobSource.WEWORKREMOTELY
    requires_browser = False
    requires_api_key = False
    enabled_by_default = False
    rate_limit_per_minute = 10

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or get_http_client()

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().weworkremotely_enabled

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        try:
            import feedparser
        except ImportError:
            r.errors.append("weworkremotely: feedparser not installed")
            return r

        for feed_url in _FEEDS:
            try:
                resp = self.client.get(feed_url)
                if resp is None or resp.status_code != 200:
                    r.errors.append(f"wwr: {feed_url} failed")
                    continue
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    try:
                        job = self._parse_entry(entry)
                        if job:
                            r.jobs.append(job)
                    except Exception as e:
                        log.warning("wwr.parse_error", error=str(e), link=entry.get("link"))
            except Exception as e:
                r.errors.append(f"wwr[{feed_url}]: {e!r}")

        if context.limit:
            r.jobs = r.jobs[: context.limit]
        r.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.info("wwr.discovered", count=len(r.jobs))
        return r

    def _parse_entry(self, entry) -> Job | None:
        title_raw = (entry.get("title") or "").strip()
        if not title_raw:
            return None
        if ":" in title_raw:
            company, _, title = title_raw.partition(":")
            company = company.strip()
            title = title.strip()
        else:
            company = "Unknown"
            title = title_raw

        description_html = entry.get("summary") or entry.get("description") or ""
        description = _clean_html(description_html)[:5000]
        location = "Remote"
        remote = _detect_remote(title, location, description) or RemotePolicy.REMOTE_GLOBAL_UNVERIFIED
        emp = _detect_employment_type(title, description)
        shift = _detect_shift(title, description)
        salary = _parse_salary(description)
        posted_at = _parse_posted_at(entry.get("published") or entry.get("pubDate"))

        create = JobCreate(
            source=JobSource.WEWORKREMOTELY,
            source_job_id=entry.get("id") or entry.get("link"),
            company=company,
            title=title,
            location=location,
            remote=remote,
            employment_type=emp,
            shift=shift,
            salary=salary,
            description=description,
            application_url=entry.get("link"),
            application_method=ApplicationMethod.COMPANY_SITE,
            posted_at=posted_at,
        )
        return Job.from_create(create)
