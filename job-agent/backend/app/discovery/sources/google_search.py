from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.discovery.http_client import HttpClient, get_http_client
from app.observability import get_logger
from app.schemas import Job, JobCreate
from app.schemas.enums import ApplicationMethod, EmploymentType, JobSource, RemotePolicy, ShiftType

log = get_logger("source.google_cse")


_SITE_SCOPES = [
    "site:boards.greenhouse.io",
    "site:jobs.lever.co",
    "site:jobs.ashbyhq.com",
    "site:careers.google.com",
    "site:apply.workable.com",
    "site:jobs.smartrecruiters.com",
    "site:remoteok.com",
    "site:weworkremotely.com",
]


class GoogleProgrammableSearchSource(BaseSource):
    source_id = JobSource.GOOGLE_SEARCH
    requires_browser = False
    requires_api_key = True
    enabled_by_default = False
    rate_limit_per_minute = 10

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or get_http_client()
        self.api_key = os.environ.get("GOOGLE_CSE_API_KEY")
        self.engine_id = os.environ.get("GOOGLE_CSE_ENGINE_ID")

    def is_enabled(self) -> bool:
        from app.config import get_settings
        return get_settings().google_search_enabled and bool(self.api_key and self.engine_id)

    def _build_queries(self, context: SourceContext) -> list[str]:
        base_terms = context.queries or [
            "AI Engineer", "Machine Learning Engineer", "LLM Engineer", "Applied AI Engineer",
            "Python Developer", "Backend Engineer",
        ]
        locations = context.locations or ["Gurugram", "Noida", "India Remote"]
        queries: list[str] = []
        for term in base_terms[:5]:
            for site in _SITE_SCOPES[:3]:
                for loc in locations[:3]:
                    queries.append(f'"{term}" {loc} {site}')
        return queries[:30]

    def discover(self, context: SourceContext) -> SourceResult:
        r = SourceResult(source=self.source_id)
        if not self.api_key or not self.engine_id:
            r.errors.append(
                "google_search: GOOGLE_CSE_API_KEY and GOOGLE_CSE_ENGINE_ID required. "
                "Create a Programmable Search Engine at https://programmablesearchengine.google.com "
                "and an API key at https://console.cloud.google.com/apis/credentials."
            )
            return r

        for q in self._build_queries(context):
            try:
                resp = self.client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={"key": self.api_key, "cx": self.engine_id, "q": q, "num": 10},
                )
                if resp is None or resp.status_code != 200:
                    continue
                payload = resp.json()
                for item in payload.get("items", []):
                    try:
                        job = self._parse_item(item, source_query=q)
                        if job:
                            r.jobs.append(job)
                    except Exception as e:
                        log.warning("google_search.parse_error", error=str(e))
            except Exception as e:
                r.errors.append(f"google_search[{q[:40]}]: {e!r}")

        if context.limit:
            r.jobs = r.jobs[: context.limit]
        r.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        log.info("google_search.discovered", count=len(r.jobs))
        return r

    def _parse_item(self, item: dict[str, Any], source_query: str) -> Job | None:
        title_raw = item.get("title", "").strip()
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        if not title_raw or not link:
            return None

        company = "unknown"
        if "greenhouse.io" in link:
            parts = link.split("/")
            if "greenhouse.io" in link and len(parts) > 3:
                company = parts[3].replace("-", " ").title()
        elif "lever.co" in link:
            parts = link.split("/")
            if len(parts) > 3:
                company = parts[3].replace("-", " ").title()
        elif "ashbyhq.com" in link:
            parts = link.split("/")
            if len(parts) > 4:
                company = parts[4].replace("-", " ").title()

        combined = f"{title_raw} {snippet}".lower()
        remote = RemotePolicy.REMOTE_GLOBAL_UNVERIFIED if "remote" in combined else RemotePolicy.UNKNOWN
        if "hybrid" in combined:
            remote = RemotePolicy.HYBRID

        emp = EmploymentType.PART_TIME if "part-time" in combined or "part time" in combined else EmploymentType.FULL_TIME
        if "contract" in combined:
            emp = EmploymentType.CONTRACT

        create = JobCreate(
            source=JobSource.GOOGLE_SEARCH,
            source_job_id=link,
            company=company,
            title=title_raw,
            location="",
            remote=remote,
            employment_type=emp,
            shift=ShiftType.UNKNOWN,
            description=snippet,
            application_url=link,
            application_method=ApplicationMethod.COMPANY_SITE,
        )
        return Job.from_create(create)
