from __future__ import annotations

from datetime import datetime

from app.data.mock_jobs import build_mock_jobs
from app.discovery.base import BaseSource, SourceContext, SourceResult
from app.schemas.enums import EmploymentType, JobSource, RemotePolicy


class MockSource(BaseSource):
    source_id = JobSource.MOCK
    requires_browser = False
    requires_credentials = False
    requires_api_key = False
    enabled_by_default = True

    def is_enabled(self) -> bool:
        return True

    def discover(self, context: SourceContext) -> SourceResult:
        result = SourceResult(source=self.source_id)
        jobs = build_mock_jobs()

        if context.remote_only:
            jobs = [j for j in jobs if j.remote in {
                RemotePolicy.REMOTE_LOCAL, RemotePolicy.REMOTE_COUNTRY,
                RemotePolicy.REMOTE_GLOBAL, RemotePolicy.REMOTE_GLOBAL_UNVERIFIED,
            }]

        if context.employment_types:
            allowed = {e.lower() for e in context.employment_types}
            jobs = [j for j in jobs if j.employment_type.value in allowed]

        if context.locations:
            needles = [l.lower() for l in context.locations]
            jobs = [j for j in jobs if any(n in (j.location or "").lower() for n in needles) or j.is_remote()]

        if context.queries:
            tokens = [q.lower() for q in context.queries]
            jobs = [
                j for j in jobs
                if any(
                    t in (j.title or "").lower() or t in (j.description or "").lower()
                    for t in tokens
                )
            ]

        if context.limit:
            jobs = jobs[: context.limit]

        result.jobs = jobs
        result.finished_at = datetime.utcnow()
        return result
